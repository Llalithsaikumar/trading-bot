# CryptoTrader AI — Architecture Documentation

## Table of Contents
1. [System Overview](#1-system-overview)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Clean Architecture Layers](#3-clean-architecture-layers)
4. [Component Deep-Dive](#4-component-deep-dive)
5. [LangGraph Agent Pipeline](#5-langgraph-agent-pipeline)
6. [Data Flow](#6-data-flow)
7. [Database Schema Overview](#7-database-schema-overview)
8. [API Design](#8-api-design)
9. [Real-Time Communication](#9-real-time-communication)
10. [Background Workers](#10-background-workers)
11. [Security Architecture](#11-security-architecture)
12. [Infrastructure & Deployment](#12-infrastructure--deployment)
13. [ADRs — Architecture Decision Records](#13-adrs--architecture-decision-records)

---

## 1. System Overview

CryptoTrader AI is an **autonomous AI-powered cryptocurrency trading platform** that:
- Connects to multiple exchanges via `ccxt`
- Runs LangGraph-orchestrated LLM agents to analyse markets and generate trading signals
- Enforces risk rules before executing orders
- Provides a real-time React dashboard over WebSockets
- Schedules periodic strategies through Celery workers

**Technology stack at a glance**

| Layer             | Technology                          |
|-------------------|-------------------------------------|
| Language          | Python 3.13                         |
| Package manager   | uv                                  |
| Web framework     | FastAPI + Uvicorn                   |
| AI orchestration  | LangGraph + LangChain               |
| LLM              | Claude (claude-sonnet-4-6) via Anthropic |
| Exchange APIs     | ccxt (async)                        |
| ORM               | SQLAlchemy 2.0 async                |
| Migrations        | Alembic                             |
| Primary DB        | PostgreSQL 16                       |
| Cache / Broker    | Redis 7                             |
| Task queue        | Celery + RedBeat                    |
| Frontend          | React 18 + Vite + TypeScript        |
| State management  | Zustand + React Query               |
| Reverse proxy     | Nginx                               |
| Containerisation  | Docker Compose                      |
| Logging           | Loguru (structured JSON)            |
| Monitoring        | Prometheus + Grafana                |

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER BROWSER                                  │
│                     React + Vite SPA (port 5173/80)                    │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌─────────────────────┐  │
│  │Dashboard │  │ Trading  │  │ Portfolio  │  │ Strategy Manager    │  │
│  └──────────┘  └──────────┘  └────────────┘  └─────────────────────┘  │
└───────────────────────┬─────────────────────┬───────────────────────────┘
                        │ HTTP/REST            │ WebSocket
                        ▼                      ▼
┌───────────────── Nginx Reverse Proxy (port 80) ──────────────────────────┐
│                     /api/* → backend    /ws/* → backend                  │
└───────────────────────┬──────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────── FastAPI Backend (port 8000) ───────────────────────────┐
│                                                                          │
│  ┌─── API Layer ─────────────────────────────────────────────────────┐  │
│  │  /api/v1/auth   /api/v1/portfolios  /api/v1/orders               │  │
│  │  /api/v1/strategies  /api/v1/market  /ws/ticker  /ws/portfolio   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                        │                                                  │
│  ┌─── Service Layer ──────────────────────────────────────────────────┐  │
│  │  AuthService  OrderService  MarketDataService  StrategyService    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                        │                                                  │
│  ┌─── Infrastructure Layer ───────────────────────────────────────────┐  │
│  │  Repositories  ExchangeClient(ccxt)  RedisClient  WSManager       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└────────────┬─────────────────────┬──────────────────────────────────────┘
             │                     │
     ┌───────▼───────┐    ┌────────▼────────┐
     │  PostgreSQL   │    │     Redis        │
     │  (port 5432)  │    │   (port 6379)   │
     └───────────────┘    └─────────────────┘

┌────────────────── Celery Workers ────────────────────────────────────────┐
│                                                                          │
│  ┌── Worker ─────────────────────────────────────────────────────────┐  │
│  │  trading_tasks  market_data_tasks  notification_tasks             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌── Beat Scheduler ─────────────────────────────────────────────────┐  │
│  │  run_active_strategies (5m)  sync_market_data (60s)               │  │
│  │  check_alerts (60s)         sync_order_statuses (30s)            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                        │                                                  │
│  ┌─── LangGraph Agent Pipeline ──────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  MarketData → Analysis → LLMDecision → Risk → Execution          │  │
│  │       │           │           │          │         │              │  │
│  │     ccxt       pandas     Claude AI   Rules     ccxt.order       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

┌────────────── External Services ─────────────────────────────────────────┐
│  Binance API   Coinbase API   Kraken API   Anthropic API                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Clean Architecture Layers

The backend follows **Clean Architecture** with strict dependency inversion:

```
backend/app/
├── domain/           ← Innermost — no external dependencies
│   ├── models/       ← SQLAlchemy ORM entities
│   ├── schemas/      ← Pydantic v2 DTOs (request/response)
│   ├── enums/        ← StrEnum value types
│   └── interfaces/   ← Abstract repository contracts
│
├── infrastructure/   ← Adapters — implements domain interfaces
│   ├── database/     ← SQLAlchemy session, engine
│   ├── repositories/ ← Concrete repository implementations
│   ├── cache/        ← Redis client
│   ├── exchange/     ← CCXT async wrapper
│   └── messaging/    ← WebSocket manager
│
├── services/         ← Application layer — use cases
│   ├── auth/
│   ├── trading/
│   ├── portfolio/
│   └── market_data/
│
├── agents/           ← AI orchestration (LangGraph)
│   ├── graph/        ← State types + graph builder helpers
│   ├── trading_agent/← Main trade decision pipeline
│   ├── analysis_agent/← Technical indicator computation
│   └── risk_agent/   ← Risk rule evaluation
│
├── workers/          ← Celery tasks + beat schedule
│   └── tasks/
│
├── api/              ← Outermost — HTTP/WS adapters
│   ├── v1/endpoints/ ← FastAPI route handlers
│   └── middleware/   ← Exception handlers, logging
│
└── core/             ← Cross-cutting: config, security, logging, constants
```

**Dependency rule:** Every inner layer is unaware of outer layers.
`domain` ← `infrastructure` ← `services` ← `agents`/`workers` ← `api`

---

## 4. Component Deep-Dive

### 4.1 FastAPI Backend
- **Entry point:** `app/main.py` — creates the `FastAPI` instance, mounts routers, registers exception handlers
- **Lifespan context manager** opens/closes the DB connection pool, Redis, and exchange clients
- **Prometheus metrics** exposed at `/metrics` via `prometheus-fastapi-instrumentator`
- All responses use **orjson** for fast serialisation

### 4.2 SQLAlchemy Async ORM
- `create_async_engine` with `asyncpg` driver
- Connection pool: `pool_size=20`, `max_overflow=10`
- `expire_on_commit=False` for safer async patterns
- All queries use `select()` / `execute()` (no lazy loading in async)

### 4.3 CCXT Exchange Layer
- One async exchange instance per exchange ID (pooled)
- Sandbox/testnet mode configurable via env
- Unified `ExchangeClient` wrapper normalises CCXT responses to typed dicts

### 4.4 LangGraph Agents
See [Section 5](#5-langgraph-agent-pipeline).

### 4.5 Celery + RedBeat
- **Three queues:** `trading`, `market_data`, `notifications`
- **Beat:** RedBeat scheduler stores schedules in Redis (survives restarts)
- `task_acks_late=True` — tasks are only acknowledged after completion, preventing data loss on worker crash

### 4.6 WebSocket Manager
- `ConnectionManager` maps `user_id → set[WebSocket]` for unicast
- `channel → set[WebSocket]` for broadcast (tickers, signals)
- Auto-removes dead connections on write failure

---

## 5. LangGraph Agent Pipeline

```
                    ┌─────────────────────────────────────────┐
                    │           TradingState (Pydantic)        │
                    │  strategy_id, symbols, timeframe         │
                    │  ohlcv, tickers, indicators             │
                    │  signal, confidence, reasoning          │
                    │  risk_approved, order_placed            │
                    └─────────────────────────────────────────┘
                                       │
              ┌────────────────────────▼────────────────────────┐
              │              LangGraph StateGraph               │
              │                                                  │
              │  ┌─────────────┐                                 │
              │  │MarketData   │ ccxt.fetch_ohlcv, fetch_ticker  │
              │  │Node         │ → state.ohlcv, state.tickers    │
              │  └──────┬──────┘                                 │
              │         │                                        │
              │  ┌──────▼──────┐                                 │
              │  │Analysis     │ pandas + ta-lib indicators      │
              │  │Node         │ → state.indicators              │
              │  └──────┬──────┘                                 │
              │         │                                        │
              │  ┌──────▼──────┐                                 │
              │  │LLMDecision  │ Claude via langchain_anthropic  │
              │  │Node         │ → state.signal, confidence,     │
              │  │             │   reasoning                     │
              │  └──────┬──────┘                                 │
              │         │                                        │
              │  ┌──────▼──────┐                                 │
              │  │Risk         │ check_daily_loss_limit          │
              │  │Node         │ check_position_size             │
              │  │             │ check_max_open_positions        │
              │  │             │ check_signal_confidence         │
              │  │             │ → state.risk_approved           │
              │  └──────┬──────┘                                 │
              │         │ conditional edge                       │
              │    ┌────┴──────┐                                 │
              │   yes          no                                │
              │    │           └──► END (no trade)              │
              │  ┌─▼───────────┐                                 │
              │  │Execution    │ ccxt.create_order               │
              │  │Node         │ → state.order_id, order_placed  │
              │  └──────┬──────┘                                 │
              │         │                                        │
              │        END                                       │
              └──────────────────────────────────────────────────┘
```

**State persistence:** Each run is recorded as a `StrategyExecution` row including the LLM's reasoning, token usage, and duration.

---

## 6. Data Flow

### 6.1 Market Data Ingestion
```
Celery Beat (every 60s)
    → sync_market_data task
    → ccxt.fetch_tickers() (batch)
    → upsert MarketTicker (PostgreSQL)
    → cache in Redis (TTL 30s)
    → ws_manager.broadcast_channel("ticker:exchange:symbol")
    → React frontend receives live price update
```

### 6.2 Strategy Execution
```
Celery Beat (every 5m)
    → run_active_strategies task
    → query strategies WHERE status='active'
    → for each: run_strategy_task.delay(strategy_id)
        → load Strategy from DB
        → build TradingState
        → trading_graph.ainvoke(state)
            → MarketData → Analysis → LLM → Risk → (Execute)
        → save StrategyExecution record
        → if order placed: persist Order to DB
        → broadcast signal via WebSocket
```

### 6.3 Manual Order Flow
```
POST /api/v1/orders
    → OrderCreate schema validated
    → OrderService.place_order()
        → RiskService.validate()
        → ExchangeClient.create_order()
        → persist Order (DB)
    → 201 OrderResponse
    → broadcast to portfolio WebSocket channel
```

---

## 7. Database Schema Overview

```
users
  id (UUID PK)
  email (unique), username (unique)
  hashed_password, role, status
  two_fa_enabled, two_fa_secret

portfolios
  id, user_id (FK→users)
  name, exchange, quote_currency
  total_value_usdt, available_balance
  unrealized_pnl, realized_pnl, daily_pnl
  is_paper_trading

positions
  id, portfolio_id (FK)
  symbol, side, quantity, entry_price
  current_price, leverage
  unrealized_pnl, stop_loss, take_profit

orders
  id, portfolio_id (FK), exchange_order_id
  symbol, exchange, side, order_type, status
  quantity, price, filled_quantity
  average_fill_price, fee
  strategy_id (FK), agent_reasoning

strategies
  id, user_id (FK)
  name, exchange, symbols (JSON), timeframe
  status, risk params (stop_loss_pct, …)
  config (JSON), performance metrics

strategy_executions
  id, strategy_id (FK)
  run_id, status, signal, reasoning
  tokens_used, duration_ms

ohlcv
  exchange, symbol, timeframe, timestamp (composite unique)
  open, high, low, close, volume

market_tickers
  exchange, symbol (composite unique)
  bid, ask, last, volume_24h, change_24h_pct

alerts
  id, user_id (FK)
  symbol, alert_type, condition_value
  is_active, is_triggered, notify_*
```

---

## 8. API Design

Base path: `/api/v1`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create user account |
| POST | `/auth/login` | Authenticate, get tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Invalidate refresh token |
| GET | `/users/me` | Current user profile |
| GET | `/portfolios` | List portfolios |
| POST | `/portfolios` | Create portfolio |
| GET | `/portfolios/{id}` | Get portfolio + positions |
| GET | `/orders` | Order history (paginated) |
| POST | `/orders` | Place order |
| DELETE | `/orders/{id}` | Cancel order |
| GET | `/strategies` | List strategies |
| POST | `/strategies` | Create strategy |
| POST | `/strategies/{id}/start` | Activate strategy |
| POST | `/strategies/{id}/stop` | Pause strategy |
| GET | `/market/ticker/{exchange}/{symbol}` | Live ticker |
| GET | `/market/ohlcv/{exchange}/{symbol}` | Candlestick data |
| GET | `/market/orderbook/{exchange}/{symbol}` | Order book depth |
| WS | `/ws/ticker/{exchange}/{symbol}` | Real-time price stream |
| WS | `/ws/portfolio/{id}` | Live portfolio updates |
| WS | `/ws/signals` | AI trading signal stream |

All endpoints return consistent JSON envelopes. Errors follow `ErrorResponse { error, code, detail }`.

---

## 9. Real-Time Communication

### WebSocket Message Format
```json
{
  "type": "ticker_update",
  "channel": "ticker:binance:BTC/USDT",
  "payload": {
    "last": "67432.50",
    "bid": "67431.00",
    "ask": "67434.00",
    "change_24h_pct": "2.34"
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Channel Naming Convention
| Channel | Description |
|---------|-------------|
| `ticker:{exchange}:{symbol}` | Price tick |
| `orderbook:{exchange}:{symbol}` | Order book delta |
| `portfolio:{portfolio_id}` | PnL / balance update |
| `signals` | AI-generated trading signals |
| `alerts:{user_id}` | Price alert notifications |

---

## 10. Background Workers

### Queue Configuration
| Queue | Workers | Purpose |
|-------|---------|---------|
| `default` | 2 | General tasks |
| `trading` | 4 | Strategy execution (latency-sensitive) |
| `market_data` | 2 | Ticker / OHLCV sync |
| `notifications` | 1 | Email / push alerts |

### Periodic Tasks (Beat)
| Task | Interval | Description |
|------|----------|-------------|
| `sync_market_data` | 60s | Refresh all tracked tickers |
| `run_active_strategies` | 5m | Trigger LangGraph for each active strategy |
| `check_price_alerts` | 60s | Evaluate alert conditions |
| `sync_order_statuses` | 30s | Reconcile open orders with exchange |

---

## 11. Security Architecture

| Concern | Implementation |
|---------|---------------|
| Authentication | JWT Bearer tokens (access 30m + refresh 7d) |
| Password storage | bcrypt via passlib |
| Token refresh | Silent re-issue via Axios interceptor |
| Token revocation | Refresh token blacklist in Redis |
| 2FA | TOTP (HMAC-SHA1) — optional per user |
| Input validation | Pydantic v2 strict models |
| SQL injection | ORM parameterised queries (no raw SQL) |
| CORS | Explicit origin allowlist |
| Rate limiting | Redis-backed (to be implemented) |
| Secrets | Environment variables (never committed) |
| HTTPS | Nginx TLS termination in production |

---

## 12. Infrastructure & Deployment

### Development
```bash
make env-copy    # cp .env.example .env
make dev         # docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
make migrate     # run Alembic migrations
```

### Production
```bash
make build       # docker compose build
make up          # docker compose up -d
make migrate
```

### Service Ports (development)
| Service | Port |
|---------|------|
| Frontend (Vite) | 5173 |
| Backend API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Nginx | 80 |
| Prometheus | 9090 |
| Grafana | 3001 |
| pgAdmin | 5050 |
| RedisInsight | 8001 |
| Mailhog SMTP | 1025 |
| Mailhog UI | 8025 |

---

## 13. ADRs — Architecture Decision Records

### ADR-001: LangGraph for Agent Orchestration
**Context:** Need to chain market data → analysis → LLM decision → risk → execution with conditional routing.
**Decision:** Use LangGraph `StateGraph` with typed `TradingState`.
**Rationale:** Native support for conditional edges (skip execution if risk fails), built-in state serialisation, easy integration with LangChain tool calls.
**Trade-offs:** LangGraph is a heavier dependency than a custom pipeline; debugging requires LangSmith or structured logging.

### ADR-002: Async SQLAlchemy with asyncpg
**Context:** FastAPI is fully async; blocking DB calls would defeat its concurrency model.
**Decision:** `create_async_engine` + `asyncpg` + `async_sessionmaker`.
**Rationale:** Keeps the entire request path non-blocking. No ORM lazy-loading (explicit `noload` on relationships).
**Trade-offs:** More verbose queries; no `session.refresh()` without explicit `await`.

### ADR-003: Celery for Background Workers
**Context:** Strategy execution and market data sync must run independently of the API.
**Decision:** Celery with Redis broker, RedBeat scheduler.
**Rationale:** Mature ecosystem, `task_acks_late` for reliability, RedBeat survives restarts.
**Trade-offs:** Celery workers use sync code — async tasks require `asyncio.run()` wrappers.

### ADR-004: Pydantic v2 for All DTOs
**Context:** Need fast, strict validation at API boundaries.
**Decision:** All request/response schemas extend `BaseSchema(BaseModel)` with `from_attributes=True`.
**Rationale:** v2 is 5-50× faster than v1; model_validator and field_validator provide clean validation hooks.
**Trade-offs:** v2 breaking changes from v1 require migration effort if upgrading existing code.

### ADR-005: Redis as Cache + Broker
**Context:** Redis is already required for Celery; also needed for rate limiting, session blacklist, and market data cache.
**Decision:** Use a single Redis instance with separate DBs per concern (0=app, 1=celery broker, 2=celery results).
**Rationale:** Reduces operational overhead.
**Trade-offs:** Single point of failure; mitigate with Redis Sentinel / Cluster in production.

### ADR-006: CCXT for Exchange Connectivity
**Context:** Need to connect to multiple exchanges with a unified API.
**Decision:** `ccxt.async_support` with a thin `ExchangeClient` wrapper.
**Rationale:** 100+ exchanges supported, well-maintained, unified order/ticker/balance interface.
**Trade-offs:** CCXT normalises data but each exchange has quirks; error handling must be exchange-aware.
