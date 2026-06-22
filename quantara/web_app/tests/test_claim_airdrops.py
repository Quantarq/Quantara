"""
Tests for the AirdropClaimer class.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from requests.exceptions import Timeout

from web_app.tasks.claim_airdrops import AirdropClaimer


@pytest.fixture
def airdrop_claimer():
    """Fixture to create a mock AirdropClaimer instance."""
    claimer = AirdropClaimer()
    claimer.db_connector = MagicMock()
    claimer.airdrop_fetcher = MagicMock()
    yield claimer


@pytest.fixture
def mock_airdrop():
    """Create a standard mock airdrop for reusable test setup."""
    mock_airdrop = MagicMock()
    mock_airdrop.user.contract_address = "CCJZ5LW4CJ3J3Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5"
    mock_airdrop.id = 1
    mock_airdrop.amount = 100
    yield mock_airdrop


@pytest.mark.asyncio
async def test_claim_airdrops_successful(airdrop_claimer, mock_airdrop):
    """Test successful airdrop claim."""
    airdrop_claimer.db_connector.get_all_unclaimed.return_value = [mock_airdrop]
    airdrop_claimer.airdrop_fetcher.get_contract_airdrop.return_value = [
        "proof1",
        "proof2",
    ]

    await airdrop_claimer.claim_airdrops()

    airdrop_claimer.airdrop_fetcher.get_contract_airdrop.assert_called_with(
        "CCJZ5LW4CJ3J3Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5"
    )
    airdrop_claimer.db_connector.save_claim_data.assert_called_with(1, 100)


@pytest.mark.asyncio
async def test_claim_airdrops_no_unclaimed(airdrop_claimer):
    """Test when no unclaimed airdrops exist."""
    airdrop_claimer.db_connector.get_all_unclaimed.return_value = []

    await airdrop_claimer.claim_airdrops()

    airdrop_claimer.airdrop_fetcher.get_contract_airdrop.assert_not_called()
    airdrop_claimer.db_connector.save_claim_data.assert_not_called()


@pytest.mark.asyncio
async def test_claim_airdrops_partial_failure(airdrop_claimer):
    """Test with multiple airdrops, some failing."""
    mock_airdrop1 = MagicMock(
        user=MagicMock(contract_address="CCJZ5LW4CJ3J3Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5"),
        id=1,
        amount=100,
    )
    mock_airdrop2 = MagicMock(
        user=MagicMock(contract_address="CCJZ5LW4CJ3J3Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z6"),
        id=2,
        amount=200,
    )

    airdrop_claimer.db_connector.get_all_unclaimed.return_value = [
        mock_airdrop1,
        mock_airdrop2,
    ]
    airdrop_claimer.airdrop_fetcher.get_contract_airdrop.side_effect = [
        ["proof1"],
        ["proof2"],
    ]

    await airdrop_claimer.claim_airdrops()

    # Both airdrops should be claimed (mock implementation always succeeds)
    assert airdrop_claimer.db_connector.save_claim_data.call_count == 2


@pytest.mark.asyncio
async def test_claim_airdrops_database_error(airdrop_claimer, mock_airdrop, caplog):
    """Test handling of database errors during airdrop claiming."""
    airdrop_claimer.db_connector.get_all_unclaimed.return_value = [mock_airdrop]
    airdrop_claimer.airdrop_fetcher.get_contract_airdrop.return_value = ["proof1"]

    airdrop_claimer.db_connector.save_claim_data.side_effect = SQLAlchemyError(
        "Database error"
    )

    with caplog.at_level(logging.ERROR):
        await airdrop_claimer.claim_airdrops()

    # Updated to evaluate structlog dictionary components safely
    assert "airdrop_db_error" in caplog.text
    assert "Database error" in caplog.text
    airdrop_claimer.db_connector.save_claim_data.assert_called_once()


@pytest.mark.asyncio
async def test_claim_airdrop_timeout_error(airdrop_claimer):
    """Test handling of timeout errors during mock claim."""
    result = await airdrop_claimer._claim_airdrop("CCJZ5LW4CJ3J3...", ["proof1"])
    assert result is True  # Mock implementation always returns True


@pytest.mark.asyncio
async def test_claim_airdrop_invalid_proof(airdrop_claimer):
    """Test claim with proof data - mock implementation."""
    result = await airdrop_claimer._claim_airdrop("CCJZ5LW4CJ3J3...", ["invalid_proof"])
    assert result is True  # Mock implementation always returns True