"""
Main FastAPI application module for the QUANTARA API (Stellar/Soroban).

Sets up FastAPI with session and CORS middleware, registers routers for
dashboard, position, user, vault, leaderboard, referal, telegram, and
authentication endpoints, and exposes a /health endpoint for CI orchestration.
"""

import logging
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
import redis.asyncio as redis

from web_app.api.rate_limiter import limiter
from web_app.api.dashboard import router as dashboard_router
from web_app.api.position import router as position_router
from web_app.api.telegram import router as telegram_router
from web_app.api.user import router as user_router
from web_app.api.vault import router as vault_router
from web_app.api.leaderboard import router as leaderboard_router
from web_app.api.referal import router as referal_router
from web_app.api.wallet_auth import router as auth_router
from web_app.config_validator import assert_valid_config
from web_app.api.middleware import MaxBodySizeMiddleware
from web_app.db.database import init_db
from web_app.db.database import init_db, get_database

logger = logging.getLogger(__name__)
DEFAULT_CORS_ORIGINS = ["http://localhost:3000"]
CORS_ALLOW_METHODS = ["GET", "POST"]
CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "X-Wallet-Id", "X-Nonce", "X-Signature"]


def get_cors_origins() -> list[str]:
    """
    Return the allowed CORS origins from the environment.

    A comma-separated CORS_ORIGINS value is supported for production. When the
    variable is unset or blank, development keeps working against localhost.
    """
    raw_origins = os.getenv("CORS_ORIGINS")
    if not raw_origins:
        return DEFAULT_CORS_ORIGINS

    origins = [origin.strip() for origin in raw_origins.split(",")]
    return [origin for origin in origins if origin] or DEFAULT_CORS_ORIGINS

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles application startup and shutdown events.
    """
    init_db()

    # Validate required environment variables at startup.
    assert_valid_config()

    # Enforce minimum length for session secret at startup
    secret = os.getenv("SESSION_SECRET_KEY")
    if secret and len(secret) < 32:
        raise ValueError("SESSION_SECRET_KEY must be at least 32 characters long.")

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
    yield

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
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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

# Fetch at import time for middleware registration, but do not raise exceptions here.
# Strict validation and missing value errors are handled by assert_valid_config() and lifespan().
_session_secret = os.getenv("SESSION_SECRET_KEY", os.urandom(32).hex())

# Add session middleware with a persistent secret key
app.add_middleware(SessionMiddleware, secret_key=_session_secret)
# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_headers=CORS_ALLOW_HEADERS,
    allow_methods=CORS_ALLOW_METHODS,
)
# Rate limiting middleware -- must be added after CORS/session so it wraps the
# full middleware stack and can reject requests before they reach routers.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(MaxBodySizeMiddleware, max_body_size=1024*1024)


@app.get("/health", tags=["Health"], summary="Health check endpoint")
async def health_check(response: Response, db: Session = Depends(get_database)):
    """Returns 200 OK when the service is running and dependencies are healthy."""
    health_status = {"status": "healthy", "database": "up", "redis": "up"}
    is_healthy = True

    # Check Database
    try:
        # Use asyncio.to_thread for synchronous SQLAlchemy call to prevent blocking the event loop
        await asyncio.wait_for(
            asyncio.to_thread(db.execute, text("SELECT 1")), timeout=2.0
        )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "down"
        is_healthy = False

    # Check Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        r = redis.from_url(redis_url)
        await asyncio.wait_for(r.ping(), timeout=2.0)
        await r.close()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["redis"] = "down"
        is_healthy = False

    if not is_healthy:
        health_status["status"] = "degraded"
        response.status_code = 503

    return health_status


# No startup-time blockchain contract init needed -- the frontend
# invokes Soroban contracts directly via Freighter + stellar-sdk.

# Include the routers
app.include_router(position_router)
app.include_router(dashboard_router)
app.include_router(user_router)
app.include_router(telegram_router)
app.include_router(vault_router)
app.include_router(leaderboard_router)
app.include_router(referal_router)
app.include_router(auth_router)
