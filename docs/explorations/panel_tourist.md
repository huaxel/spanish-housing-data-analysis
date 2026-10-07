# Tourist intensity vs prices: null at municipal grain

Computed by `explorations/panel_tourist.py` from `muni_bcn`
(raw output: `artifacts/panel_tourist.json`, git-ignored). Barcelona
demarcation, 310 municipios; y = sale/rent YoY % on change in tourist
dwellings per 1,000 inhabitants (± population growth); municipio + year
FE; SEs clustered by municipio (G up to 253). Adjusted description —
licensing follows demand and regulation jointly with prices.

## Results

| | sale, tour only | sale + pop | rent, tour only | rent + pop |
| --- | --- | --- | --- | --- |
| d_tour | −0.21 (0.31) | −0.18 (0.31) | +0.01 (0.23) | +0.01 (0.23) |
| wild-p | 0.49 | 0.56 | 0.96 | 0.96 |
| n / clusters / R² | 1159 / 130 / 0.04 | same / 0.05 | 2109 / 253 / 0.03 | same |

(Coefficient (clustered SE) per +1 tourist dwelling per 1,000 inhabitants.)

## Reading

Null everywhere: within-municipio changes in tourist intensity do not
track sale or rent accelerations, with or without population controls,
at sale grain (130 municipios with DIBA prices) or rent grain (253).
R² ≈ 0.03–0.05 — the regressors explain essentially nothing once
municipio and year effects are absorbed. This is the within-variation
version of the repo's composition finding: the crisis is second homes,
vacancy, and incomes — tourist flats are a footnote even where they
concentrate, because licensing froze the margin (registry snapshots
flat since 2015) while prices moved on other demand.

## Limits

- Tourist counts are registry snapshots (Dec), not occupied beds; illegal
  stock is invisible by construction.
- Post-2015 licensing freezes truncate the very variation being tested —
  a null under a freeze does not generalize to an unregulated counterfactual.
- Sale sample (130 municipios with DIBA prices) skews larger/urban vs
  the rent sample (253); neither is the full demarcation.
- Barcelona only — Balears/Canarias, where tourist shares are higher,
  are the external-validity question. **Now tested**: see
  `tourist_rents.md` — SERPAVI extends rents nationally; the level
  signal is a scale artifact (prov Spearman 0.016) and growth is
  weakly positive (0.041), not distinguishable from zero.
