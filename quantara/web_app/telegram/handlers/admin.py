"""Administrative Telegram commands for incident response."""

import asyncio
import logging
import os
import secrets
import time

import redis.asyncio as redis
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from web_app.db.crud.telegram import TelegramUserDBConnector
from web_app.telegram.config import TELEGRAM_ADMIN_USER_IDS

logger = logging.getLogger(__name__)

admin_router = Router()
telegram_db = TelegramUserDBConnector()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
BROADCAST_RATE_LIMIT_SECONDS = 60 * 60
BROADCAST_CONFIRM_TTL_SECONDS = 10 * 60
HEALTH_REDIS_TIMEOUT_SECONDS = 1.5
NOTIFICATION_PAUSE_KEY = "quantara:telegram:notifications:paused"
BROADCAST_RATE_KEY_PREFIX = "quantara:telegram:admin:broadcast:rate"
BROADCAST_PENDING_KEY_PREFIX = "quantara:telegram:admin:broadcast:pending"
BOT_STARTED_AT = time.monotonic()

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return the lazily initialized shared Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _is_admin(user) -> bool:
    """Return whether an aiogram user is in the configured admin allowlist."""
    return bool(user and user.id in TELEGRAM_ADMIN_USER_IDS)


async def _reject_unauthorized(event: Message | CallbackQuery) -> bool:
    """Reply to unauthorized callers and report whether processing must stop."""
    if _is_admin(event.from_user):
        return False
    if isinstance(event, CallbackQuery):
        await event.answer("Admin authorization required.", show_alert=True)
    else:
        await event.answer("Admin authorization required.")
    return True


def _rate_key(admin_id: int) -> str:
    """Build the per-admin hourly broadcast rate-limit key."""
    return f"{BROADCAST_RATE_KEY_PREFIX}:{admin_id}"


def _pending_key(admin_id: int, nonce: str) -> str:
    """Build the key for a broadcast awaiting confirmation."""
    return f"{BROADCAST_PENDING_KEY_PREFIX}:{admin_id}:{nonce}"


async def notifications_are_paused() -> bool:
    """Return whether alert delivery is globally paused, failing open on Redis errors."""
    try:
        return bool(await get_redis_client().exists(NOTIFICATION_PAUSE_KEY))
    except Exception as exc:
        logger.error("Unable to read Telegram pause state: %s", exc)
        return False


@admin_router.message(
    Command("broadcast"), F.from_user.func(lambda user: _is_admin(user))
)
async def broadcast_cmd(message: Message, command: CommandObject) -> None:
    """Stage a broadcast and ask the administrator for confirmation."""
    if await _reject_unauthorized(message):
        return

    text = (command.args or "").strip()
    if not text:
        await message.answer("Usage: /broadcast <message>")
        return

    client = get_redis_client()
    remaining = await client.ttl(_rate_key(message.from_user.id))
    if remaining > 0:
        await message.answer(
            f"Broadcast rate limit active. Try again in {remaining} seconds."
        )
        return

    nonce = secrets.token_urlsafe(8)
    await client.setex(
        _pending_key(message.from_user.id, nonce),
        BROADCAST_CONFIRM_TTL_SECONDS,
        text,
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Confirm broadcast",
                    callback_data=f"admin:broadcast:confirm:{nonce}",
                ),
                InlineKeyboardButton(
                    text="Cancel",
                    callback_data=f"admin:broadcast:cancel:{nonce}",
                ),
            ]
        ]
    )
    await message.answer(
        f"Broadcast this message to all opted-in users?\n\n{text}",
        reply_markup=keyboard,
    )


async def _send_broadcast(bot, recipients: list[str], text: str) -> tuple[int, int]:
    """Send a bounded-concurrency broadcast and return sent/failed counts."""
    semaphore = asyncio.Semaphore(20)

    async def send(telegram_id: str) -> bool:
        """Send to one recipient without aborting the remaining broadcast."""
        async with semaphore:
            try:
                await bot.send_message(chat_id=telegram_id, text=text)
                return True
            except Exception as exc:
                logger.warning("Broadcast delivery failed for %s: %s", telegram_id, exc)
                return False

    results = await asyncio.gather(*(send(telegram_id) for telegram_id in recipients))
    sent = sum(results)
    return sent, len(results) - sent


@admin_router.callback_query(
    F.data.startswith("admin:broadcast:confirm:"),
    F.from_user.func(lambda user: _is_admin(user)),
)
async def confirm_broadcast(callback: CallbackQuery) -> None:
    """Send a staged broadcast after atomically acquiring the hourly limit."""
    if await _reject_unauthorized(callback):
        return

    nonce = callback.data.rsplit(":", 1)[-1]
    client = get_redis_client()
    pending_key = _pending_key(callback.from_user.id, nonce)
    text = await client.get(pending_key)
    if text is None:
        await callback.answer("This confirmation expired.", show_alert=True)
        return

    acquired = await client.set(
        _rate_key(callback.from_user.id),
        "1",
        ex=BROADCAST_RATE_LIMIT_SECONDS,
        nx=True,
    )
    if not acquired:
        await callback.answer("Broadcast rate limit active.", show_alert=True)
        return

    await client.delete(pending_key)
    await callback.answer("Broadcast started.")
    recipients = await asyncio.to_thread(telegram_db.get_notification_recipients)
    sent, failed = await _send_broadcast(callback.bot, recipients, text)
    await callback.message.edit_text(
        f"Broadcast complete: {sent} sent, {failed} failed."
    )


@admin_router.callback_query(
    F.data.startswith("admin:broadcast:cancel:"),
    F.from_user.func(lambda user: _is_admin(user)),
)
async def cancel_broadcast(callback: CallbackQuery) -> None:
    """Discard a staged broadcast."""
    if await _reject_unauthorized(callback):
        return

    nonce = callback.data.rsplit(":", 1)[-1]
    await get_redis_client().delete(_pending_key(callback.from_user.id, nonce))
    await callback.answer("Broadcast cancelled.")
    await callback.message.edit_text("Broadcast cancelled.")


@admin_router.message(Command("pause"), F.from_user.func(lambda user: _is_admin(user)))
async def pause_cmd(message: Message, command: CommandObject) -> None:
    """Pause Telegram alert delivery for the requested number of minutes."""
    if await _reject_unauthorized(message):
        return

    try:
        minutes = int((command.args or "").strip())
    except ValueError:
        minutes = 0
    if minutes <= 0:
        await message.answer("Usage: /pause <positive minutes>")
        return

    seconds = minutes * 60
    await get_redis_client().set(
        NOTIFICATION_PAUSE_KEY,
        str(message.from_user.id),
        ex=seconds,
    )
    await message.answer(f"Notifications paused for {minutes} minute(s).")


@admin_router.message(Command("health"), F.from_user.func(lambda user: _is_admin(user)))
async def health_cmd(message: Message) -> None:
    """Report bot uptime and bounded Redis ping latency."""
    if await _reject_unauthorized(message):
        return

    started = time.perf_counter()
    try:
        await asyncio.wait_for(
            get_redis_client().ping(), timeout=HEALTH_REDIS_TIMEOUT_SECONDS
        )
        redis_status = "up"
    except TimeoutError:
        redis_status = "timeout"
    except Exception:
        redis_status = "down"
    latency_ms = (time.perf_counter() - started) * 1_000
    uptime_seconds = int(time.monotonic() - BOT_STARTED_AT)
    await message.answer(
        f"Bot uptime: {uptime_seconds}s\n" f"Redis: {redis_status} ({latency_ms:.1f}ms)"
    )
