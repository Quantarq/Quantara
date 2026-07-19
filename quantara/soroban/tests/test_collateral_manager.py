import sys
from unittest.mock import MagicMock

# Mock the constants module before importing CollateralManager
mock_constants = MagicMock()
mock_constants.ETH_ASSET_ID = "ETH"
mock_constants.USDC_ASSET_ID = "USDC"
mock_constants.XLM_ASSET_ID = "native"
mock_constants.IS_MAINNET = False
sys.modules['web_app.contract_tools.constants'] = mock_constants

import pytest
from decimal import Decimal, ROUND_HALF_UP
from hypothesis import given, strategies as st
from soroban.adapters.CollateralManager import CollateralManager

def test_round_half_up_logic():
    # Test cases for ROUND_HALF_UP
    # 0.5 -> 1, 0.4 -> 0
    # The _round method uses 10 decimal places precision: 0.0000000001
    # So 0.12345678905 -> 0.1234567891
    # 0.12345678904 -> 0.1234567890
    
    assert CollateralManager._round(Decimal("0.12345678905")) == Decimal("0.1234567891")
    assert CollateralManager._round(Decimal("0.12345678904")) == Decimal("0.1234567890")

@given(
    collateral_value=st.decimals(min_value=0, max_value=1000000, places=5),
    borrowed_value=st.decimals(min_value=0.00001, max_value=1000000, places=5),
    collateral_factor=st.decimals(min_value=0, max_value=1, places=5)
)
def test_calculate_health_ratio_property(collateral_value, borrowed_value, collateral_factor):
    result = CollateralManager.calculate_health_ratio(collateral_value, borrowed_value, collateral_factor)
    assert isinstance(result, Decimal)
    # Check if the result is rounded to 10 decimal places
    # The result should have at most 10 decimal places
    assert result.as_tuple().exponent >= -10

@given(
    borrowed_value=st.decimals(min_value=0, max_value=1000000, places=5),
    collateral_amount=st.decimals(min_value=0.00001, max_value=1000000, places=5),
    liquidation_threshold=st.decimals(min_value=0.00001, max_value=1, places=5)
)
def test_calculate_liquidation_price_property(borrowed_value, collateral_amount, liquidation_threshold):
    result = CollateralManager.calculate_liquidation_price(borrowed_value, collateral_amount, liquidation_threshold)
    assert isinstance(result, Decimal)
    assert result.as_tuple().exponent >= -10
