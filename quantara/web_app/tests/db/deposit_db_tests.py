"""
Test cases for DepositDBConnector functionality in web_app.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
import uuid

import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from web_app.db.crud import DepositDBConnector
from web_app.db.models import Base, User, Vault


@pytest.fixture
def db_session_factory():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session


@pytest.fixture
def deposit_connector(db_session_factory):
    """Provide a DepositDBConnector backed by an in-memory SQLite database."""
    connector = object.__new__(DepositDBConnector)
    connector.Session = db_session_factory
    return connector


@pytest.fixture
def mock_user():
    """
    Mocked User instance.
    """
    return User(id=uuid.uuid4(), wallet_id="wallet123")


@pytest.fixture
def mock_vault():
    """
    Mocked Vault instance.
    """
    return Vault(id=uuid.uuid4(), user_id=uuid.uuid4(), symbol="ETH", amount="100.00")


class TestCreateVault:
    """
    Tests for creating a vault using DepositDBConnector.
    """

    def test_create_vault_success(self, deposit_connector, mock_user):
        """
        Test successful creation of a vault via upsert.
        """
        vault = deposit_connector.create_vault(
            user=mock_user,
            symbol="BTC",
            amount="50.00",
        )

        assert vault.symbol == "BTC"
        assert vault.amount == "50.00"
        assert vault.user_id == mock_user.id

    def test_create_vault_idempotent(self, deposit_connector, mock_user):
        """
        Test that calling create_vault twice adds amounts (upsert behaviour).
        """
        deposit_connector.create_vault(user=mock_user, symbol="BTC", amount="50.00")
        vault = deposit_connector.create_vault(
            user=mock_user, symbol="BTC", amount="25.00"
        )
        assert Decimal(vault.amount) == Decimal("75.00")

    def test_create_vault_failure_invalid_user(self, deposit_connector):
        """
        Test failure when creating a vault with an invalid user.
        """
        with pytest.raises((AttributeError, TypeError)):
            deposit_connector.create_vault(
                user=None,
                symbol="BTC",
                amount="50.00",
            )


class TestAddVaultBalance:
    """
    Tests for adding to a vault's balance using DepositDBConnector.
    """

    def test_add_balance_success(self, deposit_connector, mock_user):
        """
        Test successfully adding to a vault's balance.
        """
        deposit_connector.upsert_vault(mock_user.id, "ETH", "100.00")
        vault = deposit_connector.add_vault_balance(
            wallet_id=mock_user.wallet_id,
            symbol="ETH",
            amount="50.00",
        )
        assert Decimal(vault.amount) == Decimal("150.00")

    def test_add_balance_failure_vault_not_found(self, deposit_connector):
        """
        Test failure when adding to a vault balance for a non-existent user.
        """
        with pytest.raises(ValueError, match="User not found"):
            deposit_connector.add_vault_balance(
                wallet_id="invalid_wallet",
                symbol="ETH",
                amount="50.00",
            )
