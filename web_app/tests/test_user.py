import pytest
from unittest.mock import MagicMock

from web_app.tests.conftest import client, mock_user_db_connector
from web_app.api.serializers.transaction import UpdateUserContractRequest


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

    is_contract_deployed = response_json.get("is_contract_deployed")
    assert is_contract_deployed or not is_contract_deployed


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
