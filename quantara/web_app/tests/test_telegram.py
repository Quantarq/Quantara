"""
Tests for the Telegram bot module (``web_app/telegram/``).

Scope:
- ``utils.check_telegram_authorization``: HMAC-SHA-256 verification of
  Telegram ``initData`` payloads (valid, wrong hash, wrong token, empty,
  missing hash, expired).
- ``notifications.send_health_ratio_notification``: recurses the retry
  loop when Telegram replies with ``RetryAfter``, falls back to a
  default retry interval when the server does not specify one, gives up
  after the default retry count, and logs-and-returns on an unexpected
  exception.
- ``handlers.command``: ``/start`` basic greeting flow and the
  ``/start <user_id>`` deep-link flow that turns notifications on.

Static-only modules (``config``, ``texts``, ``markups``) and the entry
point ``__main__`` are intentionally out of scope: they are constants or
wiring and get implicit coverage through the flows above.
"""

import hashlib
import hmac
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramRetryAfter


# ─────────────────────────────────────────────────────────────────────────────
# Module-level state hygiene
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _snapshot_and_restore_telegram_singletons():
    """Save and restore module-level singletons so test order is irrelevant."""
    from web_app.telegram import notifications as notifications_module

    saved_bot = notifications_module.bot
    yield
    notifications_module.bot = saved_bot


def _retry_after_exc(retry_after):
    """Construct a real ``TelegramRetryAfter`` so ``raise`` propagates.

    ``MagicMock(spec=TelegramRetryAfter)`` is not derived from
    ``BaseException``, so Python refuses to re-raise it inside the SUT's
    ``except TelegramRetryAfter`` block — the retry branch never executes
    and tests observe wrong ``send_message.await_count`` values. Using the
    real class keeps both ``isinstance(exc, TelegramRetryAfter)`` and
    ``raise`` semantics intact.
    """
    return TelegramRetryAfter(
        method=MagicMock(),
        message="rate-limit",
        retry_after=retry_after,
    )


@pytest.fixture
def notifications_module():
    """Replace ``notifications.bot`` and stub ``asyncio.sleep`` for retry tests."""
    from web_app.telegram import notifications

    notifications.bot = MagicMock()
    sleep_mock = AsyncMock()
    with patch("web_app.telegram.notifications.asyncio.sleep", new=sleep_mock):
        yield notifications, sleep_mock


# ─────────────────────────────────────────────────────────────────────────────
# 1. utils.check_telegram_authorization
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckTelegramAuthorization:
    """HMAC-SHA-256 verification of Telegram initData payloads."""

    BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    USER_ID = 11111111
    AUTH_DATE = 1700000000

    @staticmethod
    def _build_auth(token, **overrides):
        """Build an auth_data dict whose hash is valid for ``token``."""
        fields = {
            "id": str(TestCheckTelegramAuthorization.USER_ID),
            "first_name": "Test",
            "username": "tester",
            "auth_date": str(TestCheckTelegramAuthorization.AUTH_DATE),
            "query_id": "AAHdF6IQAAAAAN0XHmA",
        }
        fields.update(overrides)
        sorted_pairs = sorted((k, v) for k, v in fields.items() if k != "hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)
        secret_key = hashlib.sha256(token.encode()).digest()
        fields["hash"] = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        return fields

    def test_accepts_payload_without_expiry(self):
        """A correctly-signed payload verifies as True."""
        from web_app.telegram.utils import check_telegram_authorization
        data = self._build_auth(self.BOT_TOKEN)
        assert check_telegram_authorization(self.BOT_TOKEN, data) is True

    def test_rejects_wrong_hash(self):
        """A mutated hash fails verification even with the right token."""
        from web_app.telegram.utils import check_telegram_authorization
        data = self._build_auth(self.BOT_TOKEN)
        data["hash"] = "0" * 64
        assert check_telegram_authorization(self.BOT_TOKEN, data) is False

    def test_rejects_payload_signed_with_other_token(self):
        """Hash produced for one token does not verify against another."""
        from web_app.telegram.utils import check_telegram_authorization
        data = self._build_auth("not-the-real-token")
        assert check_telegram_authorization(self.BOT_TOKEN, data) is False

    def test_rejects_empty_inputs(self):
        """Empty token or payload cannot verify."""
        from web_app.telegram.utils import check_telegram_authorization
        assert check_telegram_authorization("", {"hash": "x"}) is False
        assert check_telegram_authorization(self.BOT_TOKEN, {}) is False

    def test_rejects_missing_hash(self):
        """A payload without ``hash`` cannot verify."""
        from web_app.telegram.utils import check_telegram_authorization
        data = self._build_auth(self.BOT_TOKEN)
        data.pop("hash")
        assert check_telegram_authorization(self.BOT_TOKEN, data) is False

    def test_rejects_expired_payload(self):
        """An auth_date well outside the expiry window is rejected."""
        from web_app.telegram.utils import check_telegram_authorization
        old_date = self.AUTH_DATE - 10_000_000
        data = self._build_auth(self.BOT_TOKEN, auth_date=str(old_date))
        ok = check_telegram_authorization(
            self.BOT_TOKEN, data, expiration_seconds=60,
        )
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# 2. notifications.send_health_ratio_notification
# ─────────────────────────────────────────────────────────────────────────────


class TestSendHealthRatioNotification:
    """Retry recursion on rate-limit responses from Telegram."""

    async def test_sends_message_with_full_formatted_template(
        self, notifications_module,
    ):
        """First-attempt send uses the complete ``HEALTH_RATIO_WARNING_MESSAGE`` template."""
        from web_app.telegram.texts import HEALTH_RATIO_WARNING_MESSAGE

        notifications, _ = notifications_module
        notifications.bot.send_message = AsyncMock(return_value=None)
        ratio = Decimal("1.5")

        await notifications.send_health_ratio_notification("42", ratio)

        notifications.bot.send_message.assert_awaited_once()
        kwargs = notifications.bot.send_message.await_args.kwargs
        assert kwargs["chat_id"] == "42"
        assert kwargs["text"] == HEALTH_RATIO_WARNING_MESSAGE.format(
            health_ratio=ratio,
        )

    async def test_retries_with_servers_retry_after(self, notifications_module):
        """First attempt rate-limited → sleep(servers_value) → succeed."""
        notifications, sleep_mock = notifications_module
        notifications.bot.send_message = AsyncMock(
            side_effect=[_retry_after_exc(3), None],
        )
        await notifications.send_health_ratio_notification(
            "42", Decimal("1.5"),
        )
        assert notifications.bot.send_message.await_count == 2
        sleep_mock.assert_awaited_once_with(3)

    async def test_falls_back_to_default_retry_after(self, notifications_module):
        """``retry_after`` falsy → use ``DEFAULT_RETRY_AFTER`` instead."""
        notifications, sleep_mock = notifications_module
        notifications.bot.send_message = AsyncMock(
            side_effect=[_retry_after_exc(None), None],
        )
        await notifications.send_health_ratio_notification(
            "42", Decimal("1.5"),
        )
        sleep_mock.assert_awaited_once_with(notifications.DEFAULT_RETRY_AFTER)

    async def test_gives_up_after_default_retry_count(self, notifications_module):
        """``DEFAULT_RETRY_COUNT=1`` → exactly one retry before giving up."""
        notifications, _ = notifications_module
        notifications.bot.send_message = AsyncMock(
            side_effect=[_retry_after_exc(1), _retry_after_exc(1)],
        )
        await notifications.send_health_ratio_notification(
            "42", Decimal("1.5"),
        )
        assert notifications.bot.send_message.await_count == 2

    async def test_logs_and_returns_on_unexpected_exception(
        self, notifications_module,
    ):
        """Non-TelegramRetryAfter exceptions log and return without recursion."""
        notifications, sleep_mock = notifications_module
        notifications.bot.send_message = AsyncMock(
            side_effect=RuntimeError("boom"),
        )
        await notifications.send_health_ratio_notification(
            "42", Decimal("1.5"),
        )
        notifications.bot.send_message.assert_awaited_once()
        sleep_mock.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 3. handlers/command — /start (basic) and /start <user_id> (deep link)
# ─────────────────────────────────────────────────────────────────────────────


class TestCommandHandlers:
    """Behaviour of registered command handlers."""

    @staticmethod
    def _fake_message(from_user_id=999):
        msg = SimpleNamespace(
            from_user=SimpleNamespace(id=from_user_id),
        )
        msg.answer = AsyncMock(return_value=None)
        return msg

    async def test_notification_allowed_invokes_db_layers_and_answers(self):
        """Deep-link ``/start`` flips notification state and replies."""
        from web_app.db.models import User
        from web_app.telegram.handlers import command

        fake_user = SimpleNamespace(wallet_id="WALLET-XYZ")
        command.db_connector.get_object = MagicMock(return_value=fake_user)
        command.telegram_db.update_telegram_user = MagicMock(return_value=None)
        command.telegram_db.set_allow_notification = MagicMock(return_value=None)

        msg = self._fake_message()
        cmd_obj = SimpleNamespace(args="USER-123")

        await command.notification_allowed(msg, cmd_obj)

        command.db_connector.get_object.assert_called_once_with(
            User, "USER-123",
        )
        command.telegram_db.update_telegram_user.assert_called_once_with(
            "999", {"wallet_id": "WALLET-XYZ"},
        )
        command.telegram_db.set_allow_notification.assert_called_once_with(
            "999", "WALLET-XYZ",
        )
        msg.answer.assert_awaited_once_with(
            command.NOTIFICATION_ALLOWED_MESSAGE,
            reply_markup=command.launch_main_web_app_kb,
        )

    async def test_start_cmd_sends_welcome_with_inline_keyboard(self):
        """Plain ``/start`` answers with the welcome text and reply markup."""
        from web_app.telegram.handlers import command

        msg = SimpleNamespace(
            from_user=SimpleNamespace(id=999),
        )
        msg.answer = MagicMock(return_value=None)

        await command.start_cmd(msg)
        msg.answer.assert_called_once_with(
            command.WELCOME_MESSAGE,
            reply_markup=command.launch_main_web_app_kb,
        )
