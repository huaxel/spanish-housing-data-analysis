.PHONY: sync test lint fetch build verify audit backup restore dashboard evidence-install evidence-dev evidence-build evidence-smoke evidence-smoke-browser clean

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
	uv run python scripts/fetch_censo_anual.py
	uv run python scripts/fetch_valor_tasado.py
	uv run python scripts/fetch_renta.py
	uv run python scripts/parse_edad.py
	uv run python scripts/fetch_hipotecas.py
	uv run python scripts/fetch_ipc.py
	uv run python scripts/fetch_ech.py
	uv run python scripts/fetch_censo2021.py
	uv run python scripts/fetch_intensidad.py
	uv run python scripts/fetch_serpavi.py
	uv run python scripts/fetch_migracion.py
	uv run python scripts/fetch_padron_extranjeros.py
	uv run python scripts/fetch_turisticas.py
	uv run python scripts/fetch_municipios_mad.py
	uv run python scripts/fetch_padron_municipios_mad.py
	uv run python scripts/fetch_censo2011_municipios.py
	uv run python scripts/fetch_transmisiones.py
	uv run python scripts/fetch_censo2011_vintage.py
	uv run python scripts/fetch_censo2011_tenencia.py
	uv run python scripts/fetch_diba.py
	uv run python scripts/fetch_padron_municipios_bcn.py

build:
	uv run python scripts/build_marts.py

verify:
	uv run python scripts/verify_data.py

audit:
	uv run python scripts/audit_claims.py

# Full local gate: lint -> fetch -> build -> verify -> audit -> test
gates: lint fetch build verify audit test

dashboard:
	uv run python scripts/render_preview.py
	python3 -m http.server -d artifacts/preview 8091 --bind 0.0.0.0

evidence-install:
	cd evidence && npm ci

# The housing-evidence user service owns port 3000 and .evidence/template/.
# Manual dev would fail on the busy port; a concurrent build corrupts the
# template both commands regenerate. Stop the service first, or set ALLOW=1.
evidence-dev:
	@if [ -z "$(ALLOW)" ] && { ss -ltn 2>/dev/null | grep -q '127.0.0.1:3000 ' || systemctl --user is-active -q housing-evidence.service; }; then echo "Local dev server running? Stop it first: systemctl --user stop housing-evidence (or make evidence-dev ALLOW=1)."; exit 1; fi
	cd evidence && npm run dev

evidence-build:
	@if [ -z "$(ALLOW)" ] && { ss -ltn 2>/dev/null | grep -q '127.0.0.1:3000 ' || systemctl --user is-active -q housing-evidence.service; }; then echo "Refusing: dev server/service owns .evidence/template/. Stop it first: systemctl --user stop housing-evidence (or make evidence-build ALLOW=1)."; exit 1; fi
	cd evidence && npm run build

# Cloudflare deploy: DuckDB WASM blobs exceed the 25 MiB Workers asset
# limit, so worker.js proxies them from the pinned npm CDN (byte-identical
# to the build blobs — see worker.js); build-cf is build/ minus *.wasm.
# Re-run after every evidence-build (hashed filenames change). Custom domain
# vivienda.juanbenjumea.me attaches via workers.dev dashboard/API once.
evidence-deploy:
	rm -rf evidence/build-cf && cp -r evidence/build evidence/build-cf
	rm -f evidence/build-cf/_app/immutable/assets/*.wasm
	cd evidence && npx wrangler deploy

evidence-smoke:
	bash scripts/smoke_dashboard.sh

evidence-smoke-browser:
	bash scripts/smoke_browser.sh

# Local-only copy of data/ (git-ignored, publisher data). Override the
# destination with BACKUP_DIR=/path/to/dir. Restore with:
#   make restore FILE=<tarball>   (re-verifies after unpacking)
BACKUP_DIR ?= $(HOME)/backups/spanish-housing
BACKUP_FILE = $(BACKUP_DIR)/spanish-housing-data-$(shell date +%F).tar.gz

backup:
	mkdir -p $(BACKUP_DIR)
	tar -czf $(BACKUP_FILE) data/
	@echo "wrote $(BACKUP_FILE)"

restore:
	@if [ -z "$(FILE)" ]; then echo "usage: make restore FILE=<tarball>"; exit 1; fi
	tar -xzf $(FILE)
	uv run python scripts/verify_data.py

clean:
	rm -rf .pytest_cache src/spanish_housing/__pycache__ tests/__pycache__
