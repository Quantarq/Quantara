"""
This module defines the serializers for the user data.
"""

from pydantic import BaseModel, Field


class CheckUserResponse(BaseModel):
    """
    Pydantic model for the check user response.
    """

    is_contract_deployed: bool = Field(
        ..., example=False, description="Indicates if the user's contract is deployed."
    )


class UpdateUserContractResponse(BaseModel):
    """
    Pydantic model for the update user contract response.
    """

    is_contract_deployed: bool = Field(
        ..., example=False, description="Indicates if the user's contract is deployed."
    )


class GetUserContractAddressResponse(BaseModel):
    """
    Pydantic model for the get user contract address response.
    """

    contract_address: str | None = Field(
        None,
        example="0xabc123...",
        description="The contract address of the user, or None if not deployed.",
    )


class GetStatsResponse(BaseModel):
    """
    Pydantic model for the get_stats response.
    """
    total_opened_amount: float = Field(
        ...,
        example=1000.0,
        description="Total amount for all open positions across all users.",
    )
    unique_users: int = Field(
        ...,
        example=5,
        description="Number of unique users in the database.",
    )