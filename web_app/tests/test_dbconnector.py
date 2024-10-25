"""Test cases for DBConnector"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from web_app.db.crud import DBConnector, PositionDBConnector, UserDBConnector
from web_app.db.models import Base, Position, Status, User


@pytest.fixture(scope="function")
def sample_user(mock_db_connector):
    """
    Fixture to create a sample user for testing using the mock DBConnector.
    """
    user = User(wallet_id="test_wallet_id")
    mock_db_connector.write_to_db.return_value = user
    return user


@pytest.fixture(scope="function")
def sample_position(mock_db_connector, sample_user):
    """
    Fixture to create a sample position for testing using the mock DBConnector.
    """
    position = Position(
        user_id=sample_user.id,
        token_symbol="ETH",
        amount="100",
        multiplier=2,
        status=Status.PENDING.value,
        start_price=0.0,
    )
    mock_db_connector.write_to_db.return_value = position
    return position


### Positive Test Cases ###


def test_write_to_db_positive(mock_db_connector):
    """
    Test writing an object to the database successfully using the mock DBConnector.
    """
    user = User(wallet_id="positive_wallet")
    mock_db_connector.write_to_db.return_value = user
    result = mock_db_connector.write_to_db(user)
    assert result.wallet_id == "positive_wallet"


def test_get_object_positive(mock_db_connector, sample_user):
    """
    Test retrieving an existing object from the database by ID using the mock DBConnector.
    """
    mock_db_connector.get_object.return_value = sample_user
    result = mock_db_connector.get_object(User, sample_user.id)
    assert result.wallet_id == "test_wallet_id"


def test_delete_object_positive(mock_db_connector, sample_position):
    """
    Test deleting an existing object from the database by ID using the mock DBConnector.
    """
    mock_db_connector.delete_object.return_value = None
    mock_db_connector.get_object.return_value = None

    mock_db_connector.delete_object(Position, sample_position.id)
    result = mock_db_connector.get_object(Position, sample_position.id)
    assert result is None


### Negative Test Cases ###


def test_write_to_db_invalid_object(mock_db_connector):
    """
    Test writing an invalid object to the database, expecting SQLAlchemyError.
    """
    mock_db_connector.write_to_db.side_effect = SQLAlchemyError("Invalid object")
    with pytest.raises(SQLAlchemyError):
        mock_db_connector.write_to_db(None)


def test_get_object_invalid_id(mock_db_connector):
    """
    Test retrieving an object with a non-existent ID, expecting None.
    """
    non_existent_id = uuid.uuid4()
    mock_db_connector.get_object.return_value = None
    result = mock_db_connector.get_object(User, non_existent_id)
    assert result is None


def test_delete_object_invalid_id(mock_db_connector):
    """
    Test deleting an object with a non-existent ID, expecting no errors.
    """
    non_existent_id = uuid.uuid4()
    mock_db_connector.delete_object(non_existent_id)
