# Andalusian-capital BU pilot: sources and method

Companion to the [capital profiles exploration](explorations/cadastre_capitals.md).
Covers the municipal-grain extension of the Sevilla physical-stock pilot
(see [cadastre_stock.md](cadastre_stock.md) for the Sevilla record semantics,
which are reused verbatim).

## Sources

DGC INSPIRE Buildings archives per capital, discovered via the provincial
ATOM feeds (feed vintage August 2026 for all three):

- Málaga: CAT code 29900 (INE 29067), province feed 29
- Granada: CAT code 18900 (INE 18087), province feed 18
- Córdoba: CAT code 14900 (INE 14021), province feed 14

CAT municipality codes differ from INE codes — capitals use 9xx00 CAT codes —
and the fetch pins both per city. Raw archives and feeds are pinned in the
input manifest; derived parquet per city plus `data/processed/stock_capitals.duckdb`
(buildings with the Sevilla schema, `municipios`, `stock_meta`) are recorded
as outputs. The parsing reuses the Sevilla GML record helpers, including the
strict parcel-reference, reversed-date and area-definition guards.

## Grain and limits

Municipal grain for all three capitals, plus sub-municipal joins where
official geometries exist: Málaga barrios (419 polygons, CC BY-SA 4.0)
and Granada districts (8 polygons, CC-BY, reprojected ED50→ETRS89) live
in the `barrios` table with conservative match statuses; Córdoba stays
municipal (`barrio_id` NULL, `match_status` "municipal_only") pending
licensed geometries. Footprint area and centroid are measured per record
where the CRS allows (25829-zone records are attribute-only by design).
