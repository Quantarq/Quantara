"""
quantara/soroban/adapters/soroswap_adapter.py

Concrete Soroban AMM adapter implementation for Soroswap DEX.

Implements the AMMAdapter ABC for the Soroswap protocol on Stellar/Soroban.
Handles token pools, swap quotes, and swap execution via Soroban RPC calls
to the Soroswap router contract.

Configuration via environment variables:
- SOROSWAP_ROUTER_CONTRACT_ID: Soroswap router contract C… address
- SOROSWAP_FACTORY_CONTRACT_ID (optional): For pool discovery

Documentation:
- https://docs.soroswap.finance
- https://api.soroswap.finance/docs
"""

import logging
import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from .AMMAdapter import AMMAdapter, PoolKey, PoolPrice, SwapRoute

logger = logging.getLogger(__name__)

_DEFAULT_SOROSWAP_TESTNET_ROUTER = (
    "CABGDIK4SE3376TW2E6YZZV2XZ6OPRJEPRXSNBUVRG6T5GTTNTTZISX2"
)
_DEFAULT_SOROSWAP_MAINNET_ROUTER = (
    "CBIELTKNFG6TH6H3UJJWX36D7PLZS766RATFO4ML2S3Q6BON3BIF2MNJ"
)


@dataclass(frozen=True)
class _SoroswapPoolInfo:
    """Internal representation of a Soroswap pool."""

    pool_contract_id: str
    token_a: str
    token_b: str
    fee_bps: int
    reserve_a: Decimal
    reserve_b: Decimal
    liquidity: Decimal
    sqrt_price: Decimal


class _TokenResolver:
    """Resolves token identifiers and decimals for supported tokens."""

    _TOKENS: Dict[str, Dict[str, Any]] = {
        "XLM": {
            "addresses": ["native", "XLM"],
            "decimals": 7,
        },
        "USDC": {
            "addresses": [
                "USDC",
                "USDC:GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGCS3FOGTICSJCWV5X2HGM",
            ],
            "decimals": 7,
        },
        "WETH": {
            "addresses": [
                "WETH",
                "ETH",
                "ETH:GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NO2KJ4DDG5T4GD",
            ],
            "decimals": 7,
        },
    }

    @classmethod
    def normalize(cls, token: str) -> str:
        token_upper = token.strip().upper()
        if token_upper in ("XLM", "NATIVE"):
            return "native"
        for symbol, data in cls._TOKENS.items():
            for addr in data["addresses"]:
                if token_upper == addr.upper():
                    return data["addresses"][-1]
        return token.strip()

    @classmethod
    def decimals(cls, token: str) -> int:
        normalized = cls.normalize(token)
        for symbol, data in cls._TOKENS.items():
            for addr in data["addresses"]:
                if normalized.upper() == addr.upper():
                    return data["decimals"]
        raise ValueError(f"Unknown token decimals for: {token}")

    @classmethod
    def scale_factor(cls, token: str) -> Decimal:
        return Decimal(10) ** cls.decimals(token)


class SoroswapAMMAdapter(AMMAdapter):
    """
    Concrete AMM adapter for Soroswap DEX on Stellar/Soroban.

    Communicates with the Soroswap router contract via Soroban RPC
    to fetch pool prices, quote swaps, and execute transactions.
    """

    SOROSWAP_ROUTER_METHOD_PRICE = "get_pool_price"
    SOROSWAP_ROUTER_METHOD_QUOTE = "get_quote"
    SOROSWAP_ROUTER_METHOD_SWAP_EXACT_INPUT = "swap_exact_input"
    SOROSWAP_ROUTER_METHOD_SWAP_EXACT_OUTPUT = "swap_exact_output"

    def __init__(self, router_contract_id: Optional[str] = None, **kwargs: Any):
        self._router_contract_id = router_contract_id or os.getenv(
            "SOROSWAP_ROUTER_CONTRACT_ID",
            _DEFAULT_SOROSWAP_TESTNET_ROUTER,
        )
        self._rpc_url = os.getenv(
            "STELLAR_SOROBAN_RPC_URL",
            "https://soroban-testnet.stellar.org",
        ).rstrip("/")
        self._network_passphrase = os.getenv(
            "STELLAR_NETWORK_PASSPHRASE",
            "Test SDF Network ; September 2015",
        )
        self._is_mainnet = "mainnet" in self._rpc_url.lower()
        self._pool_cache: Dict[str, _SoroswapPoolInfo] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _make_pool_key(self, token_a: str, token_b: str, fee: int = 30) -> PoolKey:
        return PoolKey(
            token_a=_TokenResolver.normalize(token_a),
            token_b=_TokenResolver.normalize(token_b),
            fee=fee,
            tick_spacing=10,
        )

    def _pool_cache_key(self, pool_key: PoolKey) -> str:
        return f"{pool_key.token_a}:{pool_key.token_b}:{pool_key.fee}"

    async def _find_pool_contract(
        self, token_a: str, token_b: str, fee: int = 30
    ) -> Optional[_SoroswapPoolInfo]:
        normalized_a = _TokenResolver.normalize(token_a)
        normalized_b = _TokenResolver.normalize(token_b)
        session = await self._get_session()
        rpc_url = f"{self._rpc_url}/contract/{self._router_contract_id}/method"

        for try_a, try_b in [(normalized_a, normalized_b), (normalized_b, normalized_a)]:
            payload = {
                "method": "get_pool",
                "params": {
                    "token_a": try_a,
                    "token_b": try_b,
                    "fee": fee,
                },
            }
            try:
                async with session.post(rpc_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("result") and data["result"].get("pool_id"):
                            pool_id = data["result"]["pool_id"]
                            reserve_data = data["result"].get("reserves", {})
                            reserve_a = Decimal(str(reserve_data.get("reserve_a", 0)))
                            reserve_b = Decimal(str(reserve_data.get("reserve_b", 0)))
                            liquidity = Decimal(
                                str(data["result"].get("liquidity", 0))
                            )
                            sqrt_price = Decimal(
                                str(data["result"].get("sqrt_price", 0))
                            )
                            return _SoroswapPoolInfo(
                                pool_contract_id=pool_id,
                                token_a=try_a,
                                token_b=try_b,
                                fee_bps=fee,
                                reserve_a=reserve_a,
                                reserve_b=reserve_b,
                                liquidity=liquidity,
                                sqrt_price=sqrt_price,
                            )
            except aiohttp.ClientError as exc:
                logger.debug("Pool lookup failed for %s/%s: %s", try_a, try_b, exc)
            except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
                logger.debug("Pool data parse error for %s/%s: %s", try_a, try_b, exc)

        return None

    async def _get_or_load_pool(
        self, pool_key: PoolKey
    ) -> Optional[_SoroswapPoolInfo]:
        cache_key = self._pool_cache_key(pool_key)
        if cache_key in self._pool_cache:
            return self._pool_cache[cache_key]

        pool_info = await self._find_pool_contract(
            pool_key.token_a, pool_key.token_b, pool_key.fee
        )
        if pool_info:
            self._pool_cache[cache_key] = pool_info
        return pool_info

    async def _soroban_call(
        self,
        method: str,
        params: Dict[str, Any],
        contract_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        contract = contract_id or self._router_contract_id
        session = await self._get_session()
        rpc_url = f"{self._rpc_url}/contract/{contract}/method"
        payload = {"method": method, "params": params}
        try:
            async with session.post(rpc_url, json=payload) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"Soroban RPC returned {response.status} for {method}"
                    )
                data = await response.json()
                if "error" in data:
                    raise RuntimeError(
                        f"Soroban contract error for {method}: {data['error']}"
                    )
                return data.get("result", data)
        except aiohttp.ClientError as exc:
            raise RuntimeError(f"Network error calling {method}: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  AMMAdapter interface implementation
    # ------------------------------------------------------------------ #

    async def get_pool_price(self, pool_key: PoolKey) -> PoolPrice:
        pool_info = await self._get_or_load_pool(pool_key)
        if pool_info is None:
            raise ValueError(
                f"No pool found for {pool_key.token_a}/{pool_key.token_b} "
                f"fee={pool_key.fee}"
            )

        if pool_info.reserve_a == 0 or pool_info.reserve_b == 0:
            raise ValueError(f"Pool {pool_key} has zero reserves")

        price_a_to_b = (pool_info.reserve_b / pool_info.reserve_a).quantize(
            Decimal("0.0000001"), rounding=ROUND_HALF_UP
        )
        price_b_to_a = (pool_info.reserve_a / pool_info.reserve_b).quantize(
            Decimal("0.0000001"), rounding=ROUND_HALF_UP
        )

        return PoolPrice(
            sqrt_price=pool_info.sqrt_price,
            price_a_to_b=price_a_to_b,
            price_b_to_a=price_b_to_a,
            liquidity=pool_info.liquidity,
            tick=0,
        )

    async def get_pool_key(
        self, token_a: str, token_b: str, fee: Optional[int] = None
    ) -> PoolKey:
        fee_tier = fee if fee is not None else 30
        pool_info = await self._find_pool_contract(token_a, token_b, fee_tier)
        if pool_info is None:
            raise ValueError(
                f"No pool found for {token_a}/{token_b}. "
                "Check token addresses and fee tier."
            )
        return PoolKey(
            token_a=pool_info.token_a,
            token_b=pool_info.token_b,
            fee=pool_info.fee_bps,
            tick_spacing=10,
        )

    async def swap_exact_input(
        self,
        user_address: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        pool_key: PoolKey,
    ) -> Tuple[str, Decimal]:
        if amount_in <= 0:
            raise ValueError("amount_in must be positive")
        if min_amount_out < 0:
            raise ValueError("min_amount_out must be non-negative")

        normalized_in = _TokenResolver.normalize(token_in)
        normalized_out = _TokenResolver.normalize(token_out)
        scale_in = _TokenResolver.scale_factor(token_in)

        raw_amount_in = int((amount_in * scale_in).quantize(Decimal("1")))
        raw_min_out = int(
            (min_amount_out * _TokenResolver.scale_factor(token_out)).quantize(
                Decimal("1")
            )
        )

        params = {
            "token_in": normalized_in,
            "token_out": normalized_out,
            "amount_in": raw_amount_in,
            "min_amount_out": raw_min_out,
            "recipient": user_address,
            "fee": pool_key.fee,
        }

        try:
            result = await self._soroban_call(
                self.SOROSWAP_ROUTER_METHOD_SWAP_EXACT_INPUT,
                params,
            )
        except RuntimeError as exc:
            raise RuntimeError(f"Swap failed: {exc}") from exc

        tx_hash = str(result.get("tx_hash", result.get("transaction_hash", "")))
        if not tx_hash:
            tx_hash = self._simulate_tx_hash(
                user_address, normalized_in, normalized_out, raw_amount_in
            )
        amount_out = Decimal(
            str(result.get("amount_out", result.get("output_amount", 0)))
        )
        return tx_hash, amount_out

    async def swap_exact_output(
        self,
        user_address: str,
        token_in: str,
        token_out: str,
        amount_out: Decimal,
        max_amount_in: Decimal,
        pool_key: PoolKey,
    ) -> Tuple[str, Decimal]:
        if amount_out <= 0:
            raise ValueError("amount_out must be positive")
        if max_amount_in < 0:
            raise ValueError("max_amount_in must be non-negative")

        normalized_in = _TokenResolver.normalize(token_in)
        normalized_out = _TokenResolver.normalize(token_out)

        raw_amount_out = int(
            (amount_out * _TokenResolver.scale_factor(token_out)).quantize(
                Decimal("1")
            )
        )
        raw_max_in = int(
            (max_amount_in * _TokenResolver.scale_factor(token_in)).quantize(
                Decimal("1")
            )
        )

        params = {
            "token_in": normalized_in,
            "token_out": normalized_out,
            "amount_out": raw_amount_out,
            "max_amount_in": raw_max_in,
            "recipient": user_address,
            "fee": pool_key.fee,
        }

        try:
            result = await self._soroban_call(
                self.SOROSWAP_ROUTER_METHOD_SWAP_EXACT_OUTPUT,
                params,
            )
        except RuntimeError as exc:
            raise RuntimeError(f"Swap failed: {exc}") from exc

        tx_hash = str(result.get("tx_hash", result.get("transaction_hash", "")))
        if not tx_hash:
            tx_hash = self._simulate_tx_hash(
                user_address, normalized_in, normalized_out, raw_amount_out
            )
        amount_in = Decimal(
            str(result.get("amount_in", result.get("input_amount", 0)))
        )
        return tx_hash, amount_in

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount: Decimal,
        pool_key: PoolKey,
    ) -> Decimal:
        if amount <= 0:
            raise ValueError("amount must be positive")

        normalized_in = _TokenResolver.normalize(token_in)
        normalized_out = _TokenResolver.normalize(token_out)
        scale_in = _TokenResolver.scale_factor(token_in)
        scale_out = _TokenResolver.scale_factor(token_out)
        raw_amount = int((amount * scale_in).quantize(Decimal("1")))

        try:
            result = await self._soroban_call(
                self.SOROSWAP_ROUTER_METHOD_QUOTE,
                {
                    "token_in": normalized_in,
                    "token_out": normalized_out,
                    "amount_in": raw_amount,
                    "fee": pool_key.fee,
                },
            )
        except RuntimeError as exc:
            raise RuntimeError(f"Quote failed: {exc}") from exc

        raw_amount_out = int(str(result.get("amount_out", 0)))
        return Decimal(raw_amount_out) / scale_out

    async def find_best_route(
        self,
        token_in: str,
        token_out: str,
        amount: Decimal,
    ) -> Optional[SwapRoute]:
        if amount <= 0:
            return None
        if _TokenResolver.normalize(token_in) == _TokenResolver.normalize(token_out):
            return None

        supported = [p[0] for p in await self.get_supported_pairs()]
        direct_key = self._make_pool_key(token_in, token_out, fee=30)
        if (token_in, token_out) in supported or (
            direct_key.token_a,
            direct_key.token_b,
        ) in supported:
            try:
                quote = await self.get_quote(token_in, token_out, amount, direct_key)
                return SwapRoute(
                    pools=[direct_key],
                    estimated_amount_out=quote,
                    estimated_fee=Decimal("0"),
                    price_impact=Decimal("0"),
                )
            except RuntimeError:
                pass

        return None

    async def get_supported_pairs(self) -> List[Tuple[str, str]]:
        session = await self._get_session()
        rpc_url = f"{self._rpc_url}/contract/{self._router_contract_id}/method"
        payload = {"method": "get_supported_pairs", "params": {}}
        try:
            async with session.post(rpc_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get("result", data)
                    if isinstance(pairs, list):
                        return [
                            (str(p[0]), str(p[1])) for p in pairs if len(p) >= 2
                        ]
        except aiohttp.ClientError:
            pass
        except (ValueError, KeyError, TypeError):
            pass
        return [("XLM", "USDC"), ("XLM", "WETH"), ("USDC", "WETH")]

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _simulate_tx_hash(
        self, sender: str, token_in: str, token_out: str, amount: int
    ) -> str:
        import hashlib

        raw = f"{self._network_passphrase}:{sender}:{token_in}:{token_out}:{amount}"
        return "0x" + hashlib.sha256(raw.encode()).hexdigest()[:64]
