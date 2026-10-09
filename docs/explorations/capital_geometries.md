# Capital barrio geometries: source assessment (Málaga, Granada, Córdoba)

Added 2026-10-09. Research-only assessment of official sub-municipal
polygon sources for joining the capital cadastre extracts below municipal
grain. No downloads into the repo; inspection only (one Málaga GeoJSON
fetched to /tmp to verify schema). Per-city verdicts below.

## Málaga: usable at barrio grain

- Portal: `datosabiertos.malaga.eu`, dataset
  "Sistema de Información Cartográfica - Barrio", CC BY-SA 4.0, updated
  2022-05-25.
- Files: CSV / GeoJSON / SHP / KML / GML in both EPSG:25830 and EPSG:4326,
  e.g. `da_cartografiaBarrio-25830.geojson` (use the 25830 flavor: no
  reprojection needed, same CRS as the cadastre pilot).
- Content: 419 barrio polygons (Polygon), keys `ID_BARRIO`, `NUMBARRIO`,
  `NOMBARRIO`/`NOMCOMUNBAR` (names carry trailing padding spaces —
  strip on load). 1.8 MB GeoJSON.
- Same dataset family offers Distrito Municipal and Distrito Censal as
  fallbacks. License note: BY-SA 4.0 share-alike applies to derived
  geometry products.
- **Verdict: USABLE.** Next step: vendor the 25830 GeoJSON, build the
  interior-point join, replicate per-barrio era profiles.

## Granada: districts usable, barrios unclear

- Portal: `opendata.granada.org`, dataset "Distritos y territorio",
  CC-BY, vintage 2023-01-01 (metadata updated 2026-08-03).
- Content: 8 municipal districts (Albaicín, Beiro, Centro, Chana, Genil,
  Norte, Ronda, Zaidín) as SHP/ZIP/PDF — district grain only. A second
  layer holds 101 Asociación de Vecinos action zones (SHP), which are
  administrative zones, not statistical barrios.
- What Granada calls "barrios" on the municipal site is the 8-district
  list; no official barrio-polygon layer was found.
- **Verdict: DISTRICTS USABLE (8 units, coarse); sub-district only via
  AA.VV. zones (101, non-statistical).** Decision needed before any join:
  accept district grain or adopt AA.VV. zones with an explicit
  non-comparability note vs Málaga/Sevilla barrios.

## Córdoba: districts usable, barrios blocked

- Portal: `datosabiertos.cordoba.es` (CKAN), "Recursos Cartográficos":
  `distritos.geojson` (38.8 kB, updated 2024-04-08). License field is
  unspecified on the resource **and** at dataset level (checked
  2026-10-09 via the CKAN API: `notspecified`) — there is no license
  grant, so vendoring the file is blocked regardless of technical fit.
- Barrio polygons: not found. The portal publishes barrio *statistics*
  (population by barrio, XLS/PDF) but no barrio geometry layer.
- **Verdict: DISTRICTS TECHNICALLY AVAILABLE BUT UNLICENSED — DO NOT
  VENDOR; BARRIOS BLOCKED.** Paths forward: a formal data request to
  the Ayuntamiento covering both license and barrios, or census-section
  aggregation (not assessed here).

## Recommendation

Proceed Málaga first (barrio grain, clean licensing with share-alike
noted, same CRS). Granada at district grain only after an explicit grain
decision. Córdoba stays municipal until barrio polygons surface or a
request succeeds. Each city's join needs its own geometry QA pass
(overlap/gap checks like the Sevilla pilot) before any profile is
published.
