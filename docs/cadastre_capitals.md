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

Municipal grain only. `barrio_id` is NULL and `match_status` is
"municipal_only": no barrio or district geometry layer is attempted for
these cities. Footprint area and centroid are still measured per record. A
per-city barrio join needs official local geometries and is tracked as
follow-up work.
