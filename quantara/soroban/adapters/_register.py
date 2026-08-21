"""
quantara/soroban/adapters/_register.py

Explicit registration of concrete adapters with factories.
This avoids import-time circular dependencies and makes registration obvious.
"""

from .soroswap_adapter import SoroswapAMMAdapter
from .blend_adapter import BlendLendingAdapter


_registered = False


def register_adapters() -> None:
    global _registered
    if _registered:
        return

    from .AMMAdapter import AMMAdapterFactory
    from .LendingAdapter import LendingAdapterFactory

    AMMAdapterFactory.register("soroswap", SoroswapAMMAdapter)
    LendingAdapterFactory.register("blend", BlendLendingAdapter)
    _registered = True
