# ADR-0003: Adapter Pattern for Soroban Protocol Integration

**Status:** Accepted

**Deciders:** Engineering Team

**Date:** 2026

## Context

Quantara must interact with two distinct categories of blockchain protocols on Stellar:

1. **Lending protocols** — for depositing collateral, borrowing assets, enabling/disabling collateral.
2. **AMM/DEX protocols** — for swapping between assets (e.g., borrow USDC → swap to XLM → re-deposit).

Each category contains multiple protocols, and the set of available protocols changes over time as the Stellar/Soroban ecosystem evolves. Directly coupling the business logic (leverage looping, position management) to any single protocol would:

- Make it difficult to add support for new lending or AMM protocols.
- Require changes to core business logic when a protocol's interface changes.
- Prevent testing individual protocol interactions in isolation.
- Create a monolithic dependency graph between the DeFi logic layer and external smart contracts.

Additionally, the Rust Soroban contracts that will eventually execute the on-chain loop logic (`quantara/soroban/contracts/`) are not yet deployed. The adapter layer must allow the Python backend and JavaScript frontend to interact with protocols while the Rust contract layer is being developed.

## Decision

Use the **Adapter pattern** (GoF) with abstract base classes (ABCs) and a **Factory** for protocol selection, isolating protocol-specific logic behind a stable, protocol-agnostic interface.

### Structure

```
quantara/soroban/adapters/
├── LendingAdapter.py       → ABC + LendingAdapterFactory
├── AMMAdapter.py           → ABC + AMMAdapterFactory
└── CollateralManager.py    → Concrete class (not abstract)
```

### LendingAdapter (`LendingAdapter.py`)

Abstract interface for lending protocol operations:

```python
class LendingAdapter(ABC):
    @abstractmethod
    async def get_reserve_data(self, token: str) -> ReserveData: ...
    @abstractmethod
    async def get_user_position(self, user: str) -> UserPosition: ...
    @abstractmethod
    async def deposit(self, token: str, amount: int) -> str: ...
    @abstractmethod
    async def withdraw(self, token: str, amount: int) -> str: ...
    @abstractmethod
    async def borrow(self, token: str, amount: int) -> str: ...
    @abstractmethod
    async def repay(self, token: str, amount: int) -> str: ...
    @abstractmethod
    async def enable_collateral(self, token: str) -> str: ...
    @abstractmethod
    async def disable_collateral(self, token: str) -> str: ...
    @abstractmethod
    async def get_all_reserves(self) -> list[ReserveData]: ...
```

Concrete implementations (e.g., `LendestAdapter`, `BlendAdapter`) register themselves with `LendingAdapterFactory`:

```python
class LendingAdapterFactory:
    _adapters: dict[str, type[LendingAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter: type[LendingAdapter]): ...
    @classmethod
    def create(cls, name: str, **kwargs) -> LendingAdapter: ...
```

### AMMAdapter (`AMMAdapter.py`)

Same pattern for swap operations:

```python
class AMMAdapter(ABC):
    @abstractmethod
    async def get_pool_price(self, pool: PoolKey) -> PoolPrice: ...
    @abstractmethod
    async def swap_exact_input(self, ...) -> str: ...
    @abstractmethod
    async def swap_exact_output(self, ...) -> str: ...
    @abstractmethod
    async def get_quote(self, ...) -> int: ...
    @abstractmethod
    async def find_best_route(self, ...) -> SwapRoute: ...
    @abstractmethod
    async def get_supported_pairs(self) -> list[tuple[str, str]]: ...
```

### CollateralManager (`CollateralManager.py`)

A concrete class (not an adapter) because collateral math (health ratios, liquidation prices, max leverage) is protocol-independent. It consumes data from `LendingAdapter` and `AMMAdapter` rather than wrapping a blockchain protocol.

### Data Classes

Both adapters define immutable dataclasses (`ReserveData`, `UserPosition`, `PoolKey`, `PoolPrice`, `SwapRoute`, `CollateralConfig`, `PositionHealth`, `PositionSummary`) that serve as the contract between the adapter layer and the business logic layer.

## Consequences

**Positive:**

- New lending or AMM protocols can be supported by writing a new adapter class and registering it with the corresponding factory — no changes to business logic.
- Adapters can be mocked or stubbed in unit tests, enabling fast test suites without RPC calls.
- The mixin layer (`DepositMixin`, `HealthRatioMixin`, `PositionMixin`) consumes adapters by interface, not by concrete type.
- The factory pattern allows runtime protocol selection (e.g., based on environment configuration or user preference).

**Negative:**

- Every new protocol requires an adapter implementation; thin adapters add boilerplate for simple integrations.
- The adapter interfaces must be stable; changing an abstract method signature requires updating all implementations simultaneously.
- Python's ABC runtime checks catch missing methods late (at instantiation, not import time).

**Neutral:**

- `CollateralManager` sits outside the adapter hierarchy — its concrete design reflects that collateral math is protocol-independent logic, not an integration seam.
- The adapters are defined in `quantara/soroban/` but currently consumed only by the Python backend (API layer). The frontend invokes Soroban contracts directly via `@stellar/stellar-sdk` without going through these Python adapters — creating a dual-path architecture where the frontend and backend can use different protocol interfaces.
