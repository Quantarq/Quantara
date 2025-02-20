from sqlalchemy import Column, String, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class Deposit(BaseModel):
    __tablename__ = "deposits"

    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    transaction_id = Column(String, nullable=False)
