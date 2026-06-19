"""
This module handles the Stellar blockchain calls using aiohttp for Horizon REST API
and the Quantara Soroban adapters.

NOTE: We use aiohttp directly instead of stellar_sdk.Server because the Python
stellar-sdk Server class is synchronous and does not support async/await.
For production, consider wrapping in asyncio.to_thread() or using a dedicated
async client.
"""

import asyncio
import logging
import os
from decimal import Decimal

import aiohttp

from .constants import MULTIPLIER_POWER, TokenParams

logger = logging.getLogger(__name__)

# Base64-encoded "wasm_hash" key for Soroban getContractData RPC calls
_SOROBAN_WASM_HASH_KEY = "dHJ1c3RlZAB3YXNoX2hhc2g="


class StellarClient:
    """
    A client to interact with the Stellar network via Horizon REST API and
    Soroban RPC.  Replaces the former Starknet-specific client.
    """

    SLEEP_TIME = 10

    def __init__(self):
        """
        Initializes the Stellar client with Horizon and Soroban RPC endpoints.
        """
        self.horizon_url = os.getenv(
            "STELLAR_HORIZON_URL", "https://horizon-testnet.stellar.org"
        )
        self.rpc_url = os.getenv(
            "STELLAR_SOROBAN_RPC_URL",
            "https://soroban-testnet.stellar.org",
        )
        self.network_passphrase = os.getenv(
            "STELLAR_NETWORK_PASSPHRASE",
            "Test SDF Network ; September 2015",
        )

        if not self.horizon_url:
            raise ValueError("STELLAR_HORIZON_URL environment variable is not set")

    # ------------------------------------------------------------------ #
    #  Balance queries via Horizon REST API (async with aiohttp)
    # ------------------------------------------------------------------ #

    async def get_balance(
        self,
        asset_code: str,
        holder_address: str,
        asset_issuer: str | None = None,
    ) -> str:
        """
        Fetch the balance of a Stellar asset for a given account via Horizon.

        :param asset_code: Asset code (e.g. "XLM", "USDC", or "native").
        :param holder_address: Stellar account public key (G…).
        :param asset_issuer: Issuer address for non-native assets.
        :return: Balance as a string, or "0" if not found.
        """
        if not holder_address or not asset_code:
            return "0"
        url = f"{self.horizon_url.rstrip('/')}/accounts/{holder_address}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 404:
                        logger.info(
                            "Account %s not found on Stellar network",
                            holder_address,
                        )
                        return "0"
                    if response.status != 200:
                        logger.warning(
                            "Horizon returned %d for %s", response.status, url
                        )
                        return "0"
                    account = await response.json()
        except aiohttp.ClientError as exc:
            logger.error("Network error fetching account %s: %s", holder_address, exc)
            return "0"
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("Data error fetching account %s: %s", holder_address, exc)
            return "0"

        code = asset_code.lower()
        for balance in account.get("balances", []):
            asset_type = balance.get("asset_type", "")
            if code == "native" or code == "xlm":
                if asset_type == "native":
                    return str(balance.get("balance", "0"))
            elif (
                balance.get("asset_code", "").lower() == code
                and (
                    asset_issuer is None
                    or balance.get("asset_issuer", "") == asset_issuer
                )
            ):
                return str(balance.get("balance", "0"))

        return "0"

    async def get_token_balances(
        self, holder_address: str
    ) -> dict[str, str]:
        """
        Get all supported token balances for an account.

        :param holder_address: Stellar account public key.
        :return: dict mapping token symbols to balance strings.
        """
        balances: dict[str, str] = {}
        for token in TokenParams.tokens():
            try:
                bal = await self.get_balance(
                    asset_code=token.asset_code,
                    holder_address=holder_address,
                    asset_issuer=getattr(token, "asset_issuer", None),
                )
                balances[token.name] = bal
            except (aiohttp.ClientError, ValueError, KeyError) as exc:
                logger.info(
                    "Failed to get balance for %s: %s", token.name, exc
                )
        return balances

    # ------------------------------------------------------------------ #
    #  Loop liquidity / repay data stubs (pool-agnostic for Soroban)
    # ------------------------------------------------------------------ #

    async def get_loop_liquidity_data(
        self,
        deposit_token: str,
        amount: int,
        multiplier: Decimal,
        wallet_id: str,
        borrowing_token: str,
    ) -> dict:
        """
        Prepare data for the Quantara loop_liquidity Soroban call.

        :param deposit_token: The token address/symbol being deposited.
        :param amount: The deposit amount (raw units).
        :param multiplier: The leverage multiplier.
        :param wallet_id: The user's Stellar public key.
        :param borrowing_token: The token address/symbol to borrow.
        :return: A dictionary with deposit_data.
        """
        deposit_data = {
            "token": deposit_token,
            "amount": str(amount),
            "multiplier": str(int(multiplier * 10)),
            "borrow_portion_percent": MULTIPLIER_POWER,
        }

        return {
            "deposit_data": deposit_data,
            "caller": wallet_id,
        }

    async def get_repay_data(
        self, deposit_token: str, borrowing_token: str
    ) -> dict:
        """
        Prepare data for the Quantara close_position Soroban call.

        :param deposit_token: The token address being supplied.
        :param borrowing_token: The token address being repaid.
        :return: A dictionary with supply/debt token addresses.
        """
        return {
            "supply_token": deposit_token,
            "debt_token": borrowing_token,
            "borrow_portion_percent": MULTIPLIER_POWER,
        }

    # ------------------------------------------------------------------ #
    #  Soroban contract helpers (async with aiohttp)
    # ------------------------------------------------------------------ #

    async def is_contract_deployed(self, contract_id: str) -> bool:
        """
        Check whether a Soroban contract is deployed on the network.

        :param contract_id: The Soroban contract ID (C… string).
        :return: True if the contract is deployed.
        """
        if not contract_id:
            return False
        try:
            rpc_url = f"{self.rpc_url.rstrip('/')}/transactions"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getContractData",
                "params": {
                    "contractId": contract_id,
                    "key": _SOROBAN_WASM_HASH_KEY,  # base64 "wasm_hash"
                },
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(rpc_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "error" in data:
                            logger.warning(
                                "RPC error checking contract %s: %s",
                                contract_id,
                                data["error"],
                            )
                            return False
                        return "result" in data
                    logger.warning(
                        "RPC returned %d checking contract %s",
                        response.status,
                        contract_id,
                    )
                    return False
        except aiohttp.ClientError as e:
            logger.error("Network error checking contract %s: %s", contract_id, e)
            return False
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Data error checking contract %s: %s", contract_id, e)
            return False

    async def fetch_portfolio(self, contract_address: str) -> dict:
        """
        Fetches the token balances held by a contract/account.

        :param contract_address: The account or contract ID to query.
        :return: dict mapping token keys to balance info.
        """
        results = {}
        for token in TokenParams.tokens():
            try:
                balance = await self.get_balance(
                    asset_code=token.asset_code,
                    holder_address=contract_address,
                )
                results[token.name] = {
                    "balance": balance,
                    "decimals": token.decimals,
                }
            except (aiohttp.ClientError, ValueError, KeyError) as exc:
                logger.info(
                    "Failed to get portfolio balance for %s: %s",
                    token.name,
                    exc,
                )
        return results


if __name__ == "__main__":
    res = asyncio.run(
        StellarClient().fetch_portfolio(
            "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2"
        )
    )
    print(res)
