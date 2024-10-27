from typing import List
from api.serializers.airdrop import AirdropItem, AirdropResponseModel
from contract_tools.api_request import APIRequest

class ZkLendAirdrop:
    def __init__(self, api: APIRequest):
        """
        Initializes the ZkLendAirdrop class with an APIRequest instance.
        """
        self.api = api

    async def get_contract_airdrop(self, contract_id: str) -> AirdropResponseModel:
        """
        Fetches all available airdrops for a specific contract asynchronously.
        Returns AirdropResponseModel: a validated list of airdrop items 
        for the specified contract.
        """
        endpoint = f"/contracts/{contract_id}/airdrops"
        response = await self.api.fetch(endpoint)
        return self._validate_response(response)

    def _validate_response(self, data: List[dict]) -> AirdropResponseModel:
        """
        Validates and formats the response data, keeping only necessary fields.
        Returns AirdropResponseModel: Structured and validated airdrop data.
        """
        validated_items = []
        for item in data:
            validated_item = AirdropItem(
                amount=item["amount"],
                proof=item["proof"],
                is_claimed=item["is_claimed"],
                recipient=item["recipient"]
            )
            validated_items.append(validated_item)
        return AirdropResponseModel(airdrops=validated_items)
