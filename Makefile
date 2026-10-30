.DEFAULT_GOAL := help
PY := .venv/bin/python
PIP := .venv/bin/pip
export VERIFACT_API__AUTH_ENABLED ?= false

help:  ## show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.venv:
	python3.13 -m venv .venv && $(PIP) install -q --upgrade pip

install: .venv  ## core + dev dependencies (no transformer models)
	$(PIP) install -q -e ".[dev]"

install-ml: install  ## add transformer backends (~2GB) and the spaCy model
	$(PIP) install -q -e ".[ml]"
	$(PY) -m spacy download en_core_web_sm

migrate:  ## apply migrations
	.venv/bin/alembic upgrade head

dev: migrate  ## run the API + dashboard at http://127.0.0.1:8000
	.venv/bin/uvicorn verifact.api.app:app --reload --port 8000

lint:  ## ruff
	.venv/bin/ruff check src tests
	.venv/bin/ruff format --check src tests

fmt:  ## apply formatting
	.venv/bin/ruff format src tests
	.venv/bin/ruff check --fix src tests

types:  ## mypy
	.venv/bin/mypy

test:  ## unit + integration + api, skipping tests that need models or network
	.venv/bin/pytest -m "not ml and not network"

test-all:  ## everything, including model-backed tests
	.venv/bin/pytest

cov:  ## coverage with the NFR-07 gate
	.venv/bin/pytest -m "not ml and not network" --cov --cov-report=term-missing --cov-fail-under=70

sec:  ## bandit + dependency audit
	.venv/bin/bandit -q -c pyproject.toml -r src
	.venv/bin/pip-audit --skip-editable

check: lint types test sec  ## everything CI runs

clean:
	rm -rf build .cache .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

.PHONY: help install install-ml migrate dev lint fmt types test test-all cov sec check clean
