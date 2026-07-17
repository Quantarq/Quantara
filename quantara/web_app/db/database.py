"""
This module contains the database configuration and session management.

Reads PostgreSQL connection parameters from environment variables and
exposes the SQLAlchemy engine, session factory, and declarative base
for use throughout the web application.

Observability
─────────────
A SQLAlchemy ``before_cursor_execute`` / ``after_cursor_execute`` event pair
is registered on every engine produced by this module.  Any statement that
takes longer than SLOW_QUERY_THRESHOLD_MS (default 500 ms) is logged at
WARNING level with the ``slow_query`` event key and the actual duration.

The Prometheus counter ``http_db_query_seconds`` is incremented for **every**
finished query, regardless of duration, so scrape targets can compute a
request-rate baseline.  A separate ``db_slow_queries_total`` counter tracks
only the slow queries, making it easy to build an alert rule such as::

    rate(db_slow_queries_total[5m]) > 0
"""

import os
import time
from typing import Generator

from dotenv import load_dotenv
from prometheus_client import Counter, Histogram
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from web_app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Prometheus metrics ────────────────────────────────────────────────────────

#: Total seconds spent executing database queries (histogram).
#: Label ``query_type`` is always "sql" — extend if you need finer granularity.
DB_QUERY_DURATION = Histogram(
    "http_db_query_seconds",
    "Duration of individual database queries in seconds",
    ["query_type"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

#: Incremented every time a query exceeds SLOW_QUERY_THRESHOLD_MS.
DB_SLOW_QUERY_COUNTER = Counter(
    "db_slow_queries_total",
    "Number of database queries that exceeded the slow-query threshold",
)

# Threshold in milliseconds.  Override via SLOW_QUERY_THRESHOLD_MS env var.
SLOW_QUERY_THRESHOLD_MS: float = float(
    os.environ.get("SLOW_QUERY_THRESHOLD_MS", "500")
)

# ── Module-level engine / session state ──────────────────────────────────────

engine = None
SessionLocal = None
Base = declarative_base()


# ── Slow-query instrumentation ────────────────────────────────────────────────


def _before_cursor_execute(  # pylint: disable=too-many-arguments,unused-argument
    conn: Connection,
    cursor,
    statement: str,
    parameters,
    context,
    executemany: bool,
) -> None:
    """Record the wall-clock start time on the connection's info dict."""
    conn.info.setdefault("_query_start_time", []).append(time.perf_counter())


def _after_cursor_execute(  # pylint: disable=too-many-arguments,unused-argument
    conn: Connection,
    cursor,
    statement: str,
    parameters,
    context,
    executemany: bool,
) -> None:
    """Compute elapsed time, update Prometheus metrics, and log slow queries."""
    start_times: list = conn.info.get("_query_start_time", [])
    if not start_times:
        return

    start = start_times.pop()
    elapsed_seconds: float = time.perf_counter() - start
    elapsed_ms: float = elapsed_seconds * 1000.0

    # Always record to the histogram.
    DB_QUERY_DURATION.labels(query_type="sql").observe(elapsed_seconds)

    # Log and count slow queries.
    if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
        DB_SLOW_QUERY_COUNTER.inc()
        logger.warning(
            "slow_query",
            duration_ms=round(elapsed_ms, 3),
            threshold_ms=SLOW_QUERY_THRESHOLD_MS,
            statement=statement[:500],  # truncate to avoid huge log lines
        )


def _register_slow_query_listener(eng) -> None:
    """Attach the before/after cursor-execute listeners to *eng*."""
    event.listen(eng, "before_cursor_execute", _before_cursor_execute)
    event.listen(eng, "after_cursor_execute", _after_cursor_execute)


# ── URL / pool helpers ────────────────────────────────────────────────────────


def get_database_url() -> str:
    """Construct and return the database URL from environment variables."""
    load_dotenv(override=False)

    DB_USER = os.environ.get("DB_USER", "")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_SERVER = os.environ.get("DB_HOST", "")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", "")

    return (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"
    )


def _engine_pool_kwargs() -> dict:
    """Return the standard pool-related kwargs for every SQLAlchemy engine.

    Pool sizing is read from the ``DB_POOL_SIZE``, ``DB_MAX_OVERFLOW`` and
    ``DB_POOL_RECYCLE`` environment variables with sensible defaults so
    deployment configs can tune them per environment without code
    changes. ``pool_pre_ping`` is always enabled because it is universally
    safe for a web service and prevents hard-to-debug failures after
    database restarts or network hiccups. Centralising the kwargs keeps
    the two engine constructions in this codebase consistent.
    """
    return {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "10")),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "1800")),
        "pool_pre_ping": True,
    }


# ── Engine factories ──────────────────────────────────────────────────────────


def init_engine(db_url: str = None):
    """Construct a SQLAlchemy engine that uses the project's pool policy.

    The slow-query event listeners are automatically registered on the
    returned engine.
    """
    if db_url is None:
        db_url = get_database_url()
    eng = create_engine(db_url, **_engine_pool_kwargs())
    _register_slow_query_listener(eng)
    return eng


def init_db() -> None:
    """Initialize the module-level database connection and session factory.

    The slow-query event listeners are automatically registered on the
    engine produced here.
    """
    global engine, SessionLocal
    if engine is not None:
        return

    engine = create_engine(get_database_url(), **_engine_pool_kwargs())
    _register_slow_query_listener(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_database() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and ensures cleanup.

    :yield: SQLAlchemy Session instance
    :raises: None (always closes the session in the finally block)
    """
    if SessionLocal is None:
        init_db()
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
