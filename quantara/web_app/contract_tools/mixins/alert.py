"""
This module contains the alert mixin class for health ratio monitoring.
"""

import asyncio
import logging
import os

from prometheus_client import Counter

from web_app.telegram.notifications import send_health_ratio_notification
from web_app.contract_tools.mixins.health_ratio import HealthRatioMixin
from web_app.db.crud import UserDBConnector
from web_app.api.dependencies import get_stellar_client


logger = logging.getLogger(__name__)
ALERT_THRESHOLD = float(os.getenv("HEALTH_RATIO_ALERT_THRESHOLD", "1.1"))
ALERT_BATCH_CONCURRENCY = int(os.getenv("HEALTH_ALERT_BATCH_CONCURRENCY", "16"))
ALERT_USER_TIMEOUT_SECONDS = float(os.getenv("HEALTH_ALERT_USER_TIMEOUT_SECONDS", "10"))
HEALTH_ALERT_SWEEP_RESULTS = Counter(
    "health_alert_sweep_results_total",
    "Health-ratio alert sweep outcomes by user check result.",
    ["result"],
)


class AlertMixin:
    """
    Mixin class for alert related methods.
    Handles health ratio monitoring and notification dispatch.
    """

    @classmethod
    async def _check_single_user_health_ratio(
        cls,
        contract_address: str,
        telegram_id: int,
        client,
    ) -> bool:
        if not contract_address:
            HEALTH_ALERT_SWEEP_RESULTS.labels(result="failure").inc()
            return False

        try:
            health_ratio_level, _ = await asyncio.wait_for(
                HealthRatioMixin.get_health_ratio_and_tvl(contract_address, client),
                timeout=ALERT_USER_TIMEOUT_SECONDS,
            )
        except Exception as e:
            logger.error(
                "Failed to get health ratio for %s: %s", contract_address, e
            )
            HEALTH_ALERT_SWEEP_RESULTS.labels(result="failure").inc()
            return False

        health_value = float(health_ratio_level)
        if health_value < ALERT_THRESHOLD:
            logger.info(
                "Health ratio level for user %s is %s",
                contract_address,
                health_ratio_level,
            )
            await cls.send_notification(telegram_id, health_ratio_level)

        HEALTH_ALERT_SWEEP_RESULTS.labels(result="success").inc()
        return True

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
        logger.info(f"Found number of users for notifications: {user_number}")

        semaphore = asyncio.Semaphore(ALERT_BATCH_CONCURRENCY)

        async def check_with_limit(contract_address: str, telegram_id: int) -> bool:
            async with semaphore:
                return await cls._check_single_user_health_ratio(
                    contract_address,
                    telegram_id,
                    client,
                )

        results = await asyncio.gather(
            *(
                check_with_limit(contract_address, telegram_id)
                for contract_address, telegram_id in users_data
            ),
            return_exceptions=True,
        )
        successes = sum(result is True for result in results)
        failures = len(results) - successes
        logger.info(
            "health_ratio_alert_sweep_complete",
            extra={"success": successes, "failure": failures},
        )

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
            f"Notification sent to user {telegram_id} with health ratio {health_ratio}"
        )