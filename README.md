# CryptoTrader AI

> Autonomous AI-powered cryptocurrency trading platform.

## Stack

| | |
|---|---|
| **Backend** | Python 3.13 · FastAPI · LangGraph · SQLAlchemy · Alembic · Celery |
| **AI** | Claude (claude-sonnet-4-6) · LangChain · LangGraph |
| **Exchange** | ccxt (Binance, Coinbase, Kraken …) |
| **Database** | PostgreSQL 16 · Redis 7 |
| **Frontend** | React 18 · Vite · TypeScript · Tailwind CSS · Zustand |
| **DevOps** | Docker Compose · Nginx · Prometheus · Grafana |

## Quick Start

```bash
# 1. Clone and enter
git clone <repo-url> && cd crypto-trading-platform

# 2. Configure environment
make env-copy   # creates .env from .env.example
# Edit .env — set API keys, secrets, etc.

# 3. Start development stack
make dev

# 4. Run database migrations
make migrate

# 5. Access services
# Frontend   → http://localhost:5173
# API docs   → http://localhost:8000/docs
# pgAdmin    → http://localhost:5050
# Grafana    → http://localhost:3001
```

## Project Structure

```
crypto-trading-platform/
├── backend/                   # Python FastAPI application
│   ├── app/
│   │   ├── api/v1/            # REST + WebSocket routes
│   │   ├── agents/            # LangGraph agent pipelines
│   │   ├── core/              # Config, security, logging
│   │   ├── domain/            # Models, schemas, enums
│   │   ├── infrastructure/    # DB, Redis, CCXT, WebSocket
│   │   ├── services/          # Business logic (use cases)
│   │   └── workers/           # Celery tasks + beat schedule
│   ├── migrations/            # Alembic migration scripts
│   └── tests/
│
├── frontend/                  # React + Vite SPA
│   └── src/
│       ├── api/               # Axios API clients
│       ├── components/        # UI components
│       ├── pages/             # Route pages
│       ├── stores/            # Zustand state
│       ├── types/             # TypeScript types
│       └── websocket/         # WS hooks
│
├── infra/                     # Config files for Nginx, Redis, Postgres
├── docs/architecture.md       # Full architecture documentation
├── docker-compose.yml         # Production compose
├── docker-compose.dev.yml     # Development overrides
├── Makefile                   # Developer commands
└── .env.example               # Environment template
```

## Common Commands

```bash
make help             # Show all commands
make dev              # Start dev stack
make test             # Run all tests
make lint             # Lint backend + frontend
make migrate          # Apply DB migrations
make migrate-create msg="add table"  # New migration
make logs s=backend   # Tail a service's logs
make shell-backend    # Shell into backend container
make worker-inspect   # Show active Celery tasks
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for:
- System diagram
- Clean architecture layer breakdown
- LangGraph agent pipeline
- Database schema
- API reference
- Security model
- ADRs (Architecture Decision Records)

## Implementation Status

> This repository contains the **project scaffold** — folder structure, empty modules,
> Docker files, configuration, and architecture documentation.
> Business logic is marked `TODO` / `raise NotImplementedError` and will be
> implemented in the next phase.

- [x] Project structure & clean architecture layout
- [x] Domain models (User, Portfolio, Position, Order, Strategy, OHLCV)
- [x] Pydantic v2 schemas for all entities
- [x] FastAPI application factory + lifespan
- [x] API route stubs (all endpoints declared)
- [x] LangGraph graph structure + state
- [x] Celery app + beat schedule
- [x] WebSocket manager
- [x] Docker Compose (prod + dev)
- [x] Alembic migration environment
- [x] React + Vite frontend scaffold
- [x] Zustand stores + Axios client
- [ ] Business logic implementation (next phase)
- [ ] LLM prompt engineering
- [ ] Technical indicator computation
- [ ] Risk engine implementation
- [ ] End-to-end tests
