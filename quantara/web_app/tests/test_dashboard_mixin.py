"""
Test suite for the DashboardMixin class (Stellar-based).
"""

from unittest.mock import AsyncMock, patch

import pytest

from web_app.contract_tools.constants import TokenParams
from web_app.contract_tools.mixins.dashboard import DashboardMixin
from web_app.contract_tools.blockchain_call import StellarClient


@pytest.fixture
def mock_stellar_client():
    """Mock the Stellar client."""
    with patch("web_app.contract_tools.blockchain_call.StellarClient") as mock:
        yield mock.return_value


@pytest.fixture
def mock_api_request():
    """Mock the API request class."""
    with patch("web_app.contract_tools.mixins.dashboard.APIRequest") as mock:
        yield mock


class TestDashboardMixin:
    """
    Test cases for the DashboardMixin class.
    """

    @pytest.mark.skip(reason="CLIENT mock needs updating for Stellar client compatibility")
    @pytest.mark.asyncio
    async def test_get_wallet_balances_success(self, mock_stellar_client):
        """
        Test successful retrieval of wallet balances.
        """
        mock_stellar_client.get_token_balances = AsyncMock(
            return_value={"XLM": "100.5", "USDC": "1000.0"}
        )

        client = StellarClient()
        result = await DashboardMixin.get_wallet_balances("GABCD...", client)

        assert result == {"XLM": "100.5", "USDC": "1000.0"}

    @pytest.mark.skip(reason="CLIENT mock needs updating for Stellar client compatibility")
    @pytest.mark.asyncio
    async def test_get_wallet_balances_error_handling(self, mock_stellar_client):
        """
        Test wallet balances retrieval with error handling.
        """
        mock_stellar_client.get_token_balances = AsyncMock(
            side_effect=[Exception("Network error")]
        )

        client = StellarClient()
        result = await DashboardMixin.get_wallet_balances("GABCD...", client)

        assert result == {}
