# Deficit explainer: different subtractions, not missing-home counts

The `/deficit/` page compares household growth, finished dwellings and net
modelled stock growth over the existing exploration's two calendar-year
windows. It adds no causal estimator, forecast, tourist adjustment or new
source fetch. It preserves the existing exploration and its published-number
comparisons; see [the original note](explorations/deficit_vivienda.md).

## Timing contract

For calendar years `a..b`, inclusive:

- ECP household change is January 1 of `b+1` minus January 1 of `a`.
- Finished dwellings sum monthly flows in years `a..b`, Libre + Protegida.
- Net park change is December 31 of `b` minus December 31 of `a-1`.

The stock convention follows the official [INE statistical-programme entry
for Estimación del Parque de Viviendas](https://www.ine.es/dyngs/IOE/fichaProg.htm?cid=1259946014126),
inspected 2026-10-26: the MIVAU estimate updates census housing to the total
existing at December 31, incorporating construction/rehabilitation and
removing dwellings from the stock. This is a reference-date clarification,
not a refresh of the pinned CSV or a change to existing mart year labels.
Adjacent year-boundary dates correspond but are not identical timestamps.

Thus activity in 2021–2024 compares ECP levels at the start of 2021 and 2025
with modelled park levels at the end of 2020 and 2024. The second window
extends activity through 2025, using end-2025 park and start-2026 households.
Subtracting park labelled 2025 minus park labelled 2021 would instead describe
another interval; this page does not pass that off as the same flow window.
Census anchoring, revisions and modelled withdrawals limit how organically
park changes can be read, even with these boundary conventions.

## Derivation and integrity

`scripts/export_deficit.py` reads the existing deficit artifact and validates
its `_meta` against the exploration code, estimator helper and all actual
inputs (marts, monthly completions and ECP households). It independently
checks monthly completion sums against each artifact province/window,
validates the province set and national residual identity, and derives the
net stock comparison from the correctly dated mart endpoints.

The new `data/processed/deficit.duckdb` is a presentation sidecar, separate
from marts and burden/rent-income sidecars. Its `comparisons` table contains
province/window rows and an explicitly computed national sum. `export_meta`
pins exporter bytes, artifact bytes and the source proof. `--check` recomputes
and compares every row and metadata field without writing. It fails closed
on stale source proof, unexpected keys, duplicate monthly/stock observations,
negative completion counts or contradictory artifact arithmetic. `make deficit`
regenerates only this derived presentation sidecar; it does not refit models
or regenerate the source artifact.

The analysis recipe exports the sidecar after regenerating the existing
deficit artifact; `make verify` checks it. Evidence dev/build entry points
also export it before strict source extraction. From an existing verified
checkout:

```bash
make deficit
uv run python scripts/export_deficit.py --check
make lint test verify audit
# Build Evidence in an isolated copy if the dev service owns its template.
```

On a clean checkout the full pipeline must produce the source artifact first;
`make deficit` is not a substitute for `make analysis` when that artifact is
missing or stale. The sidecar is git-ignored like other derived outputs and
not added to the input manifest: freshness is proved from the existing
pinned inputs and reviewed artifact. No existing datasets are rewritten.

## Missing values and bounds

Every raw province, month and regime is expected, including rows entirely
absent from the monthly input. A published zero is observed; a null or absent
record is not. Ceuta/Melilla are combined only after preserving both complete
cell grids. There is no silent complete-case geographic reweighting.

- Complete coverage: the published completion sum is the total for this
  measure/window, and household growth minus completions is an exact
  arithmetic residual of these inputs, not an exact economic deficit.
- Partial coverage: the observed sum is a lower bound on this nonnegative
  completion flow; household growth minus that sum is an upper bound on the
  residual. The exact residual stays null and is not plotted as an exact bar.
- No observed completion cells: the subtotal and residual bound stay null,
  not zero and not all household growth.
- Missing stock endpoint: stock change and its residual stay null, never
  interpolated or read as zero.
- National sums requiring a missing provincial value stay null. Counts of
  observed and missing monthly cells remain visible; coverage is not hidden
  by omitting affected provinces.

The exploration's previous residual values remain traceable, but where there
are missing monthly cells they are shown as subtotal-based bounds, not as
complete totals. This page does not alter the older artifact or its audits.

## Permitted interpretation

Both household and stock growth are net; neither measures gross new household
formations, latent households or currently available homes. Completions are a
flow, not listings, occupancy or a count of affordable homes. Negative changes
and residuals are valid; no growth denominator, sign filter or clipping is
introduced. Multi-year windows have different lengths and are not annualized
or treated as forecasts. There are no confidence intervals because these are
arithmetic sensitivity comparisons, not uncertainty intervals.

The page deliberately omits the exploration's partial tourism variant rather
than subtract overlapping occupancy categories or imply the unobserved foreign
buyer adjustment is available. It makes no claim about the construction
required to lower prices, an optimal local programme, usable-home shortages
or effects on young people's emancipation. See [housing access](housing_access.md).

## Checks

`tests/test_deficit_export.py` exercises timing, coverage grids, missing and
zero cells, negative changes, Ceuta/Melilla, strict national null propagation,
source-proof rejection and read-only sidecar verification. Page SQL contracts
in `tests/test_evidence_deficit.py` verify both selectors, missing exact bars,
negative results and preservation of all provinces/windows. Browser checks
exercise period and geography changes against real sidecar expectations.

### Implementation verification — 2026-10-26

Offline lint, tests, source/data verification and claim/freshness audits passed.
An isolated strict Evidence build passed without restarting the active dev
service. Browser checks matched all displayed values and nulls against the
verified sidecar for both windows, the national total, complete and incomplete
provinces, a negative completion residual and combined Ceuta/Melilla. A browser
check caught decimal year suffixes caused by Evidence's numeric export; labels
now use the window key and an offline floating-point regression protects them.
Mobile layout had no horizontal document overflow. The municipality-profile
interactive regression also passed against the combined build. Independent
read-only review found no important findings.

Only the new presentation sidecar was generated. Existing pinned inputs,
central marts, sidecars, estimator code and source artifacts were not rebuilt
or refreshed. The full network-fetch/analysis reproduction was not rerun.
No commit, push or deployment occurred.

### Reportaje reference-date correction — 2026-10-27

A final cross-page check found that the reportaje still compared park and
household levels bearing the same year labels, despite their December/January
reference-date difference. Its household section now uses the same complete
activity window as this explainer: end-2024 minus end-2020 park and start-2025
minus start-2021 ECP households. Annual bars use corresponding boundaries;
missing years stay visible as null changes. Its household-ratio chart pairs
each January household count with the previous December's park, rather than
the park at the end of that January's year. Headline values are query-bound,
not copied into the narrative.

The national headline was independently recomputed from the pinned park CSV
(provincial counts plus combined Ceuta/Melilla) and the pinned national ECP
household mirror. It matched the page queries, the sum of annual changes and
the existing deficit sidecar. All communities retained complete endpoints
and the reported direction. Regression tests also perturb irrelevant ECH
households and post-window stock levels: neither may change this section.

Offline gates, an isolated strict build, rendered headline/chart/map checks
and mobile-width checks passed. Independent read-only review found no
important issues. No datasets, estimators, source artifacts or existing
sidecars were rebuilt, and no dev-service restart, commit, push or deployment
was performed for this correction. This is not a new full-pipeline reproduction.
