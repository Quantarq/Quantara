"""
This module contains the alert mixin class for health ratio monitoring.
"""

import asyncio
import logging
import os

from prometheus_client import Counter, REGISTRY

from web_app.telegram.notifications import send_health_ratio_notification
from web_app.contract_tools.mixins.health_ratio import HealthRatioMixin
from web_app.db.crud import UserDBConnector
from web_app.api.dependencies import get_stellar_client


logger = logging.getLogger(__name__)
ALERT_THRESHOLD = float(os.getenv("HEALTH_RATIO_ALERT_THRESHOLD", "1.1"))
ALERT_CONCURRENCY_LIMIT = int(os.getenv("HEALTH_RATIO_ALERT_CONCURRENCY", "16"))
ALERT_TASK_TIMEOUT_SECONDS = float(os.getenv("HEALTH_RATIO_ALERT_TIMEOUT_SECONDS", "10"))


def _get_or_create_counter(name: str, documentation: str, labelnames: list[str]):
    """Return an existing Prometheus counter or create one."""
    existing = (
        REGISTRY._names_to_collectors.get(name)
        or REGISTRY._names_to_collectors.get(f"{name}_total")
    )
    if existing is not None:
        return existing
    return Counter(name, documentation, labelnames)


ALERT_SWEEP_COUNTER = _get_or_create_counter(
    "health_ratio_alert_sweep_results_total",
    "Health-ratio alert sweep results by outcome",
    ["outcome"],
)


class AlertMixin:
    """
    Mixin class for alert related methods.
    Handles health ratio monitoring and notification dispatch.
    """

    @classmethod
    async def check_users_health_ratio_level(cls) -> None:
        """
        Check the health ratio level for all users with an OPENED position.
        Sends a Telegram notification if a user's health ratio falls below the
        configured ALERT_THRESHOLD.
        """

        users_data = UserDBConnector().get_users_for_notifications()
        client = get_stellar_client()
        user_number = len([user for user, _ in users_data])
        logger.info("Found number of users for notifications: %s", user_number)

        semaphore = asyncio.Semaphore(ALERT_CONCURRENCY_LIMIT)
        tasks = [
            cls._check_single_user_health_ratio(
                contract_address,
                telegram_id,
                client,
                semaphore,
            )
            for contract_address, telegram_id in users_data
            if contract_address
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(result == "success" for result in results)
        failure_count = len(results) - success_count
        ALERT_SWEEP_COUNTER.labels(outcome="success").inc(success_count)
        ALERT_SWEEP_COUNTER.labels(outcome="failure").inc(failure_count)
        logger.info(
            "health_ratio_alert_sweep_summary",
            extra={"success": success_count, "failure": failure_count},
        )

    @classmethod
    async def _check_single_user_health_ratio(
        cls,
        contract_address: str,
        telegram_id: int,
        client,
        semaphore: asyncio.Semaphore,
    ) -> str:
        """Check one user's health ratio without blocking the full sweep."""
        async with semaphore:
            try:
                health_ratio_level, _ = await asyncio.wait_for(
                    HealthRatioMixin.get_health_ratio_and_tvl(contract_address, client),
                    timeout=ALERT_TASK_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                logger.error(
                    "Failed to get health ratio for %s: %s", contract_address, exc
                )
                return "failure"

            health_value = float(health_ratio_level)
            if health_value < ALERT_THRESHOLD:
                logger.info(
                    "Health ratio level for user %s is %s",
                    contract_address,
                    health_ratio_level,
                )
                await cls.send_notification(telegram_id, health_ratio_level)
            return "success"

    @staticmethod
    async def send_notification(telegram_id: int, health_ratio: float):
        """
        Send notification to a user if they have allowed notifications.

        Args:
            telegram_id: ID of the user to notify
            health_ratio: Current health ratio of the user's position
        """
        await send_health_ratio_notification(telegram_id, health_ratio)
        logger.info(
            "Notification sent to user %s with health ratio %s", telegram_id, health_ratio
        )