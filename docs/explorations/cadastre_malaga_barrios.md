# Málaga construction-era profile by barrio

Added 2026-10-09. Property-weighted construction-era shares for Málaga
capital barrios from the capital BU extract joined to the official
Ayuntamiento barrio polygons (CC BY-SA 4.0). Same record-date proxy
semantics as the [Sevilla era profile](cadastre_eras.md). Artifact:
`artifacts/cadastre_malaga_barrios.json` (exploration:
`explorations/cadastre_malaga_barrios.py`).

## Method

51,411 of the 51,455 BU records for the city join exactly one barrio
(interior-point match); 27 cross barrio boundaries, 14 fall outside all
barrio polygons and 3 are partly outside — all excluded with explicit
statuses, mirroring the Sevilla pilot's conservative join. Only
barrio-assigned records with positive housing properties enter the
profiles: **360 of 419 official barrios**, 261,073 properties, 0.00%
missing dates.

Málaga's official barrios include rural diseminados (DSMO…) and planning
sectors (SUP-…) alongside urban neighborhoods; they are kept as published,
not reclassified. The newest medians (2023–2025) belong to such sectors
and recent developments, consistent with the August 2026 feed vintage.

## Findings

**Barrio-grain era mix matches the municipal profile.**

| Era share (% of dated properties) | Barrios joined | Municipal (all records) |
|---|---|---|
| Pre-1951 | 4.2 | 4.1 |
| 1951–1970 | 22.6 | 22.6 |
| 1971–1990 | 39.5 | 39.5 |
| 1991–2010 | 28.5 | 28.6 |
| 2011+ | 5.2 | 5.2 |

The excluded records (196 properties) do not move any share by more than
0.1 points — the join is effectively complete for era purposes.

**Oldest medians** (record-date proxy): Finca La Concepción (1900, 100%
pre-1951), Olías (1925), Altos de Jaboneros and the diseminados (1936).
**Newest**: Parque Tecnológico and SUP-T.8 Universidad (2025, 100%
post-2010), El Cuartón and Pizarrillo (2024–2025).

## Limitations

- Same record-date proxy limitations as the [era profile](cadastre_eras.md).
- 59 official barrios have no assigned housing-bearing records (no stock
  in the extract, or records excluded by join status) — absence from the
  profiles is not absence of housing.
- Diseminado and SUP-sector "barrios" are administrative units; their
  medians describe scattered rural stock and greenfield sectors.
- geometries carry CC BY-SA 4.0 share-alike; derived geometry products
  inherit it.

## Relation to existing work

First sub-municipal cadastre profile outside Sevilla, enabled by the
[geometry assessment](capital_geometries.md). Granada (districts) and
Córdoba (districts or blocked barrios) remain municipal pending grain
decisions and sources.
