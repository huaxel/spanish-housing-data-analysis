# Does the two-group stock split survive INE's own household projection?

The repo's central finding is that a flat national dwellings-per-household ratio
hides two opposite regimes: metropolitan scarcity (Madrid, Cataluña) against
interior overhang (Galicia, Castilla y León). That finding is cross-sectional —
it says where the pressure is, not whether it is easing.

INE's `Proyección de Hogares` (PROH, operation 70, table 54562) publishes
households at 1 January 2026–2040 by CCAA under INE's own assumptions. Using it
as an **external input about household formation** — not as this project's
forecast — answers a question the repo could previously only extrapolate.

## The projected path

| | 2026 | 2040 | Change |
| --- | ---: | ---: | ---: |
| Spain, households | 19,759,349 | 21,867,217 | **+2,107,868 (+10.7%)** |

Projected growth is concentrated: Madrid, Cataluña, Andalucía and Comunitat
Valenciana account for **67.75%** of it. The fastest rates are Murcia,
Comunitat Valenciana and Balears; the slowest are Asturias, Extremadura and
Castilla y León, all under 4%.

A sanity note on levels: the projection's 2026 value sits **−2,334** households
against the observed ECP count at 1 January 2026 (19,761,683), because INE built
the projection before that release. Levels are therefore not interchangeable with
ECP; only the trajectory is used here.

## The split persists, not fades

Pairing each CCAA's projected growth with the stock it already has (2025
dwellings per household):

| Group | Median projected growth 2026→2040 |
| --- | ---: |
| Lean stock (lower half of dwellings per household) | **+11.9%** |
| Fat stock (upper half) | **+7.7%** |

Across the 17 CCAA the correlation between current dwellings per household and
projected growth is **−0.316**: markets that are already tight per household are
projected to add households fastest, and the overhang regions grow slowest. So
the two-group pattern is not a transient of the observed window — INE's own
projection reproduces its direction. With 17 units the coefficient is
directional, not a law (the repo applies the same reading to its other n=17
cross-sections).

## What is deliberately not computed

No "homes needed" figure is derived from this. The artifact carries
`dwellings_implied_2040` (projected households × today's dwellings per
household) purely as an **identity** for inspection, exactly the kind of
household-minus-stock remainder the [deficit explainer](../deficit_explainer.md)
warns about: it assumes the current ratio, ignores vacant and seasonal stock, and
says nothing about location, affordability or whether the projection's migration
assumptions hold. INE's projection is also an input, not a verdict: it is revised
in every release, and its base already differs from the latest ECP count.

## Reproduce

```bash
uv run python scripts/fetch_proh.py --offline
uv run python explorations/proh_households.py
```

Pinned input: `data/raw/proh_54562.json` (table 54562, 2026–2040). Output
artifact: `artifacts/proh_households.json`; `--check` verifies it against the
pinned parquet and `marts.duckdb`. The fetch collapses the five uniprovincial
territories that INE publishes twice (CCAA and province) under identical labels,
and fails if the two copies ever disagree.
