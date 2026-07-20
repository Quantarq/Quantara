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
from web_app.api.rate_limiter import limiter
from web_app.api.session import session_store
from web_app.api.wallet_auth import verify_wallet_signature
from web_app.db.crud import DBConnector, PositionDBConnector, UserDBConnector
from web_app.db.database import get_database
from web_app.db.models import ExtraDeposit


@pytest.fixture(autouse=True)
def disable_rate_limiter_globally():
    """Globally disable rate limiting on LazyLimiter instance during tests."""
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(autouse=True)
def mock_redis_and_session():
    """Globally mock Redis connection and session store calls to prevent localhost:6379 errors."""
    with patch("redis.asyncio.Redis.from_url") as mock_from_url, \
         patch("redis.Redis.from_url") as mock_sync_from_url, \
         patch.object(session_store, "get_wallet_id", new_callable=AsyncMock) as mock_get_wallet, \
         patch.object(session_store, "create_session", new_callable=AsyncMock) as mock_create_session:
        
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis
        mock_sync_from_url.return_value = MagicMock()
        
        mock_get_wallet.return_value = "G_VALID_WALLET"
        mock_create_session.return_value = "opaque_test_session_token_1234567890_32chars"
        
        yield mock_redis


@pytest.fixture(autouse=True)
def bypass_wallet_auth():
    """Bypass wallet signature verification for all tests."""
    app.dependency_overrides[verify_wallet_signature] = lambda: "test_wallet"
    yield
    app.dependency_overrides.pop(verify_wallet_signature, None)


def dict_to_object(data: dict, **kwargs) -> object:
    class Object:
        def __init__(self, **_kwargs):
            self.__dict__.update(_kwargs)

    return Object(**data, **kwargs)


@pytest.fixture(scope="module")
def client() -> None:
    mock_db_connector = MagicMock(spec=DBConnector)
    app.dependency_overrides[get_database] = lambda: mock_db_connector

    with TestClient(app=app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def mock_db_connector() -> None:
    mock_connector = MagicMock(spec=DBConnector)
    yield mock_connector


@pytest.fixture(scope="module")
def mock_user_db_connector() -> None:
    mock_user_connector = MagicMock(spec=UserDBConnector)
    yield mock_user_connector


@pytest.fixture(scope="module")
def mock_position_db_connector() -> None:
    mock_position_connector = MagicMock(spec=PositionDBConnector)
    yield mock_position_connector


@pytest.fixture
def mock_extra_deposit():
    return ExtraDeposit(
        id=uuid.uuid4(), token_symbol="XLM", amount="1.0", position_id=uuid.uuid4()
    )


@pytest.fixture(scope="function")
def mock_db_session():
    with patch.object(scoped_session, "__call__") as mock_scoped_session_call:
        mock_db_session = MagicMock()
        mock_db_session.__enter__.return_value = mock_db_session
        mock_db_session.__exit__.return_value = None
        mock_scoped_session_call.return_value = mock_db_session
        yield mock_db_session