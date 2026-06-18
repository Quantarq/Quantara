"""
quantara/soroban/adapters/_register.py

Explicit registration of concrete AMM adapters with AMMAdapterFactory.
This avoids import-time circular dependencies and makes registration obvious.
"""

from .soroswap_adapter import SoroswapAMMAdapter


def register_adapters() -> None:
    from .AMMAdapter import AMMAdapterFactory

    AMMAdapterFactory.register("soroswap", SoroswapAMMAdapter)
