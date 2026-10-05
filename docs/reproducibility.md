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
- `make audit` — 17 headline doc numbers re-queried against the marts; fails
  on drift. Add a claim whenever a doc states a quotable number.
- `make test` / `make lint` — offline parser/join-rule tests, ruff.

Record a reproduction with: checkout revision, `uv --version`, input-manifest
snapshot date, `coverage.json`, and test summary. `data/` is git-ignored by
design; the manifest (committed) is what makes a run auditable.

## Clean-rebuild record (2026-10-06)

`data/` wiped (backup in /tmp, since removed) and `make gates` rerun from
empty: fetch → build → verify → audit (26/26) → test (11) all green.
Regenerated manifest byte-identical to committed (37 pinned files — no
upstream revisions in between), marts identical (342 + 1,071 rows).
This is the evidence the pipeline reproduces, not just runs.

## Evidence explorer

```bash
make evidence-install   # npm install in evidence/
make evidence-dev       # dev server; open the printed URL
make evidence-build     # static build
```

Evidence version is pinned in `evidence/package.json` (40.1.8, 2026-10-05).
Pages query the committed-path Parquet marts via the `housing`
DuckDB source (`evidence/sources/housing/connection.yaml`).

## Known blocker (2026-10-06): Evidence 40.1.8 cannot build — upstream bug

`npm run build` and `npm run dev` both die loading
`.evidence/template/vite.config.js`. Root cause, verified 2026-10-06:
the template imports `@sveltejs/kit/vite`, whose `exports` entry has only
an `import` condition (kit 2.8.4, no `require`/`default`), while vite 5.4's
config bundler (esbuild `externalize-deps`) loads it via `require()`.
Result: `ERR_PACKAGE_PATH_NOT_EXPORTED` on Node 20, 22 and 24 alike —
no Node version can satisfy it, and 40.1.8 is the newest release, so no
bump fixes it. Ruled out: dependency skew (fails identically on a clean
strict tree), Node version, peer resolution (`overrides.typescript` gives
a clean strict install; that part is kept).

Workarounds when revisiting: patch the generated template config loading,
try `npm create evidence` output of a newer release once published, or
render the (already SQL-validated) pages elsewhere. All page SQL is
validated directly against `marts.duckdb`, so the data contract holds —
only the JS build is broken.

## Adding a source (queued 5–8)

1. Locate the table with `uv run python scripts/ine_discover.py "<keyword>"`.
2. Write `scripts/fetch_<x>.py`: staged download, raw + Parquet mirror,
   `manifest.record(...)`.
3. Extend `scripts/build_marts.py` (+ guards, never silent imputation),
   `docs/sources.md`, `docs/data_dictionary.md`, `docs/methods.md` if the
   number needs interpretation guidance.
4. `make gates`, review the diff to `coverage.json`.
