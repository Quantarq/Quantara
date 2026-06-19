"""
API dependencies for the Quantara FastAPI application.
"""

from web_app.contract_tools.blockchain_call import StellarClient

def get_stellar_client() -> StellarClient:
    """
    FastAPI dependency that returns a StellarClient instance.
    """
    return StellarClient()