import asyncio
import json
import logging
import os
from typing import Awaitable, Callable, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_REFRESH_CLAIM_SECONDS = 5
_REFRESH_POLL_SECONDS = 0.1
_pool: Optional[redis.ConnectionPool] = None
_pool_lock = asyncio.Lock()


async def get_redis_pool() -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = redis.ConnectionPool.from_url(
                    _REDIS_URL, decode_responses=True
                )
    return _pool


async def _read_cached_value(client: redis.Redis, key: str):
    cached = await client.get(key)
    if cached is None:
        return None
    return json.loads(cached)


async def _wait_for_refresh(client: redis.Redis, key: str):
    deadline = asyncio.get_running_loop().time() + _REFRESH_CLAIM_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(_REFRESH_POLL_SECONDS)
        cached = await _read_cached_value(client, key)
        if cached is not None:
            return cached
    return None


async def get_cached_or_fetch(
    key: str,
    ttl: int,
    fetch_fn: Callable[[], Awaitable],
):
    """Return cached value for key, or execute fetch_fn on miss.

    A cache miss first attempts a short Redis SET NX claim so only one caller
    refreshes an expired key. Concurrent callers wait up to five seconds for the
    claimer to publish the value before falling back to their own fetch.
    """
    pool = await get_redis_pool()
    client = redis.Redis(connection_pool=pool)
    claim_key = f"{key}:refresh-lock"
    try:
        try:
            cached = await _read_cached_value(client, key)
            if cached is not None:
                return cached
        except Exception as exc:
            logger.warning(
                "Cache read error (%s), falling through to fetch.", exc
            )

        try:
            claimed = await client.set(
                claim_key, "1", nx=True, ex=_REFRESH_CLAIM_SECONDS
            )
        except Exception as exc:
            logger.warning(
                "Cache refresh claim failed for %s: %s", key, exc
            )
            claimed = True

        if not claimed:
            try:
                refreshed = await _wait_for_refresh(client, key)
                if refreshed is not None:
                    return refreshed
            except Exception as exc:
                logger.warning(
                    "Cache refresh wait failed for %s: %s", key, exc
                )

        value = await fetch_fn()
        try:
            await client.set(
                key, json.dumps(value, default=str), ex=ttl
            )
        except Exception as exc:
            logger.warning("Cache write failed for %s: %s", key, exc)
        return value
    finally:
        await client.close()