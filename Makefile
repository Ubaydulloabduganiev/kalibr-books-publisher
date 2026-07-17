SHELL := /bin/bash
COMPOSE := docker compose
API_DIR := apps/api

.PHONY: help bootstrap install dev down logs build test lint typecheck check \
	api-dev api-test api-lint api-typecheck web-dev web-test web-lint web-typecheck \
	prod-up prod-down clean

help:
	@printf '%s\n' \
	  'Kalibr Publisher commands:' \
	  '  make bootstrap      Create .env and install local dependencies' \
	  '  make dev            Start the Docker development stack' \
	  '  make api-dev        Start the API natively with reload' \
	  '  make web-dev        Start the web app natively' \
	  '  make down           Stop the development stack' \
	  '  make logs           Follow container logs' \
	  '  make build          Build development and production images' \
	  '  make check          Run lint, type checks, and tests' \
	  '  make prod-up        Start the VPS production stack' \
	  '  make prod-down      Stop the VPS production stack'

bootstrap:
	@test -f .env || cp .env.example .env
	cd $(API_DIR) && uv sync --frozen --all-groups
	npm ci

install: bootstrap

api-dev:
	cd $(API_DIR) && uv run uvicorn kalibr_publisher.main:app --reload --no-access-log

web-dev:
	npm run web:dev

dev:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

build:
	$(COMPOSE) build
	$(COMPOSE) -f docker-compose.production.yml build

api-test:
	cd $(API_DIR) && uv run pytest

api-lint:
	cd $(API_DIR) && uv run ruff check src tests
	cd $(API_DIR) && uv run ruff format --check src tests

api-typecheck:
	cd $(API_DIR) && uv run mypy src

web-test:
	npm run web:test

web-lint:
	npm run web:lint

web-typecheck:
	npm run web:typecheck

lint: api-lint web-lint

typecheck: api-typecheck web-typecheck

test: api-test web-test

check: lint typecheck test

prod-up:
	$(COMPOSE) -f docker-compose.production.yml up -d --build

prod-down:
	$(COMPOSE) -f docker-compose.production.yml down

clean:
	$(COMPOSE) down --remove-orphans
	rm -rf apps/web/.next apps/web/coverage apps/api/.pytest_cache apps/api/.mypy_cache \
		apps/api/.ruff_cache apps/api/htmlcov apps/api/.coverage
