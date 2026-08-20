"""
quantara/soroban/adapters/__init__.py

AMM and lending protocol adapters for Stellar/Soroban.
"""

from .AMMAdapter import AMMAdapter, AMMAdapterFactory, PoolKey, PoolPrice, SwapRoute
from .soroswap_adapter import SoroswapAMMAdapter
from .LendingAdapter import LendingAdapter, LendingAdapterFactory, ReserveData, UserPosition
from .blend_adapter import BlendLendingAdapter
from .errors import AdapterRpcError

from . import _register

_register.register_adapters()

__all__ = [
    "AMMAdapter",
    "AMMAdapterFactory",
    "PoolKey",
    "PoolPrice",
    "SwapRoute",
    "SoroswapAMMAdapter",
    "LendingAdapter",
    "LendingAdapterFactory",
    "ReserveData",
    "UserPosition",
    "BlendLendingAdapter",
    "AdapterRpcError",
]
