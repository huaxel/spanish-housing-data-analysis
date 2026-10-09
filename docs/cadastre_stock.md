# Physical stock: Sevilla cadastral pilot

The explorer's `/stock/` page uses actual cadastral building footprints,
construction-date ranges, declared housing-property counts and gross floor
area. This is a physical-stock layer, not another regional stock/population
ratio and not an availability estimate.

## Sources and units

- [DGC INSPIRE Buildings municipal feed](https://www.catastro.hacienda.gob.es/INSPIRE/buildings/41/ES.SDGC.bu.atom_41.xml).
  The exact Sevilla entry and its archive URL are checked before download.
  Cadastral and INE municipality codes differ; the crosswalk is explicit.
- [Official dataset specification](https://www.catastro.hacienda.gob.es/webinspire/documentos/Conjuntos%20de%20datos.pdf), Buildings attributes section.
  A BU record groups constructions on a cadastral parcel. Separate footprint
  components are not separate independent records. Counts are cadastral
  property units, not households or necessarily census dwellings.
- SIM barrio polygons come from the same official population layer used by
  existing context tables. Both projected and map coordinate versions are
  retained and pinned; exact IDs and complete unique coverage are validated.

`dateOfConstruction` beginning/end are the oldest/newest construction dates
among the grouped units, not a single construction year for every dwelling.
The earliest-date distribution gives equal weight to each housing-bearing
BU record, not each dwelling. Missing year placeholders and malformed dates
are preserved as raw strings and flagged; no guessed digit correction.

`geometry` is an above-ground footprint. Area is calculated in the source's
metric projected CRS, subtracting explicit interior holes. Shapely/GEOS
validates self-intersections, hole containment and component overlaps before
measurement; invalid BU geometry cannot publish a supported subset. `officialArea`
uses the publisher's gross floor area and square-metre unit. That measure
includes all uses within a housing-bearing record: no residential-only
floor-area claim, footprint-times-floors inference or mean dwelling-size
estimate is made. The dominant use does not exclude mixed-use housing.

The published condition is the best condition among construction units in
a parcel according to the specification; it cannot establish whole-building
habitability. Record-registration dates are not construction dates, and
changes between snapshots would not automatically be new construction.

## Spatial allocation and denominators

Every footprint component gets a deterministic interior anchor: prefer its
area centroid if interior, otherwise use scanline parity to find an interior
point respecting holes. All component anchors must match uniquely to the
same barrio. Ambiguous, outside, partly outside and multi-barrio records
remain unassigned and visible in coverage tables; municipal distributions
include them. Counts are neither duplicated nor allocated proportionally.

This is an approximate point-based location rule, not an exact overlay.
It can miss a boundary crossing within a large component. Density uses the
validated published SIM geometry. It has not been established as the entire
administrative barrio area or as residential land. It
reports assigned housing properties, not residents or occupied homes. Empty
eligible joins yield null quantities rather than assertions of no housing.

The page juxtaposes the cadastral snapshot with separately dated SIM
household change. It does not compute a contemporary units/households ratio,
absorption, vacancy, or causal price effect from mismatched vintages.
Further physical-stock/price comparisons should retain geography, vintages,
composition and aggregation units rather than treat this as a causal model.

## Source geometry defects: explicit correction and quarantine

The SIM display geometry contains overlapping components and an invalid
self-intersecting barrio geometry. Valid components of the same feature are
explicitly dissolved into their union before computing area or drawing the
map. Source-component area and overlap correction are retained in the
sidecar and summarized on the page. Shared edges between valid GML Surface
patches are permitted; overlapping BU footprint interiors are rejected.

Invalid rings or holes are never silently repaired with buffer, make-valid
or precision snapping. A barrio with invalid topology is quarantined as a
whole: its context key remains, but area is null, it receives no spatial
assignment and it is omitted from the map. Thus an unassigned BU need not be
outside the municipality. Municipal BU attributes and date/area distributions
still retain every source record. The invalid barrio's household context is
not discarded and no zero stock is inferred.

Strict GML traversal consumes every supported geometry property, surface,
patch, ring and coordinate list; it checks the horizontal footprint reference
and rejects unknown representations or a mixture of nil and present geometry.
Dates validate the entire date-time value, not only its date prefix. The
geometry engine and GEOS versions participate in derivation freshness.

## Reproduction and checks

```sh
uv run python scripts/fetch_cadastre_stock.py           # official downloads + build
uv run python scripts/fetch_cadastre_stock.py --offline # rebuild pinned local inputs
uv run python scripts/fetch_cadastre_stock.py --check   # pins + code freshness + DB/parquet
uv run python -m pytest tests/test_cadastre_stock.py -q
```

Raw archive and feeds are pinned in `data/input_manifest.json`. Only the
building GML is streamed; the construction-part archive member is not added
to property totals. Download/member-size bounds, complete source IDs, source
CRS, area definition, duplicate parcel IDs and count signs are checked.

Outputs are `data/raw/parquet/cadastre_sevilla_buildings.parquet`, the separate
`data/processed/stock.duckdb`, and the vendored barrio map at
`evidence/static/geo/sevilla_barrios.geojson`. The sidecar stores raw-input,
script and geometry-helper hashes. Verification requires matching metadata
and output pins and exact agreement between database and parquet rows.

The main marts, estimator inputs and model outputs are deliberately unchanged.
Fetch/verify/build integration requires this sidecar without forcing a central
mart rebuild merely to add physical-stock exploration. Geometry and source
semantics are covered by offline synthetic tests; page SQL is also executed
against a small in-memory fixture, including mixed uses and unassigned rows.

## Descriptive stock/rent comparison

The stock page compares allocated physical summaries with the latest SIM
IPRA update. IPRA is a rolling rental-deposit reference level, not offer
rent or the national SERPAVI median. The page states both the stock snapshot
and contract window; current stock selection can reflect survival and
post-contract modifications. This is not a contemporary supply-demand test
or a retrospective predictor.

Rent joins require one source row per key/update and exact barrio/district
labels; duplicates, mismatches and missing rents are excluded rather than
selected arbitrarily. Correlations use pairwise complete barrios with equal
weight. Spearman uses average tied ranks. The district comparison correlates
global ranks after subtracting district means, not district-specific ranks
or an average of district correlations. Singleton groups contribute zero
residuals; insufficient variation gives null. This does not control income,
within-district centrality, contract selection or subsequent stock changes.

Leave-one-district-out checks rerank each remaining sample. They measure
geographic-composition sensitivity, not confidence intervals or significance;
no p-values or preferred causal specification are selected.

`make stock-rent` writes `artifacts/stock_rent_descriptive.json` directly from
the explorer queries, with database/query/script hashes and snapshot/method
metadata. Single-thread evaluation makes local exact checks reproducible.
`make verify` recomputes the report and refuses stale or missing results.
This target does not rerun or modify the central estimators.


## Construction-date weighting sensitivity

The page retains its equal-record earliest-year median and adds a second
lower discrete median weighted by each record's declared housing-property
count. It sums positive weights by barrio/year and selects the first year
whose cumulative weight reaches half the dated total. Ties aggregate; an
even split selects the lower central year, matching `quantile_disc`, not an
interpolated average. Integer cumulative arithmetic avoids floating-point
threshold errors and does not expand property rows.

Both versions select the same assigned housing-bearing records with valid
earliest years. The weighted-date panel reports included and excluded
property-count weight, not just the number of dated records. Unknown counts
and invalid/missing years do not gain fabricated observations; barrios without
eligible assignments retain null stock quantities. Missing dated weight is
not silently assigned the earliest/latest valid neighbour's year.

All weight inherits the BU record's earliest construction year. A BU can
contain several constructions and mixed uses; the oldest component need not
be residential. This is a **record-date proxy weighted by housing-property
counts**, not a measured distribution of individual dwelling construction
ages. It is not historical housing stock reconstructed at the IPRA date.

Both date proxies remain visible in the stock/rent, income-year and district-
omission comparisons, with the same descriptive rank procedures. Neither is
selected as a preferred causal specification. `make stock-rent` hashes the
page/analysis code and writes the dated-weight coverage alongside associations;
raw geometry and central marts/models are unchanged.
