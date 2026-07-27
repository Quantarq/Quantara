import uuid
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from web_app.api.main import app
from web_app.db.models import OutboxEvent, Position, Transaction
from web_app.tasks.outbox_relay import OutboxRelay, process_position_opened_task


@pytest.mark.anyio
async def test_open_position_queues_outbox_event(client: TestClient) -> None:
    position_id = str(uuid.uuid4())
    transaction_hash = "test_tx_hash"
    
    mock_position = MagicMock(spec=Position)
    mock_position.id = uuid.UUID(position_id)
    mock_position.status = "pending"
    
    saved_events = []
    
    def mock_write(obj):
        if isinstance(obj, OutboxEvent):
            saved_events.append(obj)
        return obj

    with patch("web_app.api.position.PositionDBConnector.get_object", return_value=mock_position) as mock_get, \
         patch("web_app.api.position.PositionDBConnector.write_to_db", side_effect=mock_write) as mock_write_db:
        
        response = client.get(
            f"/api/open-position?position_id={position_id}&transaction_hash={transaction_hash}"
        )
        assert response.status_code == 200
        assert response.json() == "pending"
        
        mock_get.assert_called_once_with(Position, uuid.UUID(position_id))
        assert len(saved_events) == 1
        assert saved_events[0].event_type == "PositionOpened"
        payload = json.loads(saved_events[0].payload)
        assert payload["position_id"] == position_id
        assert payload["transaction_hash"] == transaction_hash


def test_relay_worker_dispatches_task():
    mock_event = MagicMock(spec=OutboxEvent)
    mock_event.id = uuid.uuid4()
    mock_event.event_type = "PositionOpened"
    mock_event.payload = "{}"
    mock_event.status = "pending"
    mock_event.retry_count = 0
    mock_event.created_at = datetime.now()

    mock_db = MagicMock()
    # Query returns old events (empty) then pending events (mock_event)
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.all.side_effect = [[], [mock_event]]

    with patch("web_app.tasks.outbox_relay.SessionLocal", return_value=mock_db), \
         patch("web_app.tasks.outbox_relay.process_position_opened_task.delay") as mock_delay, \
         patch("web_app.tasks.outbox_relay.sentry_sdk.capture_message") as mock_sentry:
        
        relay = OutboxRelay(max_retries=5)
        relay.process_pending_events()

        assert mock_event.status == "processing"
        mock_delay.assert_called_once_with(str(mock_event.id))
        mock_db.commit.assert_called()


def test_relay_worker_sentry_warning_old_events():
    mock_event = MagicMock(spec=OutboxEvent)
    mock_event.id = uuid.uuid4()
    mock_event.event_type = "PositionOpened"
    mock_event.status = "pending"
    mock_event.created_at = datetime.now() - timedelta(hours=25)

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.all.side_effect = [[mock_event], []]

    with patch("web_app.tasks.outbox_relay.SessionLocal", return_value=mock_db), \
         patch("web_app.tasks.outbox_relay.process_position_opened_task.delay"), \
         patch("web_app.tasks.outbox_relay.sentry_sdk.capture_message") as mock_sentry:
        
        relay = OutboxRelay(max_retries=5)
        relay.process_pending_events()

        mock_sentry.assert_called_once()
        assert "is older than 24 hours" in mock_sentry.call_args[0][0]


def test_process_position_opened_task_success():
    event_id = str(uuid.uuid4())
    position_id = str(uuid.uuid4())
    tx_hash = "test_tx_hash"
    
    mock_event = MagicMock(spec=OutboxEvent)
    mock_event.id = uuid.UUID(event_id)
    mock_event.event_type = "PositionOpened"
    mock_event.payload = json.dumps({"position_id": position_id, "transaction_hash": tx_hash})
    mock_event.status = "pending"
    
    mock_position = MagicMock(spec=Position)
    mock_position.id = uuid.UUID(position_id)
    mock_position.status = "pending"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_event

    with patch("web_app.tasks.outbox_relay.SessionLocal", return_value=mock_db), \
         patch("web_app.tasks.outbox_relay.PositionDBConnector.get_object", return_value=mock_position), \
         patch("web_app.tasks.outbox_relay.PositionDBConnector.open_position") as mock_open, \
         patch("web_app.tasks.outbox_relay.TransactionDBConnector.get_object_by_field", return_value=None), \
         patch("web_app.tasks.outbox_relay.TransactionDBConnector.create_transaction") as mock_create_tx, \
         patch("web_app.tasks.outbox_relay.asyncio.run", return_value={"XLM": 0.1}):

        process_position_opened_task.run(event_id)

        mock_open.assert_called_once()
        mock_create_tx.assert_called_once()
        assert mock_event.status == "processed"
        mock_db.commit.assert_called()


def test_process_position_opened_task_downstream_500():
    event_id = str(uuid.uuid4())
    position_id = str(uuid.uuid4())
    tx_hash = "test_tx_hash"
    
    mock_event = MagicMock(spec=OutboxEvent)
    mock_event.id = uuid.UUID(event_id)
    mock_event.event_type = "PositionOpened"
    mock_event.payload = json.dumps({"position_id": position_id, "transaction_hash": tx_hash})
    mock_event.status = "processing"
    mock_event.retry_count = 0
    
    mock_position = MagicMock(spec=Position)
    mock_position.id = uuid.UUID(position_id)
    mock_position.status = "pending"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_event

    from celery.exceptions import Retry
    retry_exception = Retry()

    with patch("web_app.tasks.outbox_relay.SessionLocal", return_value=mock_db), \
         patch("web_app.tasks.outbox_relay.PositionDBConnector.get_object", return_value=mock_position), \
         patch("web_app.tasks.outbox_relay.TransactionDBConnector.get_object_by_field", return_value=None), \
         patch("web_app.tasks.outbox_relay.asyncio.run", side_effect=Exception("Simulated downstream 500")), \
         patch("web_app.tasks.outbox_relay.process_position_opened_task.retry", side_effect=retry_exception) as mock_retry:

        with pytest.raises(Retry):
            process_position_opened_task.run(event_id)

        assert mock_retry.called


def test_process_position_opened_task_idempotency():
    event_id = str(uuid.uuid4())
    position_id = str(uuid.uuid4())
    tx_hash = "test_tx_hash"
    
    mock_event = MagicMock(spec=OutboxEvent)
    mock_event.id = uuid.UUID(event_id)
    mock_event.event_type = "PositionOpened"
    mock_event.payload = json.dumps({"position_id": position_id, "transaction_hash": tx_hash})
    mock_event.status = "pending"
    
    mock_position = MagicMock(spec=Position)
    mock_position.id = uuid.UUID(position_id)
    mock_position.status = "opened"

    mock_tx = MagicMock(spec=Transaction)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_event

    with patch("web_app.tasks.outbox_relay.SessionLocal", return_value=mock_db), \
         patch("web_app.tasks.outbox_relay.PositionDBConnector.get_object", return_value=mock_position), \
         patch("web_app.tasks.outbox_relay.PositionDBConnector.open_position") as mock_open, \
         patch("web_app.tasks.outbox_relay.TransactionDBConnector.get_object_by_field", return_value=mock_tx), \
         patch("web_app.tasks.outbox_relay.TransactionDBConnector.create_transaction") as mock_create_tx, \
         patch("web_app.tasks.outbox_relay.asyncio.run", return_value={"XLM": 0.1}):

        process_position_opened_task.run(event_id)

        mock_open.assert_not_called()
        mock_create_tx.assert_not_called()
        assert mock_event.status == "processed"
        mock_db.commit.assert_called()
