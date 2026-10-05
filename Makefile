# Phase 2: quality gates. `make verify` runs lint, types, architecture and
# unit tests (definition of done). Windows has no `make`; run the same
# commands from `docs/how-to-run.md` instead.
.PHONY: up down seed reset test lint secret-scan verify

up:
	./scripts/dev_up.sh

down:
	docker compose down

seed:
	./scripts/seed.sh

reset:
	./scripts/reset.sh

test:
	python -m pytest -q
	cd frontend && npm run test --silent

lint:
	ruff check .
	ruff format --check .
	python -m mypy common/northstar_common verifier
	PYTHONPATH=.:backend:common lint-imports --config importlinter.ini
	python -m pytest tests/architecture -q
	cd frontend && npm run lint && npm run typecheck

secret-scan:
	python scripts/secret_scan.py

verify: lint secret-scan test
