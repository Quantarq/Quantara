"""
This module defines the serializers for the dashboard data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from pydantic import BaseModel, Field


class DashboardResponse(BaseModel):
    """
    DashboardResponse class for dashboard details.
    """
    health_ratio: dict[str, str] = Field(
        ..., example={"health_factor": "2.0", "ltv": "0.5"}, description="The health ratio of the user."
    )
    balances: Dict[str, Any] = Field(
        ...,
        example={"ETH": 5.0, "USDC": 1000.0},
        description="The wallet balances for the user.",
    )
    multipliers: Dict[str, int | None] = Field(
        ..., example={"ETH": 1.5}, description="The multipliers applied to each asset."
    )
    start_dates: Dict[str, datetime | None] = Field(
        ...,
        example={"ETH": "2024-01-01T00:00:00"},
        description="The start date for each position.",
    )
    current_sum: Decimal = Field(
        ...,
        example=5000.0,
        description="The current sum of the position.",
    )
    start_sum: Decimal = Field(
        ...,
        example=1000.0,
        description="The starting sum of the position.",
    )
