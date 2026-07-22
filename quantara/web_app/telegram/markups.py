"""
This module defines the inline keyboard markup used in the Telegram bot.

It includes the keyboard for launching the main web application
and a helper to build deep links with replay-protected nonces.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .config import WEBAPP_URL
from .nonce_store import nonce_store


launch_main_web_app_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Launch app", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
)


def build_notification_deep_link(user_id: int, bot_username: str) -> tuple[str, str]:
    """Build a /start deep link URL with a signed nonce.

    Args:
        user_id: The numeric Telegram user id to bind.
        bot_username: The bot's Telegram username (without @).

    Returns:
        A tuple of (deep_link_url, nonce). The nonce is stored server-side
        and must be validated on receipt.
    """
    nonce = nonce_store.generate(str(user_id))
    return f"https://t.me/{bot_username}?start={user_id}:{nonce}", nonce
