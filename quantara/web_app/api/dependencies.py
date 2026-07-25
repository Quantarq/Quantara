"""
API dependencies for the Quantara FastAPI application.
"""

from collections.abc import AsyncIterator

from web_app.api.wallet_auth import verify_wallet_signature
from web_app.contract_tools.blockchain_call import StellarClient


async def get_stellar_client() -> AsyncIterator[StellarClient]:
    """
    FastAPI dependency that returns and closes a StellarClient instance.
    """
    client = StellarClient()
    try:
        yield client
    finally:
        await client.close()


__all__ = ["get_stellar_client", "verify_wallet_signature"]