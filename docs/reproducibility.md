# Reproducible setup

## Core pipeline (no Node needed)

```bash
uv sync --group dev
make gates   # lint -> fetch -> build -> verify -> audit -> test
```

- `make fetch` — downloads all pinned sources into `data/raw`
  (+ Parquet mirrors). Re-running re-pins bytes in `data/input_manifest.json`.
- `make build` — refuses to run on unpinned/changed inputs; writes
  `data/processed/marts.duckdb`, `mart_*.parquet`, `dim_territorio.parquet`,
  `coverage.json`.
- `make verify` — manifest hashes + mart integrity (51 territories, no null
  keys, IPV base identity via build). Warns when the manifest snapshot is
  older than 90 days (`MANIFEST_WARN_DAYS=` overrides) — upstream tables get
  revised, so a stale snapshot means `make fetch` may not reproduce bytes.
- `make backup` / `make restore FILE=` — timestamped tarball of `data/`
  (git-ignored, not redistributable) under `~/backups/spanish-housing`
  (`BACKUP_DIR=` overrides); restore re-runs verify after unpacking.
- `make audit` — 52 headline doc numbers re-queried against the marts; fails
  on drift. Add a claim whenever a doc states a quotable number.
- `make test` / `make lint` — offline parser/join-rule tests, ruff.

Record a reproduction with: checkout revision, `uv --version`, input-manifest
snapshot date, `coverage.json`, and test summary. `data/` is git-ignored by
design; the manifest (committed) is what makes a run auditable.

## Clean-rebuild record (2026-10-06)

`data/` wiped (backup in /tmp, since removed) and `make gates` rerun from
empty: fetch → build → verify → audit (52/52) → test (42) all green.
Regenerated manifest byte-identical to committed (60 pinned paths — no
upstream revisions in between), marts identical (342 + 1,071 rows).
This is the evidence the pipeline reproduces, not just runs.

## Evidence explorer

```bash
make evidence-install   # npm ci in evidence/ (locked dependencies)
make evidence-dev       # dev server; open the printed URL
make evidence-build     # static build
```

Open `http://localhost:3000/` (or the URL printed if the port is occupied).
Dev and build automatically run strict source extraction first. The four SQL
files in `evidence/sources/housing/` export the existing tables from
`data/processed/marts.duckdb` to Parquet; page SQL queries them as
`housing.mart_ccaa_anual`, `housing.mart_provincia_anual`,
`housing.muni_madrid`, and `housing.muni_bcn`.
The connection filename is relative to `evidence/sources/housing/`, not the
project root. If the database is missing, run `make gates` first.

After `make build` (marts), restart the service
(`systemctl --user restart housing-evidence`) or run
`cd evidence && npm run sources` to refresh the dashboard data.
Page edits hot-reload without a restart.
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
