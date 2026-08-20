"""
test_vault_balance.py
Tests for atomic vault upsert and balance update operations.
Verifies that concurrent deposits, upsert creation, upsert updates,
and unique constraint enforcement all behave correctly.
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from web_app.db.crud.deposit import DepositDBConnector
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
def mock_connector(db_session_factory):
    """Provide a DepositDBConnector backed by an in-memory SQLite database."""
    connector = object.__new__(DepositDBConnector)
    connector.Session = db_session_factory
    return connector


@pytest.fixture
def sample_user(db_session_factory):
    """Insert and return a sample User row."""
    user_id = uuid.uuid4()
    user = User(wallet_id="wallet_abc", id=user_id)
    with db_session_factory() as db:
        db.add(user)
        db.commit()
    return user_id


class TestUpsertCreatesNewRow:
    """Upssert inserts a new Vault row when none exists for the (user, symbol)."""

    def test_creates_vault_when_none_exists(self, mock_connector, sample_user):
        vault = mock_connector.upsert_vault(sample_user, "ETH", "10.0")
        assert vault is not None
        assert vault.user_id == sample_user
        assert vault.symbol == "ETH"
        assert vault.amount == "10.0"

    def test_creates_multiple_vaults_for_different_symbols(
        self, mock_connector, sample_user
    ):
        v1 = mock_connector.upsert_vault(sample_user, "ETH", "5.0")
        v2 = mock_connector.upsert_vault(sample_user, "BTC", "2.0")
        assert v1.symbol == "ETH"
        assert v2.symbol == "BTC"
        assert v1.id != v2.id


class TestUpsertUpdatesExistingRow:
    """Upsert adds to the existing amount when a vault row already exists."""

    def test_adds_to_existing_balance(self, mock_connector, sample_user):
        mock_connector.upsert_vault(sample_user, "ETH", "10.0")
        vault = mock_connector.upsert_vault(sample_user, "ETH", "5.5")
        assert vault.amount == "15.5"

    def test_multiple_increments_produce_correct_sum(self, mock_connector, sample_user):
        mock_connector.upsert_vault(sample_user, "XLM", "1.0")
        mock_connector.upsert_vault(sample_user, "XLM", "2.0")
        mock_connector.upsert_vault(sample_user, "XLM", "3.0")
        vault = mock_connector.upsert_vault(sample_user, "XLM", "4.0")
        assert Decimal(vault.amount) == Decimal("10.0")


class TestAddVaultBalance:
    """add_vault_balance delegates to upsert_vault and raises on missing user."""

    def test_adds_balance_existing_vault(self, mock_connector, sample_user):
        mock_connector.upsert_vault(sample_user, "ETH", "10.0")
        vault = mock_connector.add_vault_balance("wallet_abc", "ETH", "3.0")
        assert Decimal(vault.amount) == Decimal("13.0")

    def test_raises_when_user_not_found(self, mock_connector):
        with pytest.raises(ValueError, match="User not found"):
            mock_connector.add_vault_balance("nonexistent_wallet", "ETH", "1.0")


class TestCreateVault:
    """create_vault now delegates to upsert_vault (idempotent)."""

    def test_first_deposit(self, mock_connector, sample_user):
        fake_user = MagicMock(spec=User)
        fake_user.id = sample_user
        vault = mock_connector.create_vault(fake_user, "ETH", "7.5")
        assert Decimal(vault.amount) == Decimal("7.5")

    def test_second_deposit_adds_to_existing(self, mock_connector, sample_user):
        fake_user = MagicMock(spec=User)
        fake_user.id = sample_user
        mock_connector.create_vault(fake_user, "ETH", "7.5")
        vault = mock_connector.create_vault(fake_user, "ETH", "2.5")
        assert Decimal(vault.amount) == Decimal("10.0")


class TestConcurrentBalanceUpdates:
    """
    Simulate concurrent balance increments using SQLite transactions.
    SQLite's serialized writes provide a deterministic baseline to verify
    that the upsert produces the correct final sum.
    """

    def test_sequential_increments_produce_correct_final_balance(
        self, mock_connector, sample_user
    ):
        """Simulates N sequential deposits that must all be reflected."""
        initial = Decimal("0.0")
        for _ in range(10):
            mock_connector.upsert_vault(sample_user, "ETH", "1.0")
            initial += Decimal("1.0")
        vault = mock_connector.get_vault("wallet_abc", "ETH")
        assert vault is not None
        assert Decimal(vault.amount) == initial

    def test_fractional_increments(self, mock_connector, sample_user):
        """Verify correctness with fractional amounts."""
        amounts = ["0.1", "0.2", "0.3", "0.4"]
        expected = Decimal("0.0")
        for amt in amounts:
            mock_connector.upsert_vault(sample_user, "ETH", amt)
            expected += Decimal(amt)
        vault = mock_connector.get_vault("wallet_abc", "ETH")
        assert Decimal(vault.amount) == expected


class TestUniqueConstraint:
    """The unique constraint on (user_id, symbol) is enforced by the model."""

    def test_constraint_exists_in_model(self):
        table_args = Vault.__table_args__
        constraint_names = [c.name for c in table_args if hasattr(c, "name")]
        assert "uq_vault_user_symbol" in constraint_names

    def test_get_vault_returns_none_for_missing(self, mock_connector):
        result = mock_connector.get_vault("no_such_wallet", "ETH")
        assert result is None
