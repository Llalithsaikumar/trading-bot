.PHONY: help up down build dev dev-down logs shell-backend shell-frontend \
        migrate migrate-create lint test test-backend test-frontend \
        install-backend install-frontend format clean reset

# ─── Variables ─────────────────────────────────────────────────────────────────
COMPOSE         := docker compose
COMPOSE_DEV     := docker compose -f docker-compose.yml -f docker-compose.dev.yml
BACKEND_SERVICE := backend
FRONTEND_SERVICE:= frontend
PYTHON          := python3.13

# Default target
.DEFAULT_GOAL := help

# ─── Help ──────────────────────────────────────────────────────────────────────
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\n\033[1;36mCryptoTrader AI — Makefile Commands\033[0m\n\n"} \
	/^[a-zA-Z_-]+:.*?##/ { printf "  \033[1;32m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ─── Docker – Production ───────────────────────────────────────────────────────
up: ## Start all production services
	$(COMPOSE) up -d

down: ## Stop all production services
	$(COMPOSE) down

build: ## Build all production images
	$(COMPOSE) build --no-cache

logs: ## Tail logs for all services (pass s=<service> to filter)
	$(COMPOSE) logs -f $(s)

# ─── Docker – Development ──────────────────────────────────────────────────────
dev: ## Start all services in development mode with hot-reload
	$(COMPOSE_DEV) up -d

dev-build: ## Rebuild images in development mode
	$(COMPOSE_DEV) build --no-cache

dev-down: ## Stop development services
	$(COMPOSE_DEV) down

dev-logs: ## Tail development logs
	$(COMPOSE_DEV) logs -f $(s)

# ─── Database / Migrations ─────────────────────────────────────────────────────
migrate: ## Run Alembic migrations (inside backend container)
	$(COMPOSE) exec $(BACKEND_SERVICE) alembic upgrade head

migrate-create: ## Create new migration: make migrate-create msg="add users table"
	$(COMPOSE) exec $(BACKEND_SERVICE) alembic revision --autogenerate -m "$(msg)"

migrate-down: ## Roll back last migration
	$(COMPOSE) exec $(BACKEND_SERVICE) alembic downgrade -1

migrate-history: ## Show migration history
	$(COMPOSE) exec $(BACKEND_SERVICE) alembic history --verbose

db-seed: ## Run database seed script
	$(COMPOSE) exec $(BACKEND_SERVICE) python -m scripts.seed_db

# ─── Backend ───────────────────────────────────────────────────────────────────
install-backend: ## Install backend dependencies via uv
	cd backend && uv sync --all-extras

lint-backend: ## Run ruff + mypy on backend
	cd backend && uv run ruff check app tests
	cd backend && uv run mypy app

format-backend: ## Auto-format backend code
	cd backend && uv run ruff format app tests
	cd backend && uv run ruff check --fix app tests

test-backend: ## Run backend tests
	cd backend && uv run pytest tests/ -v --cov=app --cov-report=term-missing

shell-backend: ## Open shell inside backend container
	$(COMPOSE) exec $(BACKEND_SERVICE) /bin/bash

# ─── Frontend ──────────────────────────────────────────────────────────────────
install-frontend: ## Install frontend dependencies
	cd frontend && npm install

lint-frontend: ## Lint frontend code
	cd frontend && npm run lint

format-frontend: ## Format frontend code
	cd frontend && npm run format

test-frontend: ## Run frontend tests
	cd frontend && npm run test

build-frontend: ## Build frontend for production
	cd frontend && npm run build

shell-frontend: ## Open shell inside frontend container
	$(COMPOSE) exec $(FRONTEND_SERVICE) /bin/sh

# ─── Combined ──────────────────────────────────────────────────────────────────
install: install-backend install-frontend ## Install all dependencies

lint: lint-backend lint-frontend ## Lint all code

test: test-backend test-frontend ## Run all tests

format: format-backend format-frontend ## Format all code

# ─── Infrastructure ────────────────────────────────────────────────────────────
infra-up: ## Start only infrastructure services (postgres, redis)
	$(COMPOSE) up -d postgres redis

infra-down: ## Stop infrastructure services
	$(COMPOSE) stop postgres redis

# ─── Utilities ─────────────────────────────────────────────────────────────────
env-copy: ## Copy .env.example to .env
	cp -n .env.example .env && echo ".env created from .env.example"

reset: ## Full reset: stop containers, remove volumes, rebuild (DESTRUCTIVE)
	@echo "WARNING: This will delete all data. Press Ctrl+C to cancel."
	@sleep 5
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE) build --no-cache

clean: ## Remove Python caches, node_modules dist folders
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/dist frontend/node_modules 2>/dev/null || true
	@echo "Clean complete."

ps: ## Show running containers
	$(COMPOSE) ps

worker-inspect: ## Inspect Celery workers
	$(COMPOSE) exec worker celery -A app.workers.celery_app inspect active

worker-purge: ## Purge all Celery task queues (DESTRUCTIVE)
	$(COMPOSE) exec worker celery -A app.workers.celery_app purge -f
