"""
Quantara Lending Adapter Module

This module provides an abstraction layer for lending protocol interactions
in the Stellar ecosystem. It replaces the former Starknet-specific ZkLend integration
and provides a protocol-agnostic interface for lending/borrowing operations.

The adapter pattern allows Quantara to support multiple Stellar-native lending
protocols through a unified interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ReserveData:
    """Data structure for lending protocol reserve information."""
    token_address: str
    token_symbol: str
    decimals: int
    supply_apy: Decimal
    borrow_apy: Decimal
    collateral_factor: Decimal
    borrow_factor: Decimal
    total_supply: Decimal
    total_borrows: Decimal
    liquidation_threshold: Decimal
    liquidation_bonus: Decimal


@dataclass(frozen=True)
class UserPosition:
    """Data structure for a user's lending position."""
    supplied_amount: Decimal
    borrowed_amount: Decimal
    collateral_amount: Decimal
    health_ratio: Decimal
    is_collateral_enabled: bool


class LendingAdapter(ABC):
    """
    Abstract base class for lending protocol adapters.
    
    All Stellar ecosystem lending protocol integrations should implement
    this interface to ensure compatibility with Quantara's leverage engine.
    """

    @abstractmethod
    async def get_reserve_data(self, token_address: str) -> ReserveData:
        """
        Get reserve data for a specific token from the lending protocol.
        
        Args:
            token_address: The Stellar asset address
            
        Returns:
            ReserveData with protocol-specific reserve information
        """
        ...

    @abstractmethod
    async def get_user_position(
        self, user_address: str, token_address: str
    ) -> UserPosition:
        """
        Get a user's position for a specific token.
        
        Args:
            user_address: The user's Stellar account address
            token_address: The asset address
            
        Returns:
            UserPosition with supply/borrow details
        """
        ...

    @abstractmethod
    async def deposit(
        self, user_address: str, token_address: str, amount: Decimal
    ) -> str:
        """
        Deposit tokens as collateral into the lending protocol.
        
        Args:
            user_address: The user's Stellar account address
            token_address: The asset to deposit
            amount: Amount to deposit (in human-readable units)
            
        Returns:
            Transaction hash
        """
        ...

    @abstractmethod
    async def withdraw(
        self, user_address: str, token_address: str, amount: Optional[Decimal] = None
    ) -> str:
        """
        Withdraw tokens from the lending protocol.
        
        Args:
            user_address: The user's Stellar account address
            token_address: The asset to withdraw
            amount: Amount to withdraw (None = all)
            
        Returns:
            Transaction hash
        """
        ...

    @abstractmethod
    async def borrow(
        self, user_address: str, token_address: str, amount: Decimal
    ) -> str:
        """
        Borrow tokens against deposited collateral.
        
        Args:
            user_address: The user's Stellar account address
            token_address: The asset to borrow
            amount: Amount to borrow
            
        Returns:
            Transaction hash
        """
        ...

    @abstractmethod
    async def repay(
        self, user_address: str, token_address: str, amount: Decimal
    ) -> str:
        """
        Repay borrowed tokens.
        
        Args:
            user_address: The user's Stellar account address
            token_address: The asset to repay
            amount: Amount to repay
            
        Returns:
            Transaction hash
        """
        ...

    @abstractmethod
    async def enable_collateral(
        self, user_address: str, token_address: str
    ) -> str:
        """
        Enable a token as collateral.
        
        Args:
            user_address: The user's Stellar account address
            token_address: The asset to enable as collateral
            
        Returns:
            Transaction hash
        """
        ...

    @abstractmethod
    async def disable_collateral(
        self, user_address: str, token_address: str
    ) -> str:
        """
        Disable a token as collateral.
        
        Args:
            user_address: The user's Stellar account address
            token_address: The asset to disable as collateral
            
        Returns:
            Transaction hash
        """
        ...

    @abstractmethod
    async def get_all_reserves(self) -> List[ReserveData]:
        """
        Get reserve data for all available tokens.
        
        Returns:
            List of ReserveData for all supported tokens
        """
        ...


class LendingAdapterFactory:
    """
    Factory for creating lending protocol adapters.
    
    Allows Quantara to dynamically select which lending protocol
    to interact with based on configuration.
    """
    
    _adapters: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, adapter_cls: type) -> None:
        """Register a new lending adapter implementation."""
        cls._adapters[name] = adapter_cls
    
    @classmethod
    def _ensure_registered(cls) -> None:
        if not cls._adapters:
            from ._register import register_adapters
            register_adapters()

    @classmethod
    def create(cls, name: str, **kwargs) -> LendingAdapter:
        """
        Create a lending adapter instance by name.
        
        Args:
            name: The registered adapter name
            **kwargs: Configuration parameters for the adapter
            
        Returns:
            An instance of the requested LendingAdapter
            
        Raises:
            ValueError: If the adapter name is not registered
        """
        cls._ensure_registered()
        if name not in cls._adapters:
            raise ValueError(f"Unknown lending adapter: {name}. "
                            f"Available: {list(cls._adapters.keys())}")
        return cls._adapters[name](**kwargs)
