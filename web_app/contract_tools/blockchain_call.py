import os
import time
from math import floor
from typing import Any, List

import starknet_py.cairo.felt
import starknet_py.hash.selector
import starknet_py.net.client_models
import starknet_py.net.networks
from starknet_py.contract import Contract
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.account.account import Account
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.client_models import Call

from .constants import TokenParams, EKUBO_MAINNET_ADDRESS


class StarknetClient:
    """
    A client to interact with the Starknet blockchain.
    """

    SLEEP_TIME = 10
    POOLS = {
        (TokenParams.ETH.value[0], TokenParams.USDC.value[0]): {
            "token0": TokenParams.ETH.value[0],
            "token1": TokenParams.USDC.value[0],
            "fee": 0x20c49ba5e353f80000000000000000,
            "tick_spacing": 1000,
            "extension": 0
        }
    }

    def __init__(self):
        """
        Initializes the Starknet client with a given node URL.
        """
        node_url = os.getenv("STARKNET_NODE_URL")
        if not node_url:
            raise ValueError("STARKNET_NODE_URL environment variable is not set")

        self.client = FullNodeClient(node_url=node_url)

    @staticmethod
    def _convert_address(addr: str) -> int:
        """
        Converts a hexadecimal address string to an integer.

        :param addr: The address as a hexadecimal string.
        :return: The address as an integer.
        """
        return int(addr, base=16)

    async def _func_call(self, addr: int, selector: str, calldata: List[int]) -> Any:
        """
        Internal method to make a contract call on the Starknet blockchain.

        :param addr: The contract address as an integer.
        :param selector: The name of the function to call.
        :param calldata: A list of integers representing the calldata for the function.
        :return: The response from the contract call.
        """
        call = starknet_py.net.client_models.Call(
            to_addr=addr,
            selector=starknet_py.hash.selector.get_selector_from_name(selector),
            calldata=calldata,
        )
        try:
            res = await self.client.call_contract(call)
        except:
            time.sleep(self.SLEEP_TIME)
            res = await self.client.call_contract(call)
        return res

    def _build_ekubo_pool_key(self, token0: str, token1: str, fee: int, tick_spacing, extension = 0) -> dict:
        """Get ekubo pool key."""
        return self.POOLS.get((token0, token1), {})

    async def _get_pool_price(self, pool_key, is_token1: bool): # TODO move to contract side
        """Calculate Ekubo pool price"""
        ekubo_contract = await Contract.from_address(EKUBO_MAINNET_ADDRESS, provider=self.client)
        price_data = await ekubo_contract.functions["get_pool_price"].call(pool_key)

        token_0_decimals = await self._func_call(pool_key["token0"], "decimals", [])
        token_1_decimals = await self._func_call(pool_key["token1"], "decimals", [])
        token_0_decimals, token_1_decimals = token_0_decimals[0], token_1_decimals[0]

        price = ((price_data[0]["sqrt_ratio"] / 2**128) ** 2) * (10 ** abs(token_0_decimals - token_1_decimals))
        return (1 / price) * 10**token_0_decimals if is_token1 else price * 10**token_1_decimals

    async def get_balance(
        self, token_addr: str, holder_addr: str, decimals: int = None
    ) -> int:
        """
        Fetches the balance of a holder for a specific token.

        :param token_addr: The token contract address in hexadecimal string format.
        :param holder_addr: The address of the holder in hexadecimal string format.
        :return: The token balance of the holder as an integer.
        """
        token_address_int = self._convert_address(token_addr)
        holder_address_int = self._convert_address(holder_addr)

        res = await self._func_call(
            token_address_int, "balanceOf", [holder_address_int]
        )
        if decimals:
            return round(res[0] / 10**decimals, 6)
        return round(res[0], 6)

    async def get_loop_liquidity_data(
            self, deposit_token: str, amount: int, multiplier: int, wallet_id: str, borrowing_token: str
    ) -> dict:
        """Get data for Spotnet liquidity looping call."""
        deposit_token = getattr(TokenParams, deposit_token).value[0]
        pool_key = self._build_ekubo_pool_key(deposit_token, borrowing_token, 0, 0)
        deposit_token, borrowing_token = self._convert_address(deposit_token), self._convert_address(borrowing_token)
        pool_key["token0"], pool_key["token1"] = deposit_token, borrowing_token
        wallet_id = self._convert_address(wallet_id)
        deposit_data = {"token": deposit_token, "amount": amount, "multiplier": multiplier}

        pool_price = floor(await self._get_pool_price(pool_key, deposit_token == pool_key["token0"]))
        return {
            "caller": wallet_id,
            "pool_price": pool_price,
            "pool_key": pool_key,
            "deposit_data": deposit_data
        }
