# Surface/era matrix: building size quartiles by construction era (Sevilla cadastre)

Added 2026-10-09. Descriptive cross-tabulation of the housing-bearing
cadastre BU records: equal-count `gross_floor_m2` quartiles crossed with the
construction-era profile. No trend claim, no causal claim, no significance
testing. Artifact: `artifacts/cadastre_era_surface.json` (exploration:
`explorations/cadastre_era_surface.py`).

## Method and definitions

- **Unit**: BU record (parcel/building group), not the individual dwelling.
- **Size**: `gross_floor_m2`, the record's total gross floor area
  (mixed-use buildings included; no residential-only fraction is available).
- **Age**: earliest component construction year of the record — the same
  record-date proxy as the [era profile](cadastre_eras.md), not dwelling age.
- **m² per property**: gross floor divided by declared housing properties —
  a coarse per-unit proxy that assumes the whole record's floor is
  residential.
- Quartile cutoffs are computed over the 50,320 dated housing-bearing
  records; era shares within a quartile are **property-weighted**
  (declared `dwelling_properties`).

Coverage: 50,321 housing-bearing records have a gross floor value; exactly
**1 record is dropped** for lacking a valid year. Quartile cutoffs: 132 /
227 / **623 m²** — the heavy jump to Q3 reflects extreme right skew (the
largest record is 81,757 m²), so "quartile 4" spans roughly 623–82k m².

## Findings

**Newer construction lives in larger buildings — mostly.** Share of each
era's housing properties in the largest quartile:

| Era | Median gross floor (m²) | Median m² per property | Share of properties in Q4 |
|---|---|---|---|
| Pre-1951 | 219 | 152 | 38.2% |
| 1951–1970 | 200 | **99** | 67.7% |
| 1971–1990 | 263 | 131.4 | 87.1% |
| 1991–2010 | 224 | 152 | 90.1% |
| 2011+ | **329** | **176** | **93.4%** |

Every era from 1951 on concentrates its properties overwhelmingly in
large-format buildings, and post-1990 construction adds larger *units*
(m²/property rising 99 → 131 → 152 → 176) on top of larger buildings. The
pre-1951 stock is the exception: only 38% of its properties sit in Q4 —
historic fabric mixes small parcels with some very large blocks.

**But the overall age–size association is weak.** The record-level
Spearman of construction year vs gross floor is only **+0.122**. The
era mix of the small-record quartiles is essentially flat: property-weighted
median years by quartile are 1965 / 1972 / 1964 / 1978. Small records of
every age exist (single dwellings, small row buildings), and mid-century
mass blocks dominate the large class, so size does not order age.

| Quartile (m²) | Upper cutoff | Records | Properties | Median year | Pre-1951 share | 2011+ share |
|---|---|---|---|---|---|---|
| 1 | 132 | 12,702 | 12,811 | 1965 | 20.6% | 0.7% |
| 2 | 227 | 12,481 | 13,613 | 1972 | 21.5% | 1.7% |
| 3 | 623 | 12,569 | 41,472 | 1964 | 19.3% | 1.7% |
| 4 | — | 12,568 | 259,340 | 1978 | 3.2% | 5.6% |

## Limitations

- The record, not the dwelling, is the unit; gross floor includes
  non-residential components of mixed-use records.
- m²/property divides the full record floor by declared properties; for
  mixed-use records it overstates residential unit size.
- Quartile boundaries are sample-derived and specific to this extract;
  they are labels of convenience, not market size classes.
- Record-date proxy age (see [era profile limitations](cadastre_eras.md)).
- Descriptive cross-tabulation only: no trend, causal or significance
  claim; no claim that newer construction "tends" anywhere — the weak
  record-level correlation is the honest summary.

## Relation to existing work

This matrix qualifies the [era profile](cadastre_eras.md): the 1951–1990
eras that dominate Sevilla's stock are overwhelmingly large-block formats,
and the [rehabilitation cross-check](cadastre_era_rehab.md) shows exactly
those formats carry the highest estimated need — while mid-century units
are also the smallest (99–131 m²/property). Newer stock (1991+) is both
larger and much scarcer (4.7% of properties).
