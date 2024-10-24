import pytest

from unittest.mock import AsyncMock, MagicMock, patch

from web_app.contract_tools.mixins.deposit import DepositMixin


class TestDepositMixin:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "deposit_token, amount, multiplier, wallet_id, borrowing_token",
        [
            (
                "STRK",
                "10",
                2,
                "0x27994c503bd8c32525fbdaf9d398bdd4e86757988c64581b055a06c5955ea49",
                "STRK",
            ),
        ],
    )
    @patch(
        target="web_app.contract_tools.mixins.deposit.CLIENT.get_loop_liquidity_data",
        new_callable=AsyncMock,
    )
    @patch("web_app.contract_tools.mixins.deposit.TokenParams.get_token_address")
    async def test_get_transaction_data(
        self,
        mock_get_loop_liquidity_data: AsyncMock,
        mock_get_token_address: MagicMock,
        deposit_token: str,
        amount: str,
        multiplier: int,
        wallet_id: str,
        borrowing_token: str,
    ) -> None: ...

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "supply_token",
        [
            ("STRK",),
        ],
    )
    @patch(
        target="web_app.contract_tools.mixins.deposit.CLIENT.get_repay_data",
        new_callable=AsyncMock,
    )
    @patch("web_app.contract_tools.mixins.deposit.TokenParams.get_token_address")
    async def test_get_repay_data(
        self,
        mock_get_relay_data: AsyncMock,
        mock_get_token_address: MagicMock,
        supply_token: str,
    ) -> None: ...
