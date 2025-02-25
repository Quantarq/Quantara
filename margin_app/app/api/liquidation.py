"""
API for handling liquidation endpoints.
"""

from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.liquidation import liqudation_crud
from app.schemas.liquidation import LiquidationResponse
from app.db.session import get_db

router = APIRouter()

@router.post("/liquidate", response_model=LiquidationResponse)
async def liquidate_position(
    margin_position_id: UUID,
    bonus_amount: Decimal,
    bonus_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Liquidates a margin position by adding a liquidation record.
    
    Args:
        margin_position_id (UUID): The ID of the margin position.
        bonus_amount (Decimal): The amount of bonus applied.
        bonus_token (str): The token used for the bonus.
        db (AsyncSession, optional): The database session.

    Returns:
        LiquidationResponse: Details of the liquidation entry.
    """
    try:
        liquidation_entry = await liqudation_crud.liquidate_position(
            margin_position_id, bonus_amount, bonus_token
        )
        return LiquidationResponse(
            margin_position_id=liquidation_entry.margin_position_id,
            bonus_amount=liquidation_entry.bonus_amount,
            bonus_token=liquidation_entry.bonus_token,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
