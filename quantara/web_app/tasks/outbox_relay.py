"""
Transactional outbox relay and Celery worker tasks for Soroban event delivery.
"""

import os
import asyncio
import json
import sentry_sdk
from datetime import datetime, timedelta
from celery import Celery
from sqlalchemy.orm import Session
from web_app.db.database import SessionLocal, init_db
from web_app.db.models import OutboxEvent, Position, Status, Transaction, TransactionStatus
from web_app.db.crud import PositionDBConnector, TransactionDBConnector
from web_app.contract_tools.mixins import DashboardMixin
from web_app.utils.logger import get_logger

logger = get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Initialize the Celery application
celery_app = Celery("outbox_relay", broker=REDIS_URL, backend=REDIS_URL)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=10)
def process_position_opened_task(self, event_id: str):
    """
    Celery task that consumes the PositionOpened event from the outbox.
    """
    logger.info("processing_position_opened_task_started", event_id=event_id)
    
    init_db()
    db: Session = SessionLocal()
    try:
        # 1. Fetch the outbox event
        event = db.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
        if not event:
            logger.error("outbox_event_not_found", event_id=event_id)
            return

        # If it's already processed, make it idempotent and do nothing
        if event.status == "processed":
            logger.info("outbox_event_already_processed", event_id=event_id)
            return

        # 2. Parse the payload
        payload = json.loads(event.payload)
        position_id = payload.get("position_id")
        transaction_hash = payload.get("transaction_hash")

        if not position_id or not transaction_hash:
            raise ValueError(f"Invalid payload for outbox event {event_id}")

        # 3. Connect to DB connectors
        position_db_connector = PositionDBConnector()
        transaction_db_connector = TransactionDBConnector()

        # 4. Check idempotency at resource levels
        position = position_db_connector.get_object(Position, position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found for outbox event {event_id}")

        existing_tx = transaction_db_connector.get_object_by_field(
            Transaction, "transaction_hash", transaction_hash
        )

        # Retrieve current prices
        try:
            # DashboardMixin.get_current_prices is an async function
            current_prices = asyncio.run(DashboardMixin.get_current_prices())
        except Exception as e:
            logger.error("downstream_pricing_api_failed", event_id=event_id, error=str(e))
            raise e

        # Update position status to OPENED if it's not already opened
        if position.status != Status.OPENED.value:
            position_db_connector.open_position(position_id, current_prices)
            logger.info("position_opened_successfully", position_id=position_id)
        else:
            logger.info("position_already_opened_skipping", position_id=position_id)

        # Create Transaction record if it's not already created
        if not existing_tx:
            transaction_db_connector.create_transaction(
                position_id, transaction_hash, status=TransactionStatus.OPENED.value
            )
            logger.info("transaction_recorded_successfully", transaction_hash=transaction_hash)
        else:
            logger.info("transaction_already_recorded_skipping", transaction_hash=transaction_hash)

        # 5. Mark outbox event as processed
        event.status = "processed"
        event.error_message = None
        db.commit()
        logger.info("outbox_event_processed_successfully", event_id=event_id)

    except Exception as exc:
        db.rollback()
        logger.exception("outbox_event_processing_failed", event_id=event_id, error=str(exc))
        
        # Update event status to failed and increment retry
        try:
            with SessionLocal() as fail_session:
                evt = fail_session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
                if evt:
                    evt.status = "failed"
                    evt.retry_count += 1
                    evt.error_message = str(exc)
                    fail_session.commit()
        except Exception as update_err:
            logger.error("failed_to_update_outbox_event_status", error=str(update_err))

        # Re-raise to trigger Celery retry mechanism
        raise self.retry(exc=exc)
    finally:
        db.close()


class OutboxRelay:
    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        init_db()

    def process_pending_events(self):
        """
        Scans event_outbox for pending/failed events and publishes them to Celery.
        Also flags events older than 24h with a Sentry warning.
        """
        logger.info("outbox_relay_scan_started")
        db: Session = SessionLocal()
        try:
            # Check for events older than 24h that are not processed
            cutoff_24h_naive = datetime.now() - timedelta(hours=24)
            
            old_events = db.query(OutboxEvent).filter(
                OutboxEvent.status != "processed",
                OutboxEvent.created_at < cutoff_24h_naive
            ).all()

            for event in old_events:
                msg = f"Outbox event {event.id} ({event.event_type}) is older than 24 hours and still not processed."
                logger.warning("outbox_event_older_than_24h", event_id=str(event.id), created_at=str(event.created_at))
                sentry_sdk.capture_message(msg, level="warning")

            # Fetch pending or failed events
            pending_events = db.query(OutboxEvent).filter(
                OutboxEvent.status.in_(["pending", "failed"]),
                OutboxEvent.retry_count < self.max_retries
            ).all()

            if not pending_events:
                logger.info("no_pending_outbox_events")
                return

            for event in pending_events:
                # Mark as processing
                event.status = "processing"
                db.commit()

                # Publish to Celery
                process_position_opened_task.delay(str(event.id))
                logger.info("published_outbox_event_to_queue", event_id=str(event.id))

        except Exception as e:
            logger.exception("outbox_relay_scan_failed", error=str(e))
        finally:
            db.close()


if __name__ == "__main__":
    relay = OutboxRelay()
    relay.process_pending_events()
