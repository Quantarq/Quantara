"""
Tests for issue #412: USDC issuer consistency across the stack.

Every layer — `web_app.contract_tools.constants`, `CollateralManager`, and
the Blend / Soroswap adapter `_TokenResolver`s — must resolve "USDC" to the
same on-chain asset. Before this fix the adapters hardcoded a different
issuer (`GA5ZSE...`) than the canonical env-driven one (`GBBD47...`), so
collateral was valued against one token while debt was quoted against
another.

These tests import the adapters via the `soroban.adapters` namespace path
(the same convention used by `test_collateral_manager_edge_cases.py`).
"""

from soroban.adapters.CollateralManager import CollateralManager
from soroban.adapters.blend_adapter import _TokenResolver as BlendResolver
from soroban.adapters.soroswap_adapter import _TokenResolver as SoroswapResolver
from web_app.contract_tools.constants import (
    USDC_ASSET_CODE,
    USDC_ASSET_ID,
    USDC_ASSET_ISSUER,
)

# The issuer the adapters hardcoded before this fix.
_DIVERGENT_USDC_ISSUER = "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGCS3FOGTICSJCWV5X2HGM"


def test_constants_define_canonical_usdc_id():
    assert USDC_ASSET_ID == f"{USDC_ASSET_CODE}:{USDC_ASSET_ISSUER}"


def test_collateral_manager_uses_canonical_usdc_id():
    assert CollateralManager.get_asset_id("USDC") == USDC_ASSET_ID


def test_blend_resolver_normalizes_usdc_to_canonical_asset():
    assert BlendResolver.normalize("USDC") == USDC_ASSET_ID
    assert _DIVERGENT_USDC_ISSUER not in BlendResolver._TOKENS["USDC"]["addresses"]


def test_soroswap_resolver_normalizes_usdc_to_canonical_asset():
    assert SoroswapResolver.normalize("USDC") == USDC_ASSET_ID
    assert _DIVERGENT_USDC_ISSUER not in SoroswapResolver._TOKENS["USDC"]["addresses"]


def test_all_layers_resolve_usdc_to_the_same_asset():
    resolved = {
        BlendResolver.normalize("USDC"),
        SoroswapResolver.normalize("USDC"),
        CollateralManager.get_asset_id("USDC"),
        USDC_ASSET_ID,
    }
    assert resolved == {USDC_ASSET_ID}
