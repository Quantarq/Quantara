"""Regression tests for adapter factory registration (issue #418)."""

from quantara.soroban.adapters import AMMAdapterFactory, LendingAdapterFactory
from quantara.soroban.adapters._register import register_adapters


def test_amm_factory_has_soroswap():
    assert "soroswap" in AMMAdapterFactory._adapters


def test_lending_factory_has_blend():
    assert "blend" in LendingAdapterFactory._adapters


def test_register_adapters_is_idempotent():
    register_adapters()
    register_adapters()
