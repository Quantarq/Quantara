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
from opentelemetry import trace

from .cache import get_cached_or_fetch
from .constants import MULTIPLIER_POWER, TokenParams
from web_app.utils.logger import get_logger

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

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
            with tracer.start_as_current_span("stellar.horizon.get_account") as span:
                span.set_attribute("stellar.account", holder_address)
                span.set_attribute("stellar.asset", asset_code)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        span.set_attribute("http.status_code", response.status)
                        if response.status == 404:
                            logger.info("horizon_account_not_found", account=holder_address)
                            return "0"
                        if response.status != 200:
                            logger.warning("horizon_unexpected_status", status=response.status, url=url)
                            return "0"
                        account = await response.json()
        except aiohttp.ClientError as exc:
            logger.error("horizon_network_error", account=holder_address, error=str(exc))
            return "0"
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("horizon_data_error", account=holder_address, error=str(exc))
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

    async def _get_account_data(self, holder_address: str) -> dict | None:
        """
        Fetch full account data from Horizon.
        """
        if not holder_address:
            return None
        url = f"{self.horizon_url.rstrip('/')}/accounts/{holder_address}"
        try:
            with tracer.start_as_current_span("stellar.horizon.get_account_data") as span:
                span.set_attribute("stellar.account", holder_address)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        span.set_attribute("http.status_code", response.status)
                        if response.status == 404:
                            logger.info(
                                "Account %s not found on Stellar network",
                                holder_address,
                            )
                            return None
                        if response.status != 200:
                            logger.warning(
                                "Horizon returned %d for %s", response.status, url
                            )
                            return None
                        return await response.json()
        except aiohttp.ClientError as exc:
            logger.error("Network error fetching account %s: %s", holder_address, exc)
            return None
        except (ValueError, KeyError, TypeError) as exc:
            logger.error("Data error fetching account %s: %s", holder_address, exc)
            return None

    async def get_token_balances(
        self, holder_address: str
    ) -> dict[str, str]:
        """
        Get all supported token balances for an account.

        :param holder_address: Stellar account public key.
        :return: dict mapping token symbols to balance strings.
        """
        balances: dict[str, str] = {
            token.name: "0" for token in TokenParams.tokens()
        }
        account = await self._get_account_data(holder_address)
        if not account:
            return balances

        for balance in account.get("balances", []):
            asset_type = balance.get("asset_type", "")
            asset_code = balance.get("asset_code", "").lower()
            asset_issuer = balance.get("asset_issuer", "")

            for token in TokenParams.tokens():
                target_code = token.asset_code.lower()
                target_issuer = getattr(token, "asset_issuer", None)

                if target_code == "native" or target_code == "xlm":
                    if asset_type == "native":
                        balances[token.name] = str(balance.get("balance", "0"))
                elif asset_code == target_code:
                    if target_issuer is None or asset_issuer == target_issuer:
                        balances[token.name] = str(balance.get("balance", "0"))

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
            with tracer.start_as_current_span("stellar.soroban.get_contract_data") as span:
                span.set_attribute("stellar.contract_id", contract_id)
                async with aiohttp.ClientSession() as session:
                    async with session.post(rpc_url, json=payload) as response:
                        span.set_attribute("http.status_code", response.status)
                        if response.status == 200:
                            data = await response.json()
                            if "error" in data:
                                logger.warning("rpc_contract_error", contract_id=contract_id, error=data["error"])
                                return False
                            return "result" in data
                        logger.warning("rpc_unexpected_status", status=response.status, contract_id=contract_id)
                        return False
        except aiohttp.ClientError as e:
            logger.error("rpc_network_error", contract_id=contract_id, error=str(e))
            return False
        except (ValueError, KeyError, TypeError) as e:
            logger.error("rpc_data_error", contract_id=contract_id, error=str(e))
            return False

    async def fetch_portfolio(self, contract_address: str) -> dict:
        """
        Fetches the token balances held by a contract/account.

        :param contract_address: The account or contract ID to query.
        :return: dict mapping token keys to balance info.
        """
        with tracer.start_as_current_span("stellar.fetch_portfolio") as span:
            span.set_attribute("stellar.account", contract_address)
            results = {}
            for token in TokenParams.tokens():
                results[token.name] = {
                    "balance": "0",
                    "decimals": token.decimals,
                }

            account = await self._get_account_data(contract_address)
            if not account:
                return results

            for balance in account.get("balances", []):
                asset_type = balance.get("asset_type", "")
                asset_code = balance.get("asset_code", "").lower()
                asset_issuer = balance.get("asset_issuer", "")

                for token in TokenParams.tokens():
                    target_code = token.asset_code.lower()
                    target_issuer = getattr(token, "asset_issuer", None)

                    if target_code == "native" or target_code == "xlm":
                        if asset_type == "native":
                            results[token.name]["balance"] = str(
                                balance.get("balance", "0")
                            )
                    elif asset_code == target_code:
                        if target_issuer is None or asset_issuer == target_issuer:
                            results[token.name]["balance"] = str(
                                balance.get("balance", "0")
                            )
            return results


if __name__ == "__main__":
    # Split the long dummy address to comply with 100-char linting limits
    dummy_address = (
        "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2"
        "X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2"
    )
    res = asyncio.run(StellarClient().fetch_portfolio(dummy_address))
    print(res)