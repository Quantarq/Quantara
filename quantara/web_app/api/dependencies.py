"""
API dependencies for the Quantara FastAPI application.
"""

from web_app.api.wallet_auth import verify_wallet_signature
from web_app.contract_tools.blockchain_call import StellarClient


def get_stellar_client() -> StellarClient:
    """
    FastAPI dependency that returns a StellarClient instance.
    """
    return StellarClient()


__all__ = ["get_stellar_client", "verify_wallet_signature"]
