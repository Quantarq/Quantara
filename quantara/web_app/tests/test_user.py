"""
This module contains the tests for the user endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest

from web_app.api.serializers.transaction import UpdateUserContractRequest
from web_app.db.models import TelegramUser, User
from web_app.tests.conftest import client


@pytest.fixture(autouse=True)
def bypass_rate_limiter_in_user_tests():
    """Bypass slowapi rate limit check calls for user tests to prevent 429 errors."""
    with patch("slowapi.Limiter.check", return_value=True):
        yield


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wallet_id, expected_contract_address",
    [
        ("", ""),
        (
            "0x27994c503bd8c32525fbdaf9d398bdd4e86757988c64581b055a06c5955ea49",
            "0x698b63df00be56ba39447c9b9ca576ffd0edba0526d98b3e8e4a902ffcf12f0",
        ),
        ("invalid_wallet_id", None),
        (123_456_789, None),
        (3.14, None),
        ({}, None),
    ],
)
async def test_get_user_contract(
    client: client,
    mock_user_db_connector: MagicMock,
    wallet_id: str,
    expected_contract_address: str,
) -> None:
    """
    Test get_user_contract endpoint
    :param client: fastapi.testclient.TestClient
    :param mock_user_db_connector: unittest.mock.MagicMock
    :param wallet_id: str[wallet_id]
    :param expected_contract_address: str[expected_contract_address]
    :return: None
    """
    response = client.get(
        url="/api/get-user-contract",
        params={
            "wallet_id": wallet_id,
        },
    )
    response_json = response.json()

    if response.is_success:
        assert isinstance(response_json, str)
        assert response_json == str(expected_contract_address)
    else:
        assert isinstance(response_json, dict)
        assert response_json.get("detail") in (
            "User not found",
            "Contract not deployed",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wallet_id",
    [
        "",
        "0x27994c503bd8c32525fbdaf9d398bdd4e86757988c64581b055a06c5955ea49",
        "invalid_wallet_id",
        123_456_789,
        3.14,
        {},
    ],
)
async def test_check_user(
    client: client, mock_user_db_connector: MagicMock, wallet_id: str
) -> None:
    """
    Test check_user endpoint
    :param client: fastapi.testclient.TestClient
    :param mock_user_db_connector: unittest.mock.MagicMock
    :param wallet_id: str[wallet_id]
    :return: None
    """
    response = client.get(
        url="/api/check-user",
        params={
            "wallet_id": wallet_id,
        },
    )
    response_json = response.json()

    assert response.is_success
    assert isinstance(response_json, dict)
    assert isinstance(response_json.get("is_contract_deployed"), bool)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wallet_id, contract_address",
    [
        ("", ""),
        (
            "0x27994c503bd8c32525fbdaf9d398bdd4e86757988c64581b055a06c5955ea49",
            "0x698b63df00be56ba39447c9b9ca576ffd0edba0526d98b3e8e4a902ffcf12f0",
        ),
        ("invalid_wallet_id", None),
        (123_456_789, None),
        (3.14, None),
        ({}, None),
    ],
)
async def test_change_user_contract(
    client: client,
    mock_user_db_connector: MagicMock,
    wallet_id: str,
    contract_address: str,
) -> None:
    """
    Test get_user_contract endpoint
    :param client: fastapi.testclient.TestClient
    :param mock_user_db_connector: unittest.mock.MagicMock
    :param wallet_id: str[wallet_id]
    :param contract_address: str[contract_address]
    :return: None
    """
    data = UpdateUserContractRequest(
        wallet_id=str(wallet_id),
        contract_address=str(contract_address),
    )

    response = client.post(
        url="/api/update-user-contract",
        json=data.dict(),
    )
    response_json = response.json()

    assert response.is_success
    assert isinstance(response_json, dict)
    assert response_json.get("is_contract_deployed")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wallet_id, expected_contract_address",
    [
        ("", None),
        (
            "0x27994c503bd8c32525fbdaf9d398bdd4e86757988c64581b055a06c5955ea49",
            "0x698b63df00be56ba39447c9b9ca576ffd0edba0526d98b3e8e4a902ffcf12f0",
        ),
        ("invalid_wallet_id", None),
        (123_456_789, None),
        (3.14, None),
        ({}, None),
    ],
)
async def test_get_user_contract_address(
    client: client,
    mock_user_db_connector: MagicMock,
    wallet_id: str,
    expected_contract_address: str,
) -> None:
    """
    Test get_user_contract_address endpoint
    :param client: fastapi.testclient.TestClient
    :param mock_user_db_connector: unittest.mock.MagicMock
    :param wallet_id: str[wallet_id]
    :param expected_contract_address: str[expected_contract_address]
    :return: None
    """
    response = client.get(
        url="/api/get-user-contract-address",
        params={
            "wallet_id": wallet_id,
        },
    )
    response_json = response.json()

    assert response.is_success
    assert isinstance(response_json, dict)

    contract_address = response_json.get("contract_address")
    assert str(contract_address) == str(expected_contract_address)


@pytest.mark.asyncio
@patch("web_app.db.crud.TelegramUserDBConnector.set_allow_notification")
@patch("web_app.db.crud.TelegramUserDBConnector.get_telegram_user_by_wallet_id")
@patch("web_app.db.crud.UserDBConnector.get_user_by_wallet_id")
@pytest.mark.parametrize(
    "telegram_id, wallet_id, user_telegram_id, expected_status_code, expected_response",
    [
        (
            "123456789",
            "0x27994c503bd8c32525fbdaf9d398bdd4e86757988c64581b055a06c5955ea49",
            "123456789",
            200,
            {"detail": "User subscribed to notifications successfully"},
        ),
        (
            None,
            "0x27994c503bd8c32525fbdaf9d398bdd4e86757988c64581b055a06c5955ea49",
            "123456789",
            200,
            {"detail": "User subscribed to notifications successfully"},
        ),
        (
            "123456789",
            "invalid_wallet_id",
            None,
            404,
            {"detail": "User not found"},
        ),
        (
            None,
            "0x27994c503bd8c32525fbdaf9d398bdd4e86757988c64581b055a06c5955ea49",
            None,
            400,
            {"detail": "Failed to subscribe user to notifications"},
        ),
    ],
)
async def test_subscribe_to_notification(
    mock_get_user_by_wallet_id: MagicMock,
    mock_get_telegram_user_by_wallet_id: MagicMock,
    mock_set_allow_notification: MagicMock,
    client,
    telegram_id: str | None,
    wallet_id: str,
    user_telegram_id: str | None,
    expected_status_code: int,
    expected_response: dict,
) -> None:
    """
    Test subscribe_to_notification endpoint with both positive and negative cases.
    """
    mock_set_allow_notification.return_value = True

    mock_get_user_by_wallet_id.return_value = None
    if wallet_id != "invalid_wallet_id":
        mock_get_user_by_wallet_id.return_value = User(
            wallet_id=wallet_id,
            is_contract_deployed=True,
        )

    mock_get_telegram_user_by_wallet_id.return_value = None
    if user_telegram_id:
        tg_user = TelegramUser(
            telegram_id=user_telegram_id,
            wallet_id=wallet_id,
        )
        mock_get_telegram_user_by_wallet_id.return_value = tg_user

    data = {"telegram_id": telegram_id, "wallet_id": wallet_id}

    response = client.post(
        url="/api/subscribe-to-notification",
        json=data,
    )

    assert response.status_code == expected_status_code
    if expected_response:
        assert response.json() == expected_response


@pytest.mark.asyncio
@patch("sentry_sdk.capture_message")
@patch("sentry_sdk.set_user")
@patch("sentry_sdk.set_context")
@pytest.mark.parametrize(
    "report_data, expected_status, expected_response",
    [
        (
            {
                "wallet_id": "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2",
                "telegram_id": "456",
                "bug_description": "Test bug description",
            },
            200,
            {"message": "Bug report submitted successfully"},
        ),
        (
            {"wallet_id": "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2", "bug_description": "Test without telegram"},
            200,
            {"message": "Bug report submitted successfully"},
        ),
    ],
)
async def test_save_bug_report_success(
    mock_set_context,
    mock_set_user,
    mock_capture_message,
    client,
    report_data,
    expected_status,
    expected_response,
):
    """Test successful bug report submission"""
    response = client.post("/api/save-bug-report", json=report_data)

    assert response.status_code == expected_status
    assert response.json() == expected_response
    mock_set_user.assert_called_once()
    mock_set_context.assert_called_once()
    mock_capture_message.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "report_data, expected_status, error_message",
    [
        (
            {"wallet_id": "12345678901234567890123456789012345678901234567890123456", "bug_description": "Test"},
            422,
            "String should match pattern '^G[A-Za-z0-9]{55}$'",
        ),
        (
            {"wallet_id": "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2", "telegram_id": "abc", "bug_description": "Test"},
            422,
            "String should match pattern '^\\d+$'",
        ),
        (
            {"wallet_id": "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2", "bug_description": ""},
            422,
            "String should have at least 1 character",
        ),
        (
            {"telegram_id": "456", "bug_description": "Missing wallet"},
            422,
            "Field required",
        ),
        (
            {"wallet_id": "GA7QYNF7SOWQ3GLR2ZGMH2Z5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2X2H5Y2", "telegram_id": "456"},
            422,
            "Field required",
        ),
        (
            {},
            422,
            "Field required",
        ),
    ],
)
async def test_save_bug_report_validation(
    client, report_data, expected_status, error_message
):
    """Test bug report validation failures"""
    response = client.post("/api/save-bug-report", json=report_data)

    assert response.status_code == expected_status
    assert response.json()["detail"][0]["msg"] == error_message