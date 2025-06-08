"""
This module contains Pydantic schemas for admin.
"""

from uuid import UUID
from typing import Optional
from .base import GetAll
from pydantic import BaseModel, EmailStr, ConfigDict


class AdminBase(BaseModel):
    """
    Admin base model
    """

    name: Optional[str] = None
    email: EmailStr


class AdminRequest(AdminBase):
    """
    Admin request model
    """

    email: EmailStr
    name: Optional[str] = None

    class Config:
        "Only allow fields that are defined in the model"
        extra = "forbid"


class AdminResetPassword(BaseModel):
    """
    Admin reset password model
    """

    old_password: str
    new_password: str


class AdminResponse(AdminBase):
    """
    Admin response model
    """

    id: UUID

    model_config = ConfigDict(from_attributes=True)


class AdminGetAllResponse(GetAll[AdminResponse]):
    """
    Admin get all response model
    """
