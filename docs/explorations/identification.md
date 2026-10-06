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

### B. Saiz elasticity for supply → prices (credible, heavy)

Developable-land share (slope + water/wetland masks) × national demand
as supply-elasticity instrument, à la Saiz (2010). Exclusion is the
usual geography-only-via-supply argument.
Data: NOT in reach — needs a GIS build (IGN MDT elevation, SIOSE/Corine
land cover) reduced to province elasticities. Weeks, not days, plus a
new pipeline discipline (rasters don't fit the manifest-pin pattern
without thought). The single biggest data investment on this list.

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
   the demand half, reuses pinned Padrón/ECP patterns.
2. C (tourist exposure, Barcelona pilot): municipal, already-pinned data.
3. B (Saiz GIS build): only after A or C shows the machinery works.
4. Nothing causal merges into synthesis until an independent read of the
   design — same bar as v1's methods review (plan milestone 5).

## What would need building (when, not now)

- `fetch_migracion.py` (nationality shares by provincia) + shift-share
  constructor in explorations + weak-IV diagnostics in `ols.py`
  (AR confidence sets, first-stage F with clustered SEs).
- GIS pipeline + manifest treatment for rasters (design decision open).
