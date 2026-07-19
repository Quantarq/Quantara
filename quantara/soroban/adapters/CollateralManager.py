"""
quantara/soroban/adapters/CollateralManager.py

Quantara Collateral Manager

Provides the collateral management abstraction layer for the Quantara protocol.
Handles collateral factor calculations, health ratio monitoring, liquidation
checks, and position management across Stellar ecosystem protocols.

Asset addresses are resolved at import time from
``quantara.web_app.contract_tools.constants`` which reads from the environment,
so no TODO placeholders or hardcoded addresses exist in this module.

Rounding Policy:
All financial calculations adopt the ``ROUND_HALF_UP`` rounding mode.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from typing import Dict, List, Optional

# Set rounding policy
getcontext().rounding = ROUND_HALF_UP

from web_app.contract_tools.constants import (
    ETH_ASSET_ID,
    USDC_ASSET_ID,
    XLM_ASSET_ID,
    IS_MAINNET,
)

logger = logging.getLogger(__name__)

# Sentinel used for "no debt / infinite health"
_INFINITE_HEALTH = Decimal("999999")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_PRECISION = Decimal("0.0000000001")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CollateralConfig:
    """Immutable configuration for a single collateral asset."""

    symbol: str
    asset_id: str                   # "native" for XLM, "CODE:ISSUER" for SEP-41 assets
    decimals: int
    collateral_factor: Decimal      # Max LTV (0–1)
    borrow_factor: Decimal          # Borrow weight (typically 1)
    liquidation_threshold: Decimal  # Ratio at which liquidation is triggered (> collateral_factor)
    liquidation_bonus: Decimal      # Bonus paid to liquidator (e.g. 0.05 = 5 %)
    is_active: bool = True


@dataclass
class PositionHealth:
    """Health metrics for a single leveraged position."""

    total_collateral_value: Decimal
    total_borrow_value: Decimal
    health_ratio: Decimal           # > 1 healthy; <= 1 liquidatable
    liquidation_price: Decimal      # Asset price that triggers liquidation
    is_underwater: bool
    max_withdrawable: Decimal       # How much collateral can be withdrawn safely
    max_borrowable: Decimal         # How much more can be borrowed safely


@dataclass
class PositionSummary:
    """Aggregated health across multiple positions."""

    positions: List[PositionHealth] = field(default_factory=list)

    @property
    def worst_health_ratio(self) -> Decimal:
        if not self.positions:
            return _INFINITE_HEALTH
        return min(p.health_ratio for p in self.positions)

    @property
    def any_underwater(self) -> bool:
        return any(p.is_underwater for p in self.positions)


# ---------------------------------------------------------------------------
# CollateralManager
# ---------------------------------------------------------------------------


class CollateralManager:
    """
    Manages collateral operations for Quantara positions.

    All token configurations are loaded from environment-resolved constants so
    the same codebase runs correctly on both Testnet and Mainnet without any
    source-code changes.

    Class-level SUPPORTED_TOKENS is built once at class definition time using
    the constants resolved in ``constants.py``.

    Rounding Policy:
    All financial calculations adopt the ``ROUND_HALF_UP`` rounding mode.
    """

    SUPPORTED_TOKENS: Dict[str, CollateralConfig] = {
        "XLM": CollateralConfig(
            symbol="XLM",
            asset_id=XLM_ASSET_ID,          # always "native"
            decimals=7,
            collateral_factor=Decimal("0.80"),
            borrow_factor=Decimal("1"),
            liquidation_threshold=Decimal("0.85"),
            liquidation_bonus=Decimal("0.05"),
            is_active=True,
        ),
        "USDC": CollateralConfig(
            symbol="USDC",
            asset_id=USDC_ASSET_ID,          # resolved from env / network default
            decimals=7,
            collateral_factor=Decimal("0.85"),
            borrow_factor=Decimal("1"),
            liquidation_threshold=Decimal("0.90"),
            liquidation_bonus=Decimal("0.04"),
            is_active=True,
        ),
        "ETH": CollateralConfig(
            symbol="ETH",
            asset_id=ETH_ASSET_ID,           # resolved from env / network default
            decimals=7,
            collateral_factor=Decimal("0.75"),
            borrow_factor=Decimal("1"),
            liquidation_threshold=Decimal("0.82"),
            liquidation_bonus=Decimal("0.06"),
            is_active=IS_MAINNET,            # ETH disabled on Testnet until liquidity confirmed
        ),
    }

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        """Apply ROUND_HALF_UP."""
        return value.quantize(_PRECISION, rounding=ROUND_HALF_UP)

    # ------------------------------------------------------------------
    # Configuration queries
    # ------------------------------------------------------------------

    @classmethod
    def get_collateral_config(cls, token_symbol: str) -> CollateralConfig:
        """
        Return the ``CollateralConfig`` for *token_symbol*.

        Raises:
            ValueError: Token is unknown or inactive.
        """
        config = cls.SUPPORTED_TOKENS.get(token_symbol)
        if config is None:
            raise ValueError(
                f"Unsupported collateral token '{token_symbol}'. "
                f"Supported: {cls.get_available_tokens()}"
            )
        if not config.is_active:
            raise ValueError(
                f"Token '{token_symbol}' is configured but not active on this network."
            )
        return config

    @classmethod
    def get_available_tokens(cls, active_only: bool = True) -> List[str]:
        """
        Return token symbols that are available for use.

        Args:
            active_only: When True (default), returns only tokens where
                         ``CollateralConfig.is_active`` is True.
        """
        return [
            symbol
            for symbol, cfg in cls.SUPPORTED_TOKENS.items()
            if (cfg.is_active or not active_only)
        ]

    @classmethod
    def get_asset_id(cls, token_symbol: str) -> str:
        """
        Convenience accessor returning the canonical Stellar asset identifier
        (``"native"`` or ``"CODE:ISSUER"``) for *token_symbol*.
        """
        return cls.get_collateral_config(token_symbol).asset_id

    # ------------------------------------------------------------------
    # Core financial calculations
    # ------------------------------------------------------------------

    @classmethod
    def calculate_health_ratio(
        cls,
        collateral_value: Decimal,
        borrowed_value: Decimal,
        collateral_factor: Decimal,
    ) -> Decimal:
        """
        Compute the health ratio for a position.

        ``health_ratio = (collateral_value × collateral_factor) / borrowed_value``

        A ratio **> 1** is healthy. A ratio **<= 1** is subject to liquidation.
        Returns ``_INFINITE_HEALTH`` when there is no outstanding debt.

        Raises:
            ValueError: Any argument is negative or ``collateral_factor`` is
                        outside [0, 1].
        """
        cls._validate_non_negative(collateral_value, "collateral_value")
        cls._validate_non_negative(borrowed_value, "borrowed_value")
        cls._validate_factor(collateral_factor, "collateral_factor")

        if borrowed_value == _ZERO:
            return _INFINITE_HEALTH

        return cls._round((collateral_value * collateral_factor) / borrowed_value)

    @classmethod
    def calculate_liquidation_price(
        cls,
        borrowed_value: Decimal,
        collateral_amount: Decimal,
        liquidation_threshold: Decimal,
    ) -> Decimal:
        """
        Compute the asset price at which a position becomes liquidatable.

        ``liquidation_price = borrowed_value / (collateral_amount × liquidation_threshold)``

        Returns ``Decimal("0")`` when there is no collateral (nothing to liquidate).

        Raises:
            ValueError: Any argument is negative or ``liquidation_threshold``
                        is outside (0, 1].
        """
        cls._validate_non_negative(borrowed_value, "borrowed_value")
        cls._validate_non_negative(collateral_amount, "collateral_amount")
        cls._validate_factor(liquidation_threshold, "liquidation_threshold", allow_zero=False)

        if collateral_amount == _ZERO:
            return _ZERO

        return cls._round(borrowed_value / (collateral_amount * liquidation_threshold))

    @classmethod
    def calculate_max_leverage(
        cls,
        collateral_factor: Decimal,
        borrow_factor: Decimal,
    ) -> Decimal:
        """
        Compute the maximum achievable leverage.

        ``max_leverage = 1 / (1 − collateral_factor × borrow_factor)``

        Returns ``Decimal("1")`` (no leverage) when ``collateral_factor`` is zero.

        Raises:
            ValueError: Effective factor >= 1 (would imply infinite leverage).
        """
        cls._validate_factor(collateral_factor, "collateral_factor")
        cls._validate_non_negative(borrow_factor, "borrow_factor")

        if collateral_factor == _ZERO:
            return _ONE

        effective_factor = collateral_factor * borrow_factor
        denominator = _ONE - effective_factor

        if denominator <= _ZERO:
            raise ValueError(
                f"collateral_factor × borrow_factor = {effective_factor} implies "
                "infinite leverage — check your configuration."
            )

        return cls._round(_ONE / denominator)

    @classmethod
    def calculate_max_withdrawable(
        cls,
        collateral_value: Decimal,
        borrowed_value: Decimal,
        collateral_factor: Decimal,
    ) -> Decimal:
        """
        Compute the maximum collateral value that can be withdrawn while
        keeping the position healthy (health ratio > 1).

        ``max_withdrawable = collateral_value − (borrowed_value / collateral_factor)``

        Returns ``Decimal("0")`` if already at or below the safe threshold.
        """
        cls._validate_non_negative(collateral_value, "collateral_value")
        cls._validate_non_negative(borrowed_value, "borrowed_value")
        cls._validate_factor(collateral_factor, "collateral_factor", allow_zero=False)

        min_required = borrowed_value / collateral_factor
        withdrawable = collateral_value - min_required
        return cls._round(max(_ZERO, withdrawable))

    @classmethod
    def calculate_max_borrowable(
        cls,
        collateral_value: Decimal,
        borrowed_value: Decimal,
        collateral_factor: Decimal,
    ) -> Decimal:
        """
        Compute the additional amount that can be borrowed without breaching
        the collateral factor.

        ``max_borrowable = (collateral_value × collateral_factor) − borrowed_value``

        Returns ``Decimal("0")`` if already at or above the borrow cap.
        """
        cls._validate_non_negative(collateral_value, "collateral_value")
        cls._validate_non_negative(borrowed_value, "borrowed_value")
        cls._validate_factor(collateral_factor, "collateral_factor")

        borrow_cap = collateral_value * collateral_factor
        return cls._round(max(_ZERO, borrow_cap - borrowed_value))

    # ------------------------------------------------------------------
    # Higher-level helpers
    # ------------------------------------------------------------------

    @classmethod
    def evaluate_position(
        cls,
        token_symbol: str,
        collateral_amount: Decimal,
        collateral_price: Decimal,
        borrowed_value: Decimal,
    ) -> PositionHealth:
        """
        Produce a complete ``PositionHealth`` snapshot for a single position.

        Args:
            token_symbol:      Collateral token (e.g. ``"XLM"``).
            collateral_amount: Raw collateral units held.
            collateral_price:  Current market price per unit in the quote currency.
            borrowed_value:    Total outstanding borrow in the quote currency.

        Returns:
            A ``PositionHealth`` dataclass with all metrics pre-computed.
        """
        config = cls.get_collateral_config(token_symbol)
        collateral_value = collateral_amount * collateral_price

        health_ratio = cls.calculate_health_ratio(
            collateral_value, borrowed_value, config.collateral_factor
        )
        liquidation_price = cls.calculate_liquidation_price(
            borrowed_value, collateral_amount, config.liquidation_threshold
        )
        max_withdrawable = cls.calculate_max_withdrawable(
            collateral_value, borrowed_value, config.collateral_factor
        )
        max_borrowable = cls.calculate_max_borrowable(
            collateral_value, borrowed_value, config.collateral_factor
        )

        return PositionHealth(
            total_collateral_value=collateral_value,
            total_borrow_value=borrowed_value,
            health_ratio=health_ratio,
            liquidation_price=liquidation_price,
            is_underwater=cls.is_liquidatable(health_ratio),
            max_withdrawable=max_withdrawable,
            max_borrowable=max_borrowable,
        )

    @classmethod
    def is_liquidatable(cls, health_ratio: Decimal) -> bool:
        """Return ``True`` when *health_ratio* is at or below 1 (liquidation zone)."""
        return health_ratio <= _ONE

    # ------------------------------------------------------------------
    # Internal validators
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_non_negative(value: Decimal, name: str) -> None:
        if value < _ZERO:
            raise ValueError(f"'{name}' must be non-negative, got {value}.")

    @staticmethod
    def _validate_factor(
        value: Decimal,
        name: str,
        allow_zero: bool = True,
    ) -> None:
        lower = _ZERO if allow_zero else _ZERO
        if value < lower or value > _ONE:
            raise ValueError(
                f"'{name}' must be in [{'0' if allow_zero else '>0'}, 1], got {value}."
            )
        if not allow_zero and value == _ZERO:
            raise ValueError(f"'{name}' must be greater than zero.")