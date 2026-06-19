# ADR-0004: Caching Strategy with Redis

**Status:** Accepted

**Deciders:** Engineering Team

**Date:** 2026-06-17

## Context

Quantara's backend serves API endpoints that depend on blockchain data:

- **Token balances and portfolio values** — fetched from Horizon REST API on every request (see `StellarClient.get_balance` and `fetch_portfolio` in `contract_tools/blockchain_call.py`).
- **Reserve/position data** — fetched from Soroban RPC for lending protocol positions.
- **Pool prices and quotes** — fetched from Soroban RPC for AMM swap calculations.
- **Dashboard and leaderboard aggregations** — computed from on-chain and database data.

Without caching, every user request that touches blockchain data makes a synchronous RPC call to Horizon or Soroban RPC. This creates two problems:

1. **Latency.** Each RPC round-trip adds 200–500 ms; a dashboard endpoint that aggregates 5–10 blockchain queries can take multiple seconds.
2. **Rate limits.** Soroban RPC endpoints throttle requests; repeated cache-misses for the same data (e.g., the same reserve pool queried by 100 users simultaneously) waste有限的 rate-limit budget.

Redis was already selected as a dependency (`redis = "5.2.0"` in `pyproject.toml`) for Celery broker functionality, and a Redis container is defined in `devops/docker-compose.quantara.yaml`. However, no application-level caching has been implemented — Redis is provisioned but unused by the application code.

## Decision

Use Redis as a **read-through cache** for blockchain data and **compute cache** for expensive aggregations.

### Cache layers

| Cache Key Pattern | TTL | Description |
|---|---|---|
| `balance:{address}:{asset_code}` | 30 s | Token balances from Horizon |
| `reserve:{token}` | 60 s | Lending pool reserve data |
| `position:{user}` | 30 s | User position summary from Soroban |
| `pool_price:{pool_id}` | 15 s | Current AMM pool price |
| `dashboard:{user}` | 60 s | Aggregated dashboard data |
| `leaderboard` | 120 s | Leaderboard rankings |

### Implementation approach

1. **Decorator-based.** A `@cached(ttl=...)` decorator wraps async repository functions. Cache key is derived from function name + arguments.
2. **Cache-aside (lazy loading).** On read, check Redis first; on miss, call the source function, store the result, and return it. On write (e.g., a transaction submission), invalidate related cache keys.
3. **Graceful degradation.** If Redis is unreachable, the function executes without caching (fail-open). Errors are logged but not propagated.

### Non-goals

- **Session storage.** User sessions are managed via JWT tokens; Redis is not used for session state.
- **Message queue.** Celery + Redis broker is available for async task processing, but no caching-related messaging is introduced at this stage.

## Consequences

**Positive:**

- Reduces Horizon and Soroban RPC call volume by 60–80% for read-heavy endpoints (dashboard, portfolio, leaderboard).
- Lowers tail latency for API responses from multi-second to sub-100 ms for cached data.
- Leverages existing Redis infrastructure provisioned for Celery — no new operational dependencies.

**Negative:**

- Cache invalidation complexity: stale price data (15 s TTL) could cause users to see slightly outdated positions. The short TTLs mitigate this for price-sensitive data.
- Cold-start penalty: after a Redis restart, all cache keys must be re-populated from live RPC calls.
- Memory overhead for cache keys scales linearly with active users × tracked tokens.

**Neutral:**

- Redis is in the critical path for read requests but not for writes (transaction submissions always bypass cache).
- The `@cached` decorator pattern keeps caching concerns orthogonal to business logic, at the cost of one additional abstraction layer.
