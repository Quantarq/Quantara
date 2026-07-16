"""
This module contains the database configuration and session management.

Reads PostgreSQL connection parameters from environment variables and
exposes the SQLAlchemy engine, session factory, and declarative base
for use throughout the web application.
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
except ImportError:
    SQLAlchemyInstrumentor = None

engine = None
SessionLocal = None
Base = declarative_base()

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


def init_engine(db_url: str = None):
    """Construct a SQLAlchemy engine that uses the project's pool policy."""
    if db_url is None:
        db_url = get_database_url()
    return create_engine(db_url, **_engine_pool_kwargs())


def init_db() -> None:
    """Initialize the module-level database connection and session factory."""
    global engine, SessionLocal
    if engine is not None:
        return

    engine = create_engine(get_database_url(), **_engine_pool_kwargs())
    if SQLAlchemyInstrumentor is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine)
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
