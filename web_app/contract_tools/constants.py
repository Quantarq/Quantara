import os
from enum import Enum

EKUBO_MAINNET_ADDRESS: int = 0x00000005dd3d2f4429af886cd1a3b08289dbcea99a294197e9eb43b0e0325b4b

SPOTNET_CORE_ADDRESS = os.getenv('SPOTNET_CORE_ADDRESS')

class TokenParams(Enum):
    """
    Enum class to hold the token addresses for tokens
    """

    ETH: str = (
        "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7",
        18,
    )
    STRK: str = (
        "0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d",
        18,
    )
    USDC: str = (
        "0x053c91253bc9682c04929ca02ed00b3e423f6710d2ee7e0d5ebb06f3ecf368a8",
        6
    )


class ProtocolAddress(Enum):

    zklend: str = "0x04c0a5193d58f74fbace4b74dcf65481e734ed1714121bdc571da345540efa05"
    nostra: str = "0x00c530f2c0aa4c16a0806365b0898499fba372e5df7a7172dc6fe9ba777e8007"
