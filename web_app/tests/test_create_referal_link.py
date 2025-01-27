"""
Unit tests for the FastAPI referral link creation endpoint.

Tests include:
- Successful creation of a referral link with a valid wallet ID.
- Missing wallet ID in the request.
- User not found in the database.

Uses pytest, unittest.mock for mocking, and FastAPI's TestClient for testing the API.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from web_app.api.referal import app
from web_app.db.models import User


@pytest.fixture
def client():
    """Fixture for creating a TestClient instance for API testing."""
    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_create_referal_link_success(client):
    """Test successful referral link creation with a valid wallet ID."""
    with patch("web_app.db.database.get_database") as mock_get_db:  # Changed here
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_user = MagicMock(spec=User)
        mock_user.wallet_id = "wallet123"
        mock_db.query().filter().first.return_value = mock_user
        response = client.get("/api/create_referal_link?wallet_id=wallet123")
        assert response.status_code == 200
        data = response.json()
        assert data["wallet_id"] == "wallet123"
        assert len(data["referral_code"]) == 16


@pytest.mark.asyncio
async def test_create_referal_link_missing_wallet_id(client):
    """Test error when wallet ID is missing in the request."""
    response = client.get("/api/create_referal_link")
    assert response.status_code == 422
    data = response.json()
    assert data["detail"][0]["msg"] == "Field required"  # Updated here


@pytest.mark.asyncio
async def test_create_referal_link_user_not_found(client):
    """Test error when the user is not found in the database."""
    with patch("web_app.db.database.get_database") as mock_get_db:  # Changed here
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.query().filter().first.return_value = None
        response = client.get("/api/create_referal_link?wallet_id=wallet789")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "User with the provided wallet_id does not exist"
