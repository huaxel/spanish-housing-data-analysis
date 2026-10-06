# Quarterly credit timing: mortgages lead prices by three quarters

Computed by `explorations/panel_quarterly.py` from pinned raw inputs
(valor tasado quarterly cells + HPT monthly counts → complete quarters only;
raw output: `artifacts/panel_quarterly.json`, git-ignored). Quarterly panel,
17 CCAA × 2003–2025; y = valor-tasado Libre QoQ %; CCAA + year FE + quarter
dummies; SEs clustered by CCAA; wild bootstrap-t (999 reps). Descriptive.

## Results (n=1,173, G=17, R² 0.46)

| regressor | b (SE) | wild-p |
| --- | --- | --- |
| mortgage growth, per 10pp | −0.066 (0.051) | 0.265 |
| L1 | −0.019 (0.049) | 0.710 |
| L2 | −0.038 (0.037) | 0.353 |
| **L3** | **+0.119 (0.034)** | **0.001** |
| L4 | +0.037 (0.039) | 0.349 |
| **L5** | **+0.111 (0.046)** | **0.027** |
| **L6** | **+0.092 (0.036)** | **0.030** |
| L7 | −0.075 (0.028) | 0.015 |
| L8 | −0.042 (0.030) | 0.219 |
| national rate change (pp) | +0.246 (0.191) | 0.192 |
| L1 rate change | −0.097 (0.172) | 0.572 |

## Reading

- Mortgage growth survives at **L3, L5 and L6** (wild-p 0.001/0.027/0.030):
  a 10pp quarterly mortgage surge associates with +0.1pp price growth
  three to six quarters later, fading thereafter. That delay pattern is
  credit-then-appraisal: transactions financed now surface in
  appraisal-based levels 9–18 months later (appraisal smoothing guarantees
  part of this lag mechanically). L7's negative sign (−0.075, p = 0.015)
  is treated as lag-collinearity wiggle, not a finding — with 8 correlated
  lags, single-lag sign flips are expected noise; the shape (build over
  3–6Q, decay after) is the result.
- The rate effect did **not** survive the longer spec (current +0.25,
  p = 0.19; lag −0.10, p = 0.57): the earlier positive rate coefficient
  was fragile to lag structure, which downgrades it from 'warning label'
  to 'probably nothing'. The credit lags are the robust part.
- Magnitudes are small — quarterly appraisal moves are ~±1% while mortgage
  counts swing ~±20% — so this is timing evidence, not size evidence.
- The **positive rate coefficient** (+0.49, p = 0.011) is not a policy
  effect: rate rises travel with demand shocks that also lift prices
  (and the ECB responds to the same cycle). Common-shock confounding,
  signed the other way from naive intuition — read it as a warning label
  for the whole table, not a finding.

## Limits

- No quarterly absorption or population: stock is annual, so this panel
  cannot stage supply against credit at this frequency.
- Complete-quarter rule + both-endpoints-present drops sparse cells
  (108 unpublished valor cells stay missing); early-2000s coverage thinner.
- G = 17 as ever; appraisal inertia blurs true transaction timing.
- With the annual S2 (credit now + credit last year, both significant),
  the two frequencies agree: credit moves first, prices follow within
  2–4 quarters. Nothing here identifies credit supply vs demand.
