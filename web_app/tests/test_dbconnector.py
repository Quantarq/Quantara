import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from web_app.db.crud import DBConnector, PositionDBConnector, UserDBConnector
from web_app.db.models import Base, Position, Status, User

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_connector():
    """
    Fixture to initialize a DBConnector instance with an in-memory SQLite database.
    """
    connector = DBConnector(db_url=TEST_DATABASE_URL)
    Base.metadata.create_all(connector.engine)
    yield connector
    Base.metadata.drop_all(connector.engine)


@pytest.fixture(scope="function")
def sample_user(db_connector):
    """
    Fixture to create a sample user for testing.
    """
    user = User(wallet_id="test_wallet_id")
    return db_connector.write_to_db(user)


@pytest.fixture(scope="function")
def sample_position(db_connector, sample_user):
    """
    Fixture to create a sample position for testing.
    """
    position = Position(
        user_id=sample_user.id,
        token_symbol="ETH",
        amount="100",
        multiplier=2,
        status=Status.PENDING.value,
        start_price=0.0,  
    )
    return db_connector.write_to_db(position)


### Positive Test Cases ###


def test_write_to_db_positive(db_connector):
    """
    Test writing an object to the database successfully.
    """
    user = User(wallet_id="positive_wallet")
    result = db_connector.write_to_db(user)
    assert result.wallet_id == "positive_wallet"


def test_get_object_positive(db_connector, sample_user):
    """
    Test retrieving an existing object from the database by ID.
    """
    result = db_connector.get_object(User, sample_user.id)
    assert result.wallet_id == "test_wallet_id"


def test_delete_object_positive(db_connector, sample_position):
    """
    Test deleting an existing object from the database by ID.
    """
    db_connector.delete_object(Position, sample_position.id)
    result = db_connector.get_object(Position, sample_position.id)
    assert result is None


### Negative Test Cases ###


def test_write_to_db_invalid_object(db_connector):
    """
    Test writing an invalid object to the database, expecting SQLAlchemyError.
    """
    with pytest.raises(SQLAlchemyError):
        db_connector.write_to_db(None)


def test_get_object_invalid_id(db_connector):
    """
    Test retrieving an object with a non-existent ID, expecting None.
    """
    non_existent_id = uuid.uuid4()
    result = db_connector.get_object(User, non_existent_id)
    assert result is None


def test_delete_object_invalid_id(db_connector):
    """
    Test deleting an object with a non-existent ID, expecting no errors.
    """
    non_existent_id = uuid.uuid4()
    db_connector.delete_object(User, non_existent_id)
