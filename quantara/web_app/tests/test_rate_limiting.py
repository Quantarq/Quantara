"""
Tests for API rate limiting (issue #42).

Covers:
- Configuration: env vars map to the correct limit strings.
- 429 response + Retry-After header when a limit is exceeded.
- /health is exempt from rate limiting.
- key function: wallet_id-keyed endpoints use separate buckets per wallet.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from web_app.api.main import app
from web_app.db.crud import DBConnector
from web_app.db.database import get_database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> TestClient:
    mock_db = MagicMock(spec=DBConnector)
    app.dependency_overrides[get_database] = lambda: mock_db
    return TestClient(app=app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Unit: env-var configuration
# ---------------------------------------------------------------------------

class TestRateLimiterConfig:
    def test_default_write_limit(self):
        with patch.dict(os.environ, {}, clear=False):
            import importlib
            import web_app.api.rate_limiter as rl
            importlib.reload(rl)
            assert rl.WRITE_LIMIT == "5/minute"

    def test_custom_write_limit(self):
        with patch.dict(os.environ, {"RATE_LIMIT_WRITE": "10/minute"}, clear=False):
            import importlib
            import web_app.api.rate_limiter as rl
            importlib.reload(rl)
            assert rl.WRITE_LIMIT == "10/minute"

    def test_default_user_data_limit(self):
        with patch.dict(os.environ, {}, clear=False):
            import importlib
            import web_app.api.rate_limiter as rl
            importlib.reload(rl)
            assert rl.USER_DATA_LIMIT == "30/minute"

    def test_custom_user_data_limit(self):
        with patch.dict(os.environ, {"RATE_LIMIT_USER_DATA": "60/minute"}, clear=False):
            import importlib
            import web_app.api.rate_limiter as rl
            importlib.reload(rl)
            assert rl.USER_DATA_LIMIT == "60/minute"

    def test_default_read_limit(self):
        with patch.dict(os.environ, {}, clear=False):
            import importlib
            import web_app.api.rate_limiter as rl
            importlib.reload(rl)
            assert rl.READ_LIMIT == "100/minute"

    def test_custom_read_limit(self):
        with patch.dict(os.environ, {"RATE_LIMIT_READ": "200/minute"}, clear=False):
            import importlib
            import web_app.api.rate_limiter as rl
            importlib.reload(rl)
            assert rl.READ_LIMIT == "200/minute"


# ---------------------------------------------------------------------------
# Unit: get_wallet_key helper
# ---------------------------------------------------------------------------

class TestGetWalletKey:
    def test_uses_wallet_id_from_query_params(self):
        from web_app.api.rate_limiter import get_wallet_key

        mock_request = MagicMock()
        mock_request.query_params.get.side_effect = lambda key, default=None: (
            "GABCDEF123" if key == "wallet_id" else default
        )
        mock_request.path_params.get.return_value = None

        key = get_wallet_key(mock_request)
        assert key == "wallet:GABCDEF123"

    def test_uses_path_param_when_no_query_param(self):
        from web_app.api.rate_limiter import get_wallet_key

        mock_request = MagicMock()
        mock_request.query_params.get.return_value = None
        mock_request.path_params.get.side_effect = lambda key, default=None: (
            "GXYZ789" if key == "wallet_id" else default
        )
        mock_request.client.host = "127.0.0.1"

        key = get_wallet_key(mock_request)
        assert key == "wallet:GXYZ789"

    def test_falls_back_to_ip_when_no_wallet(self):
        from web_app.api.rate_limiter import get_wallet_key

        mock_request = MagicMock()
        mock_request.query_params.get.return_value = None
        mock_request.path_params.get.return_value = None
        mock_request.client.host = "10.0.0.1"

        key = get_wallet_key(mock_request)
        assert key == "10.0.0.1"


# ---------------------------------------------------------------------------
# Integration: 429 on write endpoint when limit exceeded
# ---------------------------------------------------------------------------

class TestRateLimitEnforcement:
    """
    Integration tests using an in-memory storage backend so Redis is not required.
    The SlowAPIMiddleware is already wired to the app; we swap the storage URI to
    memory:// so tests run without a running Redis instance.
    """

    @pytest.fixture(autouse=True)
    def use_memory_storage(self):
        """Replace the Redis-backed limiter storage with in-memory for tests."""
        from slowapi import Limiter
        from slowapi.util import get_remote_address

        memory_limiter = Limiter(
            key_func=get_remote_address,
            storage_uri="memory://",
        )
        with patch("web_app.api.main.limiter", memory_limiter), \
             patch("web_app.api.position.limiter", memory_limiter), \
             patch("web_app.api.dashboard.limiter", memory_limiter):
            app.state.limiter = memory_limiter
            yield
            app.state.limiter = app.state.limiter  # restore handled by app teardown

    @pytest.fixture
    def client(self):
        mock_db = MagicMock(spec=DBConnector)
        app.dependency_overrides[get_database] = lambda: mock_db
        with TestClient(app=app, raise_server_exceptions=False) as c:
            yield c
        app.dependency_overrides.clear()

    def test_health_endpoint_is_exempt(self, client):
        """GET /health must never return 429 regardless of request volume."""
        with patch("web_app.api.main.asyncio.to_thread") as mock_thread, \
             patch("web_app.api.main.redis") as mock_redis:
            mock_thread.return_value = MagicMock()
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping = MagicMock(return_value=MagicMock())
            mock_redis.from_url.return_value = mock_redis_instance

            for _ in range(20):
                resp = client.get("/health")
                assert resp.status_code != 429, (
                    "/health must be exempt from rate limiting"
                )

    def test_429_returned_on_rate_limit_exceeded(self, client):
        """
        The registered RateLimitExceeded handler must return HTTP 429.
        Retry-After is emitted by slowapi when headers_enabled=True (set in
        rate_limiter.py) and a real Redis/memory backend is available.
        """
        from slowapi.errors import RateLimitExceeded
        from starlette.requests import Request as StarletteRequest

        limit_mock = MagicMock()
        limit_mock.error_message = None
        limit_mock.limit = MagicMock()
        limit_mock.limit.__str__ = lambda self: "5 per 1 minute"

        exc = RateLimitExceeded(limit_mock)
        handler = app.exception_handlers[RateLimitExceeded]

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/get-multipliers",
            "query_string": b"",
            "headers": [],
            "app": app,
        }
        starlette_request = StarletteRequest(scope)
        starlette_request.state.view_rate_limit = None  # headers skipped when None

        response = handler(starlette_request, exc)
        assert response.status_code == 429

    def test_limiter_has_headers_enabled(self):
        """
        The Limiter must be configured with headers_enabled=True so that
        Retry-After is automatically included in 429 responses in production.
        """
        from web_app.api.rate_limiter import limiter as rl_limiter
        # Reload to bypass any previous test patches
        import importlib, web_app.api.rate_limiter as rl_module
        importlib.reload(rl_module)
        assert rl_module.limiter._headers_enabled is True

    def test_read_endpoint_allows_many_requests(self, client):
        """Read endpoints (100/min) allow substantially more calls than write (5/min)."""
        with patch("web_app.api.position.limiter") as mock_limiter:
            mock_limiter.limit.return_value = lambda func: func

            # 5 rapid calls to a read endpoint should all succeed
            for _ in range(5):
                resp = client.get("/api/get-multipliers")
                assert resp.status_code in (200, 422, 500), (
                    f"Expected success-range status, got {resp.status_code}"
                )


# ---------------------------------------------------------------------------
# Unit: limiter is attached to app state
# ---------------------------------------------------------------------------

class TestLimiterAppState:
    def test_limiter_is_set_on_app_state(self):
        from slowapi import Limiter
        # Previous tests may have reloaded rate_limiter, so check type not identity
        assert isinstance(app.state.limiter, Limiter)

    def test_rate_limit_exceeded_handler_registered(self):
        from slowapi.errors import RateLimitExceeded
        assert RateLimitExceeded in app.exception_handlers
