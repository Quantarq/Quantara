"""
API endpoints for order management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.order import order_crud
from app.models.user_order import UserOrder
from app.schemas.order import UserOrderCreate, UserOrderResponse

from typing import Optional

router = APIRouter()


@router.get(
    "/get_all_orders",
    status_code=status.HTTP_200_OK,
    summary="Get all orders",
    description="Gets all orders from database",
)
async def get_all_orders(
    limit: Optional[int] = Query(25, gt=0), offset: Optional[int] = Query(0, ge=0)
) -> list[UserOrderResponse]:
    """
    Return all orders.

    Parameters:
    - limit: Optional[int] - max orders to be retrieved
    - offset: Optional[int] - start retrieving at

    Returns:
    - list[UserOrder]: a list of orders

    Raises:
        HTTPException: If there's an error retrieving orders
    """
    try:
        orders = await order_crud.get_all(limit, offset)
        return orders
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}",
        )


@router.post(
    "/create_order",
    response_model=UserOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    description="Creates a new order in the system",
)
async def create_order(
    order_data: UserOrderCreate,
    db: AsyncSession = Depends(order_crud.session),
) -> UserOrder:
    """
    Create a new order with the provided order data.

    Args:
        order_data: The order data to create
        order_crud: The OrderCRUD instance for database operations

    Returns:
        The created order

    Raises:
        HTTPException: If there's an error creating the order
    """
    try:
        order = await order_crud.add_new_order(
            user_id=order_data.user_id,
            price=order_data.price,
            token=order_data.token,
            position=order_data.position,
        )
        return order
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}",
        )
