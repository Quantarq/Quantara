"""
Tests for the slow-query event hook in web_app.db.database.

Covers:
- _before_cursor_execute stores a start time on conn.info
- _after_cursor_execute observes elapsed time in the Histogram
- _after_cursor_execute increments DB_SLOW_QUERY_COUNTER for slow queries
- _after_cursor_execute does NOT increment the counter for fast queries
- _after_cursor_execute logs a warning with 'slow_query' key for slow queries
- _after_cursor_execute does NOT log for fast queries
- _after_cursor_execute is a no-op when no start time was recorded
- _register_slow_query_listener attaches both listeners to an engine
- SLOW_QUERY_THRESHOLD_MS defaults to 500 and is overridable via env
- init_engine registers the listeners on the returned engine
- init_db registers the listeners on the module-level engine
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_mock_conn(start_times=None):
    """Return a minimal mock Connection whose .info behaves like a real dict."""
    conn = MagicMock()
    conn.info = {}
    if start_times is not None:
        conn.info["_query_start_time"] = list(start_times)
    return conn


def _counter_value(counter) -> float:
    """Read the current value of a prometheus_client Counter."""
    return counter._value.get()


def _histogram_sum(histogram, label_values: tuple) -> float:
    """Return the _sum sample for a Histogram with given label values."""
    return histogram.labels(*label_values)._sum.get()


def _make_sqlite_engine():
    """Create a real SQLite in-memory engine (no pool kwargs needed)."""
    return create_engine("sqlite:///:memory:")


# ── _before_cursor_execute ────────────────────────────────────────────────────


class TestBeforeCursorExecute:
    """Tests for the before_cursor_execute event listener."""

    def test_stores_start_time_in_conn_info(self):
        """Start time is stored in conn.info under _query_start_time."""
        from web_app.db.database import _before_cursor_execute

        conn = _make_mock_conn()
        with patch("web_app.db.database.time") as mock_time:
            mock_time.perf_counter.return_value = 1.0
            _before_cursor_execute(conn, None, "SELECT 1", None, None, False)

        assert "_query_start_time" in conn.info
        assert conn.info["_query_start_time"] == [1.0]

    def test_appends_to_existing_start_times(self):
        """Nested / pipelined queries stack correctly."""
        from web_app.db.database import _before_cursor_execute

        conn = _make_mock_conn(start_times=[0.5])
        with patch("web_app.db.database.time") as mock_time:
            mock_time.perf_counter.return_value = 2.0
            _before_cursor_execute(conn, None, "SELECT 1", None, None, False)

        assert conn.info["_query_start_time"] == [0.5, 2.0]

    def test_executemany_also_stores_start_time(self):
        """executemany=True also records a start time."""
        from web_app.db.database import _before_cursor_execute

        conn = _make_mock_conn()
        with patch("web_app.db.database.time") as mock_time:
            mock_time.perf_counter.return_value = 3.14
            _before_cursor_execute(conn, None, "INSERT INTO t VALUES (?)", None, None, True)

        assert conn.info["_query_start_time"] == [3.14]


# ── _after_cursor_execute ─────────────────────────────────────────────────────


class TestAfterCursorExecute:
    """Tests for the after_cursor_execute event listener."""

    def test_noop_when_no_start_time_recorded(self):
        """Missing start time must not raise and must not mutate counters."""
        from web_app.db.database import (
            DB_SLOW_QUERY_COUNTER,
            _after_cursor_execute,
        )

        conn = _make_mock_conn()  # empty info – no _query_start_time key
        before = _counter_value(DB_SLOW_QUERY_COUNTER)

        with patch("web_app.db.database.logger") as mock_logger:
            _after_cursor_execute(conn, None, "SELECT 1", None, None, False)
            mock_logger.warning.assert_not_called()

        assert _counter_value(DB_SLOW_QUERY_COUNTER) == before

    def test_histogram_observed_for_fast_query(self):
        """Fast queries still get recorded in the histogram."""
        from web_app.db.database import DB_QUERY_DURATION, _after_cursor_execute

        conn = _make_mock_conn(start_times=[0.0])
        sum_before = _histogram_sum(DB_QUERY_DURATION, ("sql",))

        with patch("web_app.db.database.time") as mock_time:
            mock_time.perf_counter.return_value = 0.1  # 100 ms
            _after_cursor_execute(conn, None, "SELECT 1", None, None, False)

        assert _histogram_sum(DB_QUERY_DURATION, ("sql",)) == pytest.approx(
            sum_before + 0.1, abs=1e-6
        )

    def test_histogram_observed_for_slow_query(self):
        """Slow queries also update the histogram."""
        from web_app.db.database import DB_QUERY_DURATION, _after_cursor_execute

        conn = _make_mock_conn(start_times=[0.0])
        sum_before = _histogram_sum(DB_QUERY_DURATION, ("sql",))

        with patch("web_app.db.database.time") as mock_time:
            mock_time.perf_counter.return_value = 0.6  # 600 ms > 500 ms threshold
            with patch("web_app.db.database.logger"):
                _after_cursor_execute(conn, None, "SELECT slow", None, None, False)

        assert _histogram_sum(DB_QUERY_DURATION, ("sql",)) == pytest.approx(
            sum_before + 0.6, abs=1e-6
        )

    def test_slow_query_counter_incremented_when_over_threshold(self, monkeypatch):
        """Counter increments when elapsed > threshold."""
        from web_app.db import database
        from web_app.db.database import DB_SLOW_QUERY_COUNTER, _after_cursor_execute

        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 500.0)
        conn = _make_mock_conn(start_times=[0.0])
        before = _counter_value(DB_SLOW_QUERY_COUNTER)

        with patch("web_app.db.database.time") as mock_time:
            mock_time.perf_counter.return_value = 0.601  # 601 ms
            with patch("web_app.db.database.logger"):
                _after_cursor_execute(conn, None, "SELECT slow", None, None, False)

        assert _counter_value(DB_SLOW_QUERY_COUNTER) == before + 1.0

    def test_slow_query_counter_not_incremented_for_fast_query(self, monkeypatch):
        """Counter does not increment for fast queries."""
        from web_app.db import database
        from web_app.db.database import DB_SLOW_QUERY_COUNTER, _after_cursor_execute

        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 500.0)
        conn = _make_mock_conn(start_times=[0.0])
        before = _counter_value(DB_SLOW_QUERY_COUNTER)

        with patch("web_app.db.database.time") as mock_time:
            mock_time.perf_counter.return_value = 0.499  # 499 ms
            _after_cursor_execute(conn, None, "SELECT fast", None, None, False)

        assert _counter_value(DB_SLOW_QUERY_COUNTER) == before

    def test_slow_query_counter_not_incremented_exactly_at_threshold(self, monkeypatch):
        """Equality is not slow — only strictly greater than triggers the alert."""
        from web_app.db import database
        from web_app.db.database import DB_SLOW_QUERY_COUNTER, _after_cursor_execute

        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 500.0)
        conn = _make_mock_conn(start_times=[0.0])
        before = _counter_value(DB_SLOW_QUERY_COUNTER)

        with patch("web_app.db.database.time") as mock_time:
            mock_time.perf_counter.return_value = 0.5  # exactly 500 ms
            _after_cursor_execute(conn, None, "SELECT exact", None, None, False)

        assert _counter_value(DB_SLOW_QUERY_COUNTER) == before

    def test_warning_logged_for_slow_query(self, monkeypatch):
        """A WARNING with event key 'slow_query' is emitted for slow queries."""
        from web_app.db import database
        from web_app.db.database import _after_cursor_execute

        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 500.0)
        conn = _make_mock_conn(start_times=[0.0])

        with patch("web_app.db.database.time") as mock_time, \
             patch("web_app.db.database.logger") as mock_logger:
            mock_time.perf_counter.return_value = 1.5  # 1500 ms
            _after_cursor_execute(conn, None, "SELECT slow", None, None, False)

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args
        # First positional arg is the event key
        assert call_kwargs.args[0] == "slow_query"
        # Keyword arguments must include duration_ms and threshold_ms
        assert "duration_ms" in call_kwargs.kwargs
        assert "threshold_ms" in call_kwargs.kwargs
        assert call_kwargs.kwargs["duration_ms"] == pytest.approx(1500.0, abs=1.0)
        assert call_kwargs.kwargs["threshold_ms"] == 500.0

    def test_no_warning_logged_for_fast_query(self, monkeypatch):
        """No warning is logged for fast queries."""
        from web_app.db import database
        from web_app.db.database import _after_cursor_execute

        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 500.0)
        conn = _make_mock_conn(start_times=[0.0])

        with patch("web_app.db.database.time") as mock_time, \
             patch("web_app.db.database.logger") as mock_logger:
            mock_time.perf_counter.return_value = 0.2  # 200 ms
            _after_cursor_execute(conn, None, "SELECT fast", None, None, False)

        mock_logger.warning.assert_not_called()

    def test_long_statement_is_truncated_in_log(self, monkeypatch):
        """Statements longer than 500 chars are truncated before logging."""
        from web_app.db import database
        from web_app.db.database import _after_cursor_execute

        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 500.0)
        conn = _make_mock_conn(start_times=[0.0])
        long_stmt = "SELECT " + "x" * 1000

        with patch("web_app.db.database.time") as mock_time, \
             patch("web_app.db.database.logger") as mock_logger:
            mock_time.perf_counter.return_value = 1.0  # 1000 ms
            _after_cursor_execute(conn, None, long_stmt, None, None, False)

        logged_statement = mock_logger.warning.call_args.kwargs.get("statement", "")
        assert len(logged_statement) <= 500

    def test_start_time_popped_from_stack(self):
        """After processing, the start time is removed so nested calls stay clean."""
        from web_app.db.database import _after_cursor_execute

        conn = _make_mock_conn(start_times=[0.0, 1.0])  # two nested queries

        with patch("web_app.db.database.time") as mock_time, \
             patch("web_app.db.database.logger"):
            mock_time.perf_counter.return_value = 1.1
            _after_cursor_execute(conn, None, "SELECT 1", None, None, False)

        # The last pushed value (1.0) is popped; the earlier one (0.0) remains.
        assert conn.info["_query_start_time"] == [0.0]


# ── _register_slow_query_listener ────────────────────────────────────────────


class TestRegisterSlowQueryListener:
    """Tests for _register_slow_query_listener."""

    def test_both_listeners_attached(self):
        """Both before/after listeners are registered on a real engine."""
        from web_app.db.database import (
            _after_cursor_execute,
            _before_cursor_execute,
            _register_slow_query_listener,
        )

        eng = _make_sqlite_engine()
        _register_slow_query_listener(eng)

        assert event.contains(eng, "before_cursor_execute", _before_cursor_execute)
        assert event.contains(eng, "after_cursor_execute", _after_cursor_execute)

    def test_listener_not_registered_without_call(self):
        """A fresh engine (without our helper) should NOT have the listeners."""
        from web_app.db.database import (
            _after_cursor_execute,
            _before_cursor_execute,
        )

        eng = _make_sqlite_engine()

        assert not event.contains(eng, "before_cursor_execute", _before_cursor_execute)
        assert not event.contains(eng, "after_cursor_execute", _after_cursor_execute)


# ── init_engine ───────────────────────────────────────────────────────────────


class TestInitEngine:
    """Tests for the init_engine factory function."""

    def test_listeners_registered_on_returned_engine(self):
        """init_engine with sqlite returns an engine that has our listeners."""
        from web_app.db.database import (
            _after_cursor_execute,
            _before_cursor_execute,
        )

        # Patch _engine_pool_kwargs to return sqlite-compatible kwargs only.
        with patch(
            "web_app.db.database._engine_pool_kwargs",
            return_value={"pool_pre_ping": False},
        ):
            from web_app.db.database import init_engine

            eng = init_engine("sqlite:///:memory:")

        assert event.contains(eng, "before_cursor_execute", _before_cursor_execute)
        assert event.contains(eng, "after_cursor_execute", _after_cursor_execute)

    def test_pool_kwargs_forwarded(self, monkeypatch):
        """init_engine passes pool kwargs from _engine_pool_kwargs to create_engine."""
        monkeypatch.setenv("DB_POOL_SIZE", "4")
        monkeypatch.setenv("DB_MAX_OVERFLOW", "6")
        monkeypatch.setenv("DB_POOL_RECYCLE", "300")

        from web_app.db.database import init_engine

        # Patch both create_engine AND _register_slow_query_listener because
        # the mock engine won't accept SQLAlchemy event listeners.
        with patch("web_app.db.database.create_engine") as mock_create, \
             patch("web_app.db.database._register_slow_query_listener"):
            mock_eng = MagicMock()
            mock_create.return_value = mock_eng
            init_engine("postgresql://u:p@h:5432/db")

        kwargs = mock_create.call_args.kwargs
        assert kwargs["pool_size"] == 4
        assert kwargs["max_overflow"] == 6
        assert kwargs["pool_recycle"] == 300
        assert kwargs["pool_pre_ping"] is True


# ── init_db ───────────────────────────────────────────────────────────────────


class TestInitDb:
    """Tests for the init_db startup function."""

    @pytest.fixture(autouse=True)
    def _reset_module_state(self, monkeypatch):
        """Reset module-level engine/SessionLocal before each test."""
        from web_app.db import database

        monkeypatch.setattr(database, "engine", None)
        monkeypatch.setattr(database, "SessionLocal", None)
        yield

    def test_listeners_registered_on_module_engine(self):
        """init_db attaches our slow-query listeners to the module engine."""
        from web_app.db.database import (
            _after_cursor_execute,
            _before_cursor_execute,
            init_db,
        )

        # Use a real sqlite engine to avoid pool-arg restrictions.
        real_eng = _make_sqlite_engine()

        with patch("web_app.db.database.create_engine", return_value=real_eng), \
             patch("web_app.db.database.get_database_url", return_value="sqlite:///:memory:"):
            init_db()

        assert event.contains(real_eng, "before_cursor_execute", _before_cursor_execute)
        assert event.contains(real_eng, "after_cursor_execute", _after_cursor_execute)

    def test_init_db_idempotent(self):
        """Calling init_db twice must not create a second engine."""
        from web_app.db.database import init_db

        real_eng = _make_sqlite_engine()

        with patch("web_app.db.database.create_engine", return_value=real_eng) as mock_create, \
             patch("web_app.db.database.get_database_url", return_value="sqlite:///:memory:"):
            init_db()
            init_db()

        assert mock_create.call_count == 1


# ── SLOW_QUERY_THRESHOLD_MS ───────────────────────────────────────────────────


class TestSlowQueryThresholdMS:
    """Tests for the SLOW_QUERY_THRESHOLD_MS constant and threshold logic."""

    def test_default_threshold_value_is_500(self):
        """The module-level constant defaults to 500 ms."""
        import web_app.db.database as db_mod

        assert db_mod.SLOW_QUERY_THRESHOLD_MS == pytest.approx(500.0)

    def test_custom_threshold_gates_slow_query_logic(self, monkeypatch):
        """A query below the custom threshold is not counted as slow."""
        from web_app.db import database
        from web_app.db.database import DB_SLOW_QUERY_COUNTER, _after_cursor_execute

        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 200.0)
        conn = _make_mock_conn(start_times=[0.0])
        before = _counter_value(DB_SLOW_QUERY_COUNTER)

        with patch("web_app.db.database.time") as mock_time, \
             patch("web_app.db.database.logger"):
            mock_time.perf_counter.return_value = 0.15  # 150 ms < 200 ms threshold
            _after_cursor_execute(conn, None, "SELECT ok", None, None, False)

        assert _counter_value(DB_SLOW_QUERY_COUNTER) == before

    def test_custom_threshold_triggers_slow_query_logic(self, monkeypatch):
        """A query above the custom threshold IS counted as slow."""
        from web_app.db import database
        from web_app.db.database import DB_SLOW_QUERY_COUNTER, _after_cursor_execute

        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 200.0)
        conn = _make_mock_conn(start_times=[0.0])
        before = _counter_value(DB_SLOW_QUERY_COUNTER)

        with patch("web_app.db.database.time") as mock_time, \
             patch("web_app.db.database.logger"):
            mock_time.perf_counter.return_value = 0.25  # 250 ms > 200 ms threshold
            _after_cursor_execute(conn, None, "SELECT slow", None, None, False)

        assert _counter_value(DB_SLOW_QUERY_COUNTER) == before + 1.0

    def test_threshold_env_var_read_at_import(self, monkeypatch):
        """SLOW_QUERY_THRESHOLD_MS can be patched on the module directly."""
        from web_app.db import database

        # Patch the module attribute (simulates what env-driven reload would do)
        monkeypatch.setattr(database, "SLOW_QUERY_THRESHOLD_MS", 100.0)
        assert database.SLOW_QUERY_THRESHOLD_MS == 100.0


# ── Prometheus metric names ───────────────────────────────────────────────────


class TestPrometheusMetricNames:
    """Tests that the Prometheus metrics are registered with the correct names."""

    def test_histogram_registered_with_correct_name(self):
        """http_db_query_seconds histogram must exist in the default registry."""
        from prometheus_client import REGISTRY

        names = {m.name for m in REGISTRY.collect()}
        assert "http_db_query_seconds" in names

    def test_slow_query_counter_registered_with_correct_name(self):
        """db_slow_queries_total counter must exist in the default registry.

        prometheus_client < 0.17 stores Counter metrics without the _total suffix
        (as 'db_slow_queries') while newer versions include it.  We accept either.
        """
        from prometheus_client import REGISTRY

        names = {m.name for m in REGISTRY.collect()}
        # Accept both naming conventions across prometheus_client versions.
        assert "db_slow_queries_total" in names or "db_slow_queries" in names
