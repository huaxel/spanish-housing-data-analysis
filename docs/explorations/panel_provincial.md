# Provincial absorption panel: now reaches 2025

Computed by `explorations/panel_provincial.py` from the provincia mart
(raw: `artifacts/panel_provincial.json`). Annual panel, 50 provinces ×
**2002–2025** — the Censo Anual de Población extension
(`censo_anual_probe.md`) carries the mart past 2021 for the first time.
Outcome: valor-tasado €/m² YoY % (INE publishes no provincial IPV);
absorption = Δviviendas / Δpoblacion (excluded when Δpop ≤ 0); controls =
mortgage-count, transaction-count, tourist-dwelling growth (provincial).
Province + year FE via the correct two-way within transform (outcomes,
regressors, and year dummies all province-demeaned — the previous build
omitted the province FE entirely); SEs clustered by province; wild
bootstrap-t (999 reps, null-imposed via `ols.wild_bootstrap_t`, seed-fixed;
the previous build used unrestricted fitted values, which is not a
null-imposed test). Descriptive — supply and demand jointly determined.
Corrected 2026-10-06 after an external-model review caught both errors.

## Results

| | S0: absorption only | S1: + controls |
| --- | --- | --- |
| window | 2002–2025 | 2021–2025 (tourist control starts 2020) |
| absorption | −0.024 (0.008), t −2.98, **wild-p 0.19** | −0.012 (0.137), wild-p 0.97 |
| n / clusters | 777 / 49 | 178 / 46 |

## Reading

- **The panel now spans the full 2002–2025 window at province grain** —
  the gain from the census-annual mart extension. Before, population
  ended 2021 and the panel stopped there.
- **Absorption is negative everywhere but wild-robust nowhere.** S0's
  t = −2.98 looks strong, but the null-imposed wild bootstrap (49
  clusters, long series) gives p = 0.19 — the naive t overstates
  precision, the same lesson the CCAA panel (`panel_adjusted.md`)
  already recorded. The province-grain result is consistent: negative
  point estimates, not distinguishable from zero once the bootstrap
  accounts for cluster dependence.
- **S1's 2021–2025 window (−0.01, SE 0.14)** is uninformative on
  absorption once mortgage/transaction/tourist controls enter — the
  scarcity-regime signal in the raw cross-section
  (`absorption_hypothesis.md`: Spearman −0.42 in 2021–25) does not
  survive as a within-province partial effect. (The previous S1 point
  estimate, −0.21, came from the no-province-FE misspecification.)
- The window note (2021–2025 for S1) is driven by the tourist control
  (INE turísticas starts 2020), not by data loss elsewhere — a design
  artifact of the control set, disclosed rather than silent.

## Limits

- No income control at province grain (ECV is CCAA-only) — S1 has
  mortgage/transaction/tourist controls but not income.
- Valor tasado is appraisal, not transactions; provincial ECP blocked so
  population 2022+ is census-annual (seam ≤0.9%, `coverage.json`).
- Wild bootstrap with 49 clusters and 24-year series has wide tails;
  treat p-values as a floor on uncertainty, not exact.