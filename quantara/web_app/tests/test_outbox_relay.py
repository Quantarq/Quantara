"""
Tests for OutboxRelay and related helpers.
These tests use SQLAlchemy with SQLite in-memory databases so they do not
require PostgreSQL or Redis.
"""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from web_app.db.database import Base
from web_app.db.models import OutboxEvent
from web_app.tasks.outbox_relay import (
    STALE_PROCESSING_INTERVAL_MINUTES,
    OutboxRelay,
    _is_valid_uuid,
    process_position_opened_task,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def relay():
    return OutboxRelay(max_retries=5)


# ---------------------------------------------------------------------------
# UUID validation
# ---------------------------------------------------------------------------

class TestUUIDValidation:
    def test_valid_uuid(self):
        assert _is_valid_uuid(str(uuid.uuid4())) is True

    def test_invalid_uuid(self):
        assert _is_valid_uuid("not-a-uuid") is False

    def test_empty_string(self):
        assert _is_valid_uuid("") is False

    def test_truncated_uuid(self):
        valid = str(uuid.uuid4())
        assert _is_valid_uuid(valid[:30]) is False


# ---------------------------------------------------------------------------
# OutboxRelay.process_pending_events
# ---------------------------------------------------------------------------

class TestProcessPendingEvents:
    @patch("web_app.tasks.outbox_relay.SessionLocal")
    @patch("web_app.tasks.outbox_relay.process_position_opened_task")
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_pending_event_is_published(
        self, mock_init_db, mock_delay, mock_session_local, db_session
    ):
        event = OutboxEvent(
            id=uuid.uuid4(),
            event_type="PositionOpened",
            payload=json.dumps({"position_id": "p1", "transaction_hash": "0xabc"}),
            status="pending",
        )
        db_session.add(event)
        db_session.commit()
        mock_session_local.return_value = db_session

        relay = OutboxRelay(max_retries=5)
        relay.process_pending_events()

        updated = db_session.query(OutboxEvent).filter(OutboxEvent.id == event.id).one()
        assert updated.status == "processing"
        assert updated.claimed_at is not None
        mock_delay.delay.assert_called_once_with(str(event.id))

    @patch("web_app.tasks.outbox_relay.SessionLocal")
    @patch("web_app.tasks.outbox_relay.process_position_opened_task")
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_failed_event_is_requeued(
        self, mock_init_db, mock_delay, mock_session_local, db_session
    ):
        event = OutboxEvent(
            id=uuid.uuid4(),
            event_type="PositionOpened",
            payload=json.dumps({"position_id": "p1", "transaction_hash": "0xabc"}),
            status="failed",
            retry_count=1,
            error_message="previous error",
        )
        db_session.add(event)
        db_session.commit()
        mock_session_local.return_value = db_session

        relay = OutboxRelay(max_retries=5)
        relay.process_pending_events()

        updated = db_session.query(OutboxEvent).filter(OutboxEvent.id == event.id).one()
        assert updated.status == "processing"
        assert updated.claimed_at is not None
        mock_delay.delay.assert_called_once_with(str(event.id))

    @patch("web_app.tasks.outbox_relay.SessionLocal")
    @patch("web_app.tasks.outbox_relay.process_position_opened_task")
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_stale_processing_event_is_reclaimed(
        self, mock_init_db, mock_delay, mock_session_local, db_session
    ):
        stale_time = datetime.now() - timedelta(minutes=STALE_PROCESSING_INTERVAL_MINUTES + 1)
        event = OutboxEvent(
            id=uuid.uuid4(),
            event_type="PositionOpened",
            payload=json.dumps({"position_id": "p1", "transaction_hash": "0xabc"}),
            status="processing",
            claimed_at=stale_time,
            retry_count=0,
        )
        db_session.add(event)
        db_session.commit()
        mock_session_local.return_value = db_session

        relay = OutboxRelay(max_retries=5)
        relay.process_pending_events()

        updated = db_session.query(OutboxEvent).filter(OutboxEvent.id == event.id).one()
        assert updated.status == "processing"
        assert updated.claimed_at is not None
        mock_delay.delay.assert_called_once_with(str(event.id))

    @patch("web_app.tasks.outbox_relay.SessionLocal")
    @patch("web_app.tasks.outbox_relay.process_position_opened_task")
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_recent_processing_event_is_not_reclaimed(
        self, mock_init_db, mock_delay, mock_session_local, db_session
    ):
        recent_time = datetime.now() - timedelta(minutes=1)
        event = OutboxEvent(
            id=uuid.uuid4(),
            event_type="PositionOpened",
            payload=json.dumps({"position_id": "p1", "transaction_hash": "0xabc"}),
            status="processing",
            claimed_at=recent_time,
            retry_count=0,
        )
        db_session.add(event)
        db_session.commit()
        mock_session_local.return_value = db_session

        relay = OutboxRelay(max_retries=5)
        relay.process_pending_events()

        updated = db_session.query(OutboxEvent).filter(OutboxEvent.id == event.id).one()
        assert updated.status == "processing"
        mock_delay.delay.assert_not_called()

    @patch("web_app.tasks.outbox_relay.SessionLocal")
    @patch("web_app.tasks.outbox_relay.process_position_opened_task")
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_event_exceeding_max_retries_is_skipped(
        self, mock_init_db, mock_delay, mock_session_local, db_session
    ):
        event = OutboxEvent(
            id=uuid.uuid4(),
            event_type="PositionOpened",
            payload=json.dumps({"position_id": "p1", "transaction_hash": "0xabc"}),
            status="pending",
            retry_count=5,
        )
        db_session.add(event)
        db_session.commit()
        mock_session_local.return_value = db_session

        relay = OutboxRelay(max_retries=5)
        relay.process_pending_events()

        updated = db_session.query(OutboxEvent).filter(OutboxEvent.id == event.id).one()
        assert updated.status == "pending"
        mock_delay.delay.assert_not_called()

    @patch("web_app.tasks.outbox_relay.SessionLocal")
    @patch("web_app.tasks.outbox_relay.process_position_opened_task")
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_already_claimed_event_is_not_double_dispatched(
        self, mock_init_db, mock_delay, mock_session_local, db_session
    ):
        now = datetime.now()
        event = OutboxEvent(
            id=uuid.uuid4(),
            event_type="PositionOpened",
            payload=json.dumps({"position_id": "p1", "transaction_hash": "0xabc"}),
            status="pending",
        )
        db_session.add(event)
        db_session.commit()

        original_query = db_session.query

        call_count = [0]

        def patched_query(*args, **kwargs):
            q = original_query(*args, **kwargs)

            original_update = q.update

            def patched_update(*uargs, **ukwargs):
                call_count[0] += 1
                if call_count[0] == 2:
                    return 0
                return original_update(*uargs, **ukwargs)

            q.update = patched_update
            return q

        db_session.query = patched_query
        mock_session_local.return_value = db_session

        relay = OutboxRelay(max_retries=5)
        relay.process_pending_events()

        mock_delay.delay.assert_not_called()


# ---------------------------------------------------------------------------
# process_position_opened_task – UUID validation
# ---------------------------------------------------------------------------

class TestProcessPositionOpenedTask:
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_invalid_uuid_returns_early(self, mock_init_db):
        process_position_opened_task.run(event_id="not-a-uuid")

    @patch("web_app.tasks.outbox_relay.SessionLocal")
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_valid_uuid_not_found_returns_early(self, mock_init_db, mock_session_local, db_session):
        mock_session_local.return_value = db_session
        process_position_opened_task.run(event_id=str(uuid.uuid4()))

    @patch("web_app.tasks.outbox_relay.SessionLocal")
    @patch("web_app.tasks.outbox_relay.init_db")
    def test_failed_event_clears_claimed_at(self, mock_init_db, mock_session_local, db_session):
        event = OutboxEvent(
            id=uuid.uuid4(),
            event_type="PositionOpened",
            payload=json.dumps({"position_id": "p1", "transaction_hash": "0xabc"}),
            status="processing",
            claimed_at=datetime.now(),
        )
        db_session.add(event)
        db_session.commit()
        mock_session_local.return_value = db_session

        with patch("web_app.tasks.outbox_relay.DashboardMixin") as mock_dash:
            mock_dash.get_current_prices = MagicMock(
                side_effect=RuntimeError("pricing down")
            )
            with patch("web_app.tasks.outbox_relay.PositionDBConnector") as mock_pdbc:
                instance = mock_pdbc.return_value
                instance.get_object.return_value = None
                with pytest.raises(Exception):
                    process_position_opened_task.run(event_id=str(event.id))

        updated = db_session.query(OutboxEvent).filter(OutboxEvent.id == event.id).one()
        assert updated.status == "failed"
        assert updated.claimed_at is None
        assert updated.retry_count == 1
