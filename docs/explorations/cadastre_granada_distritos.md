# Granada construction-era profile by district

Added 2026-10-09. Property-weighted construction-era shares for Granada
capital districts from the capital BU extract joined to the official
Ayuntamiento district polygons (CC-BY, reprojected ED50→ETRS89 via
EPSG:1632 before matching). Same record-date proxy semantics as the
[Sevilla era profile](cadastre_eras.md). Artifact:
`artifacts/cadastre_granada_distritos.json` (exploration:
`explorations/cadastre_granada_distritos.py`).

## Method

20,274 of 20,277 Granada BU records join exactly one district; one
crosses a boundary, one falls outside, one is partly outside — all
excluded with explicit statuses. All **8 districts** enter the profiles
(140,817 properties, 0.02% missing dates). Granada publishes no official
barrio polygons, so this is district grain by necessity, not choice.

## Findings

**District era mix matches the municipal profile.**

| Era share (% of dated properties) | Districts joined | Municipal (all records) |
|---|---|---|
| Pre-1951 | 6.5 | 6.5 |
| 1951–1970 | 24.5 | 24.5 |
| 1971–1990 | 42.1 | 42.1 |
| 1991–2010 | 23.0 | 23.0 |
| 2011+ | 3.9 | 3.9 |

The four excluded records move nothing.

**District medians** (record-date proxy, with declared properties):

| District | Median year | Properties | Pre-1951 share |
|---|---|---|---|
| Albayzín | 1960 | 5,218 | 46.7% |
| Centro | 1970 | 15,624 | 30.0% |
| Ronda | 1974 | 29,121 | 2.8% |
| Zaidín | 1974 | 22,735 | 0.5% |
| Norte | 1976 | 12,187 | 0.0% |
| Chana | 1981 | 13,637 | 0.5% |
| Beiro | 1984 | 26,532 | 2.8% |
| Genil | 1984 | 15,763 | 1.8% |

The historic hills (Albayzín, Centro) hold the old stock; the 1970s–80s
expansion districts (Ronda, Zaidín, Beiro) hold the volume. Norte reports
0.0% pre-1951 — a fully post-war district footprint.

## Limitations

- Same record-date proxy limitations as the [era profile](cadastre_eras.md).
- District grain only: no within-district geography exists officially.
- ED50→ETRS89 reprojection carries ~1.5 m stated accuracy; only a thin
  edge band is sensitive, and edge records carry explicit statuses.
- Descriptive cross-section; no causal claim.

## Relation to existing work

Second sub-municipal capital profile after
[Málaga barrios](cadastre_malaga_barrios.md), enabled by the
[geometry assessment](capital_geometries.md). Córdoba stays municipal
(barrio polygons blocked).
