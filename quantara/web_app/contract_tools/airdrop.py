"""
This module defines the contract tools for the airdrop data.
"""

import os
import logging

import aiohttp

from web_app.api.serializers.airdrop import AirdropItem, AirdropResponseModel
from web_app.contract_tools.api_request import APIRequest

logger = logging.getLogger(__name__)


class AirdropFetcher:
    """
    A class to fetch and validate airdrop data for a specified contract.
    """

    # No Starknet-specific default. Configure a Stellar-compatible endpoint
    # when the feature is available.
    REWARD_API_ENDPOINT = os.getenv("AIRDROP_REWARD_API_ENDPOINT", "")

    def __init__(self):
        """
        Initializes the AirdropFetcher with an APIRequest instance.
        """
        self.api = (
            APIRequest(base_url=self.REWARD_API_ENDPOINT)
            if self.REWARD_API_ENDPOINT
            else None
        )

    async def get_contract_airdrop(self, contract_id: str) -> AirdropResponseModel:
        """
        Fetches all available airdrops for a specific contract.

        Args:
            contract_id: The ID of the contract for which to fetch airdrop data.
        Returns:
            AirdropResponseModel: A validated list of airdrop items.
        Raises:
            ValueError: If contract_id is None
        """
        if contract_id is None:
            raise ValueError("Contract ID cannot be None")

        underlying_contract_id = contract_id
        if not self.api:
            logger.info(
                "Airdrop endpoint is not configured; returning no data for %s",
                contract_id,
            )
            return AirdropResponseModel(airdrops=[])
        try:
            response = await self.api.fetch(underlying_contract_id)
        except (aiohttp.ClientError, ValueError, KeyError, TypeError) as e:
            logger.error("Failed to fetch airdrop data for %s: %s", contract_id, e)
            return AirdropResponseModel(airdrops=[])
        return self._validate_response(response)

    @staticmethod
    def _validate_response(data: list[dict]) -> AirdropResponseModel:
        """
        Validates and formats the response data.

        Args:
            data: Raw response data from the API.
        Returns:
            AirdropResponseModel: Structured and validated airdrop data.
        """
        validated_items = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                validated_item = AirdropItem(
                    amount=item.get("amount", 0),
                    proof=item.get("proof", []),
                    is_claimed=item.get("is_claimed", False),
                    recipient=item.get("recipient", ""),
                )
                validated_items.append(validated_item)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Skipping invalid airdrop item: %s", e)
        return AirdropResponseModel(airdrops=validated_items)


__all__ = ["AirdropFetcher"]
