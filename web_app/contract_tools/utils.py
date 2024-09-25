from typing import Dict
from web_app.contract_tools.constants import TokenParams, SPOTNET_CORE_ADDRESS
from web_app.contract_tools.blockchain_call import StarknetClient

CLIENT = StarknetClient()

class DashboardMixin:
    """
    Mixin class for dashboard related methods.
    """
    @classmethod
    async def get_wallet_balances(cls, holder_address: str) -> Dict[str, str]:
        """
        Get the wallet balances for the given holder address.
        :param holder_address: holder address
        :return: Returns the wallet balances for the given holder address.
        """
        wallet_balances = {}
        for token in TokenParams:
            token_address, decimals = token.value
            balance = await CLIENT.get_balance(
                token_addr=token_address, holder_addr=holder_address, decimals=decimals
            )
            wallet_balances[token.name] = balance
        return wallet_balances


class DepositMixin:

    @classmethod
    async def get_transaction_data(
            cls, deposit_token: str, amount: int, multiplier: int, wallet_id: str, borrowing_token: str
    ):
        approve_data = {
            "to_address": int(deposit_token, 16), "spender": int(SPOTNET_CORE_ADDRESS, 16), "amount": amount
        }
        loop_liquidity_data = await CLIENT.get_loop_liquidity_data(
            deposit_token, amount, multiplier, wallet_id, borrowing_token
        )
        return [approve_data, loop_liquidity_data]
