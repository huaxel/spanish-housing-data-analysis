# Panel: absorption vs prices with demand controls

Computed by `explorations/panel_adjusted.py` from the CCAA mart
(raw output: `artifacts/panel_adjusted.json`, git-ignored). Annual panel,
17 CCAA × 2008–2024; outcome is IPV-general YoY % change; CCAA + year fixed
effects (the year dummies absorb the national rate cycle); SEs clustered by
CCAA (CR1V). **Adjusted description only** — income, credit, and population
are jointly determined with prices, so no coefficient below is a structural
or causal estimate.

## Results

| | S0: absorption only | S1: + demand controls |
| --- | --- | --- |
| absorption (dwellings per new person) | −0.111 (0.044) [−0.20, −0.03], wild-p **0.064** | −0.071 (0.044) [−0.16, +0.01], wild-p 0.178 |
| mortgage-count growth (pp) | — | +0.050 (0.027) [−0.00, +0.10], wild-p 0.103 |
| income growth (pp) | — | +0.031 (0.043) [−0.05, +0.12], wild-p 0.456 |
| 20–34 share change (pp) | — | +3.81 (1.28) [+1.30, +6.32], wild-p **0.032** |
| n / clusters / within-R² | 194 / 17 / 0.91 | 178 / 17 / 0.91 |

(Coefficient (CR1V clustered SE) [95% CI]; wild-p from 2,999-rep
Rademacher bootstrap-t, null-imposed, seed-fixed. regressors YoY % or pp.)

## Reading

- The absorption sign survives the panel arithmetically (−0.11, analytic CI
  clear of zero) but **fails the wild bootstrap (p = 0.064)** even before
  controls — with 17 clusters, the "significant" S0 is analytic-SE
  optimism. With demand covariates it attenuates further (−0.07, wild-p
  0.18). Double attenuation — by controls and by honest SEs — is the
  finding: the supply–price link is partly demand in disguise and partly
  small-sample noise, exactly as hypothesis-01 argued from the denominator.
- Credit (+0.05, t ≈ 1.9) and the young-cohort share (+3.8 per pp, t ≈ 3.0)
  carry the tightening story better than unit counts do. The cohort number
  is large because a 1pp age-share shift is a big demographic event — and
  it is the most reverse-caused regressor here (the young move to booming
  markets), so read it as association with an arrow going both ways.
- Income near zero is not "incomes don't matter": the year FEs absorb the
  national income cycle, leaving only idiosyncratic CCAA deviations to
  identify from. Same reason R² ≈ 0.91 flatters — the year dummies, not the
  regressors, explain the cycle.

## Limits (binding)

- **37% of rows dropped** (112/306): absorption is undefined when population
  shrinks, so bust years are underrepresented — the same selection the
  window analysis suffers, now quantified.
- **G = 17 clusters** is below the ~30–50 comfort zone: the wild-t
  (Rademacher, null-imposed, 2,999 reps, fixed seed) is the reported
  significance, not the analytic t. Only the cohort association clears it
  (p = 0.032) — and it is the most reverse-caused regressor.
- Annual absorption is noisy (small denominators); no lags modelled, so
  construction-completion timing vs price timing is blurred.
- Next: lags and — only with an instrument or design, not more controls —
  anything causal.
