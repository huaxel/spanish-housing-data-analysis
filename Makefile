.PHONY: sync test lint fetch build verify audit evidence-install evidence-dev evidence-build clean

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
	uv run python scripts/fetch_renta.py
	uv run python scripts/parse_edad.py
	uv run python scripts/fetch_hipotecas.py
	uv run python scripts/fetch_turisticas.py
	uv run python scripts/fetch_municipios_mad.py
	uv run python scripts/fetch_padron_municipios_mad.py
	uv run python scripts/fetch_censo2011_municipios.py
	uv run python scripts/fetch_transmisiones.py
	uv run python scripts/fetch_censo2011_vintage.py
	uv run python scripts/fetch_diba.py
	uv run python scripts/fetch_padron_municipios_bcn.py

build:
	uv run python scripts/build_marts.py

verify:
	uv run python scripts/verify_data.py

audit:
	uv run python scripts/audit_claims.py

# Full local gate: fetch -> build -> verify -> audit -> test
gates: fetch build verify audit test

evidence-install:
	cd evidence && npm install

evidence-dev:
	cd evidence && npm run dev

evidence-build:
	cd evidence && npm run build

clean:
	rm -rf .pytest_cache src/spanish_housing/__pycache__ tests/__pycache__
