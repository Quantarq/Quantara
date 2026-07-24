import asyncio
import json
import logging
import os
from typing import Awaitable, Callable, Optional

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


async def delete_cache_pattern(pattern: str) -> None:
    """Delete cached entries matching a Redis SCAN pattern."""
    pool = await get_redis_pool()
    client = redis.Redis(connection_pool=pool)
    try:
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await client.delete(*keys)
            if cursor == 0:
                break
    except Exception as exc:
        logger.warning("Cache invalidation failed for %s: %s", pattern, exc)
    finally:
        await client.close()