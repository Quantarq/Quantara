import secrets
import os
import redis.asyncio as redis
from typing import Optional

# Using the same redis URL logic as the rate limiter and other tools
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_TTL = 60 * 60 * 24 * 7  # 7 days

class SessionStore:
    def __init__(self):
        self.client = redis.from_url(REDIS_URL, decode_responses=True)

    async def create_session(self, wallet_id: str) -> str:
        """Create a new session, store in Redis, and return the token."""
        token = secrets.token_urlsafe(32)
        # Store mapping: token -> wallet_id
        await self.client.setex(f"session:{token}", SESSION_TTL, wallet_id)
        return token

    async def get_wallet_id(self, token: str) -> Optional[str]:
        """Retrieve wallet_id for a given token."""
        return await self.client.get(f"session:{token}")

    async def delete_session(self, token: str):
        """Delete a session."""
        await self.client.delete(f"session:{token}")

# Singleton instance for the application
session_store = SessionStore()
