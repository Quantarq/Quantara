"""
This module handles position-related API endpoints for the Stellar-based Quantara protocol.
"""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends, Request

from web_app.api.serializers.position import (
    AddPositionDepositData,
    PositionFormData,
    TokenMultiplierResponse,
    UserPositionExtraDepositsResponse,
    UserPositionHistoryResponse,
)
from web_app.api.serializers.transaction import (
    LoopLiquidityData,
    RepayTransactionDataResponse,
    WithdrawAllData,
)
from web_app.contract_tools.constants import TokenMultipliers, TokenParams
from web_app.contract_tools.mixins import DashboardMixin, DepositMixin, PositionMixin
from web_app.db.crud import PositionDBConnector, TransactionDBConnector
from web_app.api.dependencies import get_stellar_client
from web_app.contract_tools.blockchain_call import StellarClient
from web_app.db.models import Status, TransactionStatus
from web_app.api.rate_limiter import limiter, WRITE_LIMIT, USER_DATA_LIMIT, READ_LIMIT

router = APIRouter()
position_db_connector = PositionDBConnector()
transaction_db_connector = TransactionDBConnector()

PAGINATION_STEP = 10


@router.get(
    "/api/get-multipliers",
    tags=["Position Operations"],
    response_model=TokenMultiplierResponse,
    summary="Get token multipliers",
    response_description="Returns token multipliers for Stellar assets.",
)
@limiter.limit(READ_LIMIT)
async def get_multipliers(request: Request) -> TokenMultiplierResponse:
    """
    Retrieve the multipliers for tokens like XLM, USDC, and ETH.
    """
    multipliers = {
        "XLM": TokenMultipliers.XLM,
        "USDC": TokenMultipliers.USDC,
        "ETH": TokenMultipliers.ETH,
    }
    return TokenMultiplierResponse(multipliers=multipliers)


@router.post(
    "/api/create-position",
    tags=["Position Operations"],
    response_model=LoopLiquidityData,
    summary="Create a new position",
    response_description="Returns the new position and transaction data.",
)
@limiter.limit(WRITE_LIMIT)
async def create_position_with_transaction_data(
    request: Request,
    form_data: PositionFormData,
    client: StellarClient = Depends(get_stellar_client),
) -> LoopLiquidityData:
    """
    Create a new user position and return the data needed by the frontend
    to call the Soroban loop_liquidity contract.

    Parameters:
    - **wallet_id**: The wallet ID of the user (Stellar public key G…).
    - **token_symbol**: The symbol of the token used for the position.
    - **amount**: The amount of the token being deposited.
    - **multiplier**: The multiplier applied to the user's position.
    - **borrowing_token**: The symbol of the borrowing token.

    Returns:
    The created position's details and loop liquidity data.
    """
    position = position_db_connector.create_position(
        form_data.wallet_id,
        form_data.token_symbol,
        form_data.amount,
        form_data.multiplier,
    )
    borrowing_token = "USDC"
    if form_data.token_symbol == "USDC":
        borrowing_token = "XLM"

    deposit_data = await DepositMixin.get_transaction_data(
        form_data.token_symbol,
        form_data.amount,
        form_data.multiplier,
        form_data.wallet_id,
        borrowing_token,
        client,
    )
    deposit_data["contract_address"] = (
        position_db_connector.get_contract_address_by_wallet_id(form_data.wallet_id)
    )
    deposit_data["position_id"] = str(position.id)
    return LoopLiquidityData(**deposit_data)


@router.get(
    "/api/get-repay-data",
    tags=["Position Operations"],
    response_model=RepayTransactionDataResponse,
    summary="Get repay data",
    response_description="Returns the repay transaction data.",
)
@limiter.limit(WRITE_LIMIT, key_func=lambda request: f"wallet:{request.query_params.get('wallet_id', request.client.host)}")
async def get_repay_data(
    request: Request,
    wallet_id: str,
    client: StellarClient = Depends(get_stellar_client),
) -> RepayTransactionDataResponse:
    """
    Obtain data for position closing.

    :param wallet_id: Wallet ID (Stellar public key G…)
    :return: Dict containing the repay transaction data
    """
    if not wallet_id:
        raise HTTPException(status_code=404, detail="Wallet not found")

    contract_address, position_id, token_symbol = position_db_connector.get_repay_data(
        wallet_id
    )
    is_opened_position = await PositionMixin.is_opened_position(contract_address, client)
    if not is_opened_position:
        raise HTTPException(status_code=400, detail="Position was closed")
    if not position_id:
        raise HTTPException(status_code=404, detail="Position not found or closed")

    repay_data = await DepositMixin.get_repay_data(token_symbol, client)
    repay_data["contract_address"] = contract_address
    repay_data["position_id"] = str(position_id)
    return repay_data


@router.get(
    "/api/close-position",
    tags=["Position Operations"],
    response_model=str,
    summary="Close a position",
    response_description="Returns the position status",
)
@limiter.limit(WRITE_LIMIT)
async def close_position(request: Request, position_id: UUID, transaction_hash: str) -> str:
    """
    Close a position.

    :param position_id: Position UUID
    :param transaction_hash: Transaction hash from the Soroban close_position call
    :return: Position status string
    """
    if position_id is None or str(position_id) == "undefined":
        raise HTTPException(status_code=404, detail="Position not Found")
    if not transaction_hash:
        raise HTTPException(status_code=400, detail="Transaction hash is required")

    position_status = position_db_connector.close_position(str(position_id))
    position_db_connector.save_transaction(
        position_id=position_id, status="closed", transaction_hash=transaction_hash
    )
    return position_status


@router.get(
    "/api/open-position",
    tags=["Position Operations"],
    response_model=str,
    summary="Open a position",
    response_description="Returns the positions status",
)
@limiter.limit(WRITE_LIMIT)
async def open_position(request: Request, position_id: str, transaction_hash: str) -> str:
    """
    Open a position after a successful Soroban loop_liquidity transaction.

    :param position_id: Position ID
    :param transaction_hash: Transaction hash from the Soroban call
    :return: Position status string
    """
    if not position_id:
        raise HTTPException(status_code=404, detail="Position not found")
    if not transaction_hash:
        raise HTTPException(status_code=400, detail="Transaction hash is required")

    current_prices = await DashboardMixin.get_current_prices()
    position_status = position_db_connector.open_position(position_id, current_prices)

    if transaction_hash:
        transaction_db_connector.create_transaction(
            position_id, transaction_hash, status=TransactionStatus.OPENED.value
        )

    return position_status


@router.get(
    "/api/get-withdraw-all-data",
    tags=["Position Operations"],
    summary="Get data to close position and withdraw all tokens",
    response_model=WithdrawAllData,
    response_description="Object containing data to withdraw all from the position",
)
@limiter.limit(WRITE_LIMIT, key_func=lambda request: f"wallet:{request.query_params.get('wallet_id', request.client.host)}")
async def get_withdraw_data(
    request: Request,
    wallet_id: str,
    client: StellarClient = Depends(get_stellar_client)
) -> WithdrawAllData:
    """
    Prepare data to withdraw all tokens and close a position.

    :param wallet_id: Stellar public key of the user
    :return: Dict containing repay data and list of extra token addresses
    """
    contract_address, position_id, token_symbol = position_db_connector.get_repay_data(
        wallet_id
    )
    if not await PositionMixin.is_opened_position(contract_address, client):
        raise HTTPException(status_code=400, detail="Position was closed")
    if not position_id:
        raise HTTPException(status_code=404, detail="Position not found or closed")

    repay_data = await DepositMixin.get_repay_data(token_symbol, client)
    extra_tokens = position_db_connector.get_extra_deposits_data(position_id).keys()
    repay_data["position_id"] = str(position_id)
    repay_data["contract_address"] = contract_address

    data = WithdrawAllData(
        repay_data=RepayTransactionDataResponse(**repay_data),
        tokens=[
            TokenParams.get_token_address(symbol)
            for symbol in extra_tokens
            if symbol != token_symbol
        ],
    )
    return data


@router.get(
    "/api/get-add-deposit-data/{position_id}",
    tags=["Position Operations"],
    summary="Add extra deposit to a user position",
    response_description="Returns the result of extra deposit",
)
@limiter.limit(USER_DATA_LIMIT)
async def get_add_deposit_data(request: Request, position_id: UUID, amount: str, token_symbol: str):
    """
    Prepare data for adding an extra deposit to a position.

    :param position_id: UUID of the position
    :param amount: Amount of tokens to deposit
    :param token_symbol: Symbol of the token being deposited
    :return: Dict containing deposit data with token address and amount
    """
    if not amount:
        raise HTTPException(status_code=400, detail="Amount is required")
    if not token_symbol:
        raise HTTPException(status_code=400, detail="Token symbol is required")

    position = position_db_connector.get_position_by_id(position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    try:
        token_address = TokenParams.get_token_address(token_symbol)
        token_amount = int(
            Decimal(amount) * 10 ** TokenParams.get_token_decimals(token_address)
        )
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="Amount is not a number")

    return {
        "deposit_data": {"token_address": token_address, "token_amount": token_amount}
    }


@router.post("/api/add-extra-deposit/{position_id}")
@limiter.limit(WRITE_LIMIT)
async def add_extra_deposit(request: Request, position_id: UUID, data: AddPositionDepositData):
    """
    Add extra deposit to a user position.

    :param position_id: UUID of the position
    :param data: Deposit data to create extra deposit
    :return: Dict containing detail
    """
    if not data.amount:
        raise HTTPException(status_code=400, detail="Amount is required")
    if not data.transaction_hash:
        raise HTTPException(status_code=400, detail="Transaction hash is required")

    position = position_db_connector.get_position_by_id(position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    if position.status != Status.OPENED.value:
        raise HTTPException(status_code=400, detail="Can only add deposits to open positions")

    position_db_connector.add_extra_deposit_to_position(
        position, data.token_symbol, data.amount
    )
    transaction_db_connector.create_transaction(
        position_id, data.transaction_hash, status=TransactionStatus.EXTRA_DEPOSIT.value
    )
    return {"detail": "Successfully added extra deposit"}


@router.get(
    "/api/user-positions/{wallet_id}",
    tags=["Position Operations"],
    response_model=UserPositionHistoryResponse,
    summary="Get all positions for a user",
    response_description="Returns paginated positions for the given wallet ID",
)
@limiter.limit(USER_DATA_LIMIT, key_func=lambda request: f"wallet:{request.path_params.get('wallet_id', request.client.host)}")
async def get_user_positions(
    request: Request,
    wallet_id: str,
    start: int = Query(0, ge=0),
    limit: int = Query(PAGINATION_STEP, ge=1, le=100),
) -> UserPositionHistoryResponse:
    """
    Get all positions for a specific user by their wallet ID.

    :param wallet_id: Wallet ID of the user
    :param start: Starting index for pagination (default: 0)
    :param limit: Number of items per page (default: 10)
    :return: UserPositionHistoryResponse with positions and total count
    """
    if not wallet_id:
        raise HTTPException(status_code=400, detail="Wallet ID is required")

    positions = position_db_connector.get_all_positions_by_wallet_id(
        wallet_id, start=start, limit=limit
    )
    total_positions = position_db_connector.get_count_positions_by_wallet_id(wallet_id)

    return UserPositionHistoryResponse(
        positions=positions,
        total_count=total_positions,
    )


@router.get(
    "/api/user-extra-positions",
    tags=["Position Operations"],
    response_model=UserPositionExtraDepositsResponse,
    summary="Get all extra positions for a user",
)
@limiter.limit(USER_DATA_LIMIT)
async def get_list_of_deposited_tokens(request: Request, position_id: UUID):
    """
    Get position and extra positions by position id.

    :param position_id: UUID of the position
    :return: Dict containing main position and extra positions
    """
    main_position = position_db_connector.get_position_by_id(position_id)
    extra_deposits = position_db_connector.get_extra_deposits_by_position_id(
        position_id
    )
    return {"main": main_position, "extra_deposits": extra_deposits}
