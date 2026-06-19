"""
Module for claiming unclaimed airdrops and updating the database.
Uses the Stellar-based Quantara protocol primitives.
"""

import asyncio
import inspect
import logging
from typing import List

from requests.exceptions import ConnectionError, Timeout
from sqlalchemy.exc import SQLAlchemyError
from web_app.contract_tools.airdrop import AirdropFetcher
from web_app.db.crud import AirDropDBConnector

logger = logging.getLogger(__name__)


class AirdropClaimer:
    """
    Handles the process of claiming unclaimed airdrops and updating the database.
    """

    def __init__(self):
        """
        Initializes the AirdropClaimer with database and airdrop fetcher instances.
        """
        self.db_connector = AirDropDBConnector()
        self.airdrop_fetcher = AirdropFetcher()

    async def claim_airdrops(self) -> None:
        """
        Retrieves unclaimed airdrops, attempts to claim them,
        and updates the database if the claim is successful.
        """
        unclaimed_airdrops = self.db_connector.get_all_unclaimed()
        if not unclaimed_airdrops:
            logger.info("No unclaimed airdrops found")
            return
        for airdrop in unclaimed_airdrops:
            try:
                user_contract_address = airdrop.user.contract_address
                if not user_contract_address:
                    logger.warning(
                        "Skipping airdrop %s: no contract address", airdrop.id
                    )
                    continue
                airdrop_data = self.airdrop_fetcher.get_contract_airdrop(
                    user_contract_address
                )
                if inspect.isawaitable(airdrop_data):
                    airdrop_data = await airdrop_data
                proofs = self._extract_proofs(airdrop_data)
                if not proofs:
                    logger.info(
                        "Skipping airdrop %s: no proof data available", airdrop.id
                    )
                    continue

                claim_successful = await self._claim_airdrop(
                    user_contract_address, proofs
                )

                if claim_successful:
                    self.db_connector.save_claim_data(airdrop.id, airdrop.amount)
                    logger.info("Airdrop %s claimed successfully.", airdrop.id)
            except ValueError as ve:
                logger.error("Invalid data for airdrop %s: %s", airdrop.id, ve)
            except SQLAlchemyError as db_err:
                logger.error(
                    "Database error while updating claim data for airdrop %s: %s",
                    airdrop.id,
                    db_err,
                )
            except ConnectionError as ce:
                logger.error(
                    "Network connection error during claim for airdrop %s: %s",
                    airdrop.id,
                    ce,
                )
            except Timeout as te:
                logger.error("Timeout during claim for airdrop %s: %s", airdrop.id, te)
            except Exception as e:
                logger.error("Unexpected error claiming airdrop %s: %s", airdrop.id, e)

    @staticmethod
    def _extract_proofs(airdrop_data):
        """
        Normalize airdrop data into the proof list expected by claim logic.
        """
        if not airdrop_data:
            return []

        if hasattr(airdrop_data, "airdrops"):
            proofs = []
            for item in airdrop_data.airdrops:
                proofs.extend(item.proof)
            return proofs

        if isinstance(airdrop_data, list):
            return airdrop_data

        return []

    async def _claim_airdrop(self, contract_address: str, proofs: List[str]) -> bool:
        """
        Claims a single airdrop.

        In a full Soroban integration, this would invoke the claim method
        on the contract. Currently a placeholder that always succeeds.
        """
        try:
            # NOTE: Soroban contract invocation for airdrop claiming pending
            #       the deployment of the claim contract on the target network.
            logger.info(
                "Airdrop claim for %s with %d proofs sent (mock implementation)",
                contract_address,
                len(proofs),
            )
            return True
        except ConnectionError as ce:
            logger.error(
                "Network connection failed for address %s: %s", contract_address, ce
            )
            return False
        except Timeout as te:
            logger.error(
                "Timeout during claim for address %s: %s", contract_address, te
            )
            return False
        except ValueError as ve:
            logger.error(
                "Invalid data format for calldata during claim for address %s: %s",
                contract_address,
                ve,
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error claiming address %s: %s", contract_address, e
            )
            return False


if __name__ == "__main__":
    airdrop_claimer = AirdropClaimer()
    asyncio.run(airdrop_claimer.claim_airdrops())
