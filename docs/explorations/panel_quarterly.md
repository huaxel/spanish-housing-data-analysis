# Quarterly credit timing: no mortgage lead once year effects are absorbed

Computed by `explorations/panel_quarterly.py` from pinned raw inputs
(valor tasado quarterly cells + HPT monthly counts/rates → complete
quarters only; raw output: `artifacts/panel_quarterly.json`, git-ignored).
Quarterly panel, 17 CCAA × 2003–2025; y = valor-tasado Libre QoQ %; CCAA +
year FE + quarter dummies via the correct two-way within transform; SEs
clustered by CCAA; wild bootstrap-t (999 reps). Descriptive.

(Corrected 2026-10-06: the previous build regressed CCAA-demeaned
outcomes on CCAA-demeaned regressors plus *raw* year/season dummies, which
left the national cycle inside the credit lags. The old headline —
mortgage growth leading prices at L3/L5/L6 — does not survive the fix.)

**Correction 2026-10-07 (repo review, rate series):** the rate-change
regressors were mis-keyed — the INE rates series is *monthly*, but the
panel looked it up by (year, *quarter*), so dr mixed month-over-month
changes (Q2→February, Q3→March, Q4→April) with a nine-month gap in Q1
(January vs the prior year's April). With rates correctly quarterized
(mean of the quarter's three months, complete quarters only), the rate
columns change materially and one verdict reverses — see Reading. All
values below are the corrected ones.

## Results (n=1,156, G=17, R² 0.483)

| regressor | b (SE) | wild-p |
| --- | --- | --- |
| mortgage growth, per 10pp | −0.048 (0.049) | 0.429 |
| L1 | −0.014 (0.049) | 0.792 |
| L2 | −0.063 (0.036) | 0.108 |
| L3 | +0.071 (0.035) | 0.057 |
| L4 | −0.006 (0.039) | 0.885 |
| L5 | +0.055 (0.045) | 0.272 |
| L6 | +0.025 (0.035) | 0.513 |
| L7 | −0.127 (0.034) | **0.005** |
| L8 | −0.065 (0.032) | 0.064 |
| national rate change (pp) | +1.001 (0.368) | **0.018** |
| L1 rate change | +0.595 (0.303) | 0.059 |

Wild-p values are the (count+1)/(reps+1) finite-rep form (applied to
`ols.wild_bootstrap_t` the same day).

## Reading

- **No mortgage lead.** L3/L5/L6 are all positive but none clears the
  bootstrap (p = 0.06/0.27/0.51); the old "credit-then-appraisal at 3–6
  quarters" shape was national-cycle leakage through the broken
  transform (and, for the rate columns, the mis-keyed series). Mortgage
  counts move with the national cycle, and once the year effects are
  correctly absorbed there is no timing evidence left. L3 sits at the
  analytic-SE edge (t = 2.05, CI clears zero) but not at the bootstrap's.
- The only wild-significant lags are **negative and late**: L7 (−0.127,
  p = 0.005), with L8 near it (−0.065, p = 0.064). A negative price
  response to mortgage growth seven-to-eight quarters earlier has no
  economic reading — it is lag-collinearity wiggle (8 correlated lags,
  single-lag sign flips are expected noise), now the *only* thing
  standing where a finding used to be. Do not quote it.
- **Rates co-move with appraisal growth within the year — the opposite
  of the old reading.** With the rate series fixed, dr is +1.00
  (p = 0.018): quarters where the average new-mortgage rate rose saw
  *higher* appraisal growth. This is the 2022–24 inflation cycle (rates
  and prices rose together; in 2009–12 they fell together) — a
  co-movement the year FEs leave in and the lag structure does not
  absorb. The old "probably nothing, sign naive intuition expects"
  reading was an artifact of the broken series and is withdrawn. Rates
  are endogenous to the same cycle here; nothing in this design
  identifies a causal rate effect.
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
