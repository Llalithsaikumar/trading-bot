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

## Running the Application

There are two ways to run the application: using **Docker Compose** (recommended for local development with all services like PostgreSQL, Redis, Celery, and monitoring), or running the **Frontend and Backend locally** (useful for direct debugging).

### Prerequisites

Ensure you have the following installed on your system:
- **Docker & Docker Desktop** (for Docker setup)
- **Python 3.13** (for local backend setup)
- **Node.js 18+ & npm** (for local frontend setup)
- **uv** (recommended Python package manager)
- **Make** (standard utility for command shortcuts)

---

### Option 1: Running with Docker Compose (Recommended)

This compiles and starts the entire suite (PostgreSQL, Redis, Celery Workers/Beat, FastAPI Backend, React Frontend, Prometheus, Grafana, and pgAdmin).

#### 1. Setup Environment
Initialize the environment file from the template and configure your secrets (such as exchange API keys and LLM keys):
```bash
make env-copy
# Or manually copy .env.example to .env
# Edit the .env file with your Anthropic/OpenAI keys, database credentials, etc.
```

#### 2. Build and Start Services
Start the development containers in the background:
```bash
make dev
```
This runs the stack with code hot-reloading for both the frontend and backend.

#### 3. Database Migrations & Seeding
Apply the Alembic migrations and populate the database with default seed data:
```bash
# Run migrations
make migrate

# Seed initial data (User, Strategies, default Portfolio)
make db-seed
```

#### 4. Verification & Testing
Run all tests inside the Docker environment to verify the setup:
```bash
make test
```

---

### Option 2: Running Locally (Without Docker)

If you prefer to run the components locally, you will need a running PostgreSQL instance and a Redis instance (or you can start them via Docker while running app code locally).

#### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies using `uv`:
   ```bash
   uv sync --all-extras
   ```
3. Initialize the environment:
   ```bash
   cp .env.example .env
   # Edit backend/.env to point to your local PostgreSQL/Redis servers
   ```
4. Run migrations and seed data:
   ```bash
   uv run alembic upgrade head
   uv run python -m scripts.seed_db
   ```
5. Start the Celery workers (in a separate terminal):
   ```bash
   uv run celery -A app.workers.celery_worker worker --loglevel=info
   uv run celery -A app.workers.celery_worker beat --loglevel=info
   ```
6. Start the FastAPI development server:
   ```bash
   uv run uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
   ```

#### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

---

### Accessing Services

Once started, the services are accessible at:
- **Frontend App**: [http://localhost:5173](http://localhost:5173)
- **Backend API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redoc API Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **pgAdmin (Postgres GUI)**: [http://localhost:5050](http://localhost:5050)
- **Grafana (Dashboards)**: [http://localhost:3001](http://localhost:3001)
- **Prometheus**: [http://localhost:9090](http://localhost:9090)


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
