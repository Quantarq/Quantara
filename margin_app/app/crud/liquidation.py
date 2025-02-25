"""This module contains the LiquidationCRUD class for managing liquidations."""

from app.crud.base import DBConnector
from app.models.liquidation import Liquidation
from uuid import UUID
from decimal import Decimal

class LiquidationCRUD(DBConnector):
    """Handles database operations for liquidations."""

    async def liquidate_position(
        self, margin_position_id: UUID, 
        bonus_amount: Decimal,
        bonus_token: str
    ) -> Liquidation:
        """
        Liquidates a position by creating a liquidation record in the database.

        :param position_id: ID of the position to be liquidated.
        :param bonus_amount: Decimal
        :param bonus_token: str
        :return: The created Liquidation record.
        """
        liquidation_entry = Liquidation(
            margin_position_id=margin_position_id,
            bonus_amount=bonus_amount,
            bonus_token=bonus_token
        )
        return await self.write_to_db(liquidation_entry)

liqudation_crud = LiquidationCRUD()


    async def add_deposit(self, margin_position_id: UUID, amount: Decimal, token: str) -> None:
        """
        Adds a deposit entry linked to a margin position.

        Args:
            margin_position_id (UUID): The ID of the margin position.
            amount (Decimal): The deposit amount.
            token (str): The token type.
        """
        deposit_entry = Liquidation(
            margin_position_id=margin_position_id,
            bonus_amount=amount,
            bonus_token=token
        )
        await self.write_to_db(deposit_entry)
