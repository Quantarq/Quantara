"""Test cases for PositionDBConnector"""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from web_app.db.models import Position, Status, User
from web_app.db.crud import PositionDBConnector


@pytest.fixture(scope="function")
def sample_user():
    """Fixture to create a sample user for testing."""
    return User(
        wallet_id="test_wallet_id"
    )


@pytest.fixture(scope="function")
def sample_position(sample_user):
    """Fixture to create a sample position for testing."""
    return Position(
        user_id=sample_user.id,
        token_symbol="ETH",
        amount="100",
        multiplier=2,
        status=Status.PENDING.value,
        start_price=0.0
    )


@pytest.fixture(scope="function")
def mock_session():
    """Fixture to create a mock database session."""
    session = MagicMock()
    return session


### Positive Test Cases ###

def test_position_to_dict(mock_position_db_connector, sample_position):
    """Test converting a Position object to dictionary."""
    result = PositionDBConnector._position_to_dict(sample_position)
    
    assert isinstance(result, dict)
    assert result["id"] == str(sample_position.id)
    assert result["user_id"] == str(sample_position.user_id)
    assert result["token_symbol"] == sample_position.token_symbol
    assert result["amount"] == sample_position.amount
    assert result["multiplier"] == sample_position.multiplier
    assert result["status"] == sample_position.status


def test_get_positions_by_wallet_id_success(
        mock_position_db_connector, 
        sample_user, 
        sample_position
):
    """Test successfully retrieving positions by wallet ID."""
    mock_position_db_connector._get_user_by_wallet_id.return_value = sample_user
    
    position_dict = {
        "id": str(sample_position.id),
        "user_id": str(sample_position.user_id),
        "token_symbol": sample_position.token_symbol,
        "amount": sample_position.amount,
        "multiplier": sample_position.multiplier,
        "status": sample_position.status,
        "start_price": sample_position.start_price
    }
    
    mock_position_db_connector.get_positions_by_wallet_id.return_value = [position_dict]

    positions = mock_position_db_connector.get_positions_by_wallet_id("test_wallet_id")

    assert len(positions) == 1
    assert positions[0]["id"] == str(sample_position.id)
    assert positions[0]["token_symbol"] == sample_position.token_symbol
    assert positions[0]["amount"] == sample_position.amount
    assert positions[0]["multiplier"] == sample_position.multiplier
    assert positions[0]["status"] == sample_position.status


def test_create_position_success(mock_position_db_connector, sample_user):
    """Test successfully creating a new position."""
    mock_position_db_connector._get_user_by_wallet_id.return_value = sample_user
    
    new_position = Position(
        user_id=sample_user.id,
        token_symbol="ETH",
        amount="200",
        multiplier=3,
        status=Status.PENDING.value,
        start_price=0.0
    )
    mock_position_db_connector.write_to_db.return_value = new_position
    mock_position_db_connector.create_position.return_value = new_position
    
    result = mock_position_db_connector.create_position(
        wallet_id="test_wallet_id",
        token_symbol="ETH",
        amount="200",
        multiplier=3
    )
    
    assert result is not None
    assert result.token_symbol == "ETH"
    assert result.amount == "200"
    assert result.multiplier == 3


def test_update_existing_pending_position(
        mock_position_db_connector, 
        sample_user, 
        sample_position
):
    """Test updating an existing pending position."""
    mock_position_db_connector._get_user_by_wallet_id.return_value = sample_user
    
    updated_position = Position(
        user_id=sample_user.id,
        token_symbol="LTC",
        amount="300",
        multiplier=4,
        status=Status.PENDING.value,
        start_price=0.0
    )
    mock_position_db_connector.create_position.return_value = updated_position
    
    result = mock_position_db_connector.create_position(
        wallet_id="test_wallet_id",
        token_symbol="LTC",
        amount="300",
        multiplier=4
    )
    
    assert result.token_symbol == "LTC"
    assert result.amount == "300"
    assert result.multiplier == 4


def test_close_position_success(mock_position_db_connector, sample_position):
    """Test successfully closing a position."""
    mock_position_db_connector.get_object.return_value = sample_position
    mock_position_db_connector.close_position.return_value = Status.CLOSED.value
    
    result = mock_position_db_connector.close_position(sample_position.id)
    
    assert result == Status.CLOSED.value


def test_open_position_success(mock_position_db_connector, sample_position):
    """Test successfully opening a position."""
    mock_position_db_connector.get_object.return_value = sample_position
    mock_position_db_connector.open_position.return_value = Status.OPENED.value
    
    result = mock_position_db_connector.open_position(sample_position.id)
    
    assert result == Status.OPENED.value


def test_get_unique_users_count(mock_position_db_connector):
    """Test getting count of unique users."""
    mock_position_db_connector.get_unique_users_count.return_value = 5
    
    result = mock_position_db_connector.get_unique_users_count()
    
    assert result == 5


def test_get_total_amounts_for_open_positions(mock_position_db_connector):
    """Test getting total amounts for open positions."""
    mock_position_db_connector.get_total_amounts_for_open_positions.return_value = 1000.0
    
    result = mock_position_db_connector.get_total_amounts_for_open_positions()
    
    assert result == 1000.0


### Negative Test Cases ###

def test_get_positions_by_wallet_id_no_user(mock_position_db_connector):
    """Test retrieving positions for non-existent user."""
    mock_position_db_connector._get_user_by_wallet_id.return_value = None
    mock_position_db_connector.get_positions_by_wallet_id.return_value = []
    
    positions = mock_position_db_connector.get_positions_by_wallet_id("nonexistent_wallet")
    
    assert positions == []


def test_get_positions_by_wallet_id_db_error(mock_position_db_connector, sample_user):
    """Test handling database error when retrieving positions."""
    mock_position_db_connector._get_user_by_wallet_id.return_value = sample_user
    
    positions = mock_position_db_connector.get_positions_by_wallet_id("test_wallet_id")
    
    assert positions == []


def test_create_position_no_user(mock_position_db_connector):
    """Test creating position for non-existent user."""
    mock_position_db_connector._get_user_by_wallet_id.return_value = None
    mock_position_db_connector.create_position.return_value = None
    
    result = mock_position_db_connector.create_position(
        wallet_id="nonexistent_wallet",
        token_symbol="ETH",
        amount="100",
        multiplier=2
    )
    
    assert result is None


def test_close_position_not_found(mock_position_db_connector):
    """Test closing non-existent position."""
    mock_position_db_connector.get_object.return_value = None
    mock_position_db_connector.close_position.return_value = None
    
    result = mock_position_db_connector.close_position(uuid.uuid4())
    
    assert result is None


def test_get_total_amounts_db_error(mock_position_db_connector):
    """Test handling database error when getting total amounts."""
    mock_position_db_connector.get_total_amounts_for_open_positions.return_value = None
    
    result = mock_position_db_connector.get_total_amounts_for_open_positions()
    
    assert result is None


def test_get_position_id_by_wallet_id_no_positions(mock_position_db_connector):
    """Test getting position ID when no positions exist."""
    mock_position_db_connector.get_positions_by_wallet_id.return_value = []
    mock_position_db_connector.get_position_id_by_wallet_id.return_value = None
    
    result = mock_position_db_connector.get_position_id_by_wallet_id("test_wallet_id")
    
    assert result is None