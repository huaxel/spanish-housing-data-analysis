# Sevilla-province cadastre coverage: extension assessment

Added 2026-10-09. Assessment of extending the physical-stock pilot from
Sevilla municipality to all of Sevilla province. Inventory artifact:
`artifacts/province_inventory.json` (script: `scripts/inventory_province.py`;
feed titles plus one HEAD per archive, no downloads).

## Inventory (measured 2026-10-09)

The province-41 ATOM feed lists **106 municipalities** totaling
**266,942,849 bytes (266.9 MB)** of BU archives. Sevilla city itself is
35,431,544 bytes (13.3%). The median municipality archive is ~1.5 MB;
76 of 106 exceed 1 MB; none is under 190 kB.

Largest archives:

| Municipality (CAT) | MB |
|---|---|
| Sevilla (41900) | 35.4 |
| Dos Hermanas (41038) | 14.9 |
| Alcalá de Guadaíra (41004) | 11.0 |
| Carmona (41024) | 8.6 |
| Utrera (41095) | 7.1 |
| Los Palacios y Villafranca (41069) | 6.8 |
| La Rinconada (41081) | 5.4 |
| Coria del Río (41034) | 5.0 |
| Écija (41039) | 4.9 |
| Mairena del Aljarafe (41059) | 4.9 |
| Morón de la Frontera (41065) | 4.8 |
| Lebrija (41053) | 4.8 |
| Mairena del Alcor (41058) | 4.5 |
| Arahal (41011) | 4.4 |
| Marchena (41060) | 4.4 |

## Cost estimate

- **Download**: ~267 MB one-time, manifest-pinned like the existing pilots.
  Same order as the three capital archives combined (73 MB).
- **Parse**: at the Sevilla rate (~1,650 records/MB) the province holds
  roughly 440,000 BU records; single-threaded GML parsing should take
  roughly 25–35 minutes. DuckDB handles that row count trivially.
- **Code**: the capitals fetch script already parameterizes CAT/INE codes
  and municipal grain; extending its city list to 106 entries is mechanical.
  No new parser logic is needed.

## Grain and join plan

Municipal grain only. Outside Sevilla capital there are no SIM-style barrio
polygons in this project, and none is assumed. The natural join partner
already exists: the municipal sidecar (`sevilla_2021.duckdb`) holds census
stock, household, vacancy-class and rent context for every province
municipality. A province build would add the missing physical-stock leg
(records, properties, era mix, surface medians) per municipality.

The one risky step is the **CAT→INE mapping for 106 municipalities**.
Feed titles carry CAT codes and names; the sidecar keys on INE codes. Name
matching has accent, article and compound-name quirks (e.g. "EL CUERVO DE
SEVILLA"), so the mapping must be validated per municipality — ideally
against the official INE–Catastro correspondence, not string matching —
before any parse output is trusted.

## Recommendation

**Proceed.** Cost is moderate (~267 MB, ~30 min parse, mechanical code
reuse), the municipal sidecar makes the join immediately useful, and there
is no geometry research to do at municipal grain. Preconditions: (1) a
validated CAT→INE map for all 106 municipalities; (2) a province DB kept
separate from `stock.duckdb` so existing freshness keys are untouched
(same pattern as `stock_capitals.duckdb`); (3) per-municipality era/surface
profiles registered as a new exploration with the usual audit wiring.
Barrio detail outside the capital stays out of scope.
