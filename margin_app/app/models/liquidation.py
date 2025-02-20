import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel

class Liquidation(BaseModel):
    
    """
    Liquidation Model
    
    Columns:
        margin_position_id (UUID): Foreign key referencing MarginPosition.id.
        bonus_amount (Decimal): The amount of bonus given during liquidation.
        bonus_token (str): The token in which the bonus is given.
        created_at (datetime): Timestamp indicating when the liquidation was created.
    """

    margin_position_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("margin_position.id"), nullable=False)
    bonus_amount: Mapped[Decimal] = mapped_column(nullable=False)
    bonus_token: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
