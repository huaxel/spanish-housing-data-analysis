# Probe: SERPAVI rent index — municipal rents for ~all of Spain

**Date:** 2026-10-06 · **Status:** reachable, high value — fetch built (`fetch_serpavi.py`; municipal and district marts live)

## What it is

**Sistema Estatal de Referencia del Precio del Alquiler de Vivienda**
(MIVAU). Official rent statistics built from the **tax exploitation of
rental deposits** (fianzas) — ~37M rental observations 2011–2023/24.
Published at **sección censal / distrito / municipio / provincia / CCAA**
grain. The rent outcome currently exists in the repo only for Barcelona
municipios (DIBA M23); SERPAVI extends it to the whole country at
municipal grain.

## Access (verified)

Download page: `mivau.gob.es/vivienda/alquila-bien-es-tu-derecho/serpavi`
(403 without a browser UA; 200 with one). The full database is a single
Excel:

```
https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx
(71 MB, fetched 200)
```

## Structure (verified by reading the workbook)

| Sheet | rows | grain |
| --- | --- | --- |
| Municipios | 8,894 | **all municipios** — named, not a top-N |
| Provincias | 53 | 52 + Nacional |
| CCAA | 25 | 17 + Nacional + aggregates |
| Distritos | 10,543 | intra-municipal |
| Secciones censales | 36,294 | finest |

Columns: 4 id + 280 data = **20 measures × 14 years (2011–2024)**. Key
measures (VC = vivienda colectiva, VU = unifamiliar, M/25/75 = mediana/P25/P75):

- `ALQM2_LV_M/25/75_VC/VU` — **€/m²/month rent**
- `ALQTBID12_M/25/75_VC/VU` — €/month total rent
- `SLVM2_M/25/75_VC/VU` — surface m²
- `BI_ALVHEPCO_TVC/TVU` — number of contracts (base)

Coverage: median €/m² populated for 1,722 municipios (2011) rising to
**2,555 (2024, 29% of all municipios)** — larger municipios and any with
enough contracts; small villages blank (suppressed).

## Validation against the mart

Barcelona city: SERPAVI 2024 median 13.68 €/m² → × ~85 m² ≈ 1,160 €/mo
vs DIBA `muni_bcn.rent_month` 2024 = 1,147 — consistent. Hospitalet
12.5→13.0 €/m² (2023–24) monotone.

## Notes / caveats

- Tax-deposit based: measures the **actual rent paid in new/rolling
  contracts**, but the tax file may under-catch sublet/recent renewals;
  vacancy and contract-length composition differ from a survey.
- The workbook is a **wide matrix** (20 measures × 14 years as columns);
  the fetch needs a melt (rows = municipio × year) — mechanical.
- Mediana + P25/P75 are the published statistics; no variance/SE (tax
  file, not sample).
- 2011–2024 window; the repo's rent coverage (DIBA M23) is 2005– and
  would remain the long series for Barcelona.

## Update: district mart built (2026-10-08)

The Distritos sheet (same 20 measures × 2011–2024, keyed by 7-digit CUDIS)
is melted in the same fetch pass into `serpavi_distritos`: 1,099,206
populated cells across 9,680 districts in 7,332 municipios (10,511 district
rows published; fully-suppressed ones contribute no cells). District names
are not published — codes only. Anchor: Madrid distrito 04 (Salamanca)
2024 collective median 18.31 €/m². Secciones censales (36,294 rows) remain
skipped: census-vintage geometry makes them unstable across years.

## Cross-check (2026-10-08)

Median-of-district-medians tracks the published municipal median within
about a percent on average across all shared municipio-years; the largest
gaps sit on thin-contract villages where medians of a handful of contracts
are noisy. No melt bug indicated — the district table is consistent with
its municipal sibling.

## Verdict

**Highest-value data candidate on the board.** Municipal rents
nationwide (2,555 municipios at 2024, ~1,700+ back to 2011), official,
single-file download, verified parseable. Unlocks: rents as a second
outcome in the municipal panels (terrain, tourist, overhang), and a
rent-vs-price wedge by municipio. Fetch pattern identical to
`fetch_intensidad.py` (static download + pin + melt). Recommend build.

## VDP001 alternative route (2026-10-09, no rebuild)

The same SERPAVI source is also served long-format as MIVAU CDN
`VDP001_01.csv` (municipio × year × colectiva/unifamiliar; `PRECIO`
median/P25/P75 in €/month, `SUPERFICIE`, `VIVIENDA` witness counts;
2024 `PRECIO` mediana populated for 3,346 municipio codes — same
population as the workbook's total-rent columns, not the €/m² ones,
which VDP001 lacks). It is **uncatalogued** (datos.gob.es publishes
VDP002–VDP007 only; no readme) and adds no measure the workbook
lacks, so the built XLSX route stays canonical. Recorded here only
as a fallback if the workbook URL ever breaks.