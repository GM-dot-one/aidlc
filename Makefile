.PHONY: help install dev up down logs seed test lint typecheck check clean compose-config serve-frontend

PY ?= python3
PIP ?= $(PY) -m pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime deps
	$(PIP) install -e .

dev: ## Install dev deps
	$(PIP) install -e '.[dev]'

up: ## Start OpenProject stack (docker compose)
	docker compose up -d
	@echo "Waiting for OpenProject to become healthy..."
	@until curl -sf http://localhost:$${OPENPROJECT_HOST_PORT:-8080}/health_checks/default >/dev/null; do sleep 5; echo -n "."; done
	@echo "\nOpenProject is up at http://localhost:$${OPENPROJECT_HOST_PORT:-8080} (admin / admin on first login)"

down: ## Stop the stack
	docker compose down

logs: ## Tail OpenProject logs
	docker compose logs -f openproject

seed: ## Seed a demo project + sample ideas into OpenProject
	$(PY) scripts/seed_openproject.py

test: ## Run the test suite
	pytest

lint: ## Ruff lint + format check
	ruff check .
	ruff format --check .

typecheck: ## mypy strict check
	mypy aidlc

check: lint typecheck test ## Run all checks

compose-config: ## Validate docker-compose.yml
	docker compose config --quiet && echo "docker-compose.yml OK"

serve-frontend: ## Serve the city-list frontend on localhost:8000
	$(PY) -m http.server 8000 --directory frontend

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
