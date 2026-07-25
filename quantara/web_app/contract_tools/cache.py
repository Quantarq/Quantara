import asyncio
import json
import logging
import os
from typing import Awaitable, Callable, Optional

import redis as redis_sync
import redis.asyncio as redis

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
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


async def get_cached_or_fetch(
    key: str,
    ttl: int,
    fetch_fn: Callable[[], Awaitable],
):
    """Return cached value for key, or execute fetch_fn on miss."""
    pool = await get_redis_pool()
    client = redis.Redis(connection_pool=pool)
    try:
        try:
            cached = await client.get(key)
            if cached is not None:
                return json.loads(cached)
        except Exception as exc:
            logger.warning(
                "Cache read error (%s), falling through to fetch.", exc
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


def delete_cache_pattern_sync(pattern: str) -> None:
    """Best-effort synchronous cache invalidation for DB lifecycle hooks."""
    client = redis_sync.Redis.from_url(_REDIS_URL, decode_responses=True)
    try:
        keys = list(client.scan_iter(match=pattern))
        if keys:
            client.delete(*keys)
    except Exception as exc:
        logger.warning("Cache invalidation failed for %s: %s", pattern, exc)
    finally:
        client.close()


def invalidate_leaderboard_cache() -> None:
    """Clear cached leaderboard aggregates after position lifecycle changes."""
    delete_cache_pattern_sync("leaderboard:*")