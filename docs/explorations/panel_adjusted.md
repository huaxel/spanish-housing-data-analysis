# Panel: absorption vs prices with demand controls

Computed by `explorations/panel_adjusted.py` from the CCAA mart
(raw output: `artifacts/panel_adjusted.json`, git-ignored). Annual panel,
17 CCAA × 2008–2025 (S0; S1/S2 stop 2024 where demand controls lack
2025); outcome is IPV-general YoY % change; CCAA + year fixed
effects (the year dummies absorb the national rate cycle); SEs clustered by
CCAA (CR1V). **Adjusted description only** — income, credit, and population
are jointly determined with prices, so no coefficient below is a structural
or causal estimate. Corrected 2026-10-06 after an external-model review
caught an incorrect two-way within transform (year dummies entered raw
after unit-demeaning — every coefficient below moved; S3's headline
inflow association did not survive).

## Results

| | S0: absorption only | S1: + demand controls |
| --- | --- | --- |
| absorption (dwellings per new person) | −0.141 (0.058) [−0.25, −0.03], wild-p 0.082 | −0.112 (0.053) [−0.22, −0.01], wild-p 0.116 |
| mortgage-count growth (pp) | — | +0.033 (0.028) [−0.02, +0.09], wild-p 0.263 |
| income growth (pp) | — | +0.003 (0.041) [−0.08, +0.08], wild-p 0.935 |
| 20–34 share change (pp) | — | +3.39 (1.47) [+0.52, +6.27], wild-p 0.068 |
| n / clusters / within-R² | 194 / 17 / 0.93 | 178 / 17 / 0.92 |

(Coefficient (CR1V clustered SE) [95% CI]; wild-p from 2,999-rep
Rademacher bootstrap-t, null-imposed, seed-fixed. regressors YoY % or pp.)

## S2: adding one-year lags (n=133, G=17, R² 0.91)

| regressor | b (SE) | wild-p |
| --- | --- | --- |
| absorption | −0.051 (0.043) | 0.151 |
| mortgage growth | +0.021 (0.033) | 0.551 |
| income growth | +0.039 (0.057) | 0.464 |
| 20–34 share Δ | +2.17 (2.02) | 0.371 |
| L.absorption | −0.162 (0.055) | **0.040** |
| L.mortgage growth | −0.003 (0.016) | 0.859 |
| L.income growth | −0.090 (0.059) | 0.259 |

(Corrected 2026-10-06: the old S2 credit dynamics — current +0.11,
lagged +0.06, both wild-significant — were an artifact of the broken
within transform and do not survive it.) Timing reverses the story:
contemporaneous absorption is weak (−0.05, p = 0.15) but *last year's*
absorption is the only wild-significant association in the panel
(−0.16, p = 0.040) — supply shows up with a one-year lag, consistent
with completions-to-price transmission. Credit, income, and cohort are
all dead in both years once the year effects are correctly absorbed. The
cohort association collapses (+2.2, p = 0.37); same reverse-causality
warning, now without even an association to warn about.

## Reading

- The absorption sign survives the panel arithmetically (−0.14, analytic CI
  clear of zero) but **fails the wild bootstrap (p = 0.082)** even before
  controls — with 17 clusters, the "significant" S0 is analytic-SE
  optimism. With demand covariates it attenuates further (−0.11, wild-p
  0.12). Double attenuation — by controls and by honest SEs — is the
  finding: the supply–price link is partly demand in disguise and partly
  small-sample noise, exactly as hypothesis-01 argued from the denominator.
- Neither credit (+0.03, p = 0.26) nor the young-cohort share (+3.4 per pp,
  p = 0.068) clears the bootstrap in S1. The cohort number is large
  because a 1pp age-share shift is a big demographic event — and it is
  the most reverse-caused regressor here (the young move to booming
  markets), so read it as association with an arrow going both ways.
- Income near zero is not "incomes don't matter": the year FEs absorb the
  national income cycle, leaving only idiosyncratic CCAA deviations to
  identify from. Same reason R² ≈ 0.91 flatters — the year dummies, not the
  regressors, explain the cycle.

## Limits (binding)

- **37% of rows dropped** (112/306): absorption is undefined when population
  shrinks, so bust years are underrepresented — the same selection the
  window analysis suffers, now quantified.
## S3: adding foreign-inflow growth (n=119, G=17, R² 0.91)

| regressor | b (SE) | wild-p |
| --- | --- | --- |
| absorption | −0.114 (0.058) | 0.095 |
| mortgage growth | +0.014 (0.033) | 0.698 |
| income growth | +0.015 (0.059) | 0.784 |
| 20–34 share Δ | +3.46 (1.70) | 0.115 |
| foreign-inflow growth (pp) | +0.005 (0.031) | 0.893 |

Sample is 2009–2021 (flows start 2008, end 2021). The old headline —
foreign-inflow growth as the strongest association in the panel (+0.094,
p = 0.004) — **did not survive the within-transform correction** (+0.005,
p = 0.89). Inflow growth is strongly pro-cyclical nationally, and the
broken transform had left the national cycle inside the regressor; once
the year effects are correctly absorbed there is nothing left. This is
the same confounding the year FE are *for*, and the correction working
as intended — but it means the 2017–19 inflow-surge narrative no longer
has panel support here. (The commissioned IV in `iv_migration.md` tests
the migration channel with an instrument instead of controls and is the
place to look, with its own qualifications.)

- **G = 17 clusters** is below the ~30–50 comfort zone: the wild-t
  (Rademacher, null-imposed, 2,999 reps, fixed seed) is the reported
  significance, not the analytic t. Nothing in S1/S3 clears it; the only
  wild-significant association in the exercise is lagged absorption in S2
  (p = 0.040).
- One annual lag only; completion-to-price timing below yearly frequency is
  blurred, and S2's complete-case n=133 compounds the selection above.
  Credit itself is reverse-caused in part (expectations drive applications
  and prices together) — timing fit is not identification.
- Next: deeper/quarterly lags and — only with an instrument or design, not
  more controls — anything causal.
