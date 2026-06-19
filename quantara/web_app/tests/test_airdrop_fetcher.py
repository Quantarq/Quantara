"""
Test module for AirdropFetcher class.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from web_app.api.serializers.airdrop import AirdropResponseModel
from web_app.contract_tools.airdrop import AirdropFetcher


@pytest.fixture
def mock_api_response() -> list:
    """Fixture providing mock API response data."""
    return [
        {
            "amount": "1000000000000000000",
            "proof": ["0xabcd", "0x1234"],
            "is_claimed": False,
            "recipient": "GABCD1234ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678",
        }
    ]


@pytest.fixture
def airdrop_fetcher():
    """Fixture providing an AirdropFetcher instance with mocked API."""
    instance = AirdropFetcher()
    instance.api = Mock()
    instance.api.fetch = AsyncMock()
    return instance


class TestAirdropFetcher:
    """Test suite for AirdropFetcher class."""

    def test_init_without_endpoint_defaults_to_noop(self, monkeypatch):
        monkeypatch.setattr(AirdropFetcher, "REWARD_API_ENDPOINT", "")

        fetcher = AirdropFetcher()

        assert isinstance(fetcher, AirdropFetcher)
        assert fetcher.api is None

    @pytest.mark.asyncio
    async def test_get_contract_airdrop_returns_empty_when_unconfigured(
        self, monkeypatch
    ):
        monkeypatch.setattr(AirdropFetcher, "REWARD_API_ENDPOINT", "")

        fetcher = AirdropFetcher()
        result = await fetcher.get_contract_airdrop("GABCD1234ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678")

        assert isinstance(result, AirdropResponseModel)
        assert len(result.airdrops) == 0

    @pytest.mark.asyncio
    async def test_get_contract_airdrop_success(
        self, airdrop_fetcher, mock_api_response
    ):
        """Test successful retrieval of airdrop data."""
        contract_id = "GABCD1234ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678"
        airdrop_fetcher.api.fetch.return_value = mock_api_response

        result = await airdrop_fetcher.get_contract_airdrop(contract_id)

        assert isinstance(result, AirdropResponseModel)
        assert len(result.airdrops) == 1
        airdrop = result.airdrops[0]
        assert airdrop.amount == "1000000000000000000"
        assert airdrop.proof == ["0xabcd", "0x1234"]
        assert airdrop.is_claimed is False
        assert airdrop.recipient == "GABCD1234ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678"

    @pytest.mark.asyncio
    async def test_get_contract_airdrop_empty_response(self, airdrop_fetcher):
        """Test handling of empty API response."""
        contract_id = "GABCD1234ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678"
        airdrop_fetcher.api.fetch.return_value = []

        result = await airdrop_fetcher.get_contract_airdrop(contract_id)

        assert isinstance(result, AirdropResponseModel)
        assert len(result.airdrops) == 0

    @pytest.mark.asyncio
    async def test_get_contract_airdrop_with_invalid_contract_id(
        self, airdrop_fetcher
    ):
        """Test handling of invalid contract IDs."""
        invalid_ids = ["", "0x"]
        airdrop_fetcher.api.fetch.return_value = []

        for invalid_id in invalid_ids:
            result = await airdrop_fetcher.get_contract_airdrop(invalid_id)
            assert isinstance(result, AirdropResponseModel)
            assert len(result.airdrops) == 0

    @pytest.mark.asyncio
    async def test_get_contract_airdrop_none_contract_id(self, airdrop_fetcher):
        """Test handling of None contract ID."""
        with pytest.raises(ValueError):
            await airdrop_fetcher.get_contract_airdrop(None)

    def test_validate_response(self, airdrop_fetcher, mock_api_response):
        """Test response validation."""
        result = airdrop_fetcher._validate_response(mock_api_response)

        assert isinstance(result, AirdropResponseModel)
        assert len(result.airdrops) == 1
        airdrop = result.airdrops[0]
        assert isinstance(airdrop.proof, list)
        assert airdrop.proof == ["0xabcd", "0x1234"]

    def test_validate_response_empty(self, airdrop_fetcher):
        """Test validation of empty response."""
        result = airdrop_fetcher._validate_response([])

        assert isinstance(result, AirdropResponseModel)
        assert len(result.airdrops) == 0

    def test_validate_response_missing_fields(self, airdrop_fetcher):
        """Test validation with missing required fields falls back to defaults."""
        invalid_data = [{"amount": "1000"}]

        result = airdrop_fetcher._validate_response(invalid_data)
        assert len(result.airdrops) == 1
        assert result.airdrops[0].amount == "1000"
        assert result.airdrops[0].proof == []
        assert result.airdrops[0].is_claimed is False
        assert result.airdrops[0].recipient == ""

    @pytest.mark.asyncio
    async def test_get_contract_airdrop_contract_formatting(self, airdrop_fetcher):
        """Test that contract ID is passed directly (no transformation)."""
        contract_id = "GABCD1234ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678ABCDEFGH5678"
        airdrop_fetcher.api.fetch.return_value = []

        await airdrop_fetcher.get_contract_airdrop(contract_id)

        airdrop_fetcher.api.fetch.assert_called_once_with(contract_id)
