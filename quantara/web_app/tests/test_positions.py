"""
test_positions.py
This module contains unit tests for the positions functionality within the web_app.
It verifies the creation, retrieval, updating, and deletion of positions, ensuring
that all edge cases and error scenarios are appropriately handled.


"""

import json
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import AsyncClient

from web_app.api.main import app
from web_app.api.position import position_db_connector
from web_app.api.wallet_auth import verify_wallet_signature
from web_app.db.models import Position, TransactionStatus, User
from web_app.tests.conftest import dict_to_object


def _unauthorized_auth() -> str:
    """Simulate verify_wallet_signature rejecting a missing/invalid signature."""
    raise HTTPException(status_code=401, detail="Invalid or expired nonce")


def _owner_mocks(position_id: uuid.UUID, owner_user_id: uuid.UUID):
    """Build a position/user pair whose ids satisfy require_position_owner."""
    position = Mock(spec=Position)
    position.id = position_id
    position.user_id = owner_user_id
    user = Mock(spec=User)
    user.id = owner_user_id
    return position, user


@pytest.mark.anyio
async def test_close_position_success(client: TestClient) -> None:
    """Closing an owned position returns its new status and records the tx."""
    position_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    position, user = _owner_mocks(position_id, owner_id)

    with (
        patch.object(
            position_db_connector, "get_position_by_id", return_value=position
        ),
        patch.object(position_db_connector, "get_user_by_wallet_id", return_value=user),
        patch.object(
            position_db_connector, "close_position", return_value="closed"
        ) as mock_close,
        patch.object(
            position_db_connector, "save_transaction", return_value=None
        ) as mock_save,
    ):
        response = client.post(
            f"/api/close-position/{position_id}",
            json={"transaction_hash": "0xabc123"},
        )

    assert response.status_code == 200
    assert response.json() == "closed"
    mock_close.assert_called_once_with(position_id)
    mock_save.assert_called_once_with(
        position_id=position_id, status="closed", transaction_hash="0xabc123"
    )


@pytest.mark.anyio
async def test_close_position_rejects_unauthenticated(client: TestClient) -> None:
    """An unauthenticated request to close-position is rejected with 401."""
    app.dependency_overrides[verify_wallet_signature] = _unauthorized_auth
    try:
        response = client.post(
            f"/api/close-position/{uuid.uuid4()}",
            json={"transaction_hash": "0xabc123"},
        )
    finally:
        app.dependency_overrides[verify_wallet_signature] = lambda: "test_wallet"
    assert response.status_code == 401


@pytest.mark.anyio
async def test_close_position_rejects_wrong_owner(client: TestClient) -> None:
    """A wallet that does not own the position is rejected with 403."""
    position_id = uuid.uuid4()
    position, _ = _owner_mocks(position_id, uuid.uuid4())
    other_user = Mock(spec=User)
    other_user.id = uuid.uuid4()

    with (
        patch.object(
            position_db_connector, "get_position_by_id", return_value=position
        ),
        patch.object(
            position_db_connector, "get_user_by_wallet_id", return_value=other_user
        ),
    ):
        response = client.post(
            f"/api/close-position/{position_id}",
            json={"transaction_hash": "0xabc123"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "not_position_owner"


@pytest.mark.anyio
async def test_open_position_success(client: TestClient) -> None:
    """Opening an owned position queues a PositionOpened outbox event."""
    position_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    position, user = _owner_mocks(position_id, owner_id)
    saved_events = []

    def _write(obj):
        saved_events.append(obj)
        return obj

    with (
        patch.object(
            position_db_connector, "get_position_by_id", return_value=position
        ),
        patch.object(position_db_connector, "get_user_by_wallet_id", return_value=user),
        patch.object(position_db_connector, "write_to_db", side_effect=_write),
    ):
        response = client.post(
            f"/api/open-position/{position_id}",
            json={"transaction_hash": "0xabc123"},
        )

    assert response.status_code == 200
    assert response.json() == "pending"
    assert len(saved_events) == 1
    assert saved_events[0].event_type == "PositionOpened"
    payload = json.loads(saved_events[0].payload)
    assert payload["position_id"] == str(position_id)
    assert payload["transaction_hash"] == "0xabc123"


@pytest.mark.anyio
async def test_open_position_rejects_unauthenticated(client: TestClient) -> None:
    """An unauthenticated request to open-position is rejected with 401."""
    app.dependency_overrides[verify_wallet_signature] = _unauthorized_auth
    try:
        response = client.post(
            f"/api/open-position/{uuid.uuid4()}",
            json={"transaction_hash": "0xabc123"},
        )
    finally:
        app.dependency_overrides[verify_wallet_signature] = lambda: "test_wallet"
    assert response.status_code == 401


@pytest.mark.anyio
async def test_open_position_rejects_wrong_owner(client: TestClient) -> None:
    """A wallet that does not own the position cannot queue its opening."""
    position_id = uuid.uuid4()
    position, _ = _owner_mocks(position_id, uuid.uuid4())
    other_user = Mock(spec=User)
    other_user.id = uuid.uuid4()

    with (
        patch.object(
            position_db_connector, "get_position_by_id", return_value=position
        ),
        patch.object(
            position_db_connector, "get_user_by_wallet_id", return_value=other_user
        ),
    ):
        response = client.post(
            f"/api/open-position/{position_id}",
            json={"transaction_hash": "0xabc123"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "not_position_owner"


@pytest.mark.anyio
async def test_get_repay_data_success(client: TestClient) -> None:
    """Repay data is returned only for the authenticated wallet."""
    position_id = uuid.uuid4()
    mock_repay_data = {
        "supply_token": "mock_supply_token",
        "debt_token": "mock_debt_token",
        "borrow_portion_percent": 1,
    }

    with (
        patch.object(
            position_db_connector,
            "get_repay_data",
            return_value=("34702534789504389704385", position_id, "ETH"),
        ),
        patch(
            "web_app.contract_tools.mixins.position.PositionMixin.is_opened_position",
            return_value=True,
        ),
        patch(
            "web_app.contract_tools.mixins.deposit.DepositMixin.get_repay_data",
            return_value=mock_repay_data,
        ),
    ):
        response = client.post("/api/get-repay-data")

    assert response.status_code == 200
    assert response.json() == {
        **mock_repay_data,
        "contract_address": "34702534789504389704385",
        "position_id": str(position_id),
    }


@pytest.mark.anyio
async def test_get_repay_data_rejects_unauthenticated(client: TestClient) -> None:
    """Repay data cannot be fetched without a valid wallet signature."""
    app.dependency_overrides[verify_wallet_signature] = _unauthorized_auth
    try:
        response = client.post("/api/get-repay-data")
    finally:
        app.dependency_overrides[verify_wallet_signature] = lambda: "test_wallet"
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_withdraw_data_success(client: TestClient) -> None:
    """Withdraw-all data is returned only for the authenticated wallet."""
    position_id = uuid.uuid4()
    mock_repay_data = {
        "supply_token": "mock_supply_token",
        "debt_token": "mock_debt_token",
        "borrow_portion_percent": 1,
    }

    with (
        patch.object(
            position_db_connector,
            "get_repay_data",
            return_value=("34702534789504389704385", position_id, "USDC"),
        ),
        patch(
            "web_app.contract_tools.mixins.position.PositionMixin.is_opened_position",
            return_value=True,
        ),
        patch(
            "web_app.contract_tools.mixins.deposit.DepositMixin.get_repay_data",
            return_value=mock_repay_data,
        ),
        patch.object(
            position_db_connector,
            "get_extra_deposits_data",
            return_value={"ETH": "100"},
        ),
        patch(
            "web_app.contract_tools.constants.TokenParams.get_token_address",
            return_value="0xETH_TOKEN",
        ),
    ):
        response = client.post("/api/get-withdraw-all-data")

    assert response.status_code == 200
    body = response.json()
    assert body["repay_data"]["position_id"] == str(position_id)
    assert body["repay_data"]["contract_address"] == "34702534789504389704385"
    assert body["tokens"] == ["0xETH_TOKEN"]


@pytest.mark.anyio
async def test_get_withdraw_data_rejects_unauthenticated(client: TestClient) -> None:
    """Withdraw-all data cannot be fetched without a valid wallet signature."""
    app.dependency_overrides[verify_wallet_signature] = _unauthorized_auth
    try:
        response = client.post("/api/get-withdraw-all-data")
    finally:
        app.dependency_overrides[verify_wallet_signature] = lambda: "test_wallet"
    assert response.status_code == 401


@pytest.mark.parametrize(
    "wallet_id, token_symbol, amount, multiplier, expected_response",
    [
        (
            "valid_wallet_id",
            "ETH",
            "1000",
            2,
            {
                "contract_address": "mock_contract_address",
                "position_id": "123",
                "caller": "valid_wallet_id",
                "deposit_data": {
                    "token": "mock_token",
                    "amount": "mock_amount",
                    "multiplier": "1",
                    "borrow_portion_percent": 0,
                },
            },
        ),
        (
            "valid_wallet_id_2",
            "ETH",
            "500",
            1,
            {
                "contract_address": "mock_contract_address",
                "position_id": "123",
                "caller": "valid_wallet_id_2",
                "deposit_data": {
                    "token": "mock_token",
                    "amount": "mock_amount",
                    "multiplier": "1",
                    "borrow_portion_percent": 0,
                },
            },
        ),
        (
            "valid_wallet_id_3",
            "ETH",
            "1500",
            3,
            {
                "contract_address": "mock_contract_address",
                "position_id": "123",
                "caller": "valid_wallet_id_3",
                "deposit_data": {
                    "token": "mock_token",
                    "amount": "mock_amount",
                    "multiplier": "1",
                    "borrow_portion_percent": 0,
                },
            },
        ),
        (
            "valid_wallet_id_4",
            "kSTRK",
            "800",
            4,
            {
                "contract_address": "mock_contract_address",
                "position_id": "123",
                "caller": "valid_wallet_id_4",
                "deposit_data": {
                    "token": "mock_token",
                    "amount": "mock_amount",
                    "multiplier": "1",
                    "borrow_portion_percent": 0,
                },
            },
        ),
    ],
)
@pytest.mark.anyio
async def test_create_position_success(
    client: TestClient, wallet_id, token_symbol, amount, multiplier, expected_response
) -> None:
    """
    Test for successfully creating a position with valid form data.
    """
    mock_position = Mock()
    mock_position.id = 123
    mock_deposit_data = {
        "deposit_data": {
            "token": "mock_token",
            "amount": "mock_amount",
            "multiplier": "1",
            "borrow_portion_percent": 0,
        },
        "contract_address": "mock_contract_address",
        "position_id": "123",
        "caller": wallet_id,
    }

    with (
        patch(
            "web_app.db.crud.PositionDBConnector.create_position"
        ) as mock_create_position,
        patch(
            "web_app.contract_tools.mixins.deposit.DepositMixin.get_transaction_data"
        ) as mock_get_transaction_data,
        patch(
            "web_app.db.crud.PositionDBConnector.get_contract_address_by_wallet_id"
        ) as mock_get_contract_address,
    ):

        mock_create_position.return_value = mock_position
        mock_get_transaction_data.return_value = mock_deposit_data
        mock_get_contract_address.return_value = "mock_contract_address"

        response = client.post(
            "/api/create-position",
            json={
                "wallet_id": wallet_id,
                "token_symbol": token_symbol,
                "amount": amount,
                "multiplier": multiplier,
            },
        )
        assert (
            response.is_success
        ), f"Expected status code 200 but got {response.status_code}"
        assert (
            response.json() == expected_response
        ), "Response JSON does not match expected response"


@pytest.mark.parametrize(
    "wallet_id, token_symbol, amount, multiplier, expected_status",
    [
        (None, "ETH", 100, 2, 422),
        (12345, "", 100, 2, 422),
        (12345, None, 100, 2, 422),
        (12345, "ETH", -50, 2, 422),
        (12345, "ETH", None, 2, 422),
        (12345, "ETH", "50", 2, 422),
        (12345, "ETH", 100, "0.01", 422),
        (12345, "ETH", 100, "1.5", 422),
    ],
)
def test_create_position_invalid(
    client: TestClient, wallet_id, token_symbol, amount, multiplier, expected_status
):
    """
    Test for attempting to create a position with various valid and invalid input data.
    Should return 422 for invalid data and 200 for valid data.
    """
    response = client.post(
        "/api/create-position",
        json={
            "wallet_id": wallet_id,
            "token_symbol": token_symbol,
            "amount": amount,
            "multiplier": multiplier,
        },
    )
    assert response.status_code == expected_status
    if expected_status == 422:
        assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_user_positions_success(client: TestClient) -> None:
    """
    Test successfully retrieving user positions.
    """
    wallet_id = "test_wallet_id"
    mock_positions = [
        {
            "id": str(uuid.uuid4()),
            "token_symbol": "ETH",
            "amount": "100",
            "multiplier": 2.0,
            "status": "opened",
            "created_at": datetime.now(),
            "start_price": 1800.0,
            "is_liquidated": False,
        }
    ]
    mock_total_count = len(mock_positions)

    with patch(
        "web_app.db.crud.PositionDBConnector.get_all_positions_by_wallet_id"
    ) as mock_get_positions, patch(
            "web_app.db.crud.PositionDBConnector.get_count_positions_by_wallet_id"
    ) as mock_get_count_positions:
        mock_get_positions.return_value = mock_positions
        mock_get_count_positions.return_value = mock_total_count

        response = client.get(f"/api/user-positions/{wallet_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["positions"]) == len(mock_positions)
        assert data["total_count"] == mock_total_count
        assert data["positions"][0]["token_symbol"] == mock_positions[0]["token_symbol"]
        assert data["positions"][0]["amount"] == mock_positions[0]["amount"]


@pytest.mark.asyncio
async def test_get_user_positions_empty_wallet_id(client: AsyncClient) -> None:
    """
    Test retrieving positions with empty wallet ID.
    """
    response = client.get("/api/user-positions/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_positions_no_positions(client: AsyncClient) -> None:
    """
    Test retrieving positions for wallet with no positions.
    """
    wallet_id = "wallet_with_no_positions"
    with patch(
        "web_app.db.crud.PositionDBConnector.get_positions_by_wallet_id"
    ) as mock_get_positions:
        mock_get_positions.return_value = []
        response = client.get(f"/api/user-positions/{wallet_id}")

        assert response.status_code == 200
        data = response.json()
        assert data == {"positions": [], "total_count": 0}


@pytest.mark.parametrize(
    "position_id, amount, token_symbol, mock_position, expected_response",
    [
        (
            "520e8441-de08-463b-864a-deccf517f0ce",
            "3.1",
            "ETH",
            {
                "id": "520e8441-de08-463b-864a-deccf517f0ce",
                "token_symbol": "ETH",
                "amount": "4",
                "status": "opened",
            },
            {
                "deposit_data": {
                    "token_address": "0x049d36570d4e46f48",
                    "token_amount": 3.1 * 10**18,
                }
            },
        ),
        (
            "0ae52807-6a32-4a68-b9b5-7d3b002b7189",
            "50.5",
            "USDC",
            {
                "id": "0ae52807-6a32-4a68-b9b5-7d3b002b7189",
                "token_symbol": "USDC",
                "amount": "500",
                "status": "opened",
            },
            {
                "deposit_data": {
                    "token_address": "0x053c91253bc9682c0492",
                    "token_amount": 50.5 * 10**6,
                }
            },
        ),
        (
            "579af7e9-6759-4285-b346-f3461dc42b1d",
            "75.25",
            "STRK",
            {
                "id": "579af7e9-6759-4285-b346-f3461dc42b1d",
                "token_symbol": "STRK",
                "amount": "750",
                "status": "opened",
            },
            {
                "deposit_data": {
                    "token_address": "0x04718f5a0fc34cc1af1",
                    "token_amount": 75.25 * 10**18,
                }
            },
        ),
    ],
)
@pytest.mark.anyio
async def test_add_extra_deposit_success(
    client: TestClient,
    position_id: str,
    amount: str,
    token_symbol: str,
    mock_position: dict,
    expected_response: dict,
) -> None:
    """
    Test successful extra deposit for various scenarios.
    """
    with (
        patch(
            "web_app.db.crud.PositionDBConnector.get_position_by_id"
        ) as mock_get_position,
        patch(
            "web_app.contract_tools.constants.TokenParams.get_token_address"
        ) as mock_get_token_address,
        patch(
            "web_app.contract_tools.constants.TokenParams.get_token_decimals"
        ) as mock_get_token_decimals,
    ):
        mock_get_position.return_value = dict_to_object(mock_position)
        mock_get_token_address.return_value = expected_response["deposit_data"][
            "token_address"
        ]
        if token_symbol == "ETH" or token_symbol == "STRK":
            mock_get_token_decimals.return_value = 18
        else:
            mock_get_token_decimals.return_value = 6

        response = client.get(
            f"/api/get-add-deposit-data/{position_id}",
            params={"amount": amount, "token_symbol": token_symbol},
        )

        assert response.status_code == 200
        assert response.json() == expected_response


@pytest.mark.parametrize(
    "position_id, amount, token_symbol, error_status, error_detail",
    [
        (None, "100.0", "ETH", 404, "Position not found"),
        ("579af7e9-6759-4285-b346-f3461dc42b1d", "", "ETH", 400, "Amount is required"),
        (
            "0ae52807-6a32-4a68-b9b5-7d3b002b7189",
            "invalid",
            "ETH",
            400,
            "Amount is not a number",
        ),
        (
            "520e8441-de08-463b-864a-deccf517f0ce",
            "100.0",
            "",
            400,
            "Token symbol is required",
        ),
    ],
)
@pytest.mark.anyio
async def test_add_extra_deposit_failure(
    client: TestClient,
    position_id: str,
    amount: str,
    token_symbol: str,
    error_status: int,
    error_detail: str,
) -> None:
    """
    Test failure scenarios for extra deposit.
    """
    with patch(
        "web_app.db.crud.PositionDBConnector.get_position_by_id"
    ) as mock_get_position:
        if position_id is not None:
            mock_get_position.return_value = dict_to_object(
                {"id": position_id, "token_symbol": token_symbol}
            )
        else:
            position_id = str(uuid.uuid4())
            mock_get_position.return_value = None

        response = client.get(
            f"/api/get-add-deposit-data/{position_id}",
            params={"amount": amount, "token_symbol": token_symbol},
        )

        assert response.status_code == error_status
        assert error_detail in response.json()["detail"]


@pytest.mark.parametrize(
    "position_id, data, mock_position, expected_response",
    [
        (
            "520e8441-de08-463b-864a-deccf517f0ce",
            {
                "amount": "100.0",
                "token_symbol": "ETH",
                "transaction_hash": "0x123456789abcdef",
            },
            {
                "id": "520e8441-de08-463b-864a-deccf517f0ce",
                "token_symbol": "ETH",
                "amount": "1000",
                "status": "opened",
            },
            {"detail": "Successfully added extra deposit"},
        ),
        (
            "0ae52807-6a32-4a68-b9b5-7d3b002b7189",
            {
                "amount": "50.5",
                "token_symbol": "USDC",
                "transaction_hash": "0xabcdef123456789",
            },
            {
                "id": "0ae52807-6a32-4a68-b9b5-7d3b002b7189",
                "token_symbol": "USDC",
                "amount": "500",
                "status": "opened",
            },
            {"detail": "Successfully added extra deposit"},
        ),
        (
            "579af7e9-6759-4285-b346-f3461dc42b1d",
            {
                "amount": "75.25",
                "token_symbol": "STRK",
                "transaction_hash": "0xdef123456789abc",
            },
            {
                "id": "579af7e9-6759-4285-b346-f3461dc42b1d",
                "token_symbol": "STRK",
                "amount": "750",
                "status": "opened",
            },
            {"detail": "Successfully added extra deposit"},
        ),
    ],
)
@pytest.mark.anyio
async def test_add_extra_deposit_transaction_success(
    client: TestClient,
    position_id: str,
    data: dict,
    mock_position: dict,
    expected_response: dict,
) -> None:
    """
    Test successful extra deposit transaction for various scenarios.
    """
    with (
        patch(
            "web_app.db.crud.PositionDBConnector.get_position_by_id"
        ) as mock_get_position,
        patch(
            "web_app.db.crud.PositionDBConnector.add_extra_deposit_to_position"
        ) as mock_add_extra_deposit,
        patch(
            "web_app.db.crud.TransactionDBConnector.create_transaction"
        ) as mock_create_transaction,
    ):
        mock_position_obj = dict_to_object(mock_position)
        mock_get_position.return_value = mock_position_obj
        mock_add_extra_deposit.return_value = None
        mock_create_transaction.return_value = None

        response = client.post(f"/api/add-extra-deposit/{position_id}", json=data)

        assert response.status_code == 200
        assert response.json() == expected_response

        mock_add_extra_deposit.assert_called_once_with(
            mock_position_obj, data["token_symbol"], data["amount"]
        )
        mock_create_transaction.assert_called_once_with(
            uuid.UUID(mock_position["id"]),
            data["transaction_hash"],
            status=TransactionStatus.EXTRA_DEPOSIT.value,
        )


@pytest.mark.parametrize(
    "position_id, data, error_status, error_detail",
    [
        (
            None,
            {
                "amount": "100.0",
                "token_symbol": "ETH",
                "transaction_hash": "0x123456789abcdef",
            },
            404,
            "Position not found",
        ),
        (
            "579af7e9-6759-4285-b346-f3461dc42b1d",
            {
                "amount": "",
                "token_symbol": "ETH",
                "transaction_hash": "0x123456789abcdef",
            },
            400,
            "Amount is required",
        ),
        (
            "0ae52807-6a32-4a68-b9b5-7d3b002b7189",
            {"amount": "100.0", "token_symbol": "ETH", "transaction_hash": ""},
            400,
            "Transaction hash is required",
        ),
    ],
)
@pytest.mark.anyio
async def test_add_extra_deposit_transaction_failure(
    client: TestClient,
    position_id: str,
    data: dict,
    error_status: int,
    error_detail: str,
) -> None:
    """
    Test failure scenarios for extra deposit transaction.
    """
    with patch(
        "web_app.db.crud.PositionDBConnector.get_position_by_id"
    ) as mock_get_position:
        if position_id is not None:
            mock_get_position.return_value = dict_to_object(
                {"id": position_id, "token_symbol": "ETH"}
            )
        else:
            position_id = str(uuid.uuid4())
            mock_get_position.return_value = None

        response = client.post(f"/api/add-extra-deposit/{position_id}", json=data)

        assert response.status_code == error_status
        assert error_detail in response.json()["detail"]
