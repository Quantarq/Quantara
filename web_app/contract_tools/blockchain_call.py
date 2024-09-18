import os
import time
from typing import List, Any
import starknet_py.hash.selector
import starknet_py.net.client_models
import starknet_py.net.networks
import starknet_py.cairo.felt
from starknet_py.net.full_node_client import FullNodeClient


class StarknetClient:
    """
    A client to interact with the Starknet blockchain.
    """
    SLEEP_TIME = 10

    def __init__(self):
        """
        Initializes the Starknet client with a given node URL.

        :param node_url: The URL of the Starknet node to connect to.
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
            calldata=calldata
        )
        try:
            res = await self.client.call_contract(call)
        except:
            time.sleep(self.SLEEP_TIME)
            res = await self.client.call_contract(call)
        return res

    async def get_balance(self, token_addr: str, holder_addr: str) -> int:
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
        return res[0]