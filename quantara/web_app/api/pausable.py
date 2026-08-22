"""
Admin pause controls and request guard for incident response.

Pause state is persisted in Redis so it propagates across all worker
processes.  A short in-memory cache avoids a Redis round-trip on every
request.  If Redis is unreachable the controller defaults to *paused*
(fail-closed) so that an infrastructure outage automatically suspends
user-facing operations.
"""

from __future__ import annotations

import asyncio
import hmac
import os
import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from web_app.api.errors import APIError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROTOCOL_PAUSED_DETAIL = "Protocol paused"
ADMIN_PAUSE_PREFIX = "/api/admin/pause"
PAUSE_ADMIN_TOKEN_ENV = "PAUSE_ADMIN_TOKEN"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
PAUSE_KEY = "protocol:paused"

_CACHE_TTL = 5  # seconds


# ---------------------------------------------------------------------------
# PauseController — Redis-backed with in-memory cache
# ---------------------------------------------------------------------------


class PauseController:
    """Redis-backed protocol pause switch.

    The pause flag is stored under ``PAUSE_KEY`` (``"1"`` = paused, key
    absent = unpaused).  A tiny in-memory cache with a configurable TTL
    prevents a Redis call on every single request.

    **Fail-closed**: if Redis is unavailable the controller reports
    *paused* so that an incident that takes down Redis also takes down
    user-facing operations (the safe default).
    """

    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

        # in-memory cache
        self._cache_value: bool = False
        self._cache_ts: float = 0.0

    # -- Redis lifecycle ----------------------------------------------------

    async def _get_redis(self) -> aioredis.Redis:
        """Lazy-initialise the Redis connection on first use."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url, decode_responses=True
            )
        return self._redis

    # -- public async API ---------------------------------------------------

    async def pause(self) -> bool:
        """Set the pause flag in Redis.  Returns the new paused state."""
        client = await self._get_redis()
        await client.set(PAUSE_KEY, "1")
        self._invalidate_cache()
        return True

    async def unpause(self) -> bool:
        """Clear the pause flag in Redis.  Returns the new paused state."""
        client = await self._get_redis()
        await client.delete(PAUSE_KEY)
        self._invalidate_cache()
        return False

    async def is_paused(self) -> bool:
        """Return whether the protocol is paused.

        Uses a short-lived in-memory cache to avoid hitting Redis on every
        request.  On Redis failure, defaults to *paused* (fail-closed).
        """
        now = time.monotonic()
        if (now - self._cache_ts) < _CACHE_TTL:
            return self._cache_value

        try:
            client = await self._get_redis()
            value = await client.get(PAUSE_KEY)
            paused = value == "1"
        except (aioredis.RedisError, OSError):
            paused = True  # fail-closed

        self._cache_value = paused
        self._cache_ts = now
        return paused

    # -- cache helpers ------------------------------------------------------

    def _invalidate_cache(self) -> None:
        self._cache_ts = 0.0


# Module-level singleton used by the middleware and router.
pause_controller = PauseController()

router = APIRouter(prefix=ADMIN_PAUSE_PREFIX, tags=["Admin"])


# ---------------------------------------------------------------------------
# Admin token helpers
# ---------------------------------------------------------------------------


def _admin_token() -> str | None:
    return os.getenv(PAUSE_ADMIN_TOKEN_ENV) or os.getenv("ADMIN_API_KEY")


def verify_admin_token(x_admin_token: str) -> None:
    """Raise :class:`APIError` if the supplied token does not match."""
    expected_token = _admin_token()
    if not expected_token or not hmac.compare_digest(x_admin_token, expected_token):
        raise APIError(
            status_code=403,
            code="admin_auth_required",
            detail="Admin authorization required",
        )


# ---------------------------------------------------------------------------
# Exempt-path check
# ---------------------------------------------------------------------------


def is_pause_exempt_path(path: str) -> bool:
    return (
        path.startswith(ADMIN_PAUSE_PREFIX)
        or path == "/health"
        or path.startswith("/metrics")
    )


# ---------------------------------------------------------------------------
# ASGI middleware
# ---------------------------------------------------------------------------


async def protocol_pause_middleware(request: Request, call_next):
    if (
        request.url.path.startswith("/api/")
        and not is_pause_exempt_path(request.url.path)
        and await pause_controller.is_paused()
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": PROTOCOL_PAUSED_DETAIL},
        )

    return await call_next(request)


# ---------------------------------------------------------------------------
# Router endpoints
# ---------------------------------------------------------------------------


@router.get("", summary="Get protocol pause status")
async def get_pause_status(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> dict:
    verify_admin_token(x_admin_token)
    paused = await pause_controller.is_paused()
    return {"paused": paused}


@router.post("", summary="Pause protocol user-facing operations")
async def pause_protocol(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> dict:
    verify_admin_token(x_admin_token)
    paused = await pause_controller.pause()
    return {"paused": paused}


@router.delete("", summary="Unpause protocol user-facing operations")
async def unpause_protocol(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> dict:
    verify_admin_token(x_admin_token)
    paused = await pause_controller.unpause()
    return {"paused": paused}
