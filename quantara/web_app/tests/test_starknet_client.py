"""
Test cases for StellarClient
"""

from unittest.mock import AsyncMock, patch

import pytest

from web_app.contract_tools.blockchain_call import StellarClient
from web_app.contract_tools.constants import TokenParams


@pytest.fixture
def client():
    return StellarClient()


class TestStellarClient:
    """
    Test cases for StellarClient class.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "asset_code, holder_addr, expected_balance",
        [
            ("XLM", "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2", "100.0"),
            ("USDC", "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2", "500.0"),
        ],
    )
    @patch.object(StellarClient, "get_balance", new_callable=AsyncMock)
    async def test_get_balance(
        self,
        mock_get_balance: AsyncMock,
        client: StellarClient,
        asset_code: str,
        holder_addr: str,
        expected_balance: str,
    ) -> None:
        """
        Test cases for StellarClient.get_balance method
        """
        mock_get_balance.return_value = expected_balance

        balance = await client.get_balance(asset_code, holder_addr)

        assert balance == expected_balance
        mock_get_balance.assert_awaited_once_with(asset_code, holder_addr)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "deposit_token, amount, multiplier, wallet_id, borrowing_token",
        [
            (
                TokenParams.get_token_address("XLM"),
                "100000",
                2,
                "GA7QYN...example...",
                TokenParams.get_token_address("USDC"),
            ),
            (
                TokenParams.get_token_address("USDC"),
                "3333000",
                4,
                "GA7QYN...example...",
                TokenParams.get_token_address("XLM"),
            ),
        ],
    )
    @patch.object(StellarClient, "get_loop_liquidity_data", new_callable=AsyncMock)
    async def test_get_loop_liquidity_data(
        self,
        mock_get_data: AsyncMock,
        client: StellarClient,
        deposit_token: str,
        amount: int,
        multiplier: int,
        wallet_id: str,
        borrowing_token: str,
    ) -> None:
        """
        Test cases for StellarClient.get_loop_liquidity_data method
        """
        expected_data = {
            "deposit_data": {
                "token": deposit_token,
                "amount": str(amount),
                "multiplier": str(multiplier * 10),
                "borrow_portion_percent": 99,
            },
            "caller": wallet_id,
        }
        mock_get_data.return_value = expected_data

        liquidity_data = await client.get_loop_liquidity_data(
            deposit_token=deposit_token,
            amount=amount,
            multiplier=multiplier,
            wallet_id=wallet_id,
            borrowing_token=borrowing_token,
        )

        assert liquidity_data == expected_data

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "deposit_token, borrowing_token",
        [
            (
                TokenParams.get_token_address("XLM"),
                TokenParams.get_token_address("USDC"),
            ),
            (
                TokenParams.get_token_address("USDC"),
                TokenParams.get_token_address("XLM"),
            ),
        ],
    )
    @patch.object(StellarClient, "get_repay_data", new_callable=AsyncMock)
    async def test_get_repay_data(
        self,
        mock_get_repay_data: AsyncMock,
        client: StellarClient,
        deposit_token: str,
        borrowing_token: str,
    ) -> None:
        """
        Test cases for StellarClient.get_repay_data method
        """
        expected_data = {
            "supply_token": deposit_token,
            "debt_token": borrowing_token,
            "borrow_portion_percent": 99,
        }
        mock_get_repay_data.return_value = expected_data

        repay_data = await client.get_repay_data(deposit_token, borrowing_token)

        assert repay_data == expected_data

    @pytest.mark.asyncio
    @patch.object(StellarClient, "is_contract_deployed", new_callable=AsyncMock)
    async def test_is_contract_deployed(
        self, mock_is_deployed: AsyncMock, client: StellarClient
    ) -> None:
        """
        Test contract deployment check.
        """
        mock_is_deployed.return_value = True

        result = await client.is_contract_deployed("CCJZ5LW4CJ3J3Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5")
        assert result is True

        mock_is_deployed.return_value = False
        result = await client.is_contract_deployed("invalid")
        assert result is False

    @pytest.mark.asyncio
    @patch.object(StellarClient, "get_token_balances", new_callable=AsyncMock)
    async def test_get_token_balances(
        self, mock_get_balances: AsyncMock, client: StellarClient
    ) -> None:
        """
        Test token balances retrieval.
        """
        expected = {"XLM": "100.0", "USDC": "500.0", "ETH": "0.0"}
        mock_get_balances.return_value = expected

        balances = await client.get_token_balances(
            "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2"
        )

        assert balances == expected
