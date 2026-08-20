import pytest
from quantara.soroban.adapters import (
    AMMAdapterFactory,
    LendingAdapterFactory,
    SoroswapAMMAdapter,
    BlendLendingAdapter,
)
from quantara.soroban.adapters._register import register_adapters


def test_factory_registration_and_idempotency() -> None:
    """Test that adapter registration is populated and idempotent."""
    # Test registration idempotency
    register_adapters()
    register_adapters()

    # Test AMM Factory create
    amm_adapter = AMMAdapterFactory.create("soroswap")
    assert isinstance(amm_adapter, SoroswapAMMAdapter)

    # Test Lending Factory create
    lending_adapter = LendingAdapterFactory.create("blend")
    assert isinstance(lending_adapter, BlendLendingAdapter)


def test_unknown_adapter_raises() -> None:
    """Test that unknown adapter names raise ValueError with available names."""
    with pytest.raises(ValueError, match="Unknown AMM adapter: invalid"):
        AMMAdapterFactory.create("invalid")

    with pytest.raises(ValueError, match="Unknown lending adapter: invalid"):
        LendingAdapterFactory.create("invalid")
