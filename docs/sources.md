# Sources

All fetches stage to a temp file and atomically replace the pinned copy;
`data/input_manifest.json` records URL/API + access date + SHA-256.
Verification (`make verify`) fails on changed bytes — re-fetch, don't edit.

| Source | Access | Grain / window | Notes |
| --- | --- | --- | --- |
| MIVAU Estimación del Parque de Viviendas (VDP002_01 CSV) | `cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP002_01.csv` | provincia × año × tipo, 2001–2025 | `;`-separated, BOM; Ceuta+Melilla one aggregate |
| INE IPV, operation IPV (Id 15), table 80271 | `servicios.ine.es/wstempus/js/es/DATOS_TABLA/80271` | CCAA × año × tipo, 2007–2025 | medias anuales; base 2025 (identity-checked) |
| INE Padrón Revisión, operation DPOP (Id 22), tables 2852/2853 | `.../DATOS_TABLA/2852`, `.../2853` | provincia/CCAA × año, 1996–2021 | ends 2021; successor pending |
| INE Censo viviendas 2001/2011 (CENSOPV) | `ine.es/jaxi/files/_px/csv_bd/t20/e244/viviendas/p07/nal02.csv` | CCAA/provincia × censo | tab-separated, BOM; anchor use |
| INE ECP población (operation ECP Id 450), table 56940 | `.../DATOS_TABLA/56940` | CCAA × 1-ene, 1971–2025 | FK_Periodo 19 = 1 Jan (date-checked at fetch) |
| INE ECP hogares (ECP), tables 60131/60133 | `.../DATOS_TABLA/60131`, `.../60133` | CCAA/provincia × 1-ene, 2021– | household totals (tamaño detail skipped) |
| INE Censo 2011 vintage por provincia (jaxi p01/01011a) | direct CSV URL in `fetch_censo2011_vintage.py` | provincia × tipo × construction band | dot thousands; '..' suppressed; ±10 additive tolerance |
| INE Censo 2011 tipos de vivienda por municipio (CENSOPV 3456) | `.../DATOS_TABLA/3456` | 2,308 municipios >2.000 hab., 2011 only | principal/secundaria/vacía; 2021 census dropped the split; joined to the 28 valor municipios |
| Diputació de Barcelona municipal housing (DIBA opendata.zip) | media.diba.cat ZIP | 311 municipios: sale €/m² M19 (2013–), rents M23 (2005–), vacant H9a (2018–), tourist H18a (2015–), burdens M11d/M11e (2015–2022) | cp1252, Catalan decimals; province row '08' mapped; muni_key() canonicalizes article order |
| Madrid municipios valor tasado (datos.comunidad.madrid, MIVAU mirror) | direct CSV URL in `fetch_municipios_mad.py` | 28 municipios × año, 2005– | cp1252 → UTF-8; '-' unpublished dropped; third-party mirror, provincial mean cross-checked |
| INE Transmisiones (jaxiT3 6155, registradores) | MIVAU-style direct CSV URL in `fetch_transmisiones.py` | CCAA/provincia × año, 2007– | Total/nueva/usada/libre/protegida; dots are thousands; nueva+usada==total asserted |
| INE Turísticas (Tempus3 39364/46141) | `.../DATOS_TABLA/39364`, `.../46141` | CCAA/provincia × mes, 2020– | December snapshot; duplicate uniprovincial series asserted identical |
| INE Hipotecas CCAA/prov/rates (Tempus3 76316/76317/76315) | `.../DATOS_TABLA/76316` etc. | CCAA/provincia × mes (2003–), rates nacional | Viviendas only; territory↔measure positions swap between tables; importe in thousands of EUR |
| INE ECV renta por hogar (Tempus3 9949) | `servicios.ine.es/wstempus/js/es/DATOS_TABLA/9949` | CCAA × encuesta, 2008– | renta_anyo = encuesta − 1; neta + con-alquiler-imputado (marts use neta); Base 2013 |
| MIVAU Valor Tasado (VDP006_01 CSV) | `cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP006_01.csv` | provincia/CCAA × trimestre, 1995– | `;`-separated, BOM; Régimen Libre/Protegida; quirks: CPRO literal `'null'` on aggregates, aggregate rows keyed by `Provincia='Total CCAA'`, Murcia aggregate with empty CODAUTO (`Murcia, Region de`, unaccented), no provincial rows for 28/30/31/33, no CCAA aggregate for Balears/Cantabria/Rioja (single-province fallback), 844 unpublished quarter-cells, one junk `Total CCAA`/empty row (skipped: empty Valor) |

Unreachable (probed 2026-10-06, do not retry blindly): provincial ECP population
(table 56945) — `DATOS_TABLA` refuses every date window down to a single day
(`restricciones de volumen`), `SERIES_TABLA/56945` returns empty, and
`DATOS_METADATAOPERACION/ECP` filters (115:provincia + 18:Total + 356:Todas,
with and without `p=1`, raw and URL-encoded) all match nothing. Filter-variable
IDs resolved for the record: Provincias=115 (Araba/Álava=2 … Ourense=53),
Sexo=18 (Total=451), Totales de edad=356 (Todas=15668). If INE lifts the block,
re-add 56945 to `scripts/fetch_ecp.py` and extend the provincia mart past 2021. |

Methodology references: INE IPV metodología Base 2025
(`ine.es/daco/daco42/ipv/metodologia2025.pdf`); MIVAU parque metodología
(`mivau.gob.es/.../2025-02_metodologia_estimacion_del_parque_de_viviendas.pdf`;
open-data readme `cdn.mivau.gob.es/.../Readme_VDP002_01.pdf`).

Table IDs were resolved via `OPERACIONES_DISPONIBLES` + `TABLAS_OPERACION`
(see `scripts/ine_discover.py`), not copied from search snippets — two
snippet-suggested IDs (67202/67232) turned out to be unrelated tables.
