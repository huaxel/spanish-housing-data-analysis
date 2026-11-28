# Tourism-panel uncertainty: interpretation, not a new estimator

Added 2026-10-08 in [`evidence/pages/incertidumbre.md`](../evidence/pages/incertidumbre.md).
All four existing Barcelona municipal specifications are presented rather
than selecting the most favorable interval. No model code, estimates,
bootstrap repetitions or central mart inputs are changed.

## What is actually available

`explorations/panel_tourist.py` already writes coefficients, clustered
standard errors, approximate normal `ci95` endpoints, and wild-bootstrap
zero-null p-values into `artifacts/panel_tourist.json`. The normal ranges
are coefficient ± **1.96** CR1 standard errors, using the **95%** nominal
normal approximation. The source rounds estimates, standard errors and
endpoints independently; the exporter validates their consistency within
rounding tolerance rather than silently changing the endpoints.

The municipal outcome is year-on-year sale/rent growth expressed in
percentage points. Exposure is the change in registered tourist dwellings
per thousand residents; the ratio can change because population changes,
not just because licenses change. Municipality and year effects are
absorbed; the augmented specification controls for population growth.

These are adjusted associations. Endogenous licensing, incomplete registry
coverage, restricted within variation, composition changes and omitted
variables prevent a causal interpretation. Sale and rent samples differ;
municipal and provincial cross-sections are different designs.

## What is not available

The existing wild-bootstrap routine imposes the null coefficient zero.
Its `t_star_ci95` endpoints are percentiles of a null distribution of
studentized statistics, not confidence bounds for the coefficient. They
must not be relabeled as a bootstrap effect interval or mechanically
transformed into one. A p-value for zero is not a posterior probability of
zero and does not establish negligible associations.

No calibrated bootstrap coefficient confidence set, formal equivalence
test, sampling-power calculation or confidence interval for cross-sectional
correlations is added. The individual normal ranges do not supply joint
coverage across all specifications or account for measurement/model bias.

## Do two official rent series even agree?

The two official series compare different quantities. SERPAVI reports the
median rent per square metre of collective housing; IPVA is a rent price index
covering both collective and single-family housing. Both use tax data, so this
is a check across measures, not independent source validation. Match official
municipality codes with published observations at both ends of each window:

| Window | Municipalities | IPVA median change | SERPAVI median change | Spearman | Median paired gap (IPVA − SERPAVI) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2013→2023 | 697 | +15.82% | +32.51% | +0.679 | −16.54 pp |
| 2019→2023 | 702 | +8.03% | +16.15% | +0.703 | −8.02 pp |
| 2019→2024 | 701 | +11.62% | +22.09% | +0.758 | −10.64 pp |

The ordering of rent growth is similar, but growth in the SERPAVI median is
roughly twice as large. That does not establish which measure is closer to a
constant-quality rent change in any particular town. See [methods and coverage](explorations/ipva_rent_index.md).

## Does the deposit register's balance measure rented-stock growth?

A second cross-measure check, on the register side. INCASÒL's rental-deposit
balances count registrations and cancellations; SERPAVI counts contracts
declared in the income-tax files. If the first were a usable estimate of the
second's annual change, the two would move together. They do not.

| Barcelona city, habitual rentals | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Deposit net balance | +3,586 | −4,820 | +9,661 | +9,073 | +6,510 | +2,724 |
| Change in declared contracts | +2,742 | +2,414 | +3,419 | +2,689 | +4,766 | +2,630 |

They agree once (**2024**, **94** apart) and disagree elsewhere; in 2020 the
register lost contracts while the declared stock grew. The balance is larger
in magnitude than the stock change in every overlap year, so it is not a
scaled estimate either. The two measure different things — filings against
contracts in force in a tax year — and no reconciliation is published. Read
the balance as registry activity. See [deposit balances](occupancy_catalonia_deposit_balances.md).

## Exploratory magnitude control

The page allows the reader to choose a symmetric magnitude band and reports
whether each **existing approximate normal interval** is contained in that
band. This is interval arithmetic only. The initial band is illustrative,
not an economically justified threshold fixed before looking at results.
The wording deliberately avoids “equivalent,” “effect small,” or “ruled out
by bootstrap.”

A range outside the band shows that this approximation includes associations
larger than the chosen magnitude. Containment is not a causal or bootstrap
conclusion; moving the threshold after seeing the estimates does not perform
a pre-specified equivalence analysis. A future analysis would need justified
magnitudes, appropriate test inversion and a declared multiplicity policy.

## Prespecified candidate inversion (tested points only)

`scripts/invert_tourist.py` inverts the wild-cluster bootstrap-t over a grid
fixed **before this inversion** (not preregistered before examining the already
published panel results): **−2.0 to +2.0** percentage points in
**0.1** steps (**41** candidates), symmetric and wider than every published
normal range. For each candidate `c` the null `H₀: coefficient = c` is imposed
by recentering the outcome, and the same restricted-fit Rademacher bootstrap
used for the zero null runs with **1999** reps and a fixed seed. One draw
sequence is shared by all candidates (common random numbers). Candidate
`c = 0` therefore reproduces `wild_p_zero` exactly. The nominal level is
**95%** (`p ≥ 0.05` accepted).

The grid helper lives in `src/spanish_housing/wild_grid.py`, deliberately
outside `ols.py`: adding it to the estimator core would change the freshness
key of every committed model artifact. The script reconstructs the four panel
designs from `marts.duckdb` without modifying `explorations/panel_tourist.py`,
verifies n/clusters/fit against the fresh artifact, then writes
`artifacts/tourist_inversion.json` with per-candidate p, the acceptance mask,
boundary warnings and code/data hashes. `make verify` runs a cheap `--check`
that recomputes the design fits and the `c = 0` anchor; a stale source or
changed grid constants fail closed.

The page publishes **tested points only**: per-candidate p and the accepted
mask, plus the extreme accepted candidates and warnings per model. It is not
a continuous confidence interval, a causal range or an equivalence test.
Warnings distinguish "accepted set may extend below/above the grid" from "no
candidate accepted at this resolution." No model is re-estimated; the published
1999-rep zero-null p-values are unchanged. Each model's acceptance mask is
per-model nominal 95%: the inverted models carry no joint coverage claim
across models. The panel-bootstrap path floors near-zero standard errors
while the grid-inversion path tests exact zero, so degenerate-cluster
behavior can differ between the two paths; all published results are
non-degenerate and unaffected.

## Reproduction and fail-closed freshness

```bash
make inference
uv run python scripts/export_inference.py --check
```

The export is appended to `make analysis` and runs before an Evidence build.
Its read-only check is part of `make verify`. The exporter first compares
the original artifact's estimator/OLS/data hashes with current files; a
stale source is rejected rather than copied. It then validates the complete
model set, model definitions, interval construction, valid p-values and
sample/cluster counts.

`data/processed/inference.duckdb` is a presentation sidecar, read through
Evidence's `inference` connection. It contains `tourism_panel`,
`tourism_inversion` (candidate rows), `tourism_inversion_meta` (per-model
accepted extremes, counts and warnings) and an export metadata table pinning
source artifact bytes, source freshness metadata and exporter code. Read-only
verification requires exact rows and exact metadata.
Changing the source, exporter or sidecar requires regeneration; no central
mart is mutated and no unrelated estimator is rerun.

`tests/test_inference_export.py` covers malformed source content, stale
metadata, exact derivation and the distinction between normal endpoints
and null-statistic quantiles. `tests/test_evidence_uncertainty.py` executes
the actual page queries on synthetic model rows, including negative/positive
ranges, boundary containment and invalid magnitude inputs. Frontend tests
must include browser hydration and magnitude-control updates: a successful
static build alone does not establish interactive correctness.

## Claim register extension

| Claim | Evidence | Permitted interpretation |
| --- | --- | --- |
| Effect size and approximate precision | `modelos_turismo`; existing `coefs.d_tour` fields, pinned by `audit_claims.py` | Individual normal-approximation association ranges in outcome/exposure units |
| Zero-null test | Existing `wild_bootstrap.d_tour.p` | Bootstrap evidence against coefficient zero in this specification; not equivalence |
| Range containment under selected band | `banda_turismo` | Exploratory arithmetic only, no new confidence set or causal conclusion |
| Presentation freshness | `export_meta` and exact read-only verifier | Export reflects current fresh model artifact and exporter code |

## Verification record

Independent read-only review on 2026-10-08 found no important issues in the
interval labels, exposure units, exploratory containment, bootstrap
interpretation, freshness verification and displayed interval audit pins.
The review was static; executing tests and builds is a separate check.

`scripts/smoke_uncertainty.sh` (also `make evidence-smoke-uncertainty`)
asserts that all model rows hydrate and changing the magnitude control
recomputes containment without changing source coefficients or tests.

### Candidate-inversion review and fixes — 2026-10-09

Independent read-only native Codex review confirmed the recentering, restricted
fit, shared cluster draws, full-model refit and CR1 studentization match the
existing zero-null routine, and found no released field that permits
reconstructing individual outcomes. Three findings were fixed:

1. `wild_grid.py` is now part of the inversion artifact's freshness key
   (`wild_grid_sha` in `_meta`), and the audit freshness device compares it,
   so a helper change fails both `--check` and the audit instead of leaving
   nonzero candidates stale.
2. `export_inference` and `--check` now enforce `keep == (p >= alpha)` and
   that warnings exactly follow the acceptance mask (edge, resolution and
   disjoint cases). These checks establish freshness and internal
   consistency of the stored grid; they do not recompute the nonzero
   candidate p-values, so byte equality with the stored JSON plus these
   gates — not full re-derivation — is what the verify step claims.
3. The page and this document qualify "prespecified" as fixed before this
   inversion, not preregistered before examining the already published panel
   results.

The reviewer did not independently rerun the grid or the gates. The offline
test suite, lint, verification, audit and model-freshness checks passed; the
isolated strict build and hydrated browser checks (41 tested points, model
switch, caveats) passed on both the isolated preview and the live app. The live Evidence dev
server auto-restarted when its source cache was regenerated; no central mart,
estimator or deployed artifact was changed.
