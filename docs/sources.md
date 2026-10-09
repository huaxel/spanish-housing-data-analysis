# Sources

All fetches stage to a temp file and atomically replace the pinned copy;
`data/input_manifest.json` records URL/API + access date + SHA-256.
Verification (`make verify`) fails on changed bytes — re-fetch, don't edit.

| Source | Access | Grain / window | Notes |
| --- | --- | --- | --- |
| MIVAU Estimación del Parque de Viviendas (VDP002_01 CSV) | `cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP002_01.csv` | provincia × año × tipo, 2001–2025 | `;`-separated, BOM; Ceuta+Melilla one aggregate |
| INE IPV, operation IPV (Id 15), table 80271 | `servicios.ine.es/wstempus/js/es/DATOS_TABLA/80271` | CCAA × año × tipo, 2007–2025 | medias anuales; base 2025 (identity-checked) |
| INE Padrón Revisión, operation DPOP (Id 22), tables 2852/2853 | `.../DATOS_TABLA/2852`, `.../2853` | provincia/CCAA × año, 1996–2021 | ends 2021; provincial 2022+ via Censo Anual (see row below) |
| INE Censo 2021 viviendas por intensidad de uso (tpx=59531) | `jaxi/files/tpx/csv_bd/59531.csv` | municipio × 18 medidas, 2021 only | static CSV; objective vacancy from electricity consumption (3,139 named + Resto); total 26,623,708, vacías 3,828,307 |
| INE Censo viviendas 2021 (viewer tpx=59521) | browser-exported CSV via playwright-cli (no static file) | provincia × tipo × banda, 2021 only | cp1252 → UTF-8 at pin; anchor = Total × Total |
| INE Censo viviendas 2001/2011 (CENSOPV) | `ine.es/jaxi/files/_px/csv_bd/t20/e244/viviendas/p07/nal02.csv` | CCAA/provincia × censo | tab-separated, BOM; anchor use |
| INE ECP población (operation ECP Id 450), table 56940 | `.../DATOS_TABLA/56940` | CCAA × 1-ene, 1971–2025 | FK_Periodo 19 = 1 Jan (date-checked at fetch) |
| INE Censo Anual de Población, table 68521 | `jaxiT3/files/t/es/csv_bd/68521.csv` | provincia × 1-ene, 2021–2025 | static CSV (no API); margin Total×Todas las edades×Total; 2025 national = ECP exact; 2021 prov-vs-padrón mean 0.17% |
| INE ECP hogares (ECP), tables 60131/60133 | `.../DATOS_TABLA/60131`, `.../60133` | CCAA/provincia × 1-ene, 2021– | household totals (tamaño detail skipped) |
| INE Censo 2011 tenure × size por CCAA/provincia (jaxi p01/02015) | direct CSV URL in `fetch_censo2011_tenencia.py` | 2011 only | '.', '..' missing; dot thousands; mortgaged anchor 5,940,928 |
| INE Censo 2011 vintage por provincia (jaxi p01/01011a) | direct CSV URL in `fetch_censo2011_vintage.py` | provincia × tipo × construction band | dot thousands; '..' suppressed; ±10 additive tolerance |
| INE Censo 2011 tipos de vivienda por municipio (CENSOPV 3456) | `.../DATOS_TABLA/3456` | 2,308 municipios >2.000 hab., 2011 only | principal/secundaria/vacía; 2021 census dropped the split; joined to the 28 valor municipios |
| Diputació de Barcelona municipal housing (DIBA opendata.zip) | media.diba.cat ZIP | 311 municipios: sale €/m² M19 (2013–), rents M23 (2005–), vacant H9a (2018–), tourist H18a (2015–), burdens M11d/M11e (2015–2022) | cp1252, Catalan decimals; province row '08' mapped; muni_key() canonicalizes article order |
| Madrid municipios valor tasado (datos.comunidad.madrid, MIVAU mirror) | direct CSV URL in `fetch_municipios_mad.py` | 28 municipios × año, 2005– | cp1252 → UTF-8; '-' unpublished dropped; third-party mirror, provincial mean cross-checked |
| Madrid barrios precio registral (Ayto. Banco de datos, Registradores) | session-built CSV export in `fetch_barrios_mad.py` (serie 0504020100060) | 153 barrios × año × tipo, 2007– | declared transaction values ~96-98% coverage; <15-case cells suppressed (null); catalog parsed dynamically; feeds `barrios_madrid` |
| Barcelona city/district/barrio rents (Generalitat, INCASÒL deposits) | 8 XLSX (`anual/trimestral_bcn_{contractes,lloguer,lloguer_m2,sup}`), `fetch_barrios_bcn.py` | city + 10 districts 2000–2025, 73 barris (annual 2013–, quarterly 2014–; 2026 partial) | filed contracts (counts, mean rent, €/m², area); <6-contract cells unpublished (null); not asking prices; feeds `barrios_bcn_lloguer_anual` (2,184 rows) and `barrios_bcn_lloguer_trimestral` (4,984 rows) |
| CGPJ launches + foreclosure filings by province (efecto de la crisis series) | consolidated provincial workbook through 2026Q1, `fetch_desahucios.py` | 50 provinces; launches 2013Q1–2026Q1 (mortgage/LAU/other), filings 2007Q1– | exhaustive juzgados series (service-common excluded); launches count properties, not tenant evictions; annual totals skipped; feeds `desahucios_provincia` (3,850 rows) |
| Barcelona registered sales (Generalitat, Registradores) | quarterly `BCN_trimestral_YYYY` / `Trimestrals_Barcelona_YYYY`, `fetch_barrios_bcn_compra.py` | city + 10 districts + 73 barris, 2018–2019 + 2021–2026 (no 2017/2020 files) | transactions (new-free/protected/used), mean area/price/€-per-m²; zero prices → null (<3 contracts); city total non-additive; 2026 adds max/min; feeds `barrios_bcn_compraventes` (2,520 rows) |
| Sevilla barrios housing indicators (EMVISESA/Ayuntamiento SIM; IPRA from AVRA fianzas) | public ArcGIS layers 179 (`X`) and 171 (`VHS`), `fetch_barrios_sev.py` | 108 barrios × 2016–2022 IPRA windows (756 rows), plus one undated purchase-price snapshot | IPRA in €/m² built/month, rolling 3-year windows, 37 missing cells; purchase €/m² built by housing type, unifamiliar missing in 31 barrios, reference period/method unspecified; both layers last edited 2023-02-12; feeds `barrios_sevilla` and `barrios_sevilla_compra` |
| Sevilla SIM barrio context (EMVISESA/Ayuntamiento) | ArcGIS population 26, households 30, typology `ñññ`/2, housing join `TTT`/4, rehabilitation `rrr`/101, use/vacancy `VIVVAC`/133; `fetch_sevilla_context.py` | 108 barrios; population + households 2015–2021; housing/rehab/use undated snapshots; tourism portal counts 2008, 2021-02, 2021-08, 2022-02 | IDG-joined, source nulls preserved; the physical/use snapshots do not publish reference years; tourism registration totals are undated. Accessibility service 109 is district-level only and is not allocated to barrios; feeds `sevilla_sim_poblacion_hogares`, `sevilla_sim_vivienda`, `sevilla_sim_turismo` |
| Sevilla second-hand offer prices (Ayuntamiento Anuario 2025, table 7.3.9; FEMAS mirror) | `7-3-9.xls`, `fetch_sevilla_oferta.py` | Fotocasa 11 districts × 12 months and Idealista 17 zones × 12 months, 2024 | €/m² offer prices, not transactions; source geographies kept separate; feeds `sevilla_oferta_zona` |
| INE Padrón municipal Valencia, operation DPOP, table 2903 | `.../DATOS_TABLA/2903` | 266 municipios × año, 1996–2025 | province aggregate 'Valencia/València' dropped with pinned-total guard; city is 'València'; feeds `muni_vlc` (rents + 2011 vacancy only — no municipal sale-price source exists) |
| INE Padrón municipal Sevilla, operation DPOP, table 2895 | `.../DATOS_TABLA/2895` | 106 municipios × año, 1996–2025 | 'Sevilla' province/city collision resolved against pinned 2021 total (province dropped, city 'Sevilla (ciudad)'); feeds `muni_sev` (same rents + vacancy design) |
| INE Padrón municipal nacional, operation DPOP, all 52 municipal tables | `.../DATOS_TABLA/<id>` (52×, per-table JSON mirrors) | 8,136 municipios × año, 1996–2025 | generic fetcher with retry; one aggregate dropped per table with pinned-total guard (same-name → anchor match, distinct-name → drop); feeds `muni_all` |
| INE Transmisiones (jaxiT3 6155, registradores) | MIVAU-style direct CSV URL in `fetch_transmisiones.py` | CCAA/provincia × año, 2007– | Total/nueva/usada/libre/protegida; dots are thousands; nueva+usada==total asserted |
| INE Turísticas (Tempus3 39364/46141) | `.../DATOS_TABLA/39364`, `.../46141` | CCAA/provincia × mes, 2020– | December snapshot; duplicate uniprovincial series asserted identical |
| INE Hipotecas CCAA/prov/rates (Tempus3 76316/76317/76315) | `.../DATOS_TABLA/76316` etc. | CCAA/provincia × mes (2003–), rates nacional | Viviendas only; territory↔measure positions swap between tables; importe in thousands of EUR |
| Padrón extranjeros por provincia (jaxi e245/p08/03005) | static CSV URL in `fetch_padron_extranjeros.py` | provincia × año, 1998–2022 | TOTAL EXTRANJEROS × Ambos sexos |
| INE EM flujos inmigración (Tempus3 24322) | `.../DATOS_TABLA/24322` | provincia × año × nacionalidad, 2008–2021 | Ambos sexos, Total edad; annual (FK_Periodo 28); Nacional + 51+52 aggregated |
| INE ECH hogares por provincia (jaxi p274/serie/def/p03/l0/03003) | static CSV URL in `fetch_ech.py` | provincia × año, 2014–2020 | Total × Total margin; thousands → units; mixed `.`/`,` decimals |
| INE ECV renta por hogar (Tempus3 9949) | `servicios.ine.es/wstempus/js/es/DATOS_TABLA/9949` | CCAA × encuesta, 2008– | renta_anyo = encuesta − 1; neta + con-alquiler-imputado (marts use neta); Base 2013 |
| INE IPC general (Tempus3 76136) | `.../DATOS_TABLA/76136` | CCAA/Nacional × mes, 2002– | general index levels only (variations recomputed); base 2021; `ipc_anual` annual means |
| MIVAU Valor Tasado (VDP006_01 CSV) | `cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP006_01.csv` | provincia/CCAA × trimestre, 1995– | `;`-separated, BOM; Régimen Libre/Protegida; quirks: CPRO literal `'null'` on aggregates, aggregate rows keyed by `Provincia='Total CCAA'`, Murcia aggregate with empty CODAUTO (`Murcia, Region de`, unaccented), no provincial rows for 28/30/31/33, no CCAA aggregate for Balears/Cantabria/Rioja (single-province fallback), 844 unpublished quarter-cells, one junk `Total CCAA`/empty row (skipped: empty Valor) |

Unreachable (probed 2026-10-06, do not retry blindly): provincial ECP population
(table 56945) — `DATOS_TABLA` refuses every date window down to a single day
(`restricciones de volumen`), `SERIES_TABLA/56945` returns empty, and
`DATOS_METADATAOPERACION/ECP` filters (115:provincia + 18:Total + 356:Todas,
with and without `p=1`, raw and URL-encoded) all match nothing. Filter-variable
IDs resolved for the record: Provincias=115 (Araba/Álava=2 … Ourense=53),

**Workaround found 2026-10-06:** the Censo Anual de Población (the
register-based replacement for the decennial census) publishes provincial
population 2021–2025 as a **static CSV** (`jaxiT3/files/t/es/csv_bd/68521.csv`, 208 MB) —
no API call needed. Verified: 2025 national 49,128,297 = mart exact;
2021 province-vs-padrón mean Δ 0.17%. See
`docs/explorations/censo_anual_probe.md`; fetch not yet built.
Sexo=18 (Total=451), Totales de edad=356 (Todas=15668). If INE lifts the block,
re-add 56945 to `scripts/fetch_ecp.py` and extend the provincia mart past 2021. |

| SERPAVI alquiler por distrito censal (MIVAU, fianzas tax exploitation) | same workbook Distritos sheet, `fetch_serpavi.py` | 9,680 districts × 2011–2024 (1,099,206 cells); codes only, no names; secciones skipped | same 20 measures; populated cells only; feeds `serpavi_distritos` |
| SERPAVI alquiler municipal (MIVAU, fianzas tax exploitation) | `cdn.mivau.gob.es/.../bd_SERPAVI_2011-2024.xlsx` | municipio × 20 medidas, 2011–2024 | 71 MB Excel wide matrix; €/m² mediana/P25/P75 (VC/VU), superficie, contratos; 2,555 municipios at 2024 (29%), all named; validated vs DIBA Barcelona (13.68 €/m² ≈ 1,147 €/mo); probe in docs/explorations/serpavi_probe.md |
| AEAT viviendas declaradas en IRPF por uso (habitual/arrendadas/a disposición) | sede AEAT irpfvivienda static HTML tables, `fetch_aeat_viviendas.py` | CCAA + provincia, tax years 2023–2024; 56 rows/year parsed to `aeat_viviendas_uso.parquet` | common fiscal territory only (no País Vasco, Navarra, Ceuta, Melilla — asserted, never filled); habitual-first use priority differs from SERPAVI rental-first; both years' Total rows exceed CCAA sums (pinned gaps) and are excluded from parsed output; hunt in docs/occupancy_availability.md |
| INE Censo 2021 section indicators (dwellings/persons/households) | `ine.es/censos2021/C2021_Indicadores.csv`, `fetch_censo_secciones.py` | 36,333 census sections, 34,970 usable (1,363 suppressed carry persons only) | t18-t22 housing + t1 persons + t21 households with occupancy ratios in `censo2021_secciones`; 2021-01-01 vintage quarantined, never joined to current series; CUSEC join keys verified against section cartography (not vendored, 64 MB); hunt in docs/occupancy_availability.md |
| Junta de Andalucía RMDVP table 01 (protected-housing demand stock) | monthly `*_rmdvp01.solicitudes...xls` twins in year archive pages, `fetch_rmdvp.py` (xlrd) | 69 months 2020-12..2026-08, municipio grain + province subtotals + Andalucía total, parsed to `rmdvp_inscripciones.parquet` | end-of-month stock of solicitudes/inscripciones (total/activas/canceladas-por-adjudicación/caducadas-y-otros) in `rmdvp_inscripciones`; only listed municipalities stored (518 growing to 543 of 785), absent never zero-filled; pre-2021 months PDF-only and out of scope; hunt in docs/occupancy_availability.md |
| Eurostat EU-SILC housing conditions (overcrowding/under-occupation/median burden) | dissemination API JSON-stat, `fetch_housing_conditions.py` (same pattern as overburden) | Spain annual person rates/medians, survey years 2003 onward; 9 datasets parsed to `housing_conditions.parquet` | overcrowding by age/tenure/urbanisation/quintile, under-occupation by age/tenure/urbanisation, median burden by age/urbanisation in the `housing_access.duckdb` sidecar (never a mart join); tenure/urbanisation cuts carry no published national total; break flags retained; see docs/housing_overburden.md |
| INE Índice de Precios de Vivienda en Alquiler (Tempus3) | live in API | CCAA/prov | redundant with SERPAVI (see construction probe) |
| Eurostat GISCO LAU 2021 (municipal polygons, map asset only) | `gisco-services.ec.europa.eu/distribution/v2/lau/topojson/LAU_RG_01M_2021_4326.json` | 8,131 municipios, EPSG:4326 | 43 MB TopoJSON (whole Europe); LAU_ID = 5-digit INE code, no name join needed; `make geo` keeps ES features, simplifies to 7% (~3.8 MB `evidence/static/geo/municipios.geojson`); vacancy join 3,139/3,185 (46 `xx999` Resto aggregates have no polygon) |

Methodology references: INE IPV metodología Base 2025
(`ine.es/daco/daco42/ipv/metodologia2025.pdf`); MIVAU parque metodología
(`mivau.gob.es/.../2025-02_metodologia_estimacion_del_parque_de_viviendas.pdf`;
open-data readme `cdn.mivau.gob.es/.../Readme_VDP002_01.pdf`).

Table IDs were resolved via `OPERACIONES_DISPONIBLES` + `TABLAS_OPERACION`
(see `scripts/ine_discover.py`), not copied from search snippets — two
snippet-suggested IDs (67202/67232) turned out to be unrelated tables.

## EU-SILC housing-cost overburden (Eurostat, national Spain)

Added 2026-10-08. `ilc_lvho07a` (age, total sex/poverty status),
`ilc_lvho07b` (income quintile) and `ilc_lvho07c` (tenure) are retrieved
through the official JSON-stat dissemination API, with raw responses and
derived sidecar pinned in the input manifest. These are percentages of
persons living in households with excessive housing costs, not shares of
households or local estimates. Survey-year timing, flags, overlapping age
groups and separate marginal populations are documented in
[housing_overburden.md](housing_overburden.md).

The Evidence `access` source reads `data/processed/housing_access.duckdb`;
the central housing marts and existing estimator inputs are unchanged.
Fetch with `scripts/fetch_housing_overburden.py`, rebuild from verified pins
with `--offline`, and verify exact derivation with
`scripts/verify_housing_overburden.py` (included in `make verify`).

## Cadastral physical stock (DGC INSPIRE BU, Sevilla pilot)

The official municipal BU archive provides parcel-grouped construction
footprints, earliest/latest construction dates, gross floor area and counts
of cadastral properties destined to housing. SIM barrio geometry uses the
same keyed geography as existing household context; labels and IDs are
validated across pinned inputs. Cadastral and INE municipality codes differ.

The stock sidecar, `data/processed/stock.duckdb`, leaves central marts and
estimator inputs unchanged. `scripts/fetch_cadastre_stock.py` downloads and
pins inputs, supports offline rebuild, and verifies pins/code freshness with
`--check` (included in `make verify`). See [cadastre_stock.md](cadastre_stock.md)
for the official specification and allocation/measurement limitations.
