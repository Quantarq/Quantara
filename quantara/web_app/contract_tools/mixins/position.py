"""
Mixins for position related methods in the Stellar-based Quantara protocol.

Provides query methods for Soroban position contract state introspection.
"""

import logging

import aiohttp

from web_app.contract_tools.blockchain_call import StellarClient

logger = logging.getLogger(__name__)


class PositionMixin:
    """
    Mixin for position related methods using Stellar/Soroban primitives.

    Provides async methods to check position state on the Stellar network
    by querying deployed Soroban contract instances.
    """

    @classmethod
    async def is_opened_position(cls, contract_address: str, client: StellarClient) -> bool:
        """
        Check whether a Soroban position contract is currently open.

        Queries the Soroban RPC to verify that the contract is deployed
        and accessible on the network. In a full integration this would
        additionally check the position status in the contract's ledger
        entry data.

        :param contract_address: Soroban contract ID (C… format)
        :param client: StellarClient instance
        :return: True if the contract exists on the network, False otherwise
        """
        if not contract_address:
            return False
        try:
            return await client.is_contract_deployed(contract_address)
        except (ValueError, KeyError, TypeError, aiohttp.ClientError) as e:
            logger.warning(
                "Failed to check position status for %s: %s",
                contract_address,
                e,
            )
            return False
