"""
This module contains the Pool and UserPool models.
"""

import uuid
from decimal import Decimal
from typing import List

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Pool(BaseModel):
    """
    Represents a pool in the application.
    """

    __tablename__ = "pools"

    token: Mapped[str] = mapped_column(String, nullable=False)
    user_pools: Mapped[List["UserPool"]] = relationship(back_populates="pool")

    def __repr__(self) -> str:
        """
        Returns a string representation of the Pool object.
        """
        return f"<Pool(id={self.id}, token={self.token})>"


class UserPool(BaseModel):
    """
    Represents a user's participation in a pool.
    This acts as an association table between users and pools,
    and stores additional information about the user's participation.
    """

    __tablename__ = "user_pools"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pools.id"), nullable=False
    )
    token: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(nullable=False)
    pool: Mapped["Pool"] = relationship(back_populates="user_pools")

    def __repr__(self) -> str:
        """
        Returns a string representation of the UserPool object.
        """
        return (
            f"<UserPool(id={self.id}, user_id={self.user_id}, pool_id={self.pool_id}, "
            f"token={self.token}, amount={self.amount})>"
        )
