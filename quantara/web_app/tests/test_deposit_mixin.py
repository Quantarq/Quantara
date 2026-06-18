"""
Test cases for DepositMixin (Stellar-based).
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_app.contract_tools.mixins.deposit import DepositMixin
from web_app.contract_tools.blockchain_call import StellarClient


class TestDepositMixin:
    """
    Test cases for DepositMixin (Stellar-based).
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "deposit_token_name, amount, multiplier, wallet_id, borrowing_token",
        [
            (
                "XLM",
                "100.0",
                2,
                "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2",
                "USDC",
            ),
            (
                "USDC",
                "3333.3",
                4,
                "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2",
                "XLM",
            ),
        ],
    )
    @patch(
        "web_app.contract_tools.blockchain_call.StellarClient.get_loop_liquidity_data",
        new_callable=AsyncMock,
    )
    async def test_get_transaction_data(
        self,
        mock_get_loop_liquidity_data: AsyncMock,
        deposit_token_name: str,
        amount: str,
        multiplier: int,
        wallet_id: str,
        borrowing_token: str,
    ) -> None:
        """
        Test cases for DepositMixin.get_transaction_data method
        """
        expected_transaction_data = {
            "deposit_data": {
                "token": deposit_token_name,
                "amount": "1000000000",
                "multiplier": str(multiplier * 10),
                "borrow_portion_percent": 99,
            },
            "caller": wallet_id,
        }

        mock_get_loop_liquidity_data.return_value = expected_transaction_data

        client = StellarClient()
        transaction_data = await DepositMixin.get_transaction_data(
            deposit_token_name,
            amount,
            multiplier,
            wallet_id,
            borrowing_token,
            client,
        )

        assert transaction_data == expected_transaction_data

    @pytest.mark.asyncio
    @pytest.mark.parametrize("supply_token", ["XLM", "USDC"])
    @patch(
        "web_app.contract_tools.blockchain_call.StellarClient.get_repay_data",
        new_callable=AsyncMock,
    )
    async def test_get_repay_data(
        self,
        mock_get_repay_data: AsyncMock,
        supply_token: str,
    ) -> None:
        """
        Test cases for DepositMixin.get_repay_data method
        """
        expected_repay_data = {
            "supply_token": supply_token,
            "debt_token": "USDC" if supply_token != "USDC" else "XLM",
            "borrow_portion_percent": 99,
        }

        mock_get_repay_data.return_value = expected_repay_data

        client = StellarClient()
        repay_data = await DepositMixin.get_repay_data(supply_token, client)

        assert repay_data == expected_repay_data
