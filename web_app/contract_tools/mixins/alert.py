"""
This module contains the alert mixin class.
"""

from typing import List

from web_app.contract_tools.mixins.custom_exception import HealthRatioLevelLowException
from web_app.contract_tools.mixins.dashboard import DashboardMixin
from web_app.db.crud import TelegramUserDBConnector, UserDBConnector
from web_app.db.models import Status

ALERT_THRESHOLD = 1.1


class AlertMixin:
    """
    Mixin class for alert related methods.
    """

    def check_users_health_ratio_level(self) -> None:
        """
        Check the health ratio level for all users with an OPENED position.
        If a user's health ratio level is lower than 1.1, raise a `HealthRatioLevelLowException`.
        """

        users = UserDBConnector().get_all_users_with_opened_position()

        for user in users:
            zk_lend_position = DashboardMixin.get_zklend_position(user.contract_address)

            health_ratio_level = zk_lend_position.health_ratio_level
            if health_ratio_level < ALERT_THRESHOLD:
                raise HealthRatioLevelLowException(user.id, health_ratio_level)

    def send_notification(self, user_id: int, health_ratio: float):
        """
        Send notification to a user if they have allowed notifications.

        Args:
            user_id: ID of the r to notify
            health_ratio: Current health ratio of the user's position
        """
        telegram_user = TelegramUserDBConnector.get_by_user_id(user_id)

        if telegram_user and telegram_user.is_allowed_notification(
            wallet_id=telegram_user.wallet_id
        ):
            # TODO: Add sending telegram message
            # Example placeholder for future implementation:
            # send_telegram_message(
            #     chat_id=telegram_user.chat_id,
            #     message=f"⚠️ Low Health Ratio Alert: Your current health ratio is {health_ratio}"
            # )
            pass
