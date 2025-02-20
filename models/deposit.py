from uuid import UUID
from decimal import Decimal
from sqlalchemy import Column, String, ForeignKey, Numeric
from spotnet.models.base import BaseModel

class Deposit(BaseModel):
    __tablename__ = "deposits"

    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    transaction_id = Column(String, nullable=False, unique=True)
