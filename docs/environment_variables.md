# Environment Variables

The QUANTARA web application reads configuration from environment
variables. Missing critical values are validated at startup by
`web_app.config_validator.assert_valid_config`; the application
will fail to start in production if any required variable is missing.

## Required in production

| Variable             | Purpose                                                    |
|----------------------|------------------------------------------------------------|
| `DB_USER`            | PostgreSQL username                                        |
| `DB_PASSWORD`        | PostgreSQL password                                        |
| `DB_HOST`            | PostgreSQL host                                            |
| `DB_NAME`            | PostgreSQL database name                                   |
| `SESSION_SECRET_KEY` | Secret used to sign session cookies (min 32 chars)         |
| `SENTRY_DSN`         | Sentry DSN for error tracking                              |

## Optional

| Variable                     | Purpose                                                |
|------------------------------|--------------------------------------------------------|
| `AIRDROP_REWARD_API_ENDPOINT` | Optional Stellar-compatible airdrop/rewards endpoint  |
| `DB_PORT`                    | PostgreSQL port (default `5432`)                       |
| `ENV_VERSION`                | `PROD` enables production-only behaviour               |
| `STELLAR_HORIZON_URL`        | Stellar Horizon endpoint                               |
| `STELLAR_SOROBAN_RPC_URL`    | Soroban RPC endpoint                                   |
| Variable                  | Purpose                                                     |
|---------------------------|-------------------------------------------------------------|
| `CORS_ORIGINS`            | Comma-separated allowed frontend origins                    |
| `DB_PORT`                 | PostgreSQL port (default `5432`)                            |
| `ENV_VERSION`             | `PROD` enables production-only behaviour                    |
| `STELLAR_HORIZON_URL`     | Stellar Horizon endpoint                                    |
| `STELLAR_SOROBAN_RPC_URL` | Soroban RPC endpoint                                        |
| `REDIS_URL`               | Redis connection URI used by the rate limiter (default `redis://localhost:6379`) |
| `RATE_LIMIT_WRITE`        | Limit for mutation endpoints — create/close position, auth (default `5/minute`)  |
| `RATE_LIMIT_USER_DATA`    | Limit for user-specific data endpoints — dashboard, positions (default `30/minute`) |
| `RATE_LIMIT_READ`         | Limit for read-only endpoints — multipliers, leaderboard (default `100/minute`)  |

## Rate limiting

Rate limiting is implemented with [slowapi](https://github.com/laurents/slowapi)
backed by Redis. All API endpoints are covered by one of three tiers:

| Tier       | Default     | Env var               | Endpoints                                              |
|------------|-------------|------------------------|--------------------------------------------------------|
| Write      | 5/minute    | `RATE_LIMIT_WRITE`    | create-position, close-position, open-position, auth/connect, vault/deposit |
| User data  | 30/minute   | `RATE_LIMIT_USER_DATA`| dashboard, user-positions, repay data, check-user, vault/balance |
| Read       | 100/minute  | `RATE_LIMIT_READ`     | get-multipliers, leaderboard, telegram link, stats     |

`GET /health` is **exempt** from rate limiting.

Exceeding a limit returns `429 Too Many Requests` with a `Retry-After`
header indicating when the client may retry.

Write and user-data endpoints that accept a `wallet_id` query/path parameter
are keyed per wallet rather than per IP, so multiple wallets sharing an IP
are throttled independently.

To raise limits in a high-traffic deployment:

```sh
RATE_LIMIT_WRITE=20/minute
RATE_LIMIT_USER_DATA=120/minute
RATE_LIMIT_READ=500/minute
```

## Generating a session secret

```sh
python -c "import os; print(os.urandom(32).hex())"
```

## Behaviour in development

In development (`ENV_VERSION != "PROD"`) the application does not
require any of the variables above. Missing optional variables
(e.g. `SENTRY_DSN`) only produce a warning in the logs.

If `AIRDROP_REWARD_API_ENDPOINT` is unset, the airdrop fetcher acts
as a no-op stub and returns no airdrop data.
If `CORS_ORIGINS` is unset, the API allows requests from
`http://localhost:3000` for local development. Set it explicitly in
production, for example:

```sh
CORS_ORIGINS="https://quantara.xyz,https://app.quantara.xyz"
```
