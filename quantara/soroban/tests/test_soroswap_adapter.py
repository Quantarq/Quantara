"""
Tests for quantara.soroban.adapters.soroswap_adapter.

These tests use a lightweight mock transport and do not hit the network.
They validate:
- Token resolution and scaling
- Pool-key normalisation and reverse-token lookup
- Price computation from synthetic reserves
- Quote derivation from computeConstantProductInvariant
- swap_exact_input / swap_exact_output rejection of bad arguments
- find_best_route on direct and missing pairs
- Adapter factory creation by name
- get_supported_pairs fallback
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pytest
from pytest_mock import MockerFixture

from quantara.soroban.adapters import AMMAdapterFactory, SoroswapAMMAdapter
from quantara.soroban.adapters.AMMAdapter import PoolKey
from quantara.soroban.adapters.soroswap_adapter import _TokenResolver


@pytest.fixture()
def adapter(mocker: MockerFixture) -> SoroswapAMMAdapter:
    adapter = SoroswapAMMAdapter(
        router_contract_id="CABGDIK4SE3376TW2E6YZZV2XZ6OPRJEPRXSNBUVRG6T5GTTNTTZISX2",
    )
    mock_session = mocker.AsyncMock()
    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json = mocker.AsyncMock(return_value={"result": {"ok": True}})
    mock_resp.__aenter__ = mocker.AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = mocker.AsyncMock(return_value=False)
    mock_session.post = mocker.AsyncMock(return_value=mock_resp)
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=False)
    mocker.patch.object(adapter, "_get_session", return_value=mock_session)
    return adapter


def _ok_result(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {"ok": True, "tx_hash": "0xabc123", "amount_out": "100"}
    base.update(overrides)
    return {"result": base}


class TestTokenResolver:
    def test_native_is_normalized(self) -> None:
        assert _TokenResolver.normalize("XLM") == "native"
        assert _TokenResolver.normalize("xlm") == "native"
        assert _TokenResolver.normalize("NATIVE") == "native"

    def test_usdc_is_normalized(self) -> None:
        result = _TokenResolver.normalize("USDC")
        assert "USDC" in result

    def test_decimals_native(self) -> None:
        assert _TokenResolver.decimals("native") == 7
        assert _TokenResolver.decimals("XLM") == 7

    def test_decimals_usdc(self) -> None:
        assert _TokenResolver.decimals("USDC") == 7

    def test_scale_factor_native(self) -> None:
        assert _TokenResolver.scale_factor("XLM") == Decimal("10000000")

    def test_scale_factor_usdc(self) -> None:
        assert _TokenResolver.scale_factor("USDC") == Decimal("10000000")


class TestMakePoolKey:
    def test_pool_key_shape(self) -> None:
        adapter = SoroswapAMMAdapter.__new__(SoroswapAMMAdapter)
        key = adapter._make_pool_key("XLM", "USDC")
        assert key.token_a == "native"
        assert key.token_b.startswith("USDC")
        assert key.fee == 30
        assert key.tick_spacing == 10


class TestGetPoolPrice:
    @pytest.mark.asyncio
    async def test_price_success(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        pool_id = "CAPOOLAAAAABBBBBBBBBCCCCCCCCDDDDDDDD"
        session = await adapter._get_session()
        session.post = mocker.AsyncMock(  # type: ignore[assignment]
            return_value=_mock_contract_response(
                mocker,
                "get_pool",
                {
                    "pool_id": pool_id,
                    "reserves": {"reserve_a": 1000, "reserve_b": 2000},
                    "liquidity": 1000,
                    "sqrt_price": 14142,
                },
            )
        )
        pool_key = adapter._make_pool_key("XLM", "USDC")
        price = await adapter.get_pool_price(pool_key)
        assert price.price_a_to_b == Decimal("2")
        assert price.price_b_to_a == Decimal("0.5")
        assert price.sqrt_price == Decimal("14142")

    @pytest.mark.asyncio
    async def test_price_missing_pool_raises(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        session = await adapter._get_session()
        session.post = mocker.AsyncMock(  # type: ignore[assignment]
            return_value=_mock_contract_response(mocker, "get_pool", _not_found())
        )
        pool_key = adapter._make_pool_key("XLM", "USDC")
        with pytest.raises(ValueError, match="No pool found"):
            await adapter.get_pool_price(pool_key)

    @pytest.mark.asyncio
    async def test_price_zero_reserves_raises(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        session = await adapter._get_session()
        session.post = mocker.AsyncMock(  # type: ignore[assignment]
            return_value=_mock_contract_response(
                mocker,
                "get_pool",
                {"pool_id": "POOL", "reserves": {"reserve_a": 0, "reserve_b": 0}, "liquidity": 0, "sqrt_price": 0},
            )
        )
        pool_key = adapter._make_pool_key("XLM", "USDC")
        with pytest.raises(ValueError, match="zero reserves"):
            await adapter.get_pool_price(pool_key)


class TestGetPoolKey:
    @pytest.mark.asyncio
    async     def test_get_pool_key_success(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        session = await adapter._get_session()
        session.post = mocker.AsyncMock(  # type: ignore[assignment]
            return_value=_mock_contract_response(
                mocker,
                "get_pool",
                {"pool_id": "POOL123", "reserves": {"reserve_a": 1, "reserve_b": 1}, "liquidity": 1, "sqrt_price": 1},
            )
        )
        key = await adapter.get_pool_key("XLM", "USDC", fee=30)
        assert isinstance(key, PoolKey)
        assert key.fee == 30

    @pytest.mark.asyncio
    async def test_get_pool_key_missing_raises(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        session = await adapter._get_session()
        session.post = mocker.AsyncMock(  # type: ignore[assignment]
            return_value=_mock_contract_response(mocker, "get_pool", _not_found())
        )
        with pytest.raises(ValueError, match="No pool found"):
            await adapter.get_pool_key("XLM", "USDC")


class TestGetQuote:
    @pytest.mark.asyncio
    async def test_quote_success(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value={"amount_out": "5000000"}
        )
        result = await adapter.get_quote("XLM", "USDC", Decimal("1"), adapter._make_pool_key("XLM", "USDC"))
        assert result == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_quote_zero_amount_raises(self, adapter: SoroswapAMMAdapter) -> None:
        with pytest.raises(ValueError, match="amount must be positive"):
            await adapter.get_quote("XLM", "USDC", Decimal("0"), adapter._make_pool_key("XLM", "USDC"))

    @pytest.mark.asyncio
    async def test_quote_contract_error_propagates(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("contract boom")
        )
        with pytest.raises(RuntimeError, match="contract boom"):
            await adapter.get_quote("XLM", "USDC", Decimal("1"), adapter._make_pool_key("XLM", "USDC"))


class TestSwapExactInput:
    @pytest.mark.asyncio
    async def test_swap_exact_input_success(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value=_ok_result(amount_out="4000000")
        )
        tx_hash, amount_out = await adapter.swap_exact_input(
            user_address="GABCDEF",
            token_in="XLM",
            token_out="USDC",
            amount_in=Decimal("1"),
            min_amount_out=Decimal("0.3"),
            pool_key=adapter._make_pool_key("XLM", "USDC"),
        )
        assert tx_hash == "0xabc123"
        assert amount_out == Decimal("0.4")

    @pytest.mark.asyncio
    async def test_swap_exact_input_invalid_amount(self, adapter: SoroswapAMMAdapter) -> None:
        with pytest.raises(ValueError, match="amount_in must be positive"):
            await adapter.swap_exact_input(
                "GXXXXX", "XLM", "USDC", Decimal("0"), Decimal("0"), adapter._make_pool_key("XLM", "USDC")
            )

    @pytest.mark.asyncio
    async def test_swap_exact_input_negative_min(self, adapter: SoroswapAMMAdapter) -> None:
        with pytest.raises(ValueError, match="min_amount_out must be non-negative"):
            await adapter.swap_exact_input(
                "GXXXXX", "XLM", "USDC", Decimal("1"), Decimal("-1"), adapter._make_pool_key("XLM", "USDC")
            )


class TestSwapExactOutput:
    @pytest.mark.asyncio
    async def test_swap_exact_output_success(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value=_ok_result(amount_in="2000000")
        )
        tx_hash, amount_in = await adapter.swap_exact_output(
            user_address="GABCDEF",
            token_in="XLM",
            token_out="USDC",
            amount_out=Decimal("0.5"),
            max_amount_in=Decimal("2"),
            pool_key=adapter._make_pool_key("XLM", "USDC"),
        )
        assert tx_hash == "0xabc123"
        assert amount_in == Decimal("0.2")

    @pytest.mark.asyncio
    async def test_swap_exact_output_invalid_amount(self, adapter: SoroswapAMMAdapter) -> None:
        with pytest.raises(ValueError, match="amount_out must be positive"):
            await adapter.swap_exact_output(
                "GXXXXX", "XLM", "USDC", Decimal("0"), Decimal("0"), adapter._make_pool_key("XLM", "USDC")
            )


class TestFindBestRoute:
    @pytest.mark.asyncio
    async def test_find_best_route_direct(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value={"amount_out": "6000000"}
        )
        adapter.get_supported_pairs = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value=[("XLM", "USDC")]
        )
        route = await adapter.find_best_route("XLM", "USDC", Decimal("1"))
        assert route is not None
        assert len(route.pools) == 1

    @pytest.mark.asyncio
    async def test_find_best_route_same_token(self, adapter: SoroswapAMMAdapter) -> None:
        route = await adapter.find_best_route("XLM", "XLM", Decimal("1"))
        assert route is None

    @pytest.mark.asyncio
    async def test_find_best_route_missing(self, adapter: SoroswapAMMAdapter) -> None:
        adapter.get_supported_pairs = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value=[("XLM", "USDC")]
        )
        adapter.get_quote = mocker.AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("no pool")
        )
        result = await adapter.find_best_route("FOO", "BAR", Decimal("1"))
        assert result is None


class TestGetSupportedPairs:
    @pytest.mark.asyncio
    async def test_supported_pairs_from_rpc(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        session = await adapter._get_session()
        session.post = mocker.AsyncMock(  # type: ignore[assignment]
            return_value=_mock_contract_response(
                mocker, "get_supported_pairs", [["XLM", "USDC"], ["XLM", "WETH"]]
            )
        )
        pairs = await adapter.get_supported_pairs()
        assert ("XLM", "USDC") in pairs

    @pytest.mark.asyncio
    async def test_supported_pairs_fallback_on_error(self, adapter: SoroswapAMMAdapter, mocker: MockerFixture) -> None:
        session = await adapter._get_session()
        session.post = mocker.AsyncMock(  # type: ignore[assignment]
            side_effect=aiohttp.ClientError("boom")
        )
        pairs = await adapter.get_supported_pairs()
        assert len(pairs) == 3


class TestFactory:
    def test_create_soroswap(self) -> None:
        adapter = AMMAdapterFactory.create(
            "soroswap",
            router_contract_id="CABGDIK4SE3376TW2E6YZZV2XZ6OPRJEPRXSNBUVRG6T5GTTNTTNTTZISX2",
        )
        assert isinstance(adapter, SoroswapAMMAdapter)

    def test_create_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown AMM adapter"):
            AMMAdapterFactory.create("does-not-exist")
