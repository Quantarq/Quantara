"""
Tests for quantara.soroban.adapters.blend_adapter.

These tests use a mocked transport and never touch the network.  They
validate the honest-failure contract introduced for issue #410:

- write methods return the real transaction hash from the RPC response
- a failed RPC call raises ``AdapterRpcError`` instead of returning a
  fabricated hash
- a response without a transaction hash raises instead of fabricating one
- read methods raise ``AdapterRpcError`` instead of returning simulated
  reserve/user-position data
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

import pytest
from pytest_mock import MockerFixture

from quantara.soroban.adapters import BlendLendingAdapter
from quantara.soroban.adapters.errors import AdapterRpcError


@pytest.fixture()
def adapter(mocker: MockerFixture) -> BlendLendingAdapter:
    adapter = BlendLendingAdapter(
        blend_contract_id="CD7K53OKK6C3R3D4G7O6Q7J5Y6T7E4W3Q2A1Z9X8C7V6B5N4M3L2K1J0H9G8F7",
    )
    mock_session = mocker.AsyncMock()
    mock_resp = mocker.AsyncMock()
    mock_resp.status = 200
    mock_resp.json = mocker.AsyncMock(return_value={"result": {"ok": True}})
    mock_resp.__aenter__ = mocker.AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = mocker.AsyncMock(return_value=False)
    mock_session.post = mocker.Mock(return_value=mock_resp)
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=False)
    mocker.patch.object(adapter, "_get_session", return_value=mock_session)
    return adapter


def _ok_result(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {"ok": True, "tx_hash": "0xabc123"}
    base.update(overrides)
    return base


class TestDeposit:
    @pytest.mark.asyncio
    async def test_deposit_returns_hash_from_response(
        self, adapter: BlendLendingAdapter, mocker: MockerFixture
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value=_ok_result(tx_hash="0xrealhash123")
        )
        tx_hash = await adapter.deposit("GABCDEF123456", "XLM", Decimal("100"))
        assert tx_hash == "0xrealhash123"

    @pytest.mark.asyncio
    async def test_deposit_rpc_failure_raises(
        self, adapter: BlendLendingAdapter, mocker: MockerFixture
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("RPC down")
        )
        with pytest.raises(AdapterRpcError, match="deposit failed"):
            await adapter.deposit("GABCDEF123456", "XLM", Decimal("100"))

    @pytest.mark.asyncio
    async def test_deposit_without_hash_raises(
        self, adapter: BlendLendingAdapter, mocker: MockerFixture
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value={"ok": True}
        )
        with pytest.raises(
            AdapterRpcError, match="without returning a transaction hash"
        ):
            await adapter.deposit("GABCDEF123456", "XLM", Decimal("100"))

    @pytest.mark.asyncio
    async def test_identical_deposits_return_response_hashes(
        self, adapter: BlendLendingAdapter, mocker: MockerFixture
    ) -> None:
        """Two identical deposits must not produce a deterministic colliding hash."""
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            side_effect=[
                _ok_result(tx_hash="0xhash-one"),
                _ok_result(tx_hash="0xhash-two"),
            ]
        )
        first = await adapter.deposit("GABCDEF123456", "XLM", Decimal("100"))
        second = await adapter.deposit("GABCDEF123456", "XLM", Decimal("100"))
        assert first == "0xhash-one"
        assert second == "0xhash-two"
        assert first != second


class TestWithdrawBorrowRepay:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method, kwargs, params",
        [
            (
                "withdraw",
                {"amount": Decimal("10")},
                {
                    "user": "GABCDEF123456",
                    "token": "native",
                    "amount": 100000000,
                    "max": False,
                },
            ),
            (
                "borrow",
                {"amount": Decimal("5")},
                {
                    "user": "GABCDEF123456",
                    "token": "USDC:GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGCS3FOGTICSJCWV5X2HGM",
                    "amount": 50000000,
                },
            ),
            (
                "repay",
                {"amount": Decimal("5")},
                {
                    "user": "GABCDEF123456",
                    "token": "USDC:GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGCS3FOGTICSJCWV5X2HGM",
                    "amount": 50000000,
                },
            ),
            ("enable_collateral", {}, {"user": "GABCDEF123456", "token": "native"}),
            ("disable_collateral", {}, {"user": "GABCDEF123456", "token": "native"}),
        ],
    )
    async def test_success_returns_response_hash(
        self,
        adapter: BlendLendingAdapter,
        mocker: MockerFixture,
        method: str,
        kwargs: Dict[str, Any],
        params: Dict[str, Any],
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value=_ok_result(tx_hash=f"0x{method}")
        )
        tx_hash = await getattr(adapter, method)(
            "GABCDEF123456", params["token"], **kwargs
        )
        assert tx_hash == f"0x{method}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method, kwargs, token",
        [
            ("withdraw", {"amount": Decimal("10")}, "XLM"),
            ("borrow", {"amount": Decimal("5")}, "USDC"),
            ("repay", {"amount": Decimal("5")}, "USDC"),
            ("enable_collateral", {}, "XLM"),
            ("disable_collateral", {}, "XLM"),
        ],
    )
    async def test_rpc_failure_raises(
        self,
        adapter: BlendLendingAdapter,
        mocker: MockerFixture,
        method: str,
        kwargs: Dict[str, Any],
        token: str,
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("network error")
        )
        with pytest.raises(AdapterRpcError):
            await getattr(adapter, method)("GABCDEF123456", token, **kwargs)


class TestReads:
    @pytest.mark.asyncio
    async def test_get_reserve_data_failure_raises(
        self, adapter: BlendLendingAdapter, mocker: MockerFixture
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("RPC down")
        )
        with pytest.raises(AdapterRpcError, match="reserve data"):
            await adapter.get_reserve_data("XLM")

    @pytest.mark.asyncio
    async def test_get_reserve_data_success(
        self, adapter: BlendLendingAdapter, mocker: MockerFixture
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value={"supply_apy": "0.05", "total_supply": "10000000"}
        )
        reserve = await adapter.get_reserve_data("XLM")
        assert reserve.supply_apy == Decimal("0.05")
        assert reserve.total_supply == Decimal("1")

    @pytest.mark.asyncio
    async def test_get_user_position_failure_raises(
        self, adapter: BlendLendingAdapter, mocker: MockerFixture
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("RPC down")
        )
        with pytest.raises(AdapterRpcError, match="user position"):
            await adapter.get_user_position("GABCDEF123456", "XLM")

    @pytest.mark.asyncio
    async def test_get_user_position_success(
        self, adapter: BlendLendingAdapter, mocker: MockerFixture
    ) -> None:
        adapter._soroban_call = mocker.AsyncMock(  # type: ignore[method-assign]
            return_value={"supplied": "10000000", "borrowed": "5000000"}
        )
        position = await adapter.get_user_position("GABCDEF123456", "XLM")
        assert position.supplied_amount == Decimal("1")
        assert position.borrowed_amount == Decimal("0.5")
