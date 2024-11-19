import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any
from datetime import datetime
from web_app.api.main import app
from web_app.db.crud import PositionDBConnector
from web_app.contract_tools.mixins.deposit import DepositMixin
from web_app.contract_tools.mixins.dashboard import DashboardMixin

client = TestClient(app)
position_db = PositionDBConnector()


class PositionCreationTest:
    """
    Integration test for creating and managing positions.

    Steps:
    1. Fetch transaction data using `DepositMixin.get_transaction_data`.
    2. Create a position using `PositionDBConnector`.
    3. Verify the created position's attributes.
    4. Fetch current token prices using `DashboardMixin`.
    5. Update position status and validate changes.
    """

    mock_user_1: Dict[str, Any] = {
        "wallet_id": "0x011F0c180b9EbB2B3F9601c41d65AcA110E48aec0292c778f41Ae286C78Cc374",
        "token_symbol": "STRK",
        "amount": "2",
        "multiplier": 1,
        "borrowing_token": "STRK",
    }

    mock_user_2: Dict[str, Any] = {
        "wallet_id": "id",
        "token_symbol": "ETH",
        "amount": "5",
        "multiplier": 1,
        "borrowing_token": "STRK",
    }

    mock_user_3: Dict[str, Any] = {
        "wallet_id": "id",
        "token_symbol": "USDC",
        "amount": "1",
        "multiplier": 1,
        "borrowing_token": "ETH",
    }

    @pytest.mark.parametrize("mock_user", [(mock_user_1), (mock_user_2), (mock_user_3)])
    def test_create_position(self, mock_user: Dict[str, Any]) -> None:
        """
        Args:
            mock_user (Dict[str, Any]): position data.

        Returns:
            None
        """
        # Extract position data
        wallet_id = mock_user["wallet_id"]
        token_symbol = mock_user["token_symbol"]
        amount = mock_user["amount"]
        multiplier = mock_user["multiplier"]
        borrowing_token = mock_user["borrowing_token"]

        position_db.create_user(wallet_id)

        transaction_data = DepositMixin.get_transaction_data(
            deposit_token=token_symbol,
            amount=amount,
            multiplier=multiplier,
            wallet_id=wallet_id,
            borrowing_token=borrowing_token,
        )
        assert "caller" in transaction_data, "Transaction data missing 'caller'"
        assert transaction_data["caller"] == wallet_id, "Mismatch in 'caller'"
        assert (
            "pool_price" in transaction_data
        ), "'pool_price' missing in transaction data"
        assert "pool_key" in transaction_data, "'pool_key' missing in transaction data"
        assert (
            "deposit_data" in transaction_data
        ), "'deposit_data' missing in transaction data"

        position = position_db.create_position(
            wallet_id=wallet_id,
            token_symbol=token_symbol,
            amount=amount,
            multiplier=multiplier,
        )
        assert (
            position.status == "pending"
        ), "Position status should be 'pending' upon creation"

        current_prices = DashboardMixin.get_current_prices()
        assert (
            position.token_symbol in current_prices
        ), "Token price missing in current prices"
        position.start_price = current_prices[position.token_symbol]
        position.created_at = datetime.utcnow()

        print(
            f"Position {position.id} created successfully with status '{position.status}'."
        )

        # Open position
        position_db.open_position(position.id, current_prices)
        assert (
            position.status == "opened"
        ), "Position status should be 'opened' upon creation"
        print(f"Position {position.id} successfully opened.")

        position_db.delete_position(position)
