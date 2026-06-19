"""
This module contains constants for the Stellar-based Quantara protocol.

Defines token configurations, multipliers, and network asset identifiers
used throughout the contract interaction layer.
"""

from decimal import Decimal
from dataclasses import dataclass
from typing import Iterator
import os

# ------------------------------------------------------------------ #
#  Stellar ecosystem addresses
# ------------------------------------------------------------------ #

MULTIPLIER_POWER = 99

XLM = "XLM"
USDC = "USDC"
ETH = "ETH"

# Stellar asset codes (non-native assets require an issuer)
# "native" is the shorthand for XLM on Stellar
XLM_ASSET_CODE = "native"
USDC_ASSET_CODE = "USDC"
# Read issuer from environment for flexibility between networks. Default to
# a known testnet USDC issuer so testnet works out-of-the-box. To use
# mainnet, set the `USDC_ASSET_ISSUER` environment variable to the
# mainnet issuer (e.g. Circle's mainnet issuer).
USDC_ASSET_ISSUER = os.getenv(
    "USDC_ASSET_ISSUER",
    "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NOJ4VBH6THS2G2V",
)

EXAMPLE_ASSET_ISSUER = (
    "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NO2KJ4DDG5T4GD"
    # Testnet USDC issuer – replace for mainnet
)


@dataclass(frozen=True)
class TokenConfig:
    """
    Configuration for a Stellar asset used by the Quantara protocol.
    """

    address: str  # Stellar asset code ("native" or issuer-generated code)
    name: str
    decimals: Decimal
    asset_code: str  # "native" for XLM, e.g. "USDC" for Circle USDC
    asset_issuer: str  # Issuer public key (empty for native/XLM)
    collateral_factor: Decimal = Decimal("0.0")
    borrow_factor: Decimal = Decimal("0.0")


@dataclass(frozen=True)
class TokenMultipliers:
    """
    Predefined multipliers for supported tokens.
    """

    XLM: float = 4.6
    USDC: float = 5.0
    ETH: float = 3.0


class TokenParams:
    """
    Token configurations for the Stellar-based Quantara protocol.
    """

    XLM = TokenConfig(
        name=XLM,
        address=XLM_ASSET_CODE,
        decimals=Decimal("7"),
        asset_code=XLM_ASSET_CODE,
        asset_issuer="",
        collateral_factor=Decimal("0.80"),
        borrow_factor=Decimal("1"),
    )
    USDC = TokenConfig(
        name=USDC,
        address=f"{USDC_ASSET_CODE}:{USDC_ASSET_ISSUER}",
        decimals=Decimal("7"),
        asset_code=USDC_ASSET_CODE,
        asset_issuer=USDC_ASSET_ISSUER,
        collateral_factor=Decimal("0.85"),
        borrow_factor=Decimal("1"),
    )
    ETH = TokenConfig(
        name=ETH,
        address="ETH",
        decimals=Decimal("7"),
        asset_code="ETH",
        asset_issuer=EXAMPLE_ASSET_ISSUER,
        collateral_factor=Decimal("0.80"),
        borrow_factor=Decimal("1"),
    )

    _SUPPORTED_TOKENS: tuple[TokenConfig, ...] = ()

    @classmethod
    def tokens(cls) -> Iterator[TokenConfig]:
        """Return an iterator over all supported token configurations."""
        if cls._SUPPORTED_TOKENS:
            return iter(cls._SUPPORTED_TOKENS)
        return iter([cls.XLM, cls.USDC, cls.ETH])

    @classmethod
    def get_token_address(cls, token_name: str) -> str:
        """
        Get the asset identifier for a token name.

        For non-native assets returns "asset_code:issuer".
        """
        for token in cls.tokens():
            if token.name == token_name:
                return token.address
        raise ValueError(f"Token {token_name} not found")

    @classmethod
    def get_borrow_factor(cls, token_identifier: str) -> Decimal:
        for token in cls.tokens():
            if token.address == token_identifier or token.name == token_identifier:
                return token.borrow_factor
        raise ValueError(f"Token {token_identifier} not found")

    @classmethod
    def get_token_decimals(cls, token_identifier: str) -> int:
        """Return the decimals for a token by name or address prefix."""
        for token in cls.tokens():
            if (
                token.address == token_identifier
                or token.name == token_identifier
                or token.asset_code == token_identifier
            ):
                return int(token.decimals)
        raise ValueError(f"Token {token_identifier} not found")

    @classmethod
    def get_token_symbol(cls, token_identifier: str) -> str:
        for token in cls.tokens():
            if (
                token.address == token_identifier
                or token.name == token_identifier
                or token.asset_code == token_identifier
            ):
                return token.name
        raise ValueError(f"Token {token_identifier} not found")

    @classmethod
    def get_token_collateral_factor(cls, token_identifier: str) -> Decimal:
        for token in cls.tokens():
            if (
                token.address == token_identifier
                or token.name == token_identifier
            ):
                return token.collateral_factor
        raise ValueError(f"Token {token_identifier} not found")
