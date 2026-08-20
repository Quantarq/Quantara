"""Tests for the Redis-backed pause controller and related helpers."""

from __future__ import annotations

import asyncio
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as aioredis

from web_app.api.pausable import (
    PauseController,
    is_pause_exempt_path,
    pause_controller,
    verify_admin_token,
)

# ---------------------------------------------------------------------------
# PauseController unit tests (no real Redis needed)
# ---------------------------------------------------------------------------


@pytest.fixture
def ctrl() -> PauseController:
    """Return a fresh PauseController with a mock Redis client."""
    controller = PauseController.__new__(PauseController)
    controller._redis_url = "redis://localhost:6379"
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock()
    mock_client.delete = AsyncMock()
    controller._redis = mock_client
    controller._cache_value = False
    controller._cache_ts = 0.0
    return controller


@pytest.mark.asyncio
async def test_pause_sets_redis_key(ctrl: PauseController):
    result = await ctrl.pause()
    ctrl._redis.set.assert_awaited_once_with("protocol:paused", "1")
    assert result is True


@pytest.mark.asyncio
async def test_unpause_deletes_redis_key(ctrl: PauseController):
    result = await ctrl.unpause()
    ctrl._redis.delete.assert_awaited_once_with("protocol:paused")
    assert result is False


@pytest.mark.asyncio
async def test_is_paused_true_when_key_present(ctrl: PauseController):
    ctrl._redis.get = AsyncMock(return_value="1")
    assert await ctrl.is_paused() is True


@pytest.mark.asyncio
async def test_is_paused_false_when_key_absent(ctrl: PauseController):
    ctrl._redis.get = AsyncMock(return_value=None)
    assert await ctrl.is_paused() is False


@pytest.mark.asyncio
async def test_cache_avoids_repeated_redis_calls(ctrl: PauseController):
    ctrl._redis.get = AsyncMock(return_value=None)
    # first call — cache miss
    assert await ctrl.is_paused() is False
    assert ctrl._redis.get.await_count == 1
    # second call — served from cache, no extra Redis call
    assert await ctrl.is_paused() is False
    assert ctrl._redis.get.await_count == 1


@pytest.mark.asyncio
async def test_cache_invalidation_on_pause(ctrl: PauseController):
    ctrl._redis.get = AsyncMock(return_value=None)
    await ctrl.is_paused()
    await ctrl.pause()
    ctrl._redis.get = AsyncMock(return_value="1")
    # cache should be invalidated, so this hits Redis again
    assert await ctrl.is_paused() is True


@pytest.mark.asyncio
async def test_fail_closed_on_redis_error(ctrl: PauseController):
    ctrl._redis.get = AsyncMock(side_effect=aioredis.RedisError("connection refused"))
    assert await ctrl.is_paused() is True


@pytest.mark.asyncio
async def test_fail_closed_on_os_error(ctrl: PauseController):
    ctrl._redis.get = AsyncMock(side_effect=OSError("network unreachable"))
    assert await ctrl.is_paused() is True


@pytest.mark.asyncio
async def test_cache_refreshes_after_ttl(ctrl: PauseController):
    import time

    ctrl._redis.get = AsyncMock(return_value=None)
    await ctrl.is_paused()
    assert ctrl._redis.get.await_count == 1

    # simulate TTL expiry
    ctrl._cache_ts = time.monotonic() - 10
    ctrl._redis.get = AsyncMock(return_value="1")
    assert await ctrl.is_paused() is True
    assert ctrl._redis.get.await_count == 1


# ---------------------------------------------------------------------------
# verify_admin_token — constant-time comparison
# ---------------------------------------------------------------------------


def test_verify_admin_token_accepts_valid(monkeypatch):
    monkeypatch.setenv("PAUSE_ADMIN_TOKEN", "super-secret")
    verify_admin_token("super-secret")  # should not raise


def test_verify_admin_token_rejects_wrong(monkeypatch):
    monkeypatch.setenv("PAUSE_ADMIN_TOKEN", "super-secret")
    with pytest.raises(Exception):
        verify_admin_token("wrong-token")


def test_verify_admin_token_uses_constant_time(monkeypatch):
    monkeypatch.setenv("PAUSE_ADMIN_TOKEN", "secret")
    with patch("web_app.api.pausable.hmac.compare_digest", wraps=hmac.compare_digest) as mock_cmp:
        verify_admin_token("secret")
        mock_cmp.assert_called_once_with("secret", "secret")


def test_verify_admin_token_raises_api_error(monkeypatch):
    monkeypatch.setenv("PAUSE_ADMIN_TOKEN", "tok")
    from web_app.api.errors import APIError
    with pytest.raises(APIError) as exc_info:
        verify_admin_token("bad")
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "admin_auth_required"


# ---------------------------------------------------------------------------
# Exempt paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/pause",
        "/api/admin/pause/status",
        "/health",
        "/metrics/something",
    ],
)
def test_exempt_paths(path: str):
    assert is_pause_exempt_path(path) is True


def test_non_exempt_path():
    assert is_pause_exempt_path("/api/check-user") is False


# ---------------------------------------------------------------------------
# Integration-style tests — middleware blocks when paused
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_middleware_blocks_when_paused():
    with patch.object(pause_controller, "is_paused", new_callable=lambda: AsyncMock(return_value=True)):
        mock_request = MagicMock()
        mock_request.url.path = "/api/check-user"
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        from web_app.api.pausable import protocol_pause_middleware

        response = await protocol_pause_middleware(mock_request, mock_call_next)
        assert response.status_code == 503
        mock_call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_middleware_passes_when_unpaused():
    with patch.object(pause_controller, "is_paused", new_callable=lambda: AsyncMock(return_value=False)):
        mock_request = MagicMock()
        mock_request.url.path = "/api/check-user"
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        from web_app.api.pausable import protocol_pause_middleware

        response = await protocol_pause_middleware(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ["/health", "/metrics/foo", "/api/admin/pause"],
)
async def test_middleware_exempt_paths_always_pass(path: str):
    with patch.object(pause_controller, "is_paused", new_callable=lambda: AsyncMock(return_value=True)):
        mock_request = MagicMock()
        mock_request.url.path = path
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        from web_app.api.pausable import protocol_pause_middleware

        response = await protocol_pause_middleware(mock_request, mock_call_next)
        assert response.status_code == 200
