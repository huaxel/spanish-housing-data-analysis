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
Evidence's `inference` connection. It contains `tourism_panel` and an export
metadata table pinning source artifact bytes, source freshness metadata and
exporter code. Read-only verification requires exact rows and exact metadata.
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
