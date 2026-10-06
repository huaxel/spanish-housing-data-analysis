# Identification: what a causal extension would take

Status: scoping memo only — no estimates, no claims. The v1 stance
(descriptive co-movements) stands; this records which designs could
survive contact with the data and what each would cost to build.

## The estimands (pick one — they need different designs)

1. **Supply → prices:** effect of additional dwellings on price growth.
   Needs supply-side variation orthogonal to demand.
2. **Demand → prices:** effect of population/household inflows on prices.
   Needs demand-side variation orthogonal to supply conditions.

Everything in the repo so far loads on (2) descriptively (migration refill,
fragmentation, cohort) while the policy question is mostly (1). Do not
mix them: instruments for one do not identify the other.

## Candidate designs, ranked by feasibility

### A. Migration shift-share for demand → prices (feasible, not light)

2000s Latin-American immigration × historical settlement networks:
Bartik-style instrument = 1990s province nationality shares × national
inflow surge. First stage is strong by construction in the boom years;
exclusion rests on historical shares being unrelated to 2000s local
supply shocks conditional on FE — the standard (contested, acceptable)
shift-share argument.
Data: Tempus DPOP has NO nationality tables (65 tables checked) and EM
flows (24322) start 2008 — but the jaxi padrón-continuo file e245/p08
(1998–2022, 137 nacionalidades × provincia) supplies origin-level
*stocks*, now pinned (`padron_extranjeros_origen`, 544,575 cells). The
*surge* half is built as national net change by origin
(`explorations/bartik_surge.py`: Ecuador +131k in 2003, Colombia +104k
in 2002, Morocco +91k in 2005, Romania +205k in 2008 on EU accession,
Venezuela +51k in 2020). Caveat: net change conflates inflows,
outflows, deaths and naturalizations — a proxy for the surge, built
descriptively. Design A is now data-complete; only the estimation +
read remain. The instrument *values* are additionally constructed
(`explorations/bartik_predict.py`: 1998 origin levels × leave-one-out
national growth → predicted inflow per 1,000 1998 inhabitants,
`artifacts/bartik_predicted.json`, mechanical asserts only) — e.g.
Madrid +348/1000 by 2008 vs +175 actual net. No first stage, no 2SLS:
constructing the series is plumbing, interpreting it is estimation. Feasible
variants with pinned-style data: 2008+ flow-based design (bust/recovery
window) or 2021+ ECP-nationality refill design (different shock, own
shares). Panel: provincias × window, CCAA + year FE, cluster by
provincia, AR CIs.

### B. Saiz elasticity for supply → prices (feasible — probe done 2026-10-06)

Developable-land share (slope + water masks) × national demand as
supply-elasticity instrument, à la Saiz (2010). Exclusion is the usual
geography-only-via-supply argument.

**Data WAS thought to be NOT in reach — that was wrong.**
`docs/explorations/saiz_gis_probe.md` builds the full 52-provincia
series from Copernicus DEM GLO-30 (AWS Open Data, public) + GISCO NUTS-3
during one session: 2.6 GB, ~2 minutes, no new committed dependencies,
spread 0.07 (Valladolid) → 0.92 (Gipuzkoa) and face-valid. Spanish IGN
is unreachable from here, but it was never needed. What remains is the
exclusion argument and pipeline discipline, not data acquisition.

Threshold is **15% grade (8.53°), not 15°** — and GLO-30 is a DSM, so the
raster must be averaged to 90 m to match Saiz. Both traps are documented
in the probe.

The plausible amenity/tourism-terrain confound is unresolved and is the
real cost of this design.

**Mechanism looks absent (2026-10-06).** Two follow-ups
(`docs/explorations/panel_saiz.md`, `panel_saiz_municipal.md`) test whether
terrain moderates anything that matters here, and it does not: the build
premise is null, the direct terrain→price association is null at provincia
grain, and the migration→price effect is right-signed but indistinguishable
across constraint groups (high τ 0.74 vs low 0.64). Moving to municipal
grain — 0.00–1.00 constraint spread within Barcelona province, real
starts/completions, density control — does **not** restore it. Combined
with the tourist-panel null, that is three independent nulls. See §Recommended
sequence item 3.

### C. Tourist-demand shift-share (feasible, wrong estimand for supply)

International arrivals × coastal/urban exposure → local demand shocks.
Identifies demand → prices/rents at municipal grain (DIBA + VTE already
pinned make Barcelona the pilot). Says nothing about supply effects —
useful as the demand half of a two-design paper, not alone.

### D. Designs that don't work here

- National policy breaks (Ley del Suelo 2008 valuation change): no
  cross-section, absorbed by year FE.
- Granular IV à la Gabaix-Koijen: needs municipal construction
  microdata we don't have.
- Lagged supply as its own instrument: fails exclusion on persistence
  grounds; the repo's own regime analysis shows why (overhang correlates
  with the bust that caused it).

## Power reality

n = 17 CCAA cannot support IV with clustered SEs (the wild bootstrap
already strains at description). Any design runs at **provincia grain**
(n ≈ 50 × T) minimum, municipal where the outcome allows (rents,
transacciones). First-stage F and weak-IV-robust CIs (Anderson-Rubin,
not t-stats) are non-negotiable reporting.

## Recommended sequence

1. A (migration shift-share, provincias 2001–2011): data-light, answers
   the demand half, reuses pinned Padrón/ECP patterns. **DONE** — merged
   with the split-sample qualifier; independent read still owed.
2. C (tourist exposure, Barcelona pilot): municipal, already-pinned data.
   **DONE** — municipal null.
3. B (Saiz GIS build): prerequisite (A or C shows the machinery works)
   is met and the data/tooling blocker was overstated — see the probe. But
   the *mechanism* does not appear in this outcome at either provincia or
   municipal grain (`panel_saiz.md`, `panel_saiz_municipal.md`).
   Recommendation: **leave B unbuilt as an instrument** — not for lack of
   data, but because three independent nulls say the terrain channel does
   little measurable work here. The stated reopen condition ("a second
   province, price levels") was attempted and **cannot be met**: Madrid's
   priced municipios span constraint 0.00–0.25 against the province's
   0.00–0.98, and its one significant association is a centrality gradient
   wearing a terrain proxy. No Spanish province publishes municipal price
   series for its steep municipios. If terrain is ever revisited it needs a
   design comparing terrain to terrain (matched pairs / within-range
   variation), not cross-sectional slopes.
4. Nothing causal merges into synthesis until an independent read of the
   design — same bar as v1's methods review (plan milestone 5). The read
   questions for design A are written out in `docs/review_brief.md`;
   A was merged ahead of that read under user direction, and the read is
   still owed.

## What would need building (when, not now)

- ~~`fetch_migracion.py` + shift-share constructor + weak-IV diagnostics~~
  DONE — see `explorations/iv_migration.py`, `bartik_*.py`, `ols.py`.
- GIS pipeline: the raster reduction exists (`scripts/probe_saiz_gis.py`),
  but its **manifest treatment is still an open design decision** — pin
  103 tiles (2.6 GB) by hash as a second manifest class, or pin the tile
  list + source version and treat rasters like `data/` (git-ignored but
  reproducible). The latter matches existing repo practice.
- Saiz-series sensitivity table (resolution 30/90/180 m, threshold
  10/15/20% grade) and audit claims for the committed series.
