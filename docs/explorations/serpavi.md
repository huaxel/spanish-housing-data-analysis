# SERPAVI rents: municipal rent-vs-sale wedge and validation

SERPAVI (MIVAU, tax-deposit exploitation) gives municipal rents nationwide
for the first time in this repo. Built: `scripts/fetch_serpavi.py` (71 MB
Excel, long melt) + `serpavi_municipal` mart table (716,889 cells, 7,331
municipios, 2011–2024, 20 measures). Analysis: `explorations/serpavi_analysis.py`
→ `artifacts/serpavi_analysis.json`. See `docs/explorations/serpavi_probe.md`
for reachability and structure.

## Validation against DIBA — independent sources agree

SERPAVI is built from rental-deposit tax data (national); DIBA M23 rents
(Barcelona demarcation) are a separate source. On the 202 overlapping
municipios (2023), SERPAVI rent (€/m² × 80 m² typical contract) vs DIBA
rent (€/month):

| | value |
| --- | --- |
| n | 202 municipios |
| Pearson | **0.825** |
| Spearman | 0.87 |

Same ordering, different administrative sources. This is the strongest
cross-source validation available to the repo (the DIBA series is already
used in `muni_bcn`; SERPAVI confirms it generalizes).

## Gross rental yield in Barcelona municipios (2023)

| | value |
| --- | --- |
| Barcelona capital | **3.61%** (4,371 €/m² sale, 13.14 €/m² rent) |
| median of 122 municipios | **4.58%** (P25 4.11%, P75 5.23%) |

Buy-to-let gross yields in the 3.5–6% band — marginal in the capital,
better in the corona. **Corrections 2026-10-06 (independent review):**
the sample is **122** municipios with both 2023 DIBA sale and SERPAVI
rent (not "~200"); quartiles are **4.11/5.23**, not 3.9/5.7. The 80 m²
typical-contract multiplier is an unvalidated assumption — it scales
levels for the Pearson comparison but does not test equal rents. DIBA
M23's contract population vs SERPAVI's tax-deposit population
(new/rolling contracts) is undocumented here, so cross-municipality
ordering is validated, not level equality or cohort comparability. The
sale series is DIBA M19 transactions-based appraised values — label the
yield an indicative statistic, not an observed investment return.

## Rent vs vacancy: substantial negative rank association (corrected)

| | value |
| --- | --- |
| n | 2,237 municipios (2023 rent × 2021 vacancy) |
| Pearson | −0.429 |
| Spearman | **−0.507** |

Municipios with higher vacancy shares have lower rents, on ranks as well
as levels. **Correction 2026-10-06 (independent review):** the first
version published Spearman −0.024 from a buggy rank function that
correlated x-ranks with y-values-sorted-by-x instead of ranking both
variables; the true two-sided Spearman is −0.507. The "no robust signal
/ scale artifact" conclusion is withdrawn. The cross-section is
consistent with the overhang direction — high-vacancy (interior)
municipios carry lower rents — and it is the strongest rank association
in this file. Still **not causal**: 2023 rents vs 2021 vacancy (temporal
mismatch), no municipality-size control, geography confounds both. It
corroborates `ratio_ccaa.md` as a spatial contrast, not a mechanism.

## What this unlocks

- **Rents as a second outcome** at municipal grain nationwide (2,555
  municipios at 2024) — the tourist, terrain, and overhang threads can now
  be re-run on rents, not just sale prices.
- **Rent-vs-sale wedge** by municipio (Barcelona 200+ now, and any future
  municipal sale series).
- **National validation** of the DIBA Barcelona rent series.

Caveats: SERPAVI measures tax-declared deposits (new/rolling contracts;
sublet/recent-renewal gaps), is a matrix download (melted here), 2011–
2024, and has no SE (tax file). Rents are nominal.