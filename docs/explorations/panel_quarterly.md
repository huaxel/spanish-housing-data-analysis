# Quarterly credit timing: mortgages lead prices by three quarters

Computed by `explorations/panel_quarterly.py` from pinned raw inputs
(valor tasado quarterly cells + HPT monthly counts → complete quarters only;
raw output: `artifacts/panel_quarterly.json`, git-ignored). Quarterly panel,
17 CCAA × 2003–2025; y = valor-tasado Libre QoQ %; CCAA + year FE + quarter
dummies; SEs clustered by CCAA; wild bootstrap-t (999 reps). Descriptive.

## Results (n=1,173, G=17, R² 0.46)

| regressor | b (SE) | wild-p |
| --- | --- | --- |
| mortgage growth, per 10pp | −0.064 (0.049) | 0.274 |
| L1 | +0.019 (0.047) | 0.691 |
| L2 | −0.012 (0.038) | 0.776 |
| **L3** | **+0.108 (0.029)** | **0.003** |
| L4 | −0.053 (0.040) | 0.207 |
| national rate change (pp) | +0.488 (0.182) | 0.011 |

## Reading

- Only the **third lag** of mortgage growth survives (wild-p 0.003):
  a 10pp quarterly mortgage surge associates with +0.11pp price growth
  three quarters later. Contemporaneous, 1-, 2- and 4-quarter lags are all
  null. That delay pattern is credit-then-appraisal: transactions financed
  now surface in appraisal-based levels ~9 months later (appraisal
  smoothing guarantees part of this lag mechanically).
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
