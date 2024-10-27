"""
This module defines the serializers for the airdrop data.
"""

from pydantic import BaseModel, Field
from typing import List

class AirdropItem(BaseModel):
    """
    A model to represent individual airdrop data with only the necessary fields.
    """
    amount: float # Amount of the airdrop tokens
    proof: str # Proof for claiming the airdrop
    is_claimed: bool # Whether the airdrop has been claimed
    recipient: str #Recipient address of the airdrop

class AirdropResponseModel(BaseModel):
    """
    A model to encapsulate a list of AirdropItem instances, providing a structured response.
    """
    airdrops: List[AirdropItem] # A list of filtered and validated airdrop items