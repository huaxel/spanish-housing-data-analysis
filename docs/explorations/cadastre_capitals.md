# Andalusian-capital physical-stock profiles (municipal grain)

Added 2026-10-09. Municipal-grain construction-era profiles for Málaga,
Granada and Córdoba capitals from the DGC INSPIRE Buildings archives (feed
vintage August 2026), with the Sevilla pilot as benchmark. Same record-date
proxy semantics as the [Sevilla era profile](cadastre_eras.md): earliest
component construction year per BU record weighted by declared housing
properties — not measured dwelling ages. Artifact:
`artifacts/cadastre_capitals.json` (fetch:
`scripts/fetch_cadastre_capitals.py`; exploration:
`explorations/cadastre_capitals.py`).

## Method

The three capital archives (33.6 / 14.2 / 25.2 MB) are parsed with the same
GML record logic as the Sevilla pilot; at the time of writing the join
was absent, so this comparison is municipal grain (109,582 BU records
total, 91,232 with a positive housing-property count). Málaga barrio and
Granada district joins have since landed in `stock_capitals.duckdb` with
their own profiles (see below); Córdoba stays municipal.

| City (CAT→INE) | Records | Housing properties | Missing-year share |
|---|---|---|---|
| Málaga (29900→29067) | 40,231 | 261,269 | 0.00% |
| Granada (18900→18087) | 18,149 | 140,818 | 0.02% |
| Córdoba (14900→14021) | 32,852 | 158,873 | 0.10% |
| Sevilla benchmark (41900→41091) | 50,321 | 327,237 | 0.00% |

## Findings

**All four capitals share the same construction-era shape.**

| Era share (% of dated properties) | Málaga | Granada | Córdoba | Sevilla |
|---|---|---|---|---|
| Pre-1951 | 4.1 | 6.5 | 4.1 | 6.7 |
| 1951–1970 | 22.6 | 24.5 | 26.6 | 28.6 |
| **1971–1990** | **39.5** | **42.1** | **34.7** | **37.9** |
| 1991–2010 | 28.6 | 23.0 | 27.8 | 22.1 |
| 2011+ | 5.2 | 3.9 | 6.8 | 4.7 |
| Property-weighted median year | 1979 | 1977 | 1980 | 1976 |

The 1971–1990 development boom dominates everywhere (35–42% of stock);
Granada peaks hardest at 42.1%. Córdoba is the youngest profile (median
1980, 34.6% post-1990 stock); Sevilla the oldest (median 1976). Pre-1951
fabric is a small minority in all four (4–7%). Median record gross floor
is similar across cities (227–256 m²), so the era mix — not building scale —
is what differs.

## Limitations

- Municipal grain for the comparison, with Málaga barrio and Granada
district profiles published separately (see below); Córdoba stays
  municipal pending licensed geometries.
- CAT municipality codes differ from INE codes (mapped explicitly above);
  mixing them up silently reassigns cities — the fetch pins both.
- Same record-date proxy limitations as the [era profile](cadastre_eras.md):
  earliest component year, mixed-use records included, cadastral property
  units.
- Feed vintage August 2026 for all three capitals; comparison with the
  Sevilla snapshot is cross-sectional, not a change measure.

## Relation to existing work

This extends the physical-stock pilot beyond Sevilla for the first time and
closes the "other Andalusian capitals" backlog item. The shared boom-era
peak suggests the Sevilla era findings (mid-century mass housing = largest
need concentration) may travel — testing that needs the same SIM-style
condition layers per city, which do not currently exist in this project.
