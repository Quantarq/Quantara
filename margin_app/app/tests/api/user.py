"""
Tests for user API endpoints.
"""

import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.api.user import router
from app.schemas.user import UserResponse


@pytest.fixture
def app():
    """
    Create a FastAPI app for testing.
    """
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """
    Create a test client for the app.
    """
    return TestClient(app)


@pytest.fixture
def mock_create_user():
    """
    Mock the create_user method of crud_create_user.
    """
    with patch("app.api.user.crud_create_user.create_user") as mock:
        yield mock


@pytest.fixture
def mock_create_deposit():
    """
    Mock the create_deposit method of deposit_crud.
    """
    with patch("app.api.user.deposit_crud.create_deposit") as mock:
        yield mock


@pytest.fixture
def mock_add_margin_position():
    """
    Mock the add_margin_position method of UserCRUD.
    """
    with patch.object("app.api.user.UserCRUD", "add_margin_position") as mock:
        yield mock


def test_create_user_success(client, mock_create_user):
    """Test successfully creating a user."""
    wallet_id = "0x1234567890abcdef1234567890abcdef12345678"
    user_id = uuid.uuid4()

    mock_create_user.return_value = UserResponse(id=user_id, wallet_id=wallet_id)

    response = client.post("/users", json={"wallet_id": wallet_id})

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"id": str(user_id), "wallet_id": wallet_id}
    mock_create_user.assert_called_once_with(wallet_id)


def test_create_user_error(client, mock_create_user):
    """Test error handling when creating a user."""
    wallet_id = "0x1234567890abcdef1234567890abcdef12345678"
    mock_create_user.side_effect = Exception("Database error")

    response = client.post("/users", json={"wallet_id": wallet_id})

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Something went wrong."}
    mock_create_user.assert_called_once_with(wallet_id)


def test_add_user_deposit_success(client, mock_create_deposit):
    """Test successfully adding a user deposit."""
    user_id = uuid.uuid4()
    deposit_id = uuid.uuid4()

    request_data = {
        "user_id": str(user_id),
        "token": "ETH",
        "amount": "1.5",
        "transaction_id": "0xabcdef1234567890",
    }

    mock_deposit = MagicMock()
    mock_deposit.id = deposit_id
    mock_create_deposit.return_value = mock_deposit

    response = client.post("/add_user_deposit", json=request_data)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"deposit_id": str(deposit_id)}
    mock_create_deposit.assert_called_once_with(
        user_id=user_id,
        token="ETH",
        amount=Decimal("1.5"),
        transaction_id="0xabcdef1234567890",
    )


def test_add_user_deposit_error(client, mock_create_deposit):
    """Test error handling when adding a user deposit."""
    user_id = uuid.uuid4()

    request_data = {
        "user_id": str(user_id),
        "token": "ETH",
        "amount": "1.5",
        "transaction_id": "0xabcdef1234567890",
    }

    mock_create_deposit.side_effect = Exception("User not found")

    response = client.post("/add_user_deposit", json=request_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "User not found"}
    mock_create_deposit.assert_called_once()


def test_add_margin_position_success(client, mock_add_margin_position):
    """Test successfully adding a margin position."""
    user_id = uuid.uuid4()
    position_id = uuid.uuid4()

    request_data = {
        "user_id": str(user_id),
        "borrowed_amount": "100.0",
        "multiplier": 5,
        "token": "BTC",
        "transaction_id": "0x9876543210abcdef",
    }

    mock_position = MagicMock()
    mock_position.id = position_id
    mock_add_margin_position.return_value = mock_position

    response = client.post("/add_margin_position", json=request_data)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"margin_position_id": str(position_id)}
    mock_add_margin_position.assert_called_once_with(
        user_id=user_id,
        borrowed_amount=Decimal("100.0"),
        multiplier=5,
        transaction_id="0x9876543210abcdef",
    )


def test_add_margin_position_error(client, mock_add_margin_position):
    """Test error handling when adding a margin position."""
    user_id = uuid.uuid4()

    request_data = {
        "user_id": str(user_id),
        "borrowed_amount": "100.0",
        "multiplier": 5,
        "token": "BTC",
        "transaction_id": "0x9876543210abcdef",
    }

    mock_add_margin_position.side_effect = ValueError(
        "Insufficient funds for margin position"
    )

    response = client.post("/add_margin_position", json=request_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Insufficient funds for margin position"}
    mock_add_margin_position.assert_called_once()


def test_create_user_invalid_wallet(client):
    """Test invalid wallet format when creating a user."""
    invalid_wallet = "invalid-wallet-format"

    response = client.post("/users", json={"wallet_id": invalid_wallet})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_add_user_deposit_invalid_amount(client):
    """Test invalid amount format when adding a user deposit."""
    user_id = uuid.uuid4()

    request_data = {
        "user_id": str(user_id),
        "token": "ETH",
        "amount": "invalid-amount",
        "transaction_id": "0xabcdef1234567890",
    }

    response = client.post("/add_user_deposit", json=request_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_add_margin_position_invalid_multiplier(client):
    """Test invalid multiplier format when adding a margin position."""
    user_id = uuid.uuid4()

    request_data = {
        "user_id": str(user_id),
        "borrowed_amount": "100.0",
        "multiplier": "invalid-multiplier",
        "token": "BTC",
        "transaction_id": "0x9876543210abcdef",
    }

    response = client.post("/add_margin_position", json=request_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
