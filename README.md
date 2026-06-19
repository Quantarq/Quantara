# Quantara

> **A Stellar-native leveraged DeFi protocol enabling automated capital looping strategies to maximize yield efficiency.**

[![CI Workflow](https://github.com/quantara-protocol/quantara/actions/workflows/ci.yml/badge.svg)](https://github.com/quantara-protocol/quantara/actions/workflows/ci.yml)

---

## Overview

**Quantara** is a professional-grade DeFi protocol built for the **Stellar ecosystem** that allows users to amplify their asset positions through automated leverage looping. By depositing collateral into lending protocols, borrowing stablecoins, swapping through AMMs, and re-depositing, Quantara enables up to **~5x leverage** on supported assets.

Built for the **Stellar ecosystem**, Quantara uses clean abstraction layers and modular architecture to maximize capital efficiency.

### Core Concepts

1. **Deposit Collateral** → Users deposit assets (XLM, ETH, USDC) into Stellar-native lending protocols
2. **Borrow Stablecoins** → Borrow against deposited collateral at optimal rates
3. **Swap via AMMs** → Swap borrowed assets via Stellar AMMs
4. **Re-Deposit & Loop** → Re-deposit swapped assets to borrow more, increasing leverage
5. **Manage Position** → Monitor health ratio, add collateral, or close position

---

## Architecture

```
quantara/
├── soroban/                  # Soroban smart contract layer (Stellar)
│   ├── adapters/             # Blockchain abstraction interfaces
│   │   ├── LendingAdapter    → Lending protocol abstraction
│   │   ├── AMMAdapter        → AMM/DEX abstraction
│   │   └── CollateralManager → Collateral & risk management
│   └── contracts/            → Soroban contract stubs (Rust)
├── web_app/                  # Python/FastAPI backend
│   ├── api/                  → REST API endpoints
│   ├── db/                   → Database models & CRUD
│   ├── contract_tools/       → Blockchain interaction layer
│   └── telegram/             → Telegram mini-app bot
├── frontend/                 # React frontend application
│   ├── src/                  → React components, hooks, services
│   └── public/               → Static assets
└── devops/                   # Docker & deployment configs
```

### Smart Contract Abstraction

Quantara uses an **adapter pattern** to abstract blockchain interactions:

| Adapter | Purpose | Description |
|---------|---------|-------------|
| `LendingAdapter` | Lending/borrowing operations | Protocol-agnostic lending abstraction |
| `AMMAdapter` | Token swapping/liquidity | Protocol-agnostic DEX abstraction |
| `CollateralManager` | Risk & collateral management | Protocol-agnostic risk engine |

---

## Why Quantara?

### Problem

DeFi users lack access to **capital-efficient leverage tools** in the Stellar ecosystem. Traditional perpetual contracts introduce volatility and high costs, while manual looping is complex and gas-inefficient.

### Solution

Quantara provides an **automated leverage engine** that:

- **Maximizes capital efficiency** through intelligent looping
- **Reduces complexity** with one-click leverage positions
- **Lowers risk** with automated health ratio monitoring
- **Enables composability** through protocol adapters
- **Provides institutional-grade** risk management

---

## Quick Start

### Prerequisites

- Docker (v24.0+) & Docker Compose (v2.0+)
- Port **5433** available for PostgreSQL

### Development

```bash
# Clone the repository
git clone <repository-url>
cd quantara

# Configure environment variables
cp .env.example .env

# Start full development environment
make dev

# Or start backend only
make back
```

### Services

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | `http://localhost:3000` | React SPA |
| **Backend API** | `http://localhost:8000` | FastAPI REST API |
| **PostgreSQL** | `localhost:5433` | Database |

### Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start development environment |
| `make back` | Start backend services only |
| `make prod` | Start production environment |
| `make windows` | Start development on Windows |

---

## Development Guide

### Running Tests

```bash
# Python backend tests
cd quantara && poetry run pytest web_app/tests

# Frontend tests
cd quantara/frontend && yarn test
```

### Database Migrations

```bash
# Start services
docker compose -f devops/docker-compose.quantara.dev.yaml up --build

# Run migrations
docker exec backend_dev alembic -c web_app/alembic.ini upgrade head

# Create new migration
docker exec backend_dev alembic -c web_app/alembic.ini revision --autogenerate -m "description"
```

### Adding Test Data

```bash
docker compose -f devops/docker-compose.quantara.dev.yaml up --build

# Seed the database
docker exec -ti backend_dev python -m web_app.db.seed_data
```

### Environment Variables

```
STELLAR_NETWORK=testnet              # testnet | mainnet | futurenet
STELLAR_HORIZON_URL=https://horizon-testnet.stellar.org
STELLAR_NODE_URL=<soroban-rpc-url>
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
