"""
This module defines the Deposit model for the Spotnet application.
"""

from sqlalchemy import Column, String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from .base import BaseModel

# pylint: disable=too-few-public-methods
class Deposit(BaseModel):
    """
    Represents a deposit transaction in the Spotnet application.
    """

    __tablename__ = "deposits"

    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    transaction_id = Column(String, nullable=False, unique=True)
    user: Mapped["User"] = relationship(back_populates="deposit")

    # pylint: disable=too-few-public-methods
