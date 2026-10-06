# Probe: Censo Anual de Población — provincial population 2021–2025

**Date:** 2026-10-06 · **Status:** reachable, verified, **fetch built** (scripts/fetch_censo_anual.py)

## What the repo lacks

`mart_provincia_anual` ends in **2021** because provincial ECP population
(table 56945) is API-blocked (`restricciones de volumen` on every date
window, empty `SERIES_TABLA`, no filter match — see `docs/sources.md`
"Unreachable"). CCAA/national run to 2025 via ECP table 56940.

## What the Censo Anual offers

The 2021 census was the last decennial census and the first fully
register-based one. Its replacement system publishes population **every
year** (Censo Anual de Población, 2021–2025) at national / CCAA /
province / municipio grain, and viviendas for years ending in 1/5/8.

The census annual **population** tables live in Tempus3 (68519–68526).
Table **68521** (`Población por sexo, edad (grupos quinquenales) y país de
nacionalidad`) is downloadable as a **static CSV**:

```
https://www.ine.es/jaxiT3/files/t/es/csv_bd/68521.csv   (208 MB, tab-separated, dot-thousands, BOM)
```

No API call needed — the `DATOS_TABLA/68521` endpoint refuses volume, but
the jaxiT3 export path serves the full table directly. Grain: 52
provinces (plus CCAA and Nacional rows), 5 years (2021–2025), × sex × age
group × nationality.

## Verification against marts

| Check | Value |
| --- | --- |
| National 2025 (census annual) | 49,128,297 |
| Mart `mart_ccaa_anual` Nacional 2025 | 49,128,297 — **exact match** |
| 2021 province-level census-vs-padrón (mart) | mean \|Δ\| = 0.17%, max 0.89% (50 provinces; Ceuta+Melilla aggregate excluded — expected grain difference, see below) |
| 2021 census annual total | 47,400,798 vs mart 47,385,107 (+0.033%) |

The 0.17% mean difference vs the padrón-based mart 2021 is the expected
register-vs-padrón seam — the same order as the ECP-vs-padrón overlap the
repo already quantifies in `coverage.json`. The 2025 national total
matching the ECP-based mart exactly means the two series are consistent at
the top.

## Caveats

- **Ceuta/Melilla grain (corrected 2026-10-06 after independent
  review):** the two CSV rows not in the 50-province comparison are
  Ceuta (51) and Melilla (52), which the mart aggregates as one `51+52`
  row — an expected grain difference, not a código mismatch. All 50
other provinces compare.
- **Province code strings**: the CSV's province column is `"01
  Araba/Álava"` style; strip the leading code at fetch time (done in
  `fetch_censo_anual.py`).
- The table has sex/age/nationality detail — the repo only needs the
  `Total × Todas las edades × Total` margin (same pattern as the ECP
  fetch), which is a small fraction of the 2.47M rows.
- Methodology: register-based annual census, not padrón — the same seam
  the repo already documents; a `pop_source` flag is needed, and the
  padrón 2021 / census 2021 overlap should be quantified like ECP's.

## Verdict

**Reachable, valuable, and now built.** `scripts/fetch_censo_anual.py`
downloads the static CSV (~208 MB), keeps the Total×Todas las edades×Total
margin, guards the 2025 provincial sum against 49,128,297, and pins both
the raw CSV and the parquet in the manifest. `build_marts.py` extends the
provincia mart to 2025 (`pop_source='censo_anual'` for 2022+, padrón
before), and `verify_data.py` windows now assert 2022–2025 coverage. The
provincia mart grew from 1,071 to 1,275 rows; 2025 provincial sum
49,128,297 matches the CCAA mart Nacional exactly. This closes the one
temporal gap the sources doc listed as unreachable.