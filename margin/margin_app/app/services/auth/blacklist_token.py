"""
Token blacklist service for invalidating refresh tokens.
"""

from datetime import datetime, timezone
from typing import Set
from loguru import logger


class TokenBlacklistService:
    """
    token blacklist service.
    """

    def __init__(self):
        self._blacklisted_tokens: Set[str] = set()

    def blacklist_token(self, token: str) -> None:
        """
        Add a token to the blacklist.

        Args:
            token: The refresh token to blacklist
        """
        self._blacklisted_tokens.add(token)
        logger.info(f"Token blacklisted at {datetime.now(timezone.utc)}")

    def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: The token to check

        Returns:
            bool: True if token is blacklisted, False otherwise
        """
        return token in self._blacklisted_tokens

    def clear_blacklist(self) -> None:
        """Clear all blacklisted tokens (for testing purposes)."""
        self._blacklisted_tokens.clear()


token_blacklist = TokenBlacklistService()
