# Quarterly credit timing: no mortgage lead once year effects are absorbed

Computed by `explorations/panel_quarterly.py` from pinned raw inputs
(valor tasado quarterly cells + HPT monthly counts → complete quarters only;
raw output: `artifacts/panel_quarterly.json`, git-ignored). Quarterly panel,
17 CCAA × 2003–2025; y = valor-tasado Libre QoQ %; CCAA + year FE + quarter
dummies via the correct two-way within transform; SEs clustered by CCAA;
wild bootstrap-t (999 reps). Descriptive.

(Corrected 2026-10-06: the previous build regressed CCAA-demeaned
outcomes on CCAA-demeaned regressors plus *raw* year/season dummies, which
left the national cycle inside the credit lags. The old headline —
mortgage growth leading prices at L3/L5/L6 — does not survive the fix.)

## Results (n=1,156, G=17, R² 0.48)

| regressor | b (SE) | wild-p |
| --- | --- | --- |
| mortgage growth, per 10pp | −0.067 (0.051) | 0.255 |
| L1 | −0.028 (0.048) | 0.595 |
| L2 | −0.067 (0.036) | 0.088 |
| L3 | +0.066 (0.034) | 0.078 |
| L4 | −0.002 (0.037) | 0.949 |
| L5 | +0.069 (0.047) | 0.195 |
| L6 | +0.055 (0.038) | 0.196 |
| L7 | −0.099 (0.030) | **0.007** |
| L8 | −0.040 (0.031) | 0.231 |
| national rate change (pp) | −0.055 (0.207) | 0.806 |
| L1 rate change | −0.350 (0.173) | 0.057 |

## Reading

- **No mortgage lead.** L3/L5/L6 are all positive but none clears the
  bootstrap (p = 0.08/0.20/0.20); the old "credit-then-appraisal at 3–6
  quarters" shape was national-cycle leakage through the broken
  transform. Mortgage counts move with the national cycle, and once the
  year effects are correctly absorbed there is no timing evidence left.
- The only wild-significant lag is **L7, negative** (−0.099, p = 0.007).
  A negative price response to mortgage growth seven quarters earlier has
  no economic reading — it is lag-collinearity wiggle (8 correlated lags,
  single-lag sign flips are expected noise), now the *only* thing
  standing where a finding used to be. Do not quote it.
- Neither rate coefficient clears the bootstrap (current −0.06, p = 0.81;
  lag −0.35, p = 0.057). Same verdict as before — 'probably nothing' —
  now with the sign naive intuition expects, which is itself just the
  cycle being absorbed properly.
- Magnitudes are small — quarterly appraisal moves are ~±1% while mortgage
  counts swing ~±20% — so this was ever timing evidence, not size
  evidence; now it is not even timing evidence.

## Limits

- No quarterly absorption or population: stock is annual, so this panel
  cannot stage supply against credit at this frequency.
- Complete-quarter rule + both-endpoints-present drops sparse cells
  (108 unpublished valor cells stay missing); early-2000s coverage thinner.
- G = 17 as ever; appraisal inertia blurs true transaction timing.
- The annual S2 agreed with the old quarterly story (credit now + credit
  last year, both significant) — that agreement died with the correction:
  S2's credit dynamics are gone too, and the only surviving cross-frequency
  pattern is lagged absorption at annual grain. Nothing here identifies
  credit supply vs demand.
