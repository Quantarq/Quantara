"""
Edge-case unit suite for CollateralManager (issue #260).

Covers the following boundary cases specified in the issue:

1. collateral_value == 0  →  health factor returns _INFINITE_HEALTH
2. borrowed_value == 0    →  health factor returns _INFINITE_HEALTH
3. collateral_factor == 1 →  calculate_max_leverage raises ValueError
4. liquidation_threshold == 0  →  calculate_liquidation_price raises ValueError
5. max_withdraw > collateral_value  →  result clamped to 0 (never negative)

Plus additional boundary and guard-rail tests for robustness.
"""

import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# CollateralManager imports from web_app.contract_tools.constants which now
# exposes XLM_ASSET_ID, USDC_ASSET_ID, ETH_ASSET_ID, and IS_MAINNET.
from soroban.adapters.CollateralManager import (
    CollateralManager,
    CollateralConfig,
    PositionHealth,
    _INFINITE_HEALTH,
    _ZERO,
    _ONE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg(
    collateral_factor: str = "0.80",
    liquidation_threshold: str = "0.85",
    borrow_factor: str = "1",
) -> CollateralConfig:
    """Return a minimal CollateralConfig with the given parameters."""
    return CollateralConfig(
        symbol="XLM",
        asset_id="native",
        decimals=7,
        collateral_factor=Decimal(collateral_factor),
        borrow_factor=Decimal(borrow_factor),
        liquidation_threshold=Decimal(liquidation_threshold),
        liquidation_bonus=Decimal("0.05"),
        is_active=True,
    )


# ===========================================================================
# 1. collateral_value == 0  →  health factor is INFINITE (or 0 with debt)
# ===========================================================================


class TestHealthRatioZeroCollateral:
    """When collateral_value is zero, health ratio must be _INFINITE_HEALTH (no debt)."""

    def test_zero_collateral_zero_debt_returns_infinite(self):
        ratio = CollateralManager.calculate_health_ratio(
            collateral_value=_ZERO,
            borrowed_value=_ZERO,
            collateral_factor=Decimal("0.80"),
        )
        assert ratio == _INFINITE_HEALTH

    def test_zero_collateral_nonzero_debt_returns_zero_ratio(self):
        """With no collateral but some debt the position is completely underwater."""
        ratio = CollateralManager.calculate_health_ratio(
            collateral_value=_ZERO,
            borrowed_value=Decimal("100"),
            collateral_factor=Decimal("0.80"),
        )
        # (0 * 0.8) / 100 == 0 — fully underwater
        assert ratio == _ZERO

    def test_zero_collateral_is_liquidatable(self):
        ratio = CollateralManager.calculate_health_ratio(
            collateral_value=_ZERO,
            borrowed_value=Decimal("1"),
            collateral_factor=Decimal("0.80"),
        )
        assert CollateralManager.is_liquidatable(ratio)


# ===========================================================================
# 2. borrowed_value == 0  →  health factor is INFINITE
# ===========================================================================


class TestHealthRatioZeroBorrow:
    """When borrowed_value is zero, health ratio must be _INFINITE_HEALTH."""

    def test_zero_borrow_returns_infinite_health(self):
        ratio = CollateralManager.calculate_health_ratio(
            collateral_value=Decimal("1000"),
            borrowed_value=_ZERO,
            collateral_factor=Decimal("0.80"),
        )
        assert ratio == _INFINITE_HEALTH

    def test_zero_borrow_zero_collateral_returns_infinite_health(self):
        ratio = CollateralManager.calculate_health_ratio(
            collateral_value=_ZERO,
            borrowed_value=_ZERO,
            collateral_factor=Decimal("0.80"),
        )
        assert ratio == _INFINITE_HEALTH

    def test_zero_borrow_not_liquidatable(self):
        ratio = CollateralManager.calculate_health_ratio(
            collateral_value=Decimal("500"),
            borrowed_value=_ZERO,
            collateral_factor=Decimal("0.75"),
        )
        assert not CollateralManager.is_liquidatable(ratio)

    def test_zero_borrow_max_borrowable_is_full_capacity(self):
        """With no existing debt, borrowable = collateral_value * collateral_factor."""
        result = CollateralManager.calculate_max_borrowable(
            collateral_value=Decimal("1000"),
            borrowed_value=_ZERO,
            collateral_factor=Decimal("0.80"),
        )
        assert result == Decimal("800")

    def test_zero_borrow_max_withdrawable_is_full_collateral(self):
        """With no debt, the entire collateral can theoretically be withdrawn."""
        result = CollateralManager.calculate_max_withdrawable(
            collateral_value=Decimal("1000"),
            borrowed_value=_ZERO,
            collateral_factor=Decimal("0.80"),
        )
        # min_required = 0 / 0.80 = 0; withdrawable = 1000 - 0 = 1000
        assert result == Decimal("1000")


# ===========================================================================
# 3. collateral_factor == 1  →  max_leverage raises ValueError
# ===========================================================================


class TestMaxLeverageAtCollateralFactorOne:
    """
    When collateral_factor * borrow_factor == 1, the geometric series
    diverges — max_leverage is undefined and must raise ValueError.
    """

    def test_collateral_factor_one_borrow_factor_one_raises(self):
        with pytest.raises(ValueError, match="infinite leverage"):
            CollateralManager.calculate_max_leverage(
                collateral_factor=_ONE,
                borrow_factor=_ONE,
            )

    def test_collateral_factor_one_borrow_factor_half_does_not_raise(self):
        """1 * 0.5 = 0.5 < 1 → should NOT raise, returns finite leverage."""
        result = CollateralManager.calculate_max_leverage(
            collateral_factor=_ONE,
            borrow_factor=Decimal("0.5"),
        )
        # 1 / (1 - 0.5) = 2.0
        assert result == Decimal("2")

    def test_collateral_factor_just_below_one_is_valid(self):
        """0.999 * 1 = 0.999 < 1 → very high but finite leverage."""
        result = CollateralManager.calculate_max_leverage(
            collateral_factor=Decimal("0.999"),
            borrow_factor=_ONE,
        )
        assert result > Decimal("100")

    def test_collateral_factor_zero_returns_no_leverage(self):
        """With zero collateral factor, max_leverage is exactly 1."""
        result = CollateralManager.calculate_max_leverage(
            collateral_factor=_ZERO,
            borrow_factor=_ONE,
        )
        assert result == _ONE

    def test_collateral_factor_above_one_raises_validation(self):
        """collateral_factor > 1 is invalid and must raise ValueError."""
        with pytest.raises(ValueError):
            CollateralManager.calculate_max_leverage(
                collateral_factor=Decimal("1.01"),
                borrow_factor=_ONE,
            )


# ===========================================================================
# 4. liquidation_threshold == 0  →  calculate_liquidation_price raises
# ===========================================================================


class TestLiquidationThresholdZero:
    """liquidation_threshold must be > 0; passing zero must raise ValueError."""

    def test_zero_threshold_raises_value_error(self):
        with pytest.raises(ValueError):
            CollateralManager.calculate_liquidation_price(
                borrowed_value=Decimal("500"),
                collateral_amount=Decimal("1000"),
                liquidation_threshold=_ZERO,
            )

    def test_negative_threshold_raises_value_error(self):
        with pytest.raises(ValueError):
            CollateralManager.calculate_liquidation_price(
                borrowed_value=Decimal("500"),
                collateral_amount=Decimal("1000"),
                liquidation_threshold=Decimal("-0.1"),
            )

    def test_threshold_above_one_raises_value_error(self):
        with pytest.raises(ValueError):
            CollateralManager.calculate_liquidation_price(
                borrowed_value=Decimal("500"),
                collateral_amount=Decimal("1000"),
                liquidation_threshold=Decimal("1.01"),
            )

    def test_zero_collateral_with_valid_threshold_returns_zero(self):
        """No collateral → nothing to liquidate, return 0."""
        result = CollateralManager.calculate_liquidation_price(
            borrowed_value=Decimal("500"),
            collateral_amount=_ZERO,
            liquidation_threshold=Decimal("0.85"),
        )
        assert result == _ZERO

    def test_zero_borrow_with_valid_threshold_returns_zero(self):
        """No debt → liquidation price = 0 / (collateral * threshold) = 0."""
        result = CollateralManager.calculate_liquidation_price(
            borrowed_value=_ZERO,
            collateral_amount=Decimal("1000"),
            liquidation_threshold=Decimal("0.85"),
        )
        assert result == _ZERO

    def test_valid_threshold_returns_correct_price(self):
        """Sanity check: borrowed / (collateral * threshold) = expected price."""
        result = CollateralManager.calculate_liquidation_price(
            borrowed_value=Decimal("850"),
            collateral_amount=Decimal("1000"),
            liquidation_threshold=_ONE,
        )
        assert result == Decimal("0.85")


# ===========================================================================
# 5. max_withdraw > collateral_value  →  clamped to 0 (floor, never negative)
# ===========================================================================


class TestMaxWithdrawableClamping:
    """
    calculate_max_withdrawable must never return a negative value.
    When borrowed_value / collateral_factor > collateral_value,
    the result is clamped to Decimal("0").
    """

    def test_over_leveraged_clamped_to_zero(self):
        """Position is over-leveraged: max withdrawable must be 0."""
        result = CollateralManager.calculate_max_withdrawable(
            collateral_value=Decimal("100"),
            borrowed_value=Decimal("500"),  # far exceeds collateral_value * factor
            collateral_factor=Decimal("0.80"),
        )
        assert result == _ZERO

    def test_at_capacity_returns_zero(self):
        """Exactly at the safe boundary: no room to withdraw."""
        # min_required = 80 / 0.8 = 100 == collateral_value → withdrawable = 0
        result = CollateralManager.calculate_max_withdrawable(
            collateral_value=Decimal("100"),
            borrowed_value=Decimal("80"),
            collateral_factor=Decimal("0.80"),
        )
        assert result == _ZERO

    def test_below_capacity_returns_positive(self):
        """Under-leveraged position: some collateral is withdrawable."""
        # min_required = 40 / 0.8 = 50; withdrawable = 100 - 50 = 50
        result = CollateralManager.calculate_max_withdrawable(
            collateral_value=Decimal("100"),
            borrowed_value=Decimal("40"),
            collateral_factor=Decimal("0.80"),
        )
        assert result == Decimal("50")

    def test_zero_borrow_max_withdrawable_equals_full_collateral(self):
        """No debt: the entire collateral value is withdrawable."""
        result = CollateralManager.calculate_max_withdrawable(
            collateral_value=Decimal("1000"),
            borrowed_value=_ZERO,
            collateral_factor=Decimal("0.80"),
        )
        assert result == Decimal("1000")

    def test_result_never_exceeds_collateral_value(self):
        """Invariant: max_withdrawable <= collateral_value always."""
        test_cases = [
            ("0", "0", "0.80"),
            ("1000", "0", "0.80"),
            ("1000", "500", "0.80"),
            ("1000", "800", "0.80"),
            ("1000", "1000", "0.80"),
            ("1000", "2000", "0.80"),
        ]
        for cv, bv, cf in test_cases:
            result = CollateralManager.calculate_max_withdrawable(
                collateral_value=Decimal(cv),
                borrowed_value=Decimal(bv),
                collateral_factor=Decimal(cf),
            )
            assert result <= Decimal(cv), (
                f"max_withdrawable={result} exceeded collateral_value={cv}"
            )
            assert result >= _ZERO, f"max_withdrawable={result} was negative"

    def test_result_never_negative(self):
        """Result is always >= 0 even when borrow massively exceeds collateral."""
        result = CollateralManager.calculate_max_withdrawable(
            collateral_value=Decimal("1"),
            borrowed_value=Decimal("999999"),
            collateral_factor=Decimal("0.80"),
        )
        assert result >= _ZERO


# ===========================================================================
# Negative input guards (_validate_non_negative / _validate_factor)
# ===========================================================================


class TestNegativeInputGuards:
    """All calculation methods must reject negative inputs."""

    def test_health_ratio_negative_collateral_raises(self):
        with pytest.raises(ValueError):
            CollateralManager.calculate_health_ratio(
                collateral_value=Decimal("-1"),
                borrowed_value=Decimal("100"),
                collateral_factor=Decimal("0.80"),
            )

    def test_health_ratio_negative_borrow_raises(self):
        with pytest.raises(ValueError):
            CollateralManager.calculate_health_ratio(
                collateral_value=Decimal("1000"),
                borrowed_value=Decimal("-1"),
                collateral_factor=Decimal("0.80"),
            )

    def test_health_ratio_negative_factor_raises(self):
        with pytest.raises(ValueError):
            CollateralManager.calculate_health_ratio(
                collateral_value=Decimal("1000"),
                borrowed_value=Decimal("100"),
                collateral_factor=Decimal("-0.1"),
            )

    def test_max_borrowable_negative_collateral_raises(self):
        with pytest.raises(ValueError):
            CollateralManager.calculate_max_borrowable(
                collateral_value=Decimal("-100"),
                borrowed_value=_ZERO,
                collateral_factor=Decimal("0.80"),
            )

    def test_liquidation_price_negative_borrow_raises(self):
        with pytest.raises(ValueError):
            CollateralManager.calculate_liquidation_price(
                borrowed_value=Decimal("-100"),
                collateral_amount=Decimal("1000"),
                liquidation_threshold=Decimal("0.85"),
            )


# ===========================================================================
# evaluate_position integration — health snapshot
# ===========================================================================


class TestEvaluatePosition:
    """Smoke tests for the higher-level evaluate_position helper."""

    def test_healthy_position(self):
        health = CollateralManager.evaluate_position(
            token_symbol="XLM",
            collateral_amount=Decimal("1000"),
            collateral_price=Decimal("1"),
            borrowed_value=Decimal("400"),
        )
        assert isinstance(health, PositionHealth)
        assert health.health_ratio > _ONE
        assert not health.is_underwater

    def test_liquidatable_position(self):
        health = CollateralManager.evaluate_position(
            token_symbol="XLM",
            collateral_amount=Decimal("100"),
            collateral_price=Decimal("1"),
            borrowed_value=Decimal("900"),  # far exceeds max LTV
        )
        assert health.is_underwater

    def test_no_borrow_infinite_health(self):
        health = CollateralManager.evaluate_position(
            token_symbol="XLM",
            collateral_amount=Decimal("1000"),
            collateral_price=Decimal("1"),
            borrowed_value=_ZERO,
        )
        assert health.health_ratio == _INFINITE_HEALTH
        assert not health.is_underwater

    def test_unknown_token_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            CollateralManager.evaluate_position(
                token_symbol="UNKNOWN",
                collateral_amount=Decimal("1000"),
                collateral_price=Decimal("1"),
                borrowed_value=_ZERO,
            )
