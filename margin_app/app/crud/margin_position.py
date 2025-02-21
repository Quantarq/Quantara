"""
This module contains the MarginPositionCRUD Class for opening ,updating and closing margin positions.
"""

import uuid
from app.crud.base import DBConnector
from app.models.margin_position import MarginPosition
from app.models.margin_position import MarginPositionStatus


class MarginPositionCRUD(DBConnector):
    """"Handles margin position database operations"""

    async def open_margin_position(self, user_id: uuid.UUID, multiplier: int, borrowed_amount:int, transaction_id:str) -> MarginPosition:
        """
        Opens a margin position by creating an entry record in the database.
        :param user_id: uuid
        :param multiplier: int
        :param borrowed_amount: int
        :param transaction_id: str
        :return: MarginPosition
        """
        position_entry = MarginPosition(user_id=user_id, 
                                         multiplier=multiplier, 
                                         borrowed_amount=borrowed_amount,
                                         status=MarginPositionStatus.OPEN.value,
                                         transaction_id=transaction_id)
        
        position = await self.write_to_db(position_entry)
        return position

    async def close_margin_position(self, position_id : str) -> MarginPosition | None:
        """
        Closes a margin position by updating the position status in the database.
        :param position_id: str
        :return: Position | None
        """
        position = self.get_object(MarginPosition, position_id)
        if position:
            position.status = MarginPositionStatus.CLOSED.value
            await self.write_to_db(position)
        return position.status
    

