"""
Tests for SQLAlchemy connection pool configuration.

Both engine construction sites (``web_app.db.database.init_db`` and the
``DBConnector`` constructor) route through
``web_app.db.database.create_engine`` so that the pool policy defined in
:func:`web_app.db.database._engine_pool_kwargs` is applied uniformly.

The actual pool behaviour is exercised in the integration suite against a
real PostgreSQL container. This file focuses narrowly on configuration by
patching ``create_engine`` so no database is required.

Note: ``_register_slow_query_listener`` is also patched in every test that
mocks ``create_engine``.  The listener registration calls ``event.listen``
on the engine object, which requires a real SQLAlchemy engine; using a
MagicMock would raise ``InvalidRequestError``.  Since pool-configuration
tests care only about the kwargs forwarded to ``create_engine``, we simply
no-op the listener step here.
"""

from unittest.mock import patch

import pytest


# Default values must stay in lock-step with the implementation in
# ``web_app/db/database.py``.
DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10
DEFAULT_POOL_RECYCLE = 1800


@pytest.fixture(autouse=True)
def _scrub_database_module_state(monkeypatch):
    """Reset module-level engine state so ``init_db`` re-runs in tests."""
    from web_app.db import database

    monkeypatch.setattr(database, "engine", None)
    monkeypatch.setattr(database, "SessionLocal", None)
    yield


def test_database_init_db_uses_env_pool_settings(monkeypatch):
    """``init_db`` forwards environment-driven pool kwargs to ``create_engine``."""
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "11")
    monkeypatch.setenv("DB_POOL_RECYCLE", "900")

    from web_app.db import database

    with patch("web_app.db.database.create_engine") as create_engine, \
         patch("web_app.db.database._register_slow_query_listener"):
        database.init_db()
        assert create_engine.call_count == 1
        kwargs = create_engine.call_args.kwargs
        assert kwargs["pool_size"] == 7
        assert kwargs["max_overflow"] == 11
        assert kwargs["pool_recycle"] == 900
        assert kwargs["pool_pre_ping"] is True


def test_database_init_db_falls_back_to_defaults(monkeypatch):
    """Defaults apply when no environment variables are set."""
    for var in ("DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_RECYCLE"):
        monkeypatch.delenv(var, raising=False)

    from web_app.db import database

    with patch("web_app.db.database.create_engine") as create_engine, \
         patch("web_app.db.database._register_slow_query_listener"):
        database.init_db()
        kwargs = create_engine.call_args.kwargs
        assert kwargs["pool_size"] == DEFAULT_POOL_SIZE
        assert kwargs["max_overflow"] == DEFAULT_MAX_OVERFLOW
        assert kwargs["pool_recycle"] == DEFAULT_POOL_RECYCLE
        assert kwargs["pool_pre_ping"] is True


def test_database_init_db_rejects_non_integer_env_values(monkeypatch):
    """Non-integer env vars surface as ``ValueError`` rather than silently falling back."""
    monkeypatch.setenv("DB_POOL_SIZE", "not-an-int")

    from web_app.db import database

    with pytest.raises(ValueError):
        database.init_db()


def test_db_connector_routes_through_init_engine(monkeypatch):
    """``DBConnector`` constructs its engine via ``init_engine``."""
    monkeypatch.setenv("DB_POOL_SIZE", "3")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "8")
    monkeypatch.setenv("DB_POOL_RECYCLE", "600")

    from web_app.db.crud.base import DBConnector

    with patch("web_app.db.database.create_engine") as create_engine, \
         patch("web_app.db.database._register_slow_query_listener"):
        DBConnector(db_url="postgresql://user:pwd@host:5432/dbname")
        assert create_engine.call_count == 1
        kwargs = create_engine.call_args.kwargs
        assert kwargs["pool_size"] == 3
        assert kwargs["max_overflow"] == 8
        assert kwargs["pool_recycle"] == 600
        assert kwargs["pool_pre_ping"] is True


def test_db_connector_falls_back_to_defaults(monkeypatch):
    """Defaults apply in ``DBConnector`` as well when env vars are unset."""
    for var in ("DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_RECYCLE"):
        monkeypatch.delenv(var, raising=False)

    from web_app.db.crud.base import DBConnector

    with patch("web_app.db.database.create_engine") as create_engine, \
         patch("web_app.db.database._register_slow_query_listener"):
        DBConnector(db_url="postgresql://user:pwd@host:5432/dbname")
        kwargs = create_engine.call_args.kwargs
        assert kwargs["pool_size"] == DEFAULT_POOL_SIZE
        assert kwargs["max_overflow"] == DEFAULT_MAX_OVERFLOW
        assert kwargs["pool_recycle"] == DEFAULT_POOL_RECYCLE
        assert kwargs["pool_pre_ping"] is True
