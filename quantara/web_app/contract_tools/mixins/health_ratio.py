"""
HealthRatioMixin is a mixin class to calculate the health ratio of a position
using the Stellar-based CollateralManager and Soroban adapters.

The health ratio indicates the safety margin of a leveraged position.
A value below 1.0 signals the position is at risk of liquidation.
"""

import asyncio
from decimal import Decimal

from web_app.contract_tools.blockchain_call import StellarClient
from web_app.contract_tools.constants import TokenParams


class HealthRatioMixin:
    """
    A mixin class to calculate the health ratio of a deposit contract
    using Stellar ecosystem data feeds.
    """

    @classmethod
    async def _get_token_prices(cls, token_symbols: set) -> dict[str, Decimal]:
        """
        Get the prices of multiple tokens from the current price feed.

        :param token_symbols: A set of token symbols.
        :return: A dictionary of token prices.
        """
        from web_app.contract_tools.mixins.dashboard import DashboardMixin

        prices = await DashboardMixin.get_current_prices()
        return {token: prices.get(token, Decimal("0")) for token in token_symbols}

    @classmethod
    async def _get_deposited_tokens(
        cls, account_address: str, client: StellarClient
    ) -> dict[str, Decimal]:
        """
        Get the deposited token balances for an account.

        :param account_address: The Stellar account public key.
        :param client: StellarClient instance.
        :return: A dictionary of token symbols to amounts.
        """
        balances = await client.get_token_balances(account_address)
        return {
            token: Decimal(balance)
            for token, balance in balances.items()
            if Decimal(balance) > 0
        }

    @classmethod
    async def _get_borrowed_token(
        cls, account_address: str
    ) -> tuple[str, int]:
        """
        Placeholder: identify borrowed token and debt amount.
        In a full Soroban integration this would query the position contract.

        :param account_address: The account address.
        :return: Tuple of (token_symbol, debt_raw) – defaults to ("USDC", 0).
        """
        # NOTE: Full Soroban integration pending — once position contracts
        #       are deployed, query the contract's ledger entry for current
        #       debt token and amount instead of returning defaults.
        return "USDC", 0

    @classmethod
    async def get_health_ratio_and_tvl(cls, account_address: str, client: StellarClient) -> tuple:
        """
        Calculate the health ratio of a position.

        :param account_address: The address of the account/contract.
        :param client: StellarClient instance.
        :return: Tuple of (health_factor, ltv) as strings.
        """
        borrowed_token, debt_raw = await cls._get_borrowed_token(account_address)
        deposits = await cls._get_deposited_tokens(account_address, client)
        prices = await cls._get_token_prices(set(deposits.keys()) | {borrowed_token})

        deposit_usdc = sum(
            amount * Decimal(prices.get(token, "0"))
            for token, amount in deposits.items()
            if amount != 0
        )

        borrowed_price = prices.get(borrowed_token, Decimal("0"))
        debt_usdc = debt_raw * borrowed_price / Decimal(10 ** int(TokenParams.get_token_decimals(borrowed_token)))

        if debt_usdc == 0:
            return "-1", "0"

        if deposit_usdc == 0:
            return "0", "0"

        health_factor = str(round(deposit_usdc / debt_usdc, 2))
        ltv = round(
            (debt_usdc / TokenParams.get_borrow_factor(borrowed_token))
            / deposit_usdc,
            2,
        )
        return health_factor, str(ltv)


if __name__ == "__main__":
    print(
        asyncio.run(
            HealthRatioMixin.get_health_ratio_and_tvl(
                "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2",
                StellarClient()
            )
        )
    )
