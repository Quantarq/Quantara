"""
This module contains the dashboard mixin class for the Stellar-based Quantara protocol.

Handles price fetching from external APIs, wallet balance queries,
and position value calculations for the dashboard view.
"""

import logging
from decimal import Decimal
from typing import Dict
from uuid import UUID

import aiohttp

from web_app.contract_tools.api_request import APIRequest
from web_app.contract_tools.blockchain_call import StellarClient
from web_app.contract_tools.constants import MULTIPLIER_POWER, TokenParams
from web_app.db.crud.position import PositionDBConnector

logger = logging.getLogger(__name__)
position_db_connector = PositionDBConnector()

# AVNU price endpoint (Stellar-compatible market data API)
AVNU_PRICE_URL = "https://starknet.impulse.avnu.fi/v1/tokens/short"


class DashboardMixin:
    """
    Mixin class for dashboard related methods using Stellar/Soroban primitives.
    """

    @classmethod
    async def get_current_prices(cls) -> Dict[str, Decimal]:
        """
        Fetch current token prices from AVNU API.

        Queries the AVNU token-short endpoint to retrieve latest market
        prices for all supported tokens. Maps addresses to token symbols
        for Quantara's internal representation.

        :return: Dictionary mapping token symbols to their current prices as Decimal.
        :raises: None (returns empty dict on any failure)
        """
        prices = {}
        try:
            response = await APIRequest(base_url=AVNU_PRICE_URL).fetch("")
            if not response:
                return prices

            for token_data in response:
                address = token_data.get("address")
                current_price = token_data.get("currentPrice")
                try:
                    if address and current_price is not None:
                        # Map token addresses to symbols
                        symbol = token_data.get("symbol", "")
                        if symbol.upper() in ("ETH", "USDC", "XLM", "STRK"):
                            prices[symbol.upper()] = Decimal(str(current_price))
                        elif "eth" in symbol.lower():
                            prices["ETH"] = Decimal(str(current_price))
                        elif "usdc" in symbol.lower():
                            prices["USDC"] = Decimal(str(current_price))
                except (AttributeError, TypeError, ValueError) as e:
                    logger.debug(f"Error parsing price for {address}: {str(e)}")

            return prices
        except (aiohttp.ClientError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error fetching current prices: {e}")
            return prices

    @classmethod
    async def get_wallet_balances(cls, holder_address: str, client: StellarClient) -> Dict[str, str]:
        """
        Get the wallet balances for the given Stellar account.

        :param holder_address: Stellar account public key (G…)
        :param client: StellarClient instance
        :return: Dictionary mapping token symbols to balance strings.
        """
        try:
            return await client.get_token_balances(holder_address)
        except (ValueError, KeyError, TypeError) as e:
            logger.error(
                "Failed to get wallet balances for %s: %s", holder_address, e
            )
            return {}

    @classmethod
    def _calculate_sum(
        cls, price: Decimal, amount: Decimal, multiplier: Decimal
    ) -> Decimal:
        """
        Calculate the sum.
        :param price: Price
        :param amount: Token amount
        :param multiplier: Position multiplier
        :return: calculated sum
        """
        try:
            return (
                price * amount * multiplier * (Decimal(100) / Decimal(MULTIPLIER_POWER))
            )
        except (TypeError, ValueError) as e:
            logger.error(f"Error calculating sum: {e}")
            return Decimal(0)

    @classmethod
    async def get_current_position_sum(cls, position: dict) -> Decimal:
        """
        Calculate the total position value including extra deposits.

        :param position: Position object containing base amount and token information
        :return: Decimal representing total position value including extra deposits
        """
        main_position = position_db_connector.get_position_by_id(position["id"])
        if not main_position:
            return Decimal(0)

        current_prices = await cls.get_current_prices()
        base_price = current_prices.get(main_position.token_symbol)
        total_sum = Decimal(0)
        if base_price:
            total_sum += cls._calculate_sum(
                base_price,
                Decimal(main_position.amount),
                Decimal(main_position.multiplier),
            )

        extra_deposits = position_db_connector.get_extra_deposits_by_position_id(
            position["id"]
        )

        for extra_deposit in extra_deposits:
            if extra_deposit.token_symbol in current_prices:
                deposit_amount = Decimal(extra_deposit.amount)
                if extra_deposit.token_symbol != main_position.token_symbol:
                    deposit_amount *= Decimal(
                        current_prices[extra_deposit.token_symbol]
                    )
                    deposit_amount /= Decimal(
                        current_prices[main_position.token_symbol]
                    )
                total_sum += deposit_amount

        return total_sum

    @classmethod
    async def get_start_position_sum(
        cls, start_price: str, amount: str, multiplier: str
    ) -> Decimal:
        """
        Calculate the start position sum.
        :param start_price: Start price
        :param amount: Token amount
        :param multiplier: Multiplier
        :return: Decimal sum
        """
        return cls._calculate_sum(
            Decimal(start_price), Decimal(amount), Decimal(multiplier)
        )

    @classmethod
    async def calculate_position_balance(cls, amount: str, multiplier: str) -> Decimal:
        """
        Calculate the position balance.
        :param amount: Position amount
        :param multiplier: Position multiplier
        :return: Position balance
        """
        return (
            Decimal(amount)
            * Decimal(multiplier)
            * (Decimal(100) / Decimal(MULTIPLIER_POWER))
        )

    @classmethod
    async def get_position_balance(cls, position_id: UUID) -> str:
        """
        Calculate the position balance.
        :param position_id: Position UUID
        :return (str): Position balance
        """
        main_position = position_db_connector.get_position_by_id(position_id)
        main_position_balance = main_position and main_position.amount or "0"
        return main_position_balance
