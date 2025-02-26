from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    """
    User base model
    """

    id: int
    wallet_id: str
    created_at: datetime

class UserCreate(UserBase):
    """
    User create model
    """

    pass

class UserResponse(UserBase):
    """
    User response model
    """

    id: UUID

    model_config = ConfigDict(from_attributes=True)