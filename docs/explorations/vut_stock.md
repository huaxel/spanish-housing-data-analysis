# How many tourist dwellings are there, officially?

The public debate about *pisos turísticos* argues about a number the repo never
had a direct measure of. The tourist claim in this project is built on
**intensity panels** — travellers and nights per resident — which measure *flow*.
INE estimates the stock separately in its [experimental tourist-dwelling
statistics](https://www.ine.es/experimental/viv_turistica/experimental_viv_turistica.htm)
(VTE, API operation 410, tables 39363/39366).

## Estimated stock in May 2026

| | Value |
| --- | ---: |
| Tourist dwellings (Spain) | **341,001** |
| Beds | **1,714,702** |
| Beds per dwelling | 5.03 |
| Share of census dwellings | **1.28%** |

The national estimate is **+6.07%** above its first snapshot (August 2020,
321,496). INE moved the reference months from February/August to May/November
in the second half of 2024. This comparison is neither seasonally matched nor
an estimate of underlying growth independent of platform coverage.

## The estimated share varies widely by municipality

INE's own share variable (tourist dwellings over census dwellings, per
municipio) uses the census denominator. The distribution below covers only
rows with a positive published share and an unambiguous label:

| Municipal share of tourist dwellings | Value |
| --- | ---: |
| Median municipio | **0.61%** |
| 90th percentile | **3.40%** |
| Maximum | **33.33%** |
| Municipios above 5% | **5.34%** |

The national share masks wide local differences. The ten largest municipal
estimates hold **14.99%** of the assigned total, led by Marbella with an
estimated 6,987 dwellings.

## What it cannot do

- **It is not a licence count or a guaranteed lower bound.** INE scrapes three
  platforms, filters listings under regional rules and deduplicates across
  platforms. A missing or invalid licence does not automatically exclude a
  listing; other characteristics can qualify it. Dwellings outside the observed
  platforms can be missed. Listings are not occupancy or evidence that a home
  left the long-term rental market.
- **Municipal assignment is incomplete.** The payload has no municipality code.
  **122 stock rows** have labels used by more than one territory, such as a
  province and its capital. The analysis marks them `ambiguo` rather than
  guessing. The rows assigned to the project's municipalities account for
  **84.52%** of the national estimate; that is join coverage, not platform
  coverage of the real market.
- **It does not identify rent effects.** The project's separate intensity panel
  uses tourist flows. Its inconclusive within-municipality results cannot be
  confirmed or overturned by this stock estimate.

## Reproduce

```bash
uv run python scripts/fetch_vut_municipal.py --offline
uv run python explorations/vut_stock.py
```

Pinned inputs: `data/raw/vut_municipal_39363.json`, `data/raw/vut_municipal_39366.json`.
Output artifact: `artifacts/vut_stock.json`; `--check` verifies it against the
pinned parquet and `marts.duckdb`.
