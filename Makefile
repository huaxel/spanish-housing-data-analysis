.PHONY: sync test lint fetch geo build analysis inference stock-rent verify audit audit-docs backup restore dashboard evidence-install evidence-dev evidence-build evidence-smoke evidence-smoke-browser evidence-smoke-purchase evidence-smoke-uncertainty evidence-smoke-stock wasm-verify clean

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
	uv run python scripts/fetch_padron_municipios_vlc.py
	uv run python scripts/fetch_padron_municipios_sev.py
	uv run python scripts/fetch_padron_municipios_all.py
	uv run python scripts/fetch_barrios_mad.py
	uv run python scripts/fetch_barrios_sev.py
	uv run python scripts/fetch_sevilla_oferta.py
	uv run python scripts/fetch_sevilla_context.py
	uv run python scripts/fetch_barrios_bcn.py
	uv run python scripts/fetch_barrios_bcn_compra.py
	uv run python scripts/fetch_desahucios.py
	uv run python scripts/fetch_housing_overburden.py
	uv run python scripts/fetch_cadastre_stock.py
	uv run python scripts/fetch_cadastre_capitals.py
	uv run python scripts/fetch_cadastre_province.py
	uv run python scripts/fetch_aeat_viviendas.py
	uv run python scripts/fetch_censo_secciones.py
	uv run python scripts/fetch_rmdvp.py
	uv run python scripts/fetch_sevilla_income.py
	uv run python scripts/build_sevilla_2021.py
	uv run python scripts/build_ecv_joint.py

# Frontend geography (vendored evidence/static asset, not an analysis input):
# Eurostat GISCO LAU polygons simplified to municipal CODIGOINE join keys.
# Re-run after evidence/static/geo/municipios.geojson is deleted; restart
# the dev service afterwards (Evidence snapshots static/ at startup).
geo:
	uv run python scripts/fetch_muni_geo.py

build:
	uv run python scripts/build_marts.py

verify:
	uv run python scripts/verify_data.py
	uv run python scripts/verify_housing_overburden.py
	uv run python scripts/build_ecv_joint.py --check
	uv run python scripts/fetch_cadastre_stock.py --check
	uv run python scripts/fetch_cadastre_capitals.py --check
	uv run python scripts/fetch_cadastre_province.py --check
	uv run python scripts/build_sevilla_2021.py --check
	uv run python scripts/analyze_stock_rent.py --check
	uv run python scripts/export_inference.py --check
	uv run python scripts/invert_tourist.py --check

audit: audit-docs
	uv run python scripts/audit_claims.py

# Doc-number cross-check: every result-like number in the narrative docs
# must match an audited claim or an explicit allowlist entry (closes the
# audit's blind spot — it pins artifacts, not docs).
audit-docs:
	uv run python scripts/audit_doc_numbers.py

# Deterministic estimators whose outputs audit requires (git-ignored
# artifacts/ JSONs + committed explorations/*.json freshness copies).
# bartik_predict first: iv_migration + panel_saiz read its instrument.
# ~30 min total (hypothesis_01 + municipios_nacional are seconds):
# pure-Python wild bootstraps dominate (panel_quarterly
# alone ~11 min, panel_adjusted ~5 min). Progress prints per script.
analysis:
	@echo "[analysis 1/18] bartik_predict (instrument)"
	uv run python explorations/bartik_predict.py
	@echo "[analysis 2/18] iv_migration"
	uv run python explorations/iv_migration.py
	@echo "[analysis 3/18] panel_saiz"
	uv run python explorations/panel_saiz.py
	@echo "[analysis 4/18] panel_provincial"
	uv run python explorations/panel_provincial.py
	@echo "[analysis 5/18] panel_adjusted (~5 min)"
	uv run python explorations/panel_adjusted.py
	@echo "[analysis 6/18] panel_tourist"
	uv run python explorations/panel_tourist.py
	@echo "[analysis 7/18] panel_quarterly (~11 min)"
	uv run python explorations/panel_quarterly.py
	@echo "[analysis 8/18] ratio_ccaa"
	uv run python explorations/ratio_ccaa.py
	@echo "[analysis 9/18] serpavi_analysis"
	uv run python explorations/serpavi_analysis.py
	@echo "[analysis 10/18] tourist_rents"
	uv run python explorations/tourist_rents.py
	@echo "[analysis 11/18] panel_saiz_municipal"
	uv run python explorations/panel_saiz_municipal.py
	@echo "[analysis 12/18] panel_saiz_madrid"
	uv run python explorations/panel_saiz_madrid.py
	@echo "[analysis 13/18] panel_saiz_madrid_vacancy"
	uv run python explorations/panel_saiz_madrid_vacancy.py
	@echo "[analysis 14/18] wild_ar_bust"
	uv run python explorations/wild_ar_bust.py
	@echo "[analysis 15/18] test_absorption_hypothesis"
	uv run python explorations/test_absorption_hypothesis.py
	@echo "[analysis 16/18] municipios_nacional (descriptive)"
	uv run python explorations/municipios_nacional.py
	@echo "[analysis 17/18] barrios_bcn_yield (descriptive)"
	uv run python explorations/barrios_bcn_yield.py
	@echo "[analysis 18/18] desahucios_renta (descriptive)"
	uv run python explorations/desahucios_renta.py
	uv run python scripts/analyze_stock_rent.py
	uv run python explorations/cadastre_eras.py
	uv run python explorations/cadastre_age_rent.py
	uv run python explorations/cadastre_era_rehab.py
	uv run python explorations/cadastre_era_quality.py
	uv run python explorations/cadastre_era_surface.py
	uv run python explorations/cadastre_vacancy_alignment.py
	uv run python explorations/cadastre_household_alignment.py
	uv run python explorations/cadastre_capitals.py
	uv run python explorations/cadastre_province.py
	uv run python explorations/cadastre_malaga_barrios.py
	uv run python explorations/cadastre_granada_distritos.py
	uv run python explorations/censo_vintage.py
	uv run python scripts/invert_tourist.py
	uv run python scripts/export_inference.py

stock-rent:
	uv run python scripts/analyze_stock_rent.py
	uv run python explorations/cadastre_eras.py
	uv run python explorations/cadastre_age_rent.py
	uv run python explorations/cadastre_era_rehab.py
	uv run python explorations/cadastre_era_quality.py
	uv run python explorations/cadastre_era_surface.py
	uv run python explorations/cadastre_vacancy_alignment.py
	uv run python explorations/cadastre_household_alignment.py
	uv run python explorations/cadastre_capitals.py
	uv run python explorations/cadastre_province.py
	uv run python explorations/cadastre_malaga_barrios.py
	uv run python explorations/cadastre_granada_distritos.py

inference:
	uv run python scripts/invert_tourist.py
	uv run python scripts/export_inference.py

# Full local gate: lint -> fetch -> build -> analysis -> verify -> audit -> test
gates: lint fetch build analysis verify audit test

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

# fix_build_meta repairs <html lang> (Evidence template hardcodes en) and
# injects per-route descriptions. Always runs post-build so deploys inherit it.
evidence-build:
	@if [ -z "$(ALLOW)" ] && { ss -ltn 2>/dev/null | grep -q '127.0.0.1:3000 ' || systemctl --user is-active -q housing-evidence.service; }; then echo "Refusing: dev server/service owns .evidence/template/. Stop it first: systemctl --user stop housing-evidence (or make evidence-build ALLOW=1)."; exit 1; fi
	uv run python scripts/invert_tourist.py --check
	uv run python scripts/export_inference.py
	uv run python scripts/fetch_cadastre_stock.py --check
	uv run python scripts/fetch_cadastre_capitals.py --check
	uv run python scripts/fetch_cadastre_province.py --check
	uv run python scripts/build_sevilla_2021.py --check
	uv run python scripts/analyze_stock_rent.py
	cd evidence && npm run build
	uv run python scripts/fix_build_meta.py

# Cloudflare deploy: DuckDB WASM blobs exceed the 25 MiB Workers asset
# limit, so worker.js proxies them from the pinned npm CDN (byte-identical
# to the build blobs — see worker.js); build-cf is build/ minus *.wasm.
# Re-run after every evidence-build (hashed filenames change). Custom domain
# vivienda.juanbenjumea.me attaches via workers.dev dashboard/API once.
# worker.js proxies *.wasm from jsDelivr at request time with no
# request-time integrity check; this gate enforces the md5 identity its
# header documents instead of trusting it. Runs before every deploy.
WASM_VERSION = $(shell grep -o 'WASM_VERSION = "[^"]*"' evidence/worker.js | cut -d'"' -f2)

wasm-verify:
	@set -e; ls evidence/build/_app/immutable/assets/duckdb-*.wasm >/dev/null 2>&1 \
	  || { echo "no wasm blobs in evidence/build — run make evidence-build"; exit 1; }; \
	for b in evidence/build/_app/immutable/assets/duckdb-*.wasm; do \
	  kind=$$(basename "$$b" | sed 's/\..*//'); \
	  url="https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@$(WASM_VERSION)/dist/$$kind.wasm"; \
	  if [ "$$(curl -fsSL "$$url" | md5sum | cut -d' ' -f1)" = "$$(md5sum "$$b" | cut -d' ' -f1)" ]; then \
	    echo "wasm OK: $$kind matches CDN $(WASM_VERSION)"; \
	  else \
	    echo "wasm MISMATCH: $$b differs from $$url — bump WASM_VERSION in evidence/worker.js"; \
	    exit 1; \
	  fi; \
	done

evidence-deploy: wasm-verify
	rm -rf evidence/build-cf && cp -r evidence/build evidence/build-cf
	rm -f evidence/build-cf/_app/immutable/assets/*.wasm
	cd evidence && npx wrangler deploy

evidence-smoke:
	bash scripts/smoke_dashboard.sh

evidence-smoke-browser:
	bash scripts/smoke_browser.sh

evidence-smoke-purchase:
	bash scripts/smoke_purchase.sh

evidence-smoke-uncertainty:
	bash scripts/smoke_uncertainty.sh

evidence-smoke-stock:
	bash scripts/smoke_stock.sh

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
