# Tourist intensity vs rents: municipal and provincial cross-sections

`panel_tourist.md` found a null (tourist change → sale/rent growth) within
Barcelona municipios, and flagged Balears/Canarias as the untested
external-validity question — rents existed only for Barcelona (DIBA).
SERPAVI now provides municipal rents nationwide. This extension
(`explorations/tourist_rents.py` → `artifacts/tourist_rents.json`) runs
two cross-sectional comparisons beyond the old panel's coverage:

1. **Independent-source cross-sectional comparison** (Barcelona municipios,
   n=199): tourist intensity (DIBA `muni_bcn.tourist`, **2019**,
   pre-regulatory peak, per 1,000) vs SERPAVI rent level (2024) and
   growth (2021→2024).
2. **Provincial cross-section** (n=45): INE turísticas intensity (2020,
   per 1,000 pop) vs SERPAVI median municipal rent level (2024) and
   growth (2020→2024) — includes Balears, Canarias, Girona, Málaga.

## Results (corrected 2026-10-06; BCN base year corrected 2026-10-07)

| Test | Pearson | Spearman | n |
| --- | --- | --- | --- |
| BCN municipal: tour vs rent level | 0.157 | 0.085 | 199 |
| BCN municipal: tour vs rent growth | 0.000 | 0.169 | 199 |
| Provincial: tour vs rent level | **0.619** | **0.525** | 45 |
| Provincial: tour vs rent growth | 0.225 | 0.304 | 45 |

**Correction 2026-10-06 (independent review):** the first version
published Spearman figures from the same buggy rank function as
`serpavi_analysis.py` (x-ranks vs y-values-sorted-by-x). All Spearman
values above are the true two-sided figures. The provincial level
Spearman moves 0.016 → **0.525**: the association survives ranking and
is no longer dismissable as pure scale.

**Correction 2026-10-07 (repo review, base year):** the BCN intensity
was supposed to be 2019 (pre-regulatory peak, predating the rent
window) but the code took each municipio's *latest* year — 2024 —
making exposure contemporaneous with the growth outcome. Fixed to the
documented 2019 base (all 310 municipios carry 2019; n unchanged). The
municipal null survives unchanged; provincial columns were always
2020-based and do not move.

**Interpretation correction 2026-10-08:** weak municipal correlations are
not an equivalence test or evidence of negligible tourism effects. These
cross-sections are not within-municipio panel estimates. Results unchanged.

## Reading

- **The provincial tourist→rent-level association is substantial on
  ranks too (0.53).** Tourist-intensive provinces have higher rents —
  Balears, Canarias, Girona, Málaga sit top on both. This does NOT
  identify a tourism effect: the cross-section cannot separate tourism
  from coastal demand, size, or income (n=45, no controls). The
  identification problem the original panel documented stands; but the
  association itself is real, not a scale artifact.
- **The municipal cross-section shows weak associations** (levels 0.157/0.085,
  growth 0.000/0.169): across Barcelona municipios, these correlations do not show a strong
  association with SERPAVI rents. This uses a different rent source but
  does not replicate the panel design or establish negligible effects.
- **Growth is moderately positive at provincial rank (0.30)** and the
  top-tourist provinces show the fastest rent growth 2020→2024
  (Tenerife +27.9%, Balears +23.0%, Girona +18.7%). But n=45 and the
  2020→24 window is the post-COVID rental boom — tourist provinces may
  just be coastal-demand provinces. Suggestive, not conclusive.

## Verdict (corrected)

The tourist-rents channel is **mixed, not null**: within-municipio
panel variation shows no detected association and municipal cross-sectional
correlations are weak, but across provinces tourist intensity and rent
levels move together substantially (Pearson 0.62, Spearman 0.53) with
moderately positive growth (0.23/0.30). The cross-section cannot
separate tourism from coastal demand — the same identification problem
the original panel documented — so this is an association with a known
confound, not evidence for or against a tourism effect. SERPAVI added provincial coverage including Balears/Canarias and found a
positive level association; it did not reproduce the panel design nationally.

## Limits

- Turísticas is a registry snapshot (Dec) of registered dwellings; illegal
  stock invisible.
- Provincial level cross-section is n=45 with size confounds; the growth
  window (2020→24) is one regime.
- SERPAVI rents are tax-deposit based (new/rolling contracts).