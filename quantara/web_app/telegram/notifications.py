"""
This module provides functionalities to send telegram notifications
"""

import asyncio
import logging
from decimal import Decimal

from aiogram.exceptions import TelegramRetryAfter

from web_app.db.crud import TelegramUserDBConnector
from web_app.telegram import bot

from .dedupe import NotificationDedupe
from .handlers.admin import notifications_are_paused
from .texts import i18n

logger = logging.getLogger(__name__)

telegram_db = TelegramUserDBConnector()
dedupe = NotificationDedupe()

DEFAULT_RETRY_AFTER = 10
DEFAULT_RETRY_COUNT = 1


async def send_health_ratio_notification(
    telegram_id: str,
    health_ratio: Decimal,
    position_id: str = "",
    retry_count: int = DEFAULT_RETRY_COUNT,
) -> None:
    """
    Send notification about health ratio to user.
    Deduplication prevents repeated alerts for the same user/position within 4h.
    """
    if await notifications_are_paused():
        logger.info(
            "Telegram alerts are paused; skipping notification to %s", telegram_id
        )
        return

    if position_id and not await dedupe.should_send(telegram_id, position_id):
        return

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=i18n.get("HEALTH_RATIO_WARNING_MESSAGE", health_ratio=health_ratio),
        )
        if position_id:
            await dedupe.record_send(telegram_id, position_id)
            await dedupe.record_success(telegram_id, position_id)
    except TelegramRetryAfter as e:
        if position_id:
            await dedupe.record_failure(telegram_id, position_id)
        if retry_count < 1:
            return logger.error(f"Failed to send notification to {telegram_id}: {e}")

        retry_after = DEFAULT_RETRY_AFTER
        if e.retry_after and 0 < e.retry_after:
            retry_after = e.retry_after

        await asyncio.sleep(retry_after)
        await send_health_ratio_notification(
            telegram_id,
            health_ratio,
            position_id=position_id,
            retry_count=retry_count - 1,
        )
    except Exception as e:
        if position_id:
            await dedupe.record_failure(telegram_id, position_id)
        logger.error(f"Failed to send notification to {telegram_id}: {e}")
