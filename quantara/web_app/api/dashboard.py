"""
This module handles dashboard-related API endpoints
for the Stellar-based Quantara protocol.
"""

import collections
from decimal import Decimal, DivisionByZero

from fastapi import APIRouter, Depends, Request

from web_app.api.serializers.dashboard import DashboardResponse
from web_app.contract_tools.mixins import DashboardMixin, HealthRatioMixin
from web_app.api.dependencies import get_stellar_client
from web_app.contract_tools.blockchain_call import StellarClient
from web_app.db.crud import PositionDBConnector
from web_app.api.rate_limiter import limiter, USER_DATA_LIMIT

router = APIRouter()
position_db_connector = PositionDBConnector()


@router.get(
    "/api/dashboard",
    tags=["Dashboard Operations"],
    summary="Get user dashboard data",
    response_model=DashboardResponse,
    response_description="Returns user's balances, multipliers, start dates, and position data.",
)
@limiter.limit(USER_DATA_LIMIT, key_func=lambda request: f"wallet:{request.query_params.get('wallet_id', request.client.host)}")
async def get_dashboard(
    request: Request,
    wallet_id: str,
    client: StellarClient = Depends(get_stellar_client)
) -> DashboardResponse:
    """
    Fetch the user's dashboard data, including balances, multipliers,
    start dates, deposit_data, and health ratio.

    Parameters:
    - **wallet_id**: User's wallet ID (Stellar public key G…)

    Returns:
    - **balances**: Wallet balances for the user.
    - **multipliers**: Multipliers applied to each asset.
    - **start_dates**: Start dates for each asset's position.
    - **health_ratio**: Current health ratio of the position.
    - **deposit_data**: Deposit data including token and amount.
    """
    contract_address = position_db_connector.get_contract_address_by_wallet_id(
        wallet_id
    )
    default_dashboard_response = DashboardResponse(
        health_ratio="0",
        multipliers={},
        start_dates={},
        current_sum=0,
        start_sum=0,
        borrowed="0",
        balance="0",
        position_id="0",
        deposit_data=[],
    )
    if not contract_address:
        return default_dashboard_response

    opened_positions = position_db_connector.get_positions_by_wallet_id(wallet_id)

    first_opened_position = (
        opened_positions[0]
        if opened_positions
        else collections.defaultdict(lambda: None)
    )
    if not first_opened_position:
        return default_dashboard_response

    try:
        health_ratio, tvl = await HealthRatioMixin.get_health_ratio_and_tvl(
            contract_address, client
        )
    except (IndexError, DivisionByZero, ZeroDivisionError):
        return default_dashboard_response

    position_multiplier = first_opened_position["multiplier"]
    position_amount = first_opened_position["amount"]

    current_sum = await DashboardMixin.get_current_position_sum(first_opened_position)
    start_sum = await DashboardMixin.get_start_position_sum(
        first_opened_position["start_price"],
        position_amount,
        position_multiplier,
    )
    position_balance = await DashboardMixin.get_position_balance(
        first_opened_position["id"]
    )
    total_position_balance = await DashboardMixin.calculate_position_balance(
        position_balance, position_multiplier
    )
    token_symbol = first_opened_position["token_symbol"]
    extra_deposits = position_db_connector.get_extra_deposits_by_position_id(
        first_opened_position["id"]
    )
    deposit_data = [
        {"token": deposit.token_symbol, "amount": deposit.amount}
        for deposit in extra_deposits
    ]

    return DashboardResponse(
        health_ratio=health_ratio,
        multipliers={token_symbol: str(position_multiplier)},
        start_dates={token_symbol: first_opened_position["created_at"]},
        current_sum=current_sum,
        start_sum=start_sum,
        borrowed=str(start_sum * Decimal(tvl)) if tvl and Decimal(tvl) > 0 else "0",
        balance=str(total_position_balance),
        position_id=first_opened_position["id"],
        deposit_data=deposit_data,
    )
