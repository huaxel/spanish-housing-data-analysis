.PHONY: sync test lint fetch build verify evidence-install evidence-dev evidence-build clean

sync:
	uv sync --group dev

test:
	uv run python -m pytest -v

lint:
	uv run python -m ruff check --no-cache
	uv run python -m ruff format --check --no-cache

fetch:
	uv run python scripts/fetch_parque.py
	uv run python scripts/fetch_ipv.py
	uv run python scripts/fetch_padron.py
	uv run python scripts/fetch_censo_viviendas.py
	uv run python scripts/fetch_ecp.py
	uv run python scripts/fetch_valor_tasado.py

build:
	uv run python scripts/build_marts.py

verify:
	uv run python scripts/verify_data.py

# Full local gate: fetch -> build -> verify -> test
gates: fetch build verify test

evidence-install:
	cd evidence && npm install

evidence-dev:
	cd evidence && npm run dev

evidence-build:
	cd evidence && npm run build

clean:
	rm -rf .pytest_cache src/spanish_housing/__pycache__ tests/__pycache__
