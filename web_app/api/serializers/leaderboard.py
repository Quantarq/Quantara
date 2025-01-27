from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from web_app.db.crud.leaderboard import LeaderboardCRUD
from web_app.db.session import get_db

router = APIRouter()

class UserLeaderboardItem(BaseModel):
    wallet_id: str
    positions_number: int

class UserLeaderboardResponse(BaseModel):
    leaderboard: List[UserLeaderboardItem]

@router.get(
    "/api/get-user-leaderboard",
    tags=["Leaderboard"],
    response_model=UserLeaderboardResponse,
    summary="Get user leaderboard",
    response_description="Returns the top 10 users ordered by closed/opened positions.",
)
async def get_user_leaderboard(db: Session = Depends(get_db)) -> UserLeaderboardResponse:
    """
    Get the top 10 users ordered by closed/opened positions.
    """
    leaderboard_crud = LeaderboardCRUD(db)
    leaderboard_data = leaderboard_crud.get_top_users_by_positions()
    return UserLeaderboardResponse(leaderboard=leaderboard_data)