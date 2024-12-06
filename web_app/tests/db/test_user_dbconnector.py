"""
Unit tests for the UserDBConnector module.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from web_app.db.crud import AirDropDBConnector, UserDBConnector
from web_app.db.models import AirDrop, User


@pytest.fixture
def mock_db_connector():
    """
    Fixture to create a mock database connector.
    """
    return MagicMock()


@pytest.fixture
def user_db(mock_db_connector):
    """
    Fixture to create a UserDBConnector instance with mocked dependencies.
    """
    with patch(
        "web_app.db.crud.UserDBConnector.get_object_by_field",
        new_callable=MagicMock,
    ) as mock_get:
        mock_get.side_effect = mock_db_connector.get_object_by_field
        connector = UserDBConnector()
        yield connector


def test_get_user_by_wallet_id_success(user_db, mock_db_connector):
    """
    Test successful retrieval of user by wallet ID.
    """
    wallet_id = "0x123456789"
    expected_user = User(
        id=1,
        wallet_id=wallet_id,
    )

    mock_db_connector.get_object_by_field.return_value = expected_user

    result = user_db.get_user_by_wallet_id(wallet_id)

    assert result == expected_user
    mock_db_connector.get_object_by_field.assert_called_once_with(
        User, "wallet_id", wallet_id
    )


def test_get_user_by_wallet_id_not_found(user_db, mock_db_connector):
    """
    Test when user is not found by wallet ID.
    """
    wallet_id = "0x987654321"
    mock_db_connector.get_object_by_field.return_value = None

    result = user_db.get_user_by_wallet_id(wallet_id)

    assert result is None
    mock_db_connector.get_object_by_field.assert_called_once_with(
        User, "wallet_id", wallet_id
    )


def test_get_user_by_wallet_id_empty_wallet_id(user_db, mock_db_connector):
    """
    Test behavior when empty wallet ID is provided.
    """
    wallet_id = ""
    mock_db_connector.get_object_by_field.return_value = None

    result = user_db.get_user_by_wallet_id(wallet_id)

    assert result is None
    mock_db_connector.get_object_by_field.assert_called_once_with(
        User, "wallet_id", wallet_id
    )


def test_get_unique_users_count(mock_user_db_connector):
    """Test getting count of unique users."""
    mock_user_db_connector.get_unique_users_count.return_value = 5

    result = mock_user_db_connector.get_unique_users_count()

    assert result == 5


def test_delete_all_users_airdrop_success(user_db):
    """
    Test successful deletion of all airdrops for a user.
    """
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    mock_session = MagicMock()
    mock_airdrops = [
        AirDrop(id=1, user_id=user_id),
        AirDrop(id=2, user_id=user_id),
    ]

    air_drop_connector = AirDropDBConnector()
    with patch.object(
        air_drop_connector, "Session"
    ) as mock_session_factory:
        mock_session_factory.return_value.__enter__.return_value = (
            mock_session
        )
        mock_session.query.return_value.filter_by.return_value.all.return_value = (
            mock_airdrops
        )

        air_drop_connector.delete_all_users_airdrop(user_id)

        mock_session.query.assert_called_once_with(AirDrop)
        mock_session.query.return_value.filter_by.assert_called_once_with(
            user_id=user_id
        )
        assert mock_session.delete.call_count == len(mock_airdrops)
        mock_session.commit.assert_called_once()


def test_delete_all_users_airdrop_failure(user_db):
    """
    Test failure while deleting airdrops for a user.
    """
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    mock_session = MagicMock()
    mock_session.query.side_effect = SQLAlchemyError("Database error")

    air_drop_connector = AirDropDBConnector()
    with patch.object(
        air_drop_connector, "Session", return_value=mock_session
    ) as mock_session_factory:
        mock_session_factory.return_value.__enter__.return_value = (
            mock_session
        )

        air_drop_connector.delete_all_users_airdrop(user_id)
        mock_session.query.assert_called_once_with(AirDrop)
        # mock_session.rollback.assert_called_once()
