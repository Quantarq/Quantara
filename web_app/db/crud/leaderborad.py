from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from web_app.db.models import User, Position
import logging

logger = logging.getLogger(__name__)

class LeaderboardCRUD:
    def __init__(self, session: Session):
        self.Session = session

    def get_top_users_by_positions(self) -> list[dict]:
        """
        Retrieves the top 10 users ordered by closed/opened positions.
        :return: List of dictionaries containing wallet_id and positions_number.
        """
        with self.Session() as db:
            try:
                results = (
                    db.query(
                        User.wallet_id,
                        func.count(Position.id).label("positions_number")
                    )
                    .join(Position, Position.user_id == User.id)
                    .group_by(User.wallet_id)
                    .order_by(func.count(Position.id).desc())
                    .limit(10)
                    .all()
                )

                return [
                    {"wallet_id": result.wallet_id, "positions_number": result.positions_number}
                    for result in results
                ]

            except SQLAlchemyError as e:
                logger.error(f"Error retrieving top users by positions: {e}")
                return []