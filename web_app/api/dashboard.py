"""
This module handles dashboard-related API endpoints.
"""

import collections

from fastapi import APIRouter
from web_app.api.serializers.dashboard import DashboardResponse
from web_app.contract_tools.mixins import DashboardMixin, HealthRatioMixin
from web_app.db.crud import PositionDBConnector

router = APIRouter()
position_db_connector = PositionDBConnector()


@router.get(
    "/api/dashboard",
    tags=["Dashboard Operations"],
    summary="Get user dashboard data",
    response_model=DashboardResponse,
    response_description="Returns user's balances, multipliers, start dates, and ZkLend positions.",
)
async def get_dashboard(wallet_id: str) -> DashboardResponse:
    """
    This endpoint fetches the user's dashboard data,
    including balances, multipliers, start dates, and ZkLend position.

    ### Parameters:
    - **wallet_id**: User's wallet ID

    ### Returns:
    A dictionary containing the user's dashboard data:
    - **balances**: Wallet balances for the user.
    - **multipliers**: Multipliers applied to each asset (e.g., ETH).
    - **start_dates**: Start dates for each asset's position.
    - **zklend_position**: Details of the ZkLend positions.
    """
    contract_address = position_db_connector.get_contract_address_by_wallet_id(
        wallet_id
    )
    opened_positions = position_db_connector.get_positions_by_wallet_id(wallet_id)

    # At the moment, we only support one position per wallet
    first_opened_position = (
        opened_positions[0]
        if opened_positions
        else collections.defaultdict(lambda: None)
    )
    # Fetch zkLend position for the wallet ID
    health_ratio = await HealthRatioMixin.get_health_ratio(
        contract_address
    )

    # Fetch balances (assuming you have a method for this)
    wallet_balances = await DashboardMixin.get_wallet_balances(wallet_id)
    current_sum = await DashboardMixin.get_current_position_sum(first_opened_position)
    start_sum = await DashboardMixin.get_start_position_sum(
        first_opened_position["start_price"],
        first_opened_position["amount"],
    )
    return DashboardResponse(
        balances=wallet_balances,
        health_ratio=health_ratio,
        multipliers={"ETH": first_opened_position["multiplier"]},
        start_dates={"ETH": first_opened_position["created_at"]},
        current_sum=current_sum,
        start_sum=start_sum,
    )
