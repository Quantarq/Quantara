"""
This module provides nonce generation and validation for deep-link replay protection.

Nonces are stored in-memory with a configurable TTL (default 5 minutes).
Each nonce is single-use and deleted after successful validation.
"""

import time
from typing import Optional

import secrets

NONCE_TTL_SECONDS = 300  # 5 minutes


class NonceStore:
    """In-memory nonce store with TTL-based expiry."""

    def __init__(self, ttl: int = NONCE_TTL_SECONDS):
        self._store: dict[str, tuple[str, float]] = {}
        self._ttl = ttl

    def generate(self, user_id: str) -> str:
        """Generate a nonce for the given user_id and store it.

        Returns the generated nonce string.
        """
        nonce = secrets.token_urlsafe(32)
        self._store[nonce] = (user_id, time.time())
        return nonce

    def validate(self, nonce: str, expected_user_id: str) -> bool:
        """Validate a nonce.

        - Checks the nonce exists
        - Checks the user_id matches
        - Checks the TTL has not expired
        - Deletes the nonce after successful validation (single-use)

        Returns True if valid, False otherwise.
        """
        entry = self._store.pop(nonce, None)
        if entry is None:
            return False

        stored_user_id, created_at = entry
        if stored_user_id != expected_user_id:
            return False

        if time.time() - created_at > self._ttl:
            return False

        return True

    def cleanup_expired(self) -> int:
        """Remove expired nonces. Returns the number of entries removed."""
        now = time.time()
        expired = [
            k for k, (_, created_at) in self._store.items()
            if now - created_at > self._ttl
        ]
        for k in expired:
            del self._store[k]
        return len(expired)


# Singleton instance used by the app
nonce_store = NonceStore()
