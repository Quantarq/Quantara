"""
Test suite for the DashboardMixin class (Stellar-based).
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import pytest

from web_app.contract_tools.mixins.dashboard import DashboardMixin
from web_app.db.models import ExtraDeposit


@pytest.fixture
def mock_api_request():
    """Mock the API request class."""
    with patch("web_app.contract_tools.mixins.dashboard.APIRequest") as mock:
        yield mock


class TestDashboardMixin:
    """
    Test cases for the DashboardMixin class.
    """

    @pytest.mark.asyncio
    async def test_get_current_prices_returns_coingecko_prices(self, mock_api_request):
        """
        Test that CoinGecko responses are mapped to Quantara token symbols.
        """
        mock_api_request.return_value.fetch = AsyncMock(
            return_value={
                "stellar": {"usd": 0.123},
                "usd-coin": {"usd": 1},
                "ethereum": {"usd": 2500.45},
            }
        )

        result = await DashboardMixin.get_current_prices()

        assert result == {
            "XLM": Decimal("0.123"),
            "USDC": Decimal("1"),
            "ETH": Decimal("2500.45"),
        }
        mock_api_request.assert_called_once()
        mock_api_request.return_value.fetch.assert_awaited_once_with(
            "",
            params={
                "ids": "stellar,usd-coin,ethereum",
                "vs_currencies": "usd",
            },
        )

    @pytest.mark.asyncio
    async def test_get_current_prices_returns_empty_dict_for_invalid_payload(
        self, mock_api_request
    ):
        """
        Test that malformed API responses fail closed.
        """
        mock_api_request.return_value.fetch = AsyncMock(return_value=["invalid"])

        result = await DashboardMixin.get_current_prices()

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_current_position_sum_converts_extra_deposits(
        self, mock_api_request
    ):
        """
        Test that current position values are derived from the configured prices.
        """
        mock_position = SimpleNamespace(
            token_symbol="XLM",
            amount="1",
            multiplier="1",
        )
        mock_prices = {
            "XLM": Decimal("99"),
            "ETH": Decimal("198"),
            "USDC": Decimal("1"),
        }
        with (
            patch(
                "web_app.contract_tools.mixins.dashboard.position_db_connector.get_position_by_id",
                return_value=mock_position,
            ),
            patch(
                "web_app.contract_tools.mixins.dashboard.position_db_connector.get_extra_deposits_by_position_id",
                return_value=[ExtraDeposit(token_symbol="ETH", amount="1")],
            ),
            patch.object(
                DashboardMixin,
                "get_current_prices",
                new_callable=AsyncMock,
                return_value=mock_prices,
            ),
        ):
            result = await DashboardMixin.get_current_position_sum({"id": "pos-1"})

        assert result == Decimal("102")
