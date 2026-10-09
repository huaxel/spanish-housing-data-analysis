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

No statistically detectable association: within-municipio changes in tourist
intensity do not reliably track sale or rent accelerations in these
specifications, with or without population controls, at sale grain
(130 municipios with DIBA prices) or rent grain (253).
R² ≈ 0.03–0.05. This is not an equivalence test: the results do not establish
that tourism's effects are small, nor identify what would happen without
licensing restrictions. Registry coverage, limited within variation and
endogenous regulation constrain interpretation. The composition of total
stock is a separate descriptive question, not established by these nulls.

**Interpretation correction 2026-10-08:** the earlier "footnote even where
concentrated" conclusion was not warranted by insignificant estimates.
Coefficients and wild-p values are unchanged; no estimator was rerun.

The [uncertainty chapter](../uncertainty.md) now exposes the existing
normal-approximation ranges alongside these zero-null tests, without
inventing bootstrap coefficient intervals or equivalence conclusions.

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
  association is positive on ranks too (prov Spearman 0.525), with
  positive provincial growth associations (Pearson 0.225, Spearman 0.304).
  These cross-sections do not separate tourism from coastal demand.
