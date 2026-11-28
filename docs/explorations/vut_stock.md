# How many tourist dwellings are there, officially?

The public debate about *pisos turísticos* argues about a number the repo never
had a direct measure of. Travellers and nights per resident measure tourism *flows*. The separate
Barcelona municipal panel instead uses DIBA’s tourist-dwelling stock per resident.
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
rows with a positive published share and a published municipality code:

| Municipal share of tourist dwellings | Value |
| --- | ---: |
| Median municipio | **0.61%** |
| 90th percentile | **3.38%** |
| Maximum | **33.33%** |
| Municipios above 5% | **5.30%** |

The national share masks wide local differences. The ten largest municipal
estimates hold **18.47%** of the assigned total, led by Madrid with an
estimated 10,836 dwellings.

## What it cannot do

- **It is not a licence count or a guaranteed lower bound.** INE scrapes three
  platforms, filters listings under regional rules and deduplicates across
  platforms. A missing or invalid licence does not automatically exclude a
  listing; other characteristics can qualify it. Dwellings outside the observed
  platforms can be missed. Listings are not occupancy or evidence that a home
  left the long-term rental market.
- **All May observations match the municipal map by code.** INE's downloadable
  JAXI CSVs include the official five-digit code even though the JSON series
  show only a name. The parser checks unique code–period–measure keys and
  reconciles the municipal stock sum to the national figure in every snapshot.
  All **8,131** May municipality codes match the project’s map, accounting for
  **100%** of the published estimate. This is geographic coverage, not the
  fraction of the real market captured by the platforms or a rent-data join.
- **It does not identify rent effects.** The [Barcelona panel](panel_tourist.md) uses
  changes in DIBA tourist dwellings per resident. A [national code-matched
  comparison](vut_rent_overlap.md) links INE stock and SERPAVI rents descriptively;
  neither design identifies a causal effect.

## Reproduce

```bash
uv run python scripts/fetch_vut_municipal.py --offline
uv run python explorations/vut_stock.py
```

Pinned inputs: `data/raw/vut_municipal_{39363,39366}.csv` from the official JAXI
downloads.
Output artifact: `artifacts/vut_stock.json`; `--check` verifies it against the
pinned parquet and `evidence/static/geo/municipios.geojson`.
