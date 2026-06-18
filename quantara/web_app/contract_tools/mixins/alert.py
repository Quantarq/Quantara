"""
This module contains the alert mixin class for health ratio monitoring.
"""

import logging
import os

from web_app.telegram.notifications import send_health_ratio_notification
from web_app.contract_tools.mixins.health_ratio import HealthRatioMixin
from web_app.db.crud import UserDBConnector
from web_app.api.dependencies import get_stellar_client


logger = logging.getLogger(__name__)
ALERT_THRESHOLD = float(os.getenv("HEALTH_RATIO_ALERT_THRESHOLD", "1.1"))


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
        logger.info(f"Found number of users for notifications: {user_number}")
        for contract_address, telegram_id in users_data:
            if not contract_address:
                continue
            try:
                health_ratio_level, _ = \
                    await HealthRatioMixin.get_health_ratio_and_tvl(contract_address, client)
            except Exception as e:
                logger.error(
                    "Failed to get health ratio for %s: %s", contract_address, e
                )
                continue

            health_value = float(health_ratio_level)
            if health_value < ALERT_THRESHOLD:
                logger.info(
                    f"Health ratio level for user {contract_address} is {health_ratio_level}"
                )
                await cls.send_notification(telegram_id, health_ratio_level)

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
