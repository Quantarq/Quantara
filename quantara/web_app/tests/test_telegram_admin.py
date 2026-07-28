"""Tests for Telegram incident-response admin commands."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from web_app.telegram.config import parse_admin_ids
from web_app.telegram.handlers import admin


def _message(user_id=7):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        answer=AsyncMock(),
    )


def _callback(data, user_id=7):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        data=data,
        answer=AsyncMock(),
        bot=SimpleNamespace(send_message=AsyncMock()),
        message=SimpleNamespace(edit_text=AsyncMock()),
    )


def test_parse_admin_ids_ignores_blanks_and_invalid_values():
    assert parse_admin_ids(" 7,8,invalid,, 9 ") == frozenset({7, 8, 9})


async def test_broadcast_requires_an_admin_even_when_called_directly():
    message = _message(user_id=99)

    with patch.object(admin, "TELEGRAM_ADMIN_USER_IDS", frozenset({7})):
        await admin.broadcast_cmd(message, SimpleNamespace(args="maintenance"))

    message.answer.assert_awaited_once_with("Admin authorization required.")


async def test_broadcast_stages_message_with_confirmation():
    message = _message()
    redis_client = MagicMock()
    redis_client.ttl = AsyncMock(return_value=-2)
    redis_client.setex = AsyncMock()

    with (
        patch.object(admin, "TELEGRAM_ADMIN_USER_IDS", frozenset({7})),
        patch.object(admin, "get_redis_client", return_value=redis_client),
        patch.object(admin.secrets, "token_urlsafe", return_value="nonce"),
    ):
        await admin.broadcast_cmd(message, SimpleNamespace(args=" maintenance "))

    redis_client.setex.assert_awaited_once_with(
        admin._pending_key(7, "nonce"),
        admin.BROADCAST_CONFIRM_TTL_SECONDS,
        "maintenance",
    )
    text, keyboard = (
        message.answer.await_args.args[0],
        message.answer.await_args.kwargs["reply_markup"],
    )
    assert "maintenance" in text
    assert keyboard.inline_keyboard[0][0].callback_data.endswith(":nonce")


async def test_confirm_broadcast_enforces_rate_limit_and_reports_delivery():
    callback = _callback("admin:broadcast:confirm:nonce")
    callback.bot.send_message.side_effect = [None, RuntimeError("blocked")]
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="maintenance")
    redis_client.set = AsyncMock(return_value=True)
    redis_client.delete = AsyncMock()

    with (
        patch.object(admin, "TELEGRAM_ADMIN_USER_IDS", frozenset({7})),
        patch.object(admin, "get_redis_client", return_value=redis_client),
        patch.object(
            admin.telegram_db,
            "get_notification_recipients",
            return_value=["11", "22"],
        ),
    ):
        await admin.confirm_broadcast(callback)

    redis_client.set.assert_awaited_once_with(
        admin._rate_key(7),
        "1",
        ex=admin.BROADCAST_RATE_LIMIT_SECONDS,
        nx=True,
    )
    assert callback.bot.send_message.await_count == 2
    callback.message.edit_text.assert_awaited_once_with(
        "Broadcast complete: 1 sent, 1 failed."
    )


async def test_confirm_broadcast_rejects_second_send_within_hour():
    callback = _callback("admin:broadcast:confirm:nonce")
    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value="maintenance")
    redis_client.set = AsyncMock(return_value=None)

    with (
        patch.object(admin, "TELEGRAM_ADMIN_USER_IDS", frozenset({7})),
        patch.object(admin, "get_redis_client", return_value=redis_client),
    ):
        await admin.confirm_broadcast(callback)

    callback.answer.assert_awaited_once_with(
        "Broadcast rate limit active.", show_alert=True
    )
    callback.bot.send_message.assert_not_awaited()


async def test_pause_persists_redis_record_with_requested_ttl():
    message = _message()
    redis_client = MagicMock()
    redis_client.set = AsyncMock()

    with (
        patch.object(admin, "TELEGRAM_ADMIN_USER_IDS", frozenset({7})),
        patch.object(admin, "get_redis_client", return_value=redis_client),
    ):
        await admin.pause_cmd(message, SimpleNamespace(args="15"))

    redis_client.set.assert_awaited_once_with(
        admin.NOTIFICATION_PAUSE_KEY,
        "7",
        ex=15 * 60,
    )


async def test_health_reports_redis_latency_and_uptime():
    message = _message()
    redis_client = MagicMock()
    redis_client.ping = AsyncMock(return_value=True)

    with (
        patch.object(admin, "TELEGRAM_ADMIN_USER_IDS", frozenset({7})),
        patch.object(admin, "get_redis_client", return_value=redis_client),
    ):
        await admin.health_cmd(message)

    response = message.answer.await_args.args[0]
    assert "Bot uptime:" in response
    assert "Redis: up" in response


async def test_paused_notifications_are_suppressed():
    from web_app.telegram import notifications

    notifications.bot = SimpleNamespace(send_message=AsyncMock())
    with patch.object(
        notifications, "notifications_are_paused", AsyncMock(return_value=True)
    ):
        await notifications.send_health_ratio_notification("11", 1.5)

    notifications.bot.send_message.assert_not_awaited()
