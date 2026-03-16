SHELL := /bin/zsh

UV_CACHE_DIR ?= /tmp/uv-cache
COREPACK_HOME ?= /tmp/corepack
COMPOSE_FILE := infra/docker-compose.yml

.PHONY: help setup infra-up infra-down dev api-dev worker-dev console-dev smoke test lint typecheck format db-migrate db-rollback phase2-demo phase2-demo-reset

help:
	@echo "Available commands:"
	@echo "  make setup      Install Python and frontend dependencies"
	@echo "  make infra-up   Start Postgres, Redis, and MinIO"
	@echo "  make infra-down Stop local infrastructure"
	@echo "  make dev        Start infra and print service start commands"
	@echo "  make api-dev    Start the FastAPI shell"
	@echo "  make worker-dev Start the worker shell"
	@echo "  make console-dev Start the Next.js console shell"
	@echo "  make smoke      Run fast scaffold smoke checks"
	@echo "  make db-migrate Apply SQL migrations to local Postgres"
	@echo "  make db-rollback Roll back the latest SQL migration"
	@echo "  make phase2-demo Create the canonical seeded dummy run"
	@echo "  make phase2-demo-reset Reset the Phase 2 schema, then create the canonical dummy run"
	@echo "  make test       Run Python and frontend tests"
	@echo "  make lint       Run Python and frontend lint checks"
	@echo "  make typecheck  Run Python and frontend type checks"
	@echo "  make format     Format Python and frontend files"

setup:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync --all-packages
	COREPACK_HOME=$(COREPACK_HOME) pnpm install

dev:
	@$(MAKE) infra-up
	@echo ""
	@echo "Infrastructure is running."
	@echo "Start app shells in separate terminals:"
	@echo "  make api-dev"
	@echo "  make worker-dev"
	@echo "  make console-dev"

smoke:
	UV_CACHE_DIR=$(UV_CACHE_DIR) COREPACK_HOME=$(COREPACK_HOME) uv run python tests/smoke_check.py

db-migrate:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run atlas-db up

db-rollback:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run atlas-db down --steps 1

phase2-demo:
	RUN_ID=$${RUN_ID:-dummy-run-001} UV_CACHE_DIR=$(UV_CACHE_DIR) zsh infra/scripts/phase2_dummy_run_demo.sh

phase2-demo-reset:
	RUN_ID=$${RUN_ID:-dummy-run-001} RESET_DB=1 UV_CACHE_DIR=$(UV_CACHE_DIR) zsh infra/scripts/phase2_dummy_run_demo.sh

test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run pytest
	COREPACK_HOME=$(COREPACK_HOME) pnpm -r test

lint:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check .
	COREPACK_HOME=$(COREPACK_HOME) pnpm -r lint

typecheck:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run mypy .
	COREPACK_HOME=$(COREPACK_HOME) pnpm -r typecheck

format:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff format .
	COREPACK_HOME=$(COREPACK_HOME) pnpm format

infra-up:
	docker compose -f $(COMPOSE_FILE) up -d
	docker compose -f $(COMPOSE_FILE) ps

infra-down:
	docker compose -f $(COMPOSE_FILE) down

api-dev:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run uvicorn atlas_api.main:app --factory --host 127.0.0.1 --port 8000

worker-dev:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run atlas-worker

console-dev:
	COREPACK_HOME=$(COREPACK_HOME) pnpm --filter @atlas/console dev
