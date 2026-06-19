# ADR-0002: Migrate from Starknet to Stellar

**Status:** Accepted (fully migrated)

**Deciders:** Engineering Team

**Date:** 2026 (migration completed)

## Context

The original Quantara prototype was built on Starknet using Cairo smart contracts. It integrated with Ekubo (AMM) and zkLend (lending protocol) on Starknet mainnet. The architecture included:

- A Cairo-based `loop_liquidity` contract handling leverage looping, position management, and reward claims.
- Starknet-specific wallet integration (Argent X, Braavos).
- STRK token for gas and reward distribution.

Several factors drove the decision to reevaluate this foundation:

1. **Ecosystem maturity.** Stellar's Soroban smart contracts platform offered a more production-ready environment with clearer regulatory standing and established tooling (`stellar-sdk`, Freighter wallet, Soroban RPC).
2. **Gas and throughput.** Stellar's fee model (fixed base fee + inclusion fees) provided more predictable transaction costs compared to Starknet's volatile gas pricing during the period.
3. **Integration surface.** The Stellar ecosystem provided Horizon REST APIs and Soroban RPC endpoints that were simpler to integrate with the Python/FastAPI backend compared to Starknet's JSON-RPC layer.
4. **Wallet ecosystem.** Freighter wallet offered a mature browser extension with straightforward `@stellar/freighter-api` integration, simplifying the frontend signing flow.

## Decision

Abandon the Starknet/Cairo implementation and rebuild Quantara on Stellar/Soroban.

The migration involved:

- Rewriting smart contract logic from Cairo to Soroban (Rust with `wasm32-unknown-unknown` target).
- Replacing `starknet.py` / Starknet JSON-RPC integration with `StellarClient` using `aiohttp` for Horizon REST API and Soroban RPC calls.
- Switching wallet integration from Argent X / Braavos to Freighter (`@stellar/freighter-api`).
- Moving from Ekubo (AMM) + zkLend (lending) on Starknet to the equivalent Soroban-based protocols on Stellar.
- Updating the token model from Starknet-native assets (ETH, STRK, USDC via Starknet bridging) to Stellar assets (XLM, USDC, issued tokens with trustlines).

One notable backend constraint was documented in `blockchain_call.py`:

> We use aiohttp directly instead of `stellar_sdk.Server` because the Python stellar-sdk Server class is synchronous and does not support async/await.

This means the backend communicates with Stellar via raw HTTP rather than the SDK, while the frontend uses `@stellar/stellar-sdk` ^15.1.0 and `@stellar/freighter-api` ^6.0.1 for all Soroban contract invocations.

## Consequences

**Positive:**

- Access to Stellar's stable, low-cost fee model and established validator set.
- Simpler wallet integration via Freighter (import-based, no wallet extension type gymnastics).
- Horizon REST API enabled async Python integration without blocking the event loop.
- Cleaner regulatory landscape for a DeFi protocol targeting cross-border use cases.

**Negative:**

- Lost compatibility with Ekubo and zkLend — the original AMM/lending protocols — requiring new Soroban protocol integrations.
- Existing Cairo contract testing and deployment tooling (Starknet Foundry, Protostar) was discarded.
- Backend cannot use `stellar_sdk.Server` due to its synchronous design; raw `aiohttp` calls must be maintained (see `contract_tools/blockchain_call.py`).
- The frontend must own all Soroban transaction signing (build → simulate → assemble → sign → submit → poll), adding complexity to the client layer (`frontend/src/services/soroban.js`).
- Legacy Starknet documentation in `docs/quantara.md`, `docs/contract_deploy.md`, and `research/manual_test_scenarios.md` must be clearly marked as deprecated to avoid confusion.

**Neutral:**

- Rust smart contracts replace Cairo; both require WASM compilation but the toolchain differs (`stellar-cli` vs `starknet-foundry`).
- The Soroban contract directory (`quantara/soroban/contracts/`) is planned but not yet populated; as of this writing only the adapter interfaces exist on disk.
