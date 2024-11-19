"""
Module: Position Creation Tests

This module contains integratin tests for the creation and management
of user positions within the webapp

Key Components:
- **TestClient**: Simulates API requests.
- **PositionDBConnector**: Manages database operations for positions.
- **DepositMixin**: Processes transaction data.
- **DashboardMixin**: Retrieves current token prices.

Test Class:
- **PositionCreationTest**: Validates position workflows:
  1. Fetching transaction data.
  2. Creating and verifying positions.
  3. Updating position statuses.
"""

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

    form_data_1: Dict[str, Any] = {
        "wallet_id": "0x011F0c180b9EbB2B3F9601c41d65AcA110E48aec0292c778f41Ae286C78Cc374",
        "token_symbol": "STRK",
        "amount": "2",
        "multiplier": 1,
        "borrowing_token": "STRK",
    }

    form_data_2: Dict[str, Any] = {
        "wallet_id": "id",
        "token_symbol": "ETH",
        "amount": "5",
        "multiplier": 1,
        "borrowing_token": "STRK",
    }

    form_data_3: Dict[str, Any] = {
        "wallet_id": "id",
        "token_symbol": "USDC",
        "amount": "1",
        "multiplier": 1,
        "borrowing_token": "ETH",
    }

    @pytest.mark.parametrize("form_data", [form_data_1, form_data_2, form_data_3])
    def test_create_position(self, form_data: Dict[str, Any]) -> None:
        """
        Args:
        form_data (Dict[str, Any]): Position data.

        Returns:
            None
        """
        wallet_id = form_data["wallet_id"]
        token_symbol = form_data["token_symbol"]
        amount = form_data["amount"]
        multiplier = form_data["multiplier"]
        borrowing_token = form_data["borrowing_token"]

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

        position_db.open_position(position.id, current_prices)
        assert (
            position.status == "opened"
        ), "Position status should be 'opened' after updating"
        print(f"Position {position.id} successfully opened.")

        position_db.delete_position(position.id)
        position_db.delete_user_by_wallet_id(wallet_id)
