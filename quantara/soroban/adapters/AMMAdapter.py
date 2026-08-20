"""
Quantara AMM Adapter Module

This module provides an abstraction layer for AMM (Automated Market Maker)
interactions in the Stellar ecosystem. It replaces the former Starknet-specific
Ekubo integration and provides a protocol-agnostic interface for token swaps.

The adapter pattern allows Quantara to support multiple Stellar-native AMM/DEX
protocols through a unified interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class PoolKey:
    """Data structure identifying an AMM liquidity pool."""
    token_a: str
    token_b: str
    fee: int
    tick_spacing: int


@dataclass(frozen=True)
class PoolPrice:
    """Data structure for pool pricing information."""
    sqrt_price: Decimal
    price_a_to_b: Decimal
    price_b_to_a: Decimal
    liquidity: Decimal
    tick: int


@dataclass(frozen=True)
class SwapRoute:
    """Data structure for a swap route/path."""
    pools: List[PoolKey]
    estimated_amount_out: Decimal
    estimated_fee: Decimal
    price_impact: Decimal


class AMMAdapter(ABC):
    """
    Abstract base class for AMM/DEX protocol adapters.
    
    All Stellar ecosystem AMM integrations should implement
    this interface to ensure compatibility with Quantara's leverage engine.
    """

    @abstractmethod
    async def get_pool_price(self, pool_key: PoolKey) -> PoolPrice:
        """
        Get the current price and liquidity for a pool.
        
        Args:
            pool_key: The pool identifier
            
        Returns:
            PoolPrice with current pricing data
        """
        ...

    @abstractmethod
    async def get_pool_key(
        self, token_a: str, token_b: str, fee: Optional[int] = None
    ) -> PoolKey:
        """
        Get or construct a pool key for a token pair.
        
        Args:
            token_a: First token address
            token_b: Second token address
            fee: Optional fee tier
            
        Returns:
            PoolKey for the specified pair
        """
        ...

    @abstractmethod
    async def swap_exact_input(
        self,
        user_address: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        pool_key: PoolKey,
    ) -> Tuple[str, Decimal]:
        """
        Execute a swap with exact input amount.
        
        Args:
            user_address: The user's Stellar account address
            token_in: Input token address
            token_out: Output token address
            amount_in: Exact input amount
            min_amount_out: Minimum output amount (slippage protection)
            pool_key: The pool to swap through
            
        Returns:
            Tuple of (transaction_hash, amount_out)
        """
        ...

    @abstractmethod
    async def swap_exact_output(
        self,
        user_address: str,
        token_in: str,
        token_out: str,
        amount_out: Decimal,
        max_amount_in: Decimal,
        pool_key: PoolKey,
    ) -> Tuple[str, Decimal]:
        """
        Execute a swap with exact output amount.
        
        Args:
            user_address: The user's Stellar account address
            token_in: Input token address
            token_out: Output token address
            amount_out: Exact output amount desired
            max_amount_in: Maximum input amount (slippage protection)
            pool_key: The pool to swap through
            
        Returns:
            Tuple of (transaction_hash, amount_in)
        """
        ...

    @abstractmethod
    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount: Decimal,
        pool_key: PoolKey,
    ) -> Decimal:
        """
        Get a swap quote without executing.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount: Amount to swap
            pool_key: The pool to quote through
            
        Returns:
            Estimated output amount
        """
        ...

    @abstractmethod
    async def find_best_route(
        self,
        token_in: str,
        token_out: str,
        amount: Decimal,
    ) -> Optional[SwapRoute]:
        """
        Find the best swap route for a token pair.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount: Amount to swap
            
        Returns:
            Best SwapRoute if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_supported_pairs(self) -> List[Tuple[str, str]]:
        """
        Get all supported trading pairs.
        
        Returns:
            List of (token_a, token_b) tuples
        """
        ...


class AMMAdapterFactory:
    """
    Factory for creating AMM protocol adapters.
    
    Allows Quantara to dynamically select which AMM/DEX
    to interact with based on configuration.
    """
    
    _adapters: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, adapter_cls: type) -> None:
        """Register a new AMM adapter implementation."""
        cls._adapters[name] = adapter_cls
    
    @classmethod
    def _ensure_registered(cls) -> None:
        if not cls._adapters:
            from ._register import register_adapters
            register_adapters()

    @classmethod
    def create(cls, name: str, **kwargs) -> AMMAdapter:
        """
        Create an AMM adapter instance by name.
        
        Args:
            name: The registered adapter name
            **kwargs: Configuration parameters for the adapter
            
        Returns:
            An instance of the requested AMMAdapter
            
        Raises:
            ValueError: If the adapter name is not registered
        """
        cls._ensure_registered()
        if name not in cls._adapters:
            raise ValueError(f"Unknown AMM adapter: {name}. "
                            f"Available: {list(cls._adapters.keys())}")
        return cls._adapters[name](**kwargs)
