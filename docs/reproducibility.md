# Reproducible setup

## Core pipeline (no Node needed)

```bash
uv sync --group dev
make gates   # fetch -> build -> verify -> test
```

- `make fetch` — downloads the four pinned sources into `data/raw`
  (+ Parquet mirrors). Re-running re-pins bytes in `data/input_manifest.json`.
- `make build` — refuses to run on unpinned/changed inputs; writes
  `data/processed/marts.duckdb`, `mart_*.parquet`, `dim_territorio.parquet`,
  `coverage.json`.
- `make verify` — manifest hashes + mart integrity (51 territories, no null
  keys, IPV base identity via build).
- `make test` / `make lint` — offline parser/join-rule tests, ruff.

Record a reproduction with: checkout revision, `uv --version`, input-manifest
snapshot date, `coverage.json`, and test summary. `data/` is git-ignored by
design; the manifest (committed) is what makes a run auditable.

## Evidence explorer

```bash
make evidence-install   # npm install in evidence/
make evidence-dev       # dev server; open the printed URL
make evidence-build     # static build
```

Evidence version is pinned in `evidence/package.json` (40.1.8, 2026-10-05).
Pages query the committed-path Parquet marts via the `housing`
DuckDB source (`evidence/sources/housing/connection.yaml`).

## Known blocker (2026-10-05): vite build fails in this environment

`npm run build` and `npm run dev` both fail loading
`.evidence/template/vite.config.js`: esbuild's `externalize-deps` plugin
tries to `require()` ESM-only packages (`@evidence-dev/sdk/*`,
`@sveltejs/kit/vite`) on Node 24, 22 and 20 alike. Install needs
`legacy-peer-deps=true` (see `evidence/.npmrc`). All page SQL is validated
directly against `marts.duckdb` (see project log), so the data contract holds
— only the JS toolchain needs a supported environment or a version bump.
Try: a clean `npm create evidence` scaffold for comparison, or newer
`@evidence-dev/evidence` once the pin is revisited.

## Adding a source (queued 5–8)

1. Locate the table with `uv run python scripts/ine_discover.py "<keyword>"`.
2. Write `scripts/fetch_<x>.py`: staged download, raw + Parquet mirror,
   `manifest.record(...)`.
3. Extend `scripts/build_marts.py` (+ guards, never silent imputation),
   `docs/sources.md`, `docs/data_dictionary.md`, `docs/methods.md` if the
   number needs interpretation guidance.
4. `make gates`, review the diff to `coverage.json`.
