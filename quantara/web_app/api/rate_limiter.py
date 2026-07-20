"""
Rate limiting configuration for the QUANTARA API.

Provides a single Limiter instance backed by Redis and three tiered limit
strings that are read from environment variables at startup so they can be
adjusted per environment without a code change.

Tiers
-----
WRITE_LIMIT      : mutation endpoints (create/close position, auth connect, etc.)
USER_DATA_LIMIT  : per-user data endpoints (dashboard, user positions, repay data)
READ_LIMIT       : cheap read-only endpoints (multipliers, leaderboard, etc.)

Key functions
-------------
get_wallet_key   : keys by wallet_id from query/path params, falls back to IP.
                   Use this on endpoints that carry wallet_id so that a single
                   IP running multiple wallets isn't unfairly throttled.
"""

import asyncio
import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

WRITE_LIMIT: str = os.getenv("RATE_LIMIT_WRITE", "5/minute")
USER_DATA_LIMIT: str = os.getenv("RATE_LIMIT_USER_DATA", "30/minute")
READ_LIMIT: str = os.getenv("RATE_LIMIT_READ", "100/minute")


def get_wallet_key(request: Request) -> str:
    wallet_id = request.query_params.get("wallet_id") or request.path_params.get(
        "wallet_id"
    )
    if wallet_id:
        return f"wallet:{wallet_id}"
    return get_remote_address(request)


def get_limiter(request: Request) -> Limiter:
    return request.app.state.limiter


class LazyLimiter:
    def __init__(self):
        # Placeholder limiter just to provide the .limit() method
        self._limiter = Limiter(key_func=get_remote_address)
        self.enabled = True

    def limit(self, *args, **kwargs):
        real_decorator = self._limiter.limit(*args, **kwargs)

        def decorator(func):
            @wraps(func)
            async def wrapper(*func_args, **func_kwargs):
                if not self.enabled:
                    return await func(*func_args, **func_kwargs)
                return await real_decorator(func)(*func_args, **func_kwargs)

            # Support synchronous handlers if any
            @wraps(func)
            def sync_wrapper(*func_args, **func_kwargs):
                if not self.enabled:
                    return func(*func_args, **func_kwargs)
                return real_decorator(func)(*func_args, **func_kwargs)

            import asyncio
            if asyncio.iscoroutinefunction(func):
                return wrapper
            return sync_wrapper

        return decorator

    def __getattr__(self, name: str):
        """Proxy attribute access to the underlying Limiter instance."""
        return getattr(self._limiter, name)


limiter = LazyLimiter()