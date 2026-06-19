"""
This module contains the deposit mixin class for the Stellar-based Quantara protocol.

Provides transaction data preparation for deposit and repay operations
on Soroban contracts.
"""

from decimal import Decimal

from web_app.contract_tools.constants import TokenParams
from web_app.contract_tools.blockchain_call import StellarClient


class DepositMixin:
    """
    Mixin class for deposit related methods using Stellar/Soroban primitives.
    """

    @classmethod
    async def get_transaction_data(
        cls,
        deposit_token: str,
        amount: str,
        multiplier: Decimal,
        wallet_id: str,
        borrowing_token: str,
        client: StellarClient,
    ) -> dict:
        """
        Get transaction data for the deposit.
        :param deposit_token: Deposit token symbol (e.g. "XLM", "USDC")
        :param amount: Amount to deposit
        :param multiplier: Multiplier
        :param wallet_id: Wallet ID (Stellar public key)
        :param borrowing_token: Borrowing token symbol
        :param client: StellarClient instance
        :return: loop_liquidity_data dict
        """
        deposit_token_address = TokenParams.get_token_address(deposit_token)
        decimal = TokenParams.get_token_decimals(deposit_token_address)
        amount = int(Decimal(amount) * 10 ** decimal)

        loop_liquidity_data = await client.get_loop_liquidity_data(
            deposit_token_address,
            amount,
            multiplier,
            wallet_id,
            borrowing_token,
        )

        return loop_liquidity_data

    @classmethod
    async def get_repay_data(
        cls, supply_token: str, client: StellarClient
    ) -> dict:
        """
        Get transaction data for the repay/close.

        :param supply_token: Deposit token symbol
        :param client: StellarClient instance
        :return: dict with repay data (supply_token, debt_token)
        """
        deposit_token_address = TokenParams.get_token_address(supply_token)
        debt_token_address = (
            TokenParams.get_token_address("USDC")
            if supply_token != "USDC"
            else TokenParams.get_token_address("XLM")
        )

        repay_data = {
            "supply_token": deposit_token_address,
            "debt_token": debt_token_address,
        }

        return repay_data | await client.get_repay_data(
            deposit_token_address, debt_token_address
        )
