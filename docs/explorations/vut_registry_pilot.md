# Tourist dwellings: municipal coverage and Barcelona register pilot

**May 2026.** INE's estimate is based on filtered, deduplicated platform
listings. The Barcelona open-data files count municipal records and publish
regional registration IDs when available. Neither source counts occupied nights.

## Before the fix, the municipal join missed major markets

To separate provinces from their same-named capitals without guessing from
values, subtract the series IDs in [INE's complete aggregate table 39364](https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/39364)
from the pinned mixed-grain table 39363. For every aggregate ID, verify the
label and May observation match; then require the remaining dwelling-count
series to sum to INE's national estimate. The complete response matters: the
repo's existing province fetch collapses duplicate uniprovincial series.

The remaining 8,131 series sum to **341,001 dwellings**. A one-to-one
normalized-name match to `muni_all` assigns **288,216 (84.52%)**. The 74
unmatched series account for **52,785 dwellings**. Madrid (10,836), Málaga
(8,288), Barcelona (8,231) and Sevilla (6,937) alone make up **65.0%** of the
unmatched total. These four municipal series do not appear by those names in
`muni_all`; removing province rows disambiguates the INE side but does not add
them to the destination. That earlier matched subset was not representative of Spain’s largest tourist
markets. The [current stock analysis](vut_stock.md) uses the official codes in
the downloadable JAXI CSVs instead of that name join. This pilot preserves the
earlier baseline and the separate Barcelona registry comparison.

## Barcelona city: adjacent registry snapshots

The [Barcelona municipal catalogue](https://opendata-ajuntament.barcelona.cat/data/es/dataset/habitatges-us-turistic)
provides Q1 and Q3 2026 files, but no Q2 2026 file was listed when checked. The
closest published snapshots straddle May; they are not a same-date match.

| Source and reference period | Records or estimated dwellings | Distinct nonblank regional registration IDs |
| --- | ---: | ---: |
| Barcelona Open Data, Q1 2026 | 10,730 records | 10,631 |
| INE VTE, May 2026 (municipal series `VTE7544`) | 8,231 estimated dwellings | — |
| Barcelona Open Data, Q3 2026 | 10,721 records | 10,624 |

INE's estimate is around **23% below** the registration-ID counts in the two
adjacent snapshots. That is a difference between published measures, not a
platform coverage rate: a registration may not be advertised, and an advert
in INE's estimate may lack a valid licence. The series also differ in date.
No dwelling-level matching or inference about illegal listings was attempted.

## Reproduce

Download the [full INE table](https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/39364)
and Barcelona's [Q1](https://opendata-ajuntament.barcelona.cat/data/dataset/c748799e-1079-44b1-9e60-88d936a3fe70/resource/297cf7da-2b43-4c83-91e2-210bfe5c33e9/download)
and [Q3](https://opendata-ajuntament.barcelona.cat/data/dataset/c748799e-1079-44b1-9e60-88d936a3fe70/resource/2214883c-3a56-43f8-b7c5-9ddc42c2ebbe/download)
archives to a local directory outside the repo. The script outputs aggregates
only; it does not export unit-level registration records or addresses.

```sh
uv run python explorations/vut_registry_pilot.py /path/ine-39364.json \
  /path/2026_1T_hut_comunicacio_opendata.csv.zip \
  /path/2026_3T_hut_comunicacio_opendata.csv.zip
```

| Download | SHA-256 |
| --- | --- |
| Full INE 39364 response | `3582bf13f1a984c2b08ca0aac48561e5f47c6ce4a47780d1cfa24436673019f6` |
| Barcelona Q1 ZIP | `8faa17b2948977e8ae5a01ae1dd90ab0712c03393ee68932b51e7210ca691929` |
| Barcelona Q3 ZIP | `99d4849f6b517266bfad5fb05408a4f18f13b3f48f1c3198771ae615af1aeb4b` |
