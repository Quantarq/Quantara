import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_app.contract_tools.mixins.alert import AlertMixin

USER_CONNECTOR = "web_app.contract_tools.mixins.alert.UserDBConnector"
STELLAR_CLIENT = "web_app.contract_tools.mixins.alert.get_stellar_client"
HEALTH_RATIO = "web_app.contract_tools.mixins.alert.HealthRatioMixin.get_health_ratio_and_tvl"


@pytest.mark.asyncio
async def test_alert_sweep_continues_after_user_failure():
    users = [("contract-ok", 1001), ("contract-fail", 1002), ("contract-low", 1003)]

    async def fake_health_ratio(contract_address, client):
        if contract_address == "contract-fail":
            raise RuntimeError("rpc failed")
        if contract_address == "contract-low":
            return "1.0", "100"
        return "1.5", "100"

    with ExitStack() as stack:
        connector = stack.enter_context(patch(USER_CONNECTOR))
        stack.enter_context(patch(STELLAR_CLIENT, return_value=MagicMock()))
        stack.enter_context(patch(HEALTH_RATIO, side_effect=fake_health_ratio))
        send_notification = stack.enter_context(
            patch.object(AlertMixin, "send_notification", new_callable=AsyncMock)
        )
        connector.return_value.get_users_for_notifications.return_value = users

        await AlertMixin.check_users_health_ratio_level()

    send_notification.assert_awaited_once_with(1003, "1.0")


@pytest.mark.asyncio
async def test_alert_sweep_runs_health_checks_concurrently():
    users = [(f"contract-{idx}", idx) for idx in range(4)]
    started = 0
    peak_started = 0
    release = asyncio.Event()

    async def fake_health_ratio(contract_address, client):
        nonlocal started, peak_started
        started += 1
        peak_started = max(peak_started, started)
        if started == len(users):
            release.set()
        await release.wait()
        return "1.5", "100"

    with ExitStack() as stack:
        stack.enter_context(
            patch("web_app.contract_tools.mixins.alert.ALERT_BATCH_CONCURRENCY", len(users))
        )
        connector = stack.enter_context(patch(USER_CONNECTOR))
        stack.enter_context(patch(STELLAR_CLIENT, return_value=MagicMock()))
        stack.enter_context(patch(HEALTH_RATIO, side_effect=fake_health_ratio))
        stack.enter_context(
            patch.object(AlertMixin, "send_notification", new_callable=AsyncMock)
        )
        connector.return_value.get_users_for_notifications.return_value = users

        await asyncio.wait_for(AlertMixin.check_users_health_ratio_level(), timeout=1)

    assert peak_started == len(users)


@pytest.mark.asyncio
async def test_single_user_timeout_does_not_stop_successes():
    users = [("contract-timeout", 1001), ("contract-ok", 1002)]

    async def fake_health_ratio(contract_address, client):
        if contract_address == "contract-timeout":
            await asyncio.sleep(1)
        return "1.5", "100"

    with ExitStack() as stack:
        stack.enter_context(
            patch("web_app.contract_tools.mixins.alert.ALERT_USER_TIMEOUT_SECONDS", 0.01)
        )
        connector = stack.enter_context(patch(USER_CONNECTOR))
        stack.enter_context(patch(STELLAR_CLIENT, return_value=MagicMock()))
        stack.enter_context(patch(HEALTH_RATIO, side_effect=fake_health_ratio))
        stack.enter_context(
            patch.object(AlertMixin, "send_notification", new_callable=AsyncMock)
        )
        connector.return_value.get_users_for_notifications.return_value = users

        await AlertMixin.check_users_health_ratio_level()