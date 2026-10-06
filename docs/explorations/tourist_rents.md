# Tourist intensity vs rents: SERPAVI extends the null nationally

`panel_tourist.md` found a null (tourist change → sale/rent growth) within
Barcelona municipios, and flagged Balears/Canarias as the untested
external-validity question — rents existed only for Barcelona (DIBA).
SERPAVI now provides municipal rents nationwide. This extension
(`explorations/tourist_rents.py` → `artifacts/tourist_rents.json`) runs
the two tests the old panel could not:

1. **Replication with an independent rent source** (Barcelona municipios,
   n=199): tourist intensity (DIBA `muni_bcn.tourist`, per 1,000) vs
   SERPAVI rent level (2024) and growth (2021→2024).
2. **Provincial cross-section** (n=45): INE turísticas intensity (2020,
   per 1,000 pop) vs SERPAVI median municipal rent level (2024) and
   growth (2020→2024) — includes Balears, Canarias, Girona, Málaga.

## Results

| Test | Pearson | Spearman | n |
| --- | --- | --- | --- |
| BCN municipal: tour vs rent level | 0.087 | 0.037 | 199 |
| BCN municipal: tour vs rent growth | 0.020 | −0.024 | 199 |
| Provincial: tour vs rent level | **0.619** | **0.016** | 45 |
| Provincial: tour vs rent growth | 0.225 | 0.041 | 45 |

## Reading

- **The Pearson 0.619 is a scale artifact, not a tourism effect.**
  Provinces with more tourist dwellings are also larger/coastal/richer;
  on ranks the level correlation vanishes (Spearman 0.016). The same
  pattern as the rent-vacancy cross (`serpavi.md`): a level correlation
  dominated by city size, not by the tourist margin.
- **The municipal replication is a clean null** (levels 0.087, growth
  0.020): within Barcelona, tourist intensity does not predict SERPAVI
  rents either — confirming the old panel's DIBA-based null with an
  independent rent source.
- **Growth is weakly positive at provincial rank (0.041)** and the
  top-tourist provinces do show the fastest rent growth 2020→2024
  (Tenerife +27.9%, Balears +23.0%, Girona +18.7%). But n=45, rank
  correlation 0.041, and the 2020→24 window is the post-COVID rental
  boom — tourist provinces may just be coastal-demand provinces. Not
  distinguishable from zero by this design.

## Verdict

The tourist-rents channel joins the tourist-sale channel as a **null at
the margin**: within-municipio variation does not track rents, and the
provincial level association is a composition effect. Where tourism
might matter (levels across provinces), the design cannot separate
tourism from coastal demand — the same identification problem the
original panel documented. SERPAVI did not overturn the panel; it
extended its external-validity claim to Balears/Canarias and found the
same non-result.

## Limits

- Turísticas is a registry snapshot (Dec) of registered dwellings; illegal
  stock invisible.
- Provincial level cross-section is n=45 with size confounds; the growth
  window (2020→24) is one regime.
- SERPAVI rents are tax-deposit based (new/rolling contracts).