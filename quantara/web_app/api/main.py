"""
Main FastAPI application module for the QUANTARA API (Stellar/Soroban).

Sets up FastAPI with session and CORS middleware, registers routers for
dashboard, position, user, vault, leaderboard, referal, and telegram
endpoints, and exposes a /health endpoint for CI orchestration.
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from web_app.api.dashboard import router as dashboard_router
from web_app.api.position import router as position_router
from web_app.api.telegram import router as telegram_router
from web_app.api.user import router as user_router
from web_app.api.vault import router as vault_router
from web_app.api.leaderboard import router as leaderboard_router
from web_app.api.referal import router as referal_router

logger = logging.getLogger(__name__)

# Initialize Sentry SDK if in production
if os.getenv("ENV_VERSION") == "PROD":
    import sentry_sdk

    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=1.0,
        _experiments={
            "continuous_profiling_auto_start": True,
        },
    )


app = FastAPI(
    title="QUANTARA API",
    description=(
        "An API that supports depositing collateral, borrowing stablecoins, "
        "trading on AMMs, and managing user positions via Stellar ecosystem integrations."
    ),
    version="0.1.0",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that masks internal exception details.

    Catches any uncaught exception and returns a sanitized 500 response
    without leaking internal details (stack traces, database errors,
    file paths, etc.) to the API consumer. The full exception is
    logged server-side for operators to investigate.

    :param request: The incoming HTTP request that raised the exception.
    :param exc: The unhandled exception instance.
    :return: JSON response with a generic error message and 500 status.
    """
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

_SESSION_SECRET_MIN_LENGTH = 32
_is_production = os.getenv("ENV_VERSION") == "PROD"

_session_secret = os.getenv("SESSION_SECRET_KEY")

if _session_secret:
    if len(_session_secret) < _SESSION_SECRET_MIN_LENGTH:
        raise ValueError(
            f"SESSION_SECRET_KEY must be at least {_SESSION_SECRET_MIN_LENGTH} characters long."
        )
elif _is_production:
    raise ValueError(
        "SESSION_SECRET_KEY environment variable must be set in production. "
        "Generate one with: python -c \"import os; print(os.urandom(32).hex())\""
    )
else:
    # Development only: auto-generate a key (sessions won't persist across restarts)
    _session_secret = os.urandom(32).hex()

# Add session middleware with a persistent secret key
app.add_middleware(SessionMiddleware, secret_key=_session_secret)
# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]
)


@app.get("/health", tags=["Health"], summary="Health check endpoint")
async def health_check():
    """Returns 200 OK when the service is running."""
    return {"status": "healthy"}


# No startup-time blockchain contract init needed – the frontend
# invokes Soroban contracts directly via Freighter + stellar-sdk.

# Include the routers
app.include_router(position_router)
app.include_router(dashboard_router)
app.include_router(user_router)
app.include_router(telegram_router)
app.include_router(vault_router)
app.include_router(leaderboard_router)
app.include_router(referal_router)
