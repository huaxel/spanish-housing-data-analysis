# Sevilla-province physical-stock profiles per municipality

Added 2026-10-09. Per-municipality construction-era profiles for all 106
Sevilla-province municipalities from `stock_province.duckdb`, joined to the
municipal sidecar (census households, dwellings, rent context). Municipal
grain only; same record-date proxy semantics as the Sevilla pilot. Artifact:
`artifacts/cadastre_province.json` (fetch: `scripts/fetch_cadastre_province.py`;
exploration: `explorations/cadastre_province.py`).

## Method

Of 512,758 parsed BU records, **415,518 are housing-bearing** (positive
declared properties) and enter the profiles; the rest are non-residential
parcels. Era shares are property-weighted within each municipality. The
CAT→INE map was derived at runtime with strict bijection assertions (see
the [coverage assessment](provincial_coverage.md)). Records west of the
UTM zone line carry 25829 geometry and contribute attributes only
(`municipal_only_25829`, 42 municipalities); no planar measures are mixed
across zones.

## Findings

**Province: 891,374 declared housing properties; the capital holds 36.7%.**

| Province measure | Value |
|---|---|
| Housing-bearing records | 415,518 |
| Declared housing properties | 891,374 |
| Sevilla-city share of properties | 36.7% |
| Median of rest-of-province median years | 1986 |

**The province peaks a generation later than the capitals.**

| Era share (% of dated properties) | Province | Sevilla city |
|---|---|---|
| Pre-1951 | 7.8 | 6.7 |
| 1951–1970 | 20.2 | 28.6 |
| 1971–1990 | 31.0 | 37.9 |
| **1991–2010** | **35.6** | 22.1 |
| 2011+ | 5.3 | 4.7 |

Province-wide, the 1991–2010 suburban expansion (35.6%) outweighs the
1971–1990 boom that dominates every capital — the metro periphery and the
medium towns built their stock later. The rest-of-province median of
median construction years is 1986, a decade after the capital (1976).

**Properties per household peak in the small Sierra municipalities**
(El Castillo de las Guardas 2.82, El Madroño 2.39, El Ronquillo 2.15) —
second homes and registration gaps, not over-occupancy; the same pattern
seen at barrio grain inside the capital, at larger amplitude.

## Limitations

- Municipal grain only; no within-municipality geography outside Sevilla
  capital (covered at barrio grain in the Sevilla pilot).
- One case-normalized parcel reference exists in the parse (lowercase check
  character, validated against its gml:id); duplicate detection still
  applies post-normalization.
- 25829-zone records contribute attributes only; footprint/centroid are
  NULL for 42 municipalities by design.
- Record-date proxy age, cadastral property units, mixed-use records
  included — see the [era profile limitations](cadastre_eras.md).
- Descriptive cross-section; no causal claim.

## Relation to existing work

This implements the [coverage assessment](provincial_coverage.md)
recommendation: the municipal sidecar now has its physical-stock leg for
every province municipality, in a separate database that leaves all
existing freshness keys untouched.
