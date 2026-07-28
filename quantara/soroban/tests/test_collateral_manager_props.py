"""
quantara/soroban/tests/test_collateral_manager_props.py

Property-based tests for CollateralManager using Hypothesis.
"""

from decimal import Decimal
import pytest
from hypothesis import given, settings, strategies as st
from quantara.soroban.adapters.CollateralManager import CollateralManager

# Setup strategies as specified in the issue:
# collateral_value ∈ [0, 1e9]
# borrowed_value ∈ [0, 1e9]
# liquidation_threshold ∈ (0, 1]

decimal_val_strat = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("1000000000"),  # 1e9
    places=7
)

decimal_threshold_strat = st.decimals(
    min_value=Decimal("0.0000001"),  # exclude 0
    max_value=Decimal("1.0"),
    places=7
)

decimal_factor_strat = st.decimals(
    min_value=Decimal("0.0"),
    max_value=Decimal("1.0"),
    places=7
)


@given(
    collateral_value=decimal_val_strat,
    borrowed_value=decimal_val_strat,
    collateral_factor=decimal_factor_strat
)
@settings(max_examples=1000)
def test_calculate_health_ratio_properties(collateral_value, borrowed_value, collateral_factor):
    """Test health ratio calculations and their invariants."""
    health_ratio = CollateralManager.calculate_health_ratio(
        collateral_value, borrowed_value, collateral_factor
    )
    
    assert health_ratio >= Decimal("0")
    
    if borrowed_value == Decimal("0"):
        # No debt implies infinite health sentinel
        assert health_ratio == Decimal("999999")
    else:
        expected = (collateral_value * collateral_factor) / borrowed_value
        assert health_ratio == expected


@given(
    borrowed_value=decimal_val_strat,
    collateral_amount=decimal_val_strat,
    liquidation_threshold=decimal_threshold_strat
)
@settings(max_examples=1000)
def test_calculate_liquidation_price_properties(borrowed_value, collateral_amount, liquidation_threshold):
    """Test liquidation price calculations and their invariants."""
    liq_price = CollateralManager.calculate_liquidation_price(
        borrowed_value, collateral_amount, liquidation_threshold
    )
    
    assert liq_price >= Decimal("0")
    
    if collateral_amount == Decimal("0"):
        assert liq_price == Decimal("0")
    else:
        expected = borrowed_value / (collateral_amount * liquidation_threshold)
        assert liq_price == expected
        
        # If asset price is exactly liquidation price, then the health ratio calculated
        # using liquidation_threshold as the collateral factor must be exactly 1
        if borrowed_value > Decimal("0"):
            collateral_value_at_liq = collateral_amount * liq_price
            health_at_liq = CollateralManager.calculate_health_ratio(
                collateral_value_at_liq, borrowed_value, liquidation_threshold
            )
            assert abs(health_at_liq - Decimal("1")) < Decimal("1e-9")


@given(
    collateral_value=decimal_val_strat,
    borrowed_value=decimal_val_strat,
    collateral_factor=st.decimals(min_value=Decimal("0.0000001"), max_value=Decimal("1.0"), places=7)
)
@settings(max_examples=1000)
def test_calculate_max_withdrawable_properties(collateral_value, borrowed_value, collateral_factor):
    """Test max withdrawable collateral calculations and invariants."""
    max_withdrawable = CollateralManager.calculate_max_withdrawable(
        collateral_value, borrowed_value, collateral_factor
    )
    
    assert max_withdrawable >= Decimal("0")
    
    min_required = borrowed_value / collateral_factor
    if collateral_value >= min_required:
        assert max_withdrawable == collateral_value - min_required
    else:
        assert max_withdrawable == Decimal("0")


@given(
    collateral_value=decimal_val_strat,
    borrowed_value=decimal_val_strat,
    collateral_factor=decimal_factor_strat
)
@settings(max_examples=1000)
def test_calculate_max_borrowable_properties(collateral_value, borrowed_value, collateral_factor):
    """Test max borrowable calculations and invariants."""
    max_borrow = CollateralManager.calculate_max_borrowable(
        collateral_value, borrowed_value, collateral_factor
    )
    
    assert max_borrow >= Decimal("0")
    
    borrow_cap = collateral_value * collateral_factor
    if borrow_cap >= borrowed_value:
        assert max_borrow == borrow_cap - borrowed_value
    else:
        assert max_borrow == Decimal("0")


@given(
    collateral_value=decimal_val_strat,
    borrowed_value=decimal_val_strat,
    collateral_factor=st.decimals(min_value=Decimal("0.0000001"), max_value=Decimal("1.0"), places=7)
)
@settings(max_examples=1000)
def test_interrelated_properties(collateral_value, borrowed_value, collateral_factor):
    """Test interrelated properties between health ratio, borrowable, and withdrawable limits."""
    health_ratio = CollateralManager.calculate_health_ratio(
        collateral_value, borrowed_value, collateral_factor
    )
    max_borrow = CollateralManager.calculate_max_borrowable(
        collateral_value, borrowed_value, collateral_factor
    )
    max_withdrawable = CollateralManager.calculate_max_withdrawable(
        collateral_value, borrowed_value, collateral_factor
    )
    
    # If health_ratio <= 1, then max_borrowable and max_withdrawable must be exactly 0
    if health_ratio <= Decimal("1"):
        assert max_borrow == Decimal("0")
        assert max_withdrawable == Decimal("0")
        
    # If health_ratio > 1 and there is active debt, both max_borrowable and max_withdrawable must be > 0
    if health_ratio > Decimal("1") and borrowed_value > Decimal("0"):
        assert max_borrow > Decimal("0")
        assert max_withdrawable > Decimal("0")
