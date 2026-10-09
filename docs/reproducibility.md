# Reproducible setup

## Core pipeline (no Node needed)

```bash
uv sync --group dev
make gates   # lint -> fetch -> build -> analysis -> verify -> audit -> test
```

- `make fetch` — downloads all pinned sources into `data/raw`
  (+ Parquet mirrors). Re-running re-pins bytes in `data/input_manifest.json`.
- `make build` — refuses to run on unpinned/changed inputs; writes
  `data/processed/marts.duckdb`, `mart_*.parquet`, `dim_territorio.parquet`,
  `coverage.json`.
- `make analysis` — re-runs the deterministic estimators whose outputs
  `make audit` requires (git-ignored `artifacts/` JSONs plus the committed
  `explorations/iv_results.json` / `panel_saiz_results.json` copies the
  audit freshness-checks). `bartik_predict` runs first: `iv_migration` +
  `panel_saiz` read its instrument. Required on a clean checkout (where
  `artifacts/` is absent) and after every `make build` (see below).
  Runtime: ~30 min (pure-Python wild bootstraps dominate; `panel_quarterly`
  alone ~11 min, `panel_adjusted` ~5 min) — the Makefile prints per-script
  progress.
- `make verify` — manifest hashes + mart integrity (51 territories, no null
  keys, IPV base identity via build). Warns when the manifest snapshot is
  older than 90 days (`MANIFEST_WARN_DAYS=` overrides) — upstream tables get
  revised, so a stale snapshot means `make fetch` may not reproduce bytes.
- `make backup` / `make restore FILE=` — timestamped tarball of `data/`
  (git-ignored, not redistributable) under `~/backups/spanish-housing`
  (`BACKUP_DIR=` overrides); restore re-runs verify after unpacking.
- `make audit` — 460 headline doc numbers (192 mart + 24 committed-model + 19 probe + 6 sensitivity + 17 panel_saiz + 11 panel_saiz_municipal + 5 probe anchors + 6 madrid leg + 36 ratio_ccaa + 13 serpavi + 13 tourist_rents + 7 madrid_vacancy + 10 panel_provincial + 23 panel_quarterly + 4 wild-AR + 6 hypothesis_01 + 14 panel_tourist + 38 panel_adjusted + 16 municipios_nacional) re-queried, plus 16 model-freshness checks (each estimator output must postdate its script, `ols.py`, and the inputs it actually reads — `marts.duckdb` for the marts-based ones, the raw hipotecas/valor files for the quarterly panel, `bartik_predicted.json` for the IV + Saiz outputs, the committed terrain JSONs for the Saiz family); a green audit can no longer pass on stale model numbers; fails
  on drift. Add a claim whenever a doc states a quotable number. `make audit` also runs
  `make audit-docs`, which inverts the check for the narrative surface (synthesis + README):
  every result-like number there must match an audited claim or an explicit allowlist entry —
  the claims pin artifacts, the doc check pins the docs. Note:
  `marts.duckdb` is not byte-stable across rebuilds (container metadata
  drifts even with identical inputs), so every `make build` invalidates
  the six model freshness keys — run `make analysis` after a rebuild
  (their numbers must not move; if they do, the rebuild changed
  the data, not just the container).
- `make test` / `make lint` — offline parser/join-rule tests, ruff.

Record a reproduction with: checkout revision, `uv --version`, input-manifest
snapshot date, `coverage.json`, and test summary. `data/` is git-ignored by
design; the manifest (committed) is what makes a run auditable.

## Clean-rebuild record (2026-10-06, rerun 20:15 UTC)

`data/` wiped (backup in `~/backups/spanish-housing/`) and `make gates`
rerun from empty: fetch → build → verify → audit (199/199) → test (52)
all green. marts byte-identical to the pre-wipe build (sha256 of
`mart_*.parquet` + `dim_territorio.parquet` match; 342 + 1,275 rows
unchanged), so the pipeline reproduced — not just ran. This run also
re-fetched and re-pinned all newer sources (Censo Anual 68521 static
CSV, SERPAVI 71 MB Excel, intensidad 59531 CSV): all reproduce
byte-identical and the newer mart tables (`serpavi_municipal` 716,889
rows, `censo2021_intensidad` 57,330 rows) are present.

The rerun caught one real (minor) flaw in the morning: the regenerated
manifest was not byte-identical to committed, only set-identical.
`manifest.record` appended one entry per fetch, so JSON byte order
silently followed fetch sequence. Fixed with `sort_keys=True` on write
(now deterministic and idempotent); the committed manifest is the sorted
form, so a same-day regeneration is byte-identical. This is the evidence
the pipeline reproduces, not just runs.

## Evidence explorer

```bash
make evidence-install   # npm ci in evidence/ (locked dependencies)
make evidence-dev       # dev server; open the printed URL
make evidence-build     # static build
make evidence-deploy    # publish to Cloudflare (see below)
```

### Public deploy (Cloudflare Workers Static Assets)

`make evidence-deploy` publishes `evidence/build/` to the
`vivienda-explorer` worker (`evidence/wrangler.toml` + `worker.js`).
Two subtleties, both load-bearing:

- DuckDB WASM blobs exceed the 25 MiB asset limit, so `worker.js`
  proxies `*.wasm` from pinned jsDelivr npm bytes (verified
  md5-identical to the build blobs; the check is enforced at deploy time
  by `make wasm-verify`, which `evidence-deploy` runs first — the CDN
  has no request-time integrity check of its own). Bump `WASM_VERSION`
  when `@duckdb/duckdb-wasm` updates. An R2-bucket variant was tried
  and abandoned (jurisdictional shadowing); the bucket has been deleted.
- Smoke scripts assert shipped content only: dev renders
  query-inspector chrome (`'N records ...'`) that static builds omit.
- `make evidence-build` runs `scripts/fix_build_meta.py` afterwards:
  the Evidence template hardcodes `<html lang="en">` and is regenerated
  on every build, so the script repairs it to `es` and injects per-route
  meta descriptions post-build (idempotent; fails loudly if the build
  layout changes out from under it).
- `worker.js` serves WASM cache-first from `caches.default`, filled via
  `waitUntil`. Keys are the hashed build paths, so a dependency bump
  fills new keys and can never serve stale bytes within a pinned version.
  Hashed `/_app/immutable/` files get the same treatment with an immutable
  year (Static Assets defaults those to must-revalidate — a round trip on
  every repeat visit). Verified live on both domains.
- Bundle weight (measured 2026-10-07): each route ships a ~4.8 MB JS bundle
  (~2 MB gzip), near-identical across routes — Evidence architecture, not
  fixable from here. `DataTable` already scrolls horizontally
  (`overflow-x: auto`), so wide tables need no responsive treatment.
- On any data refresh, update the `Instantánea de datos` footer date in
  every `evidence/pages/*.md` to the new manifest snapshot date before
  rebuilding — the footers are static text, not wired to the manifest.
- Deploy record: rebuilt + redeployed 2026-10-09 17:35 UTC after the
  October stock expansion (capitals + province sections, stock/rent lectura)
  and the new access/purchase/uncertainty/stock-2021 routes — the previous
  public build predated all of them; the site now serves `/stock/`,
  `/acceso/`, `/compra/`, `/incertidumbre/` and `/stock-2021/`, footers
  2026-10-09, live-smoke verified on the public domain (pinned coverage
  hydrates, barrio map renders). Version
  `7b2e6db3-2f70-454f-a43f-03ff1730bce9`.
- Custom domain `vivienda.juanbenjumea.me` is attached and serving
  byte-identical content to the workers.dev URL (verified 2026-10-09) —
  the dashboard attach happened outside this repo.

Open `http://localhost:3000/` (or the URL printed if the port is occupied).
Dev and build automatically run strict source extraction first. The five SQL
files in `evidence/sources/housing/` export the existing tables from
`data/processed/marts.duckdb` to Parquet; page SQL queries them as
`housing.mart_ccaa_anual`, `housing.mart_provincia_anual`,
`housing.muni_madrid`, `housing.muni_bcn`, and `housing.ipc_anual`.
The connection filename is relative to `evidence/sources/housing/`, not the
project root. If the database is missing, run `make gates` first.

After `make build` (marts), restart the service
(`systemctl --user restart housing-evidence`) or run
`cd evidence && npm run sources` to refresh the dashboard data.
Page edits hot-reload without a restart, but **new files under
`evidence/static/` do not** — Evidence snapshots static assets at
startup, so `make geo` (or any new static file) needs a service
restart before the dev server serves it.
`make evidence-dev` and `make evidence-build` refuse to run while port
3000 is busy or the service is active (both regenerate the same
`.evidence/template/` directory); stop the service first, then restart it
after the build. Override only if you know why with `ALLOW=1`.
To preview the static build: `cd evidence && npm run preview`.
For remote access, explicitly opt in with
`cd evidence && npm run dev -- --host 0.0.0.0` (no authentication; trusted
networks only).

### Tailnet-only access

Keep dev bound to localhost and forward a dedicated Tailscale TCP port:

```bash
cd evidence && npm run dev -- --host 127.0.0.1
# in another terminal:
tailscale serve --bg --tcp=3000 tcp://127.0.0.1:3000
# open http://<tailscale-ip>:3000/ from a device in the tailnet
```

On the current machine: `http://100.116.127.30:3000/`.
This leaves existing Tailscale HTTPS routes untouched and does not enable
Funnel/public access. Tailnet ACLs still apply. The Tailscale proxy stays
configured across reboots, and the user service below starts the dev server
at boot, so the tailnet address keeps working unattended.
Remove just this proxy with `tailscale serve --tcp=3000 off` (do not reset
all Serve configuration).

Verify everything with `make evidence-smoke`: dev liveness on all four
pages locally and via Tailscale, content markers in the static build,
the Tailscale proxy, and the extracted source manifest.
`make evidence-smoke-browser` goes further in a real (headless) browser via
the global `playwright-cli`: it waits for chart hydration on all four pages
and asserts canvas counts, key content, and zero page errors.

The dev server runs as the user service `housing-evidence.service`
(`~/.config/systemd/user/`), enabled for boot via linger. It binds only to
localhost; Tailscale forwards tailnet port 3000 to it. Useful commands:
`systemctl --user status housing-evidence`,
`journalctl --user -u housing-evidence -f`,
`systemctl --user restart housing-evidence` (e.g. after rebuilding marts).
Disable with `systemctl --user disable --now housing-evidence`.

### Resolved startup blocker

Evidence 40.1.8 is pinned, with explicit core-components, tailwind, and DuckDB
plugins. The previous ESM-only config-loading failure was caused by the app's
missing `"type": "module"` in `evidence/package.json`; adding it lets Vite
load the generated config as ESM without modifying dependencies or generated
files. The datasource also needs a `name`, registered plugin, and export SQL.
Both source extraction and the static build run in strict mode to surface
errors. Source extraction (342 regional / 1,071 provincial rows), strict build,
and dev HTTP checks were verified on Node 24.21.0.

The pinned upstream dependency tree has npm audit advisories (40 remaining,
reviewed 2026-10-06). All except one have no compatible fix; the rest resolve
only via a breaking Evidence downgrade (40.1.8 → 29.x) that would break the
app, so they are accepted. The single fixable item, `cookie` <0.7.0, is
pinned to 0.7.2 via `overrides` (SvelteKit uses only its stable
`parse`/`serialize` API); strict build and smoke tests pass with it.
Do not run `npm audit fix --force`. Containment instead of patching: dev
binds to localhost only, Tailscale serves tailnet-only TCP with no Funnel,
and the service manager restarts it on failure.

## Adding a source (see queue in the project plan)

1. Locate the table with `uv run python scripts/ine_discover.py "<keyword>"`.
2. Write `scripts/fetch_<x>.py`: staged download, raw + Parquet mirror,
   `manifest.record(...)`.
3. Extend `scripts/build_marts.py` (+ guards, never silent imputation),
   `docs/sources.md`, `docs/data_dictionary.md`, `docs/methods.md` if the
   number needs interpretation guidance.
4. `make gates`, review the diff to `coverage.json`.
