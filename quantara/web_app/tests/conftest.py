"""
This module contains the fixtures for the tests.
"""

import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import scoped_session

from web_app.api.main import app
from web_app.api.rate_limiter import limiter as _ORIGINAL_LIMITER
from web_app.api.wallet_auth import verify_wallet_signature
from web_app.db.crud import DBConnector, PositionDBConnector, UserDBConnector
from web_app.db.database import get_database
from web_app.db.models import ExtraDeposit


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable rate limiting in all tests to avoid Redis dependency.

    Three separate Limiter instances can exist during a test run:
      1. _ORIGINAL_LIMITER -- created when rate_limiter.py was first loaded;
         all @limiter.limit() wrappers in user.py, vault.py, etc. close over it.
      2. A reloaded limiter -- TestRateLimiterConfig calls importlib.reload(),
         which creates a fresh instance and updates the module-level name.
      3. A memory_limiter -- TestRateLimitEnforcement swaps app.state.limiter for
         an in-memory instance so tests don't need Redis.
    We collect every unique instance we can find and disable them all so that
    the middleware, the decorator wrappers, and direct function calls all skip
    rate limiting during tests.
    """
    limiters: set = set()
    limiters.add(_ORIGINAL_LIMITER)
    limiters.add(app.state.limiter)
    rate_limiter_mod = sys.modules.get("web_app.api.rate_limiter")
    if rate_limiter_mod is not None:
        limiters.add(rate_limiter_mod.limiter)

    for lim in limiters:
        lim.enabled = False
    yield
    for lim in limiters:
        lim.enabled = True


@pytest.fixture(autouse=True)
def bypass_wallet_auth():
    """Bypass wallet signature verification for all tests.

    Adds a dependency override so every endpoint that Depends(verify_wallet_signature)
    receives a fixed wallet_id of "test_wallet" without any real signature exchange.
    This keeps tests decoupled from the nonce store and stellar-sdk crypto.

    The override is removed (not cleared, to preserve other overrides) after each test.
    """
    app.dependency_overrides[verify_wallet_signature] = lambda: "test_wallet"
    yield
    app.dependency_overrides.pop(verify_wallet_signature, None)


def dict_to_object(data: dict, **kwargs) -> object:
    """
    Convert a dictionary to an attribute object
    :param data: dict
    :return: object
    """

    class Object:
        """
        Object class
        """

        def __init__(self, **_kwargs):
            self.__dict__.update(_kwargs)

    return Object(**data, **kwargs)


@pytest.fixture(scope="module")
def client() -> None:
    """
    A client mock fixture.
    """
    mock_db_connector = MagicMock(spec=DBConnector)
    app.dependency_overrides[get_database] = lambda: mock_db_connector

    with TestClient(app=app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def mock_db_connector() -> None:
    """
    Mock DBConnector
    :return: None
    """
    mock_connector = MagicMock(spec=DBConnector)
    yield mock_connector


@pytest.fixture(scope="module")
def mock_user_db_connector() -> None:
    """
    Mock for UserDBConnector
    :return: None
    """
    mock_user_connector = MagicMock(spec=UserDBConnector)
    yield mock_user_connector


@pytest.fixture(scope="module")
def mock_position_db_connector() -> None:
    """
    Mock for PositionDBConnector
    :return: None
    """
    mock_position_connector = MagicMock(spec=PositionDBConnector)
    yield mock_position_connector


@pytest.fixture
def mock_extra_deposit():
    """Fixture for mocking ExtraDeposit instances"""
    return ExtraDeposit(
        id=uuid.uuid4(), token_symbol="XLM", amount="1.0", position_id=uuid.uuid4()
    )


@pytest.fixture(scope="function")
def mock_db_session():
    """Fixture to create a mock database session."""
    with patch.object(scoped_session, "__call__") as mock_scoped_session_call:
        mock_db_session = MagicMock()
        mock_db_session.__enter__.return_value = mock_db_session
        mock_db_session.__exit__.return_value = None
        mock_scoped_session_call.return_value = mock_db_session
        yield mock_db_session
