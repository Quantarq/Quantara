"""
This module contains the API routes for the user.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..crud.user import user_crud as crud_create_user
from app.schemas.user import UserResponse, UserCreate

router = APIRouter()


@router.post(
    "/users", 
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    )

async def user_crud(user: UserCreate, db: AsyncSession = Depends(get_db))-> UserResponse:
    """
    Create a new user.

    Parameters:
    - wallet_id: str, the wallet ID of the user

    Returns:
    - UserResponse: The created user object
    """
    db_user = await crud_create_user(db, user.wallet_id)
    if db_user is None:
        raise HTTPException(status_code=400, detail="User could not be created")
    return db_user