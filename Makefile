.DEFAULT_GOAL := help
COMPOSE := docker compose
PY := backend/.venv/bin/python
PIP := backend/.venv/bin/pip
#: Interpreter path relative to the backend/ directory.
VENV_PY := .venv/bin/python

.PHONY: help
help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# --- Docker workflow -------------------------------------------------------

.PHONY: runner-image
runner-image: ## Build the hardened Python runner image
	$(COMPOSE) --profile build-only build runner

.PHONY: up
up: runner-image ## Start the full stack
	$(COMPOSE) up --build -d db redis api web

.PHONY: down
down: ## Stop the stack
	$(COMPOSE) down

.PHONY: logs
logs: ## Tail API logs
	$(COMPOSE) logs -f api

.PHONY: seed
seed: ## Load the seed curriculum into the database
	$(COMPOSE) exec api python -m app.db.init_db --seed

# --- Local (no Docker) -----------------------------------------------------

.PHONY: venv
venv: ## Create backend virtualenv and install dependencies
	python3 -m venv backend/.venv
	$(PIP) install --upgrade pip
	$(PIP) install -e "backend[dev]"

.PHONY: dev-api
dev-api: ## Run the API locally with reload
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

.PHONY: dev-web
dev-web: ## Run the frontend dev server
	cd frontend && npm run dev

.PHONY: seed-local
seed-local: ## Seed a local database
	cd backend && .venv/bin/python -m app.db.init_db --seed

# --- Quality ---------------------------------------------------------------

.PHONY: fmt
fmt: ## Format backend + frontend
	cd backend && $(VENV_PY) -m ruff format . && $(VENV_PY) -m ruff check --fix .
	cd frontend && npm run format

.PHONY: lint
lint: ## Lint and type-check everything
	cd backend && $(VENV_PY) -m ruff check . \
		&& $(VENV_PY) -m ruff format --check . \
		&& $(VENV_PY) -m mypy app
	cd frontend && npm run lint && npm run typecheck

.PHONY: test
test: ## Run backend unit + integration tests
	cd backend && .venv/bin/pytest -q

.PHONY: test-cov
test-cov: ## Run backend tests with coverage
	cd backend && .venv/bin/pytest --cov=app --cov-report=term-missing --cov-report=xml

.PHONY: e2e
e2e: ## Run the Playwright end-to-end suite
	cd e2e && npm run test

.PHONY: check
check: lint test ## Everything CI runs on a pull request
