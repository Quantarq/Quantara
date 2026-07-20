"""
Notification deduplication with exponential backoff for Telegram alerts.
"""

import json
import logging
import os
import time

import redis.asyncio as redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
KEY_PREFIX = "qa:notif"
DEDUPE_TTL = 4 * 3600  # 4 hours in seconds

BACKOFF_SCHEDULE = [0, 60, 300, 1800]  # 1st=immediate, 2nd=60s, 3rd=5m, 4th=30m
CIRCUIT_BREAK_THRESHOLD = 3  # skip after 3 consecutive misses


class NotificationDedupe:
    """Per-user per-position deduplication with exponential backoff."""

    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self._redis_url = redis_url
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    def _key(self, telegram_id: str, position_id: str) -> str:
        return f"{KEY_PREFIX}:{telegram_id}:{position_id}"

    async def should_send(self, telegram_id: str, position_id: str) -> bool:
        """Return True if the notification should be sent (not deduped)."""
        try:
            client = await self._get_client()
            key = self._key(telegram_id, position_id)
            raw = await client.get(key)
            if raw is None:
                return True

            data = json.loads(raw)
            count = data.get("count", 0)
            last_ts = data.get("last_ts", 0)
            elapsed = time.time() - last_ts

            if count >= CIRCUIT_BREAK_THRESHOLD:
                idx = min(count - 1, len(BACKOFF_SCHEDULE) - 1)
                if elapsed < BACKOFF_SCHEDULE[idx]:
                    logger.debug(
                        "Dedupe: circuit-break for %s:%s (%d misses, %.0fs elapsed)",
                        telegram_id, position_id, count, elapsed,
                    )
                    return False

            idx = min(count, len(BACKOFF_SCHEDULE) - 1)
            if elapsed < BACKOFF_SCHEDULE[idx]:
                logger.debug(
                    "Dedupe: skip for %s:%s (%d sends, %.0fs elapsed)",
                    telegram_id, position_id, count, elapsed,
                )
                return False

            return True

        except Exception as e:
            logger.error("Dedupe check failed, allowing send: %s", e)
            return True

    async def record_send(self, telegram_id: str, position_id: str) -> None:
        """Record that a notification was sent (increment count)."""
        try:
            client = await self._get_client()
            key = self._key(telegram_id, position_id)
            raw = await client.get(key)
            if raw is None:
                data = {"count": 1, "last_ts": time.time()}
            else:
                data = json.loads(raw)
                data["count"] = data.get("count", 0) + 1
                data["last_ts"] = time.time()
            await client.set(key, json.dumps(data), ex=DEDUPE_TTL)
        except Exception as e:
            logger.error("Dedupe record_send failed: %s", e)

    async def record_success(self, telegram_id: str, position_id: str) -> None:
        """Record a successful send – reset count on success."""
        try:
            client = await self._get_client()
            key = self._key(telegram_id, position_id)
            data = {"count": 0, "last_ts": time.time()}
            await client.set(key, json.dumps(data), ex=DEDUPE_TTL)
        except Exception as e:
            logger.error("Dedupe record_success failed: %s", e)

    async def record_failure(self, telegram_id: str, position_id: str) -> None:
        """Record a failed send (increment failure count)."""
        try:
            client = await self._get_client()
            key = self._key(telegram_id, position_id)
            raw = await client.get(key)
            if raw is None:
                data = {"count": 1, "last_ts": time.time()}
            else:
                data = json.loads(raw)
                data["count"] = data.get("count", 0) + 1
                data["last_ts"] = time.time()
            await client.set(key, json.dumps(data), ex=DEDUPE_TTL)
        except Exception as e:
            logger.error("Dedupe record_failure failed: %s", e)
