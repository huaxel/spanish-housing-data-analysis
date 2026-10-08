# Data dictionary

## mart_ccaa_anual (2007–2025; 18 = 17 CCAA + Nacional)

| Column | Meaning | Origin |
| --- | --- | --- |
| ccaa | INE CCAA name (or `Nacional`) | INE / aggregation |
| anyo | reference year | all sources |
| viviendas_total / _principales / _no_principales | dwelling counts | MIVAU parque, summed over provinces |
| poblacion | inhabitants (1-Jan) | Padrón ≤2021, ECP ≥2022 (CCAA rows); Nacional: padrón sum / ECP direct |
| pop_source | `padron` or `ecp` — never compare across the seam without the overlap note | methods §1 |
| hogares | households in family dwellings (2021+ ECP; 2014–20 ECH; 2011 exact census; NULL otherwise) | ECP / ECH / Censo 2011 tenencia |
| viv_por_hogar | dwellings per household (2021+, 2011) | derived |
| hogares_2001_proxy / viv_por_hogar_2001_proxy | 2001 principales-as-households (provincia mart only; ±2.1% tolerance) | derived, flagged |
| viv_por_1000_hab | dwellings per 1,000 inhabitants | derived |
| ipv_general / ipv_nueva / ipv_segunda_mano | quality-adjusted price index, base 2025 | INE IPV rows (never averaged) |
| eur_m2_libre | mean appraised €/m², vivienda libre (annual mean of published quarters) | MIVAU valor tasado |
| pob_20_34 / share_20_34 | residents aged 20–34 / share of población (1-Jan) | ECP single-year detail, parsed bands |
| hog_1persona / share_1persona | 1-person households / share of hogares (2021–; sizes additive-checked) | ECP tamaño detail |
| hip_viv_num / hip_ticket_miles | mortgages on dwellings / mean capital (thousands EUR; NULL before 2003) | INE HPT (complete years only) |
| trx_total / share_nueva | registered transactions / new-build share (NULL before 2007) | Transmisiones (nueva+usada==total asserted) |
| viv_turisticas / share_turistica_no_princ | registered tourist dwellings / share of non-primary stock (December snapshot; NULL before 2020) | INE VTE |
| renta_hogar_neta | mean net household income, income year (NULL for 2025: ECV lags) | INE ECV |
| afford_90m2_years | years of net income for 90 m² at Libre €/m² | derived (AFFORD_M2=90) |
| eur_m2_n_trim | quarters averaged (completeness flag — partial years visible) | derived |
| vt_source | `ccaa_direct` / `prov_direct` / `ccaa_fill` (28/30/31/33) / `prov_fill` (Balears/Cantabria/Rioja CCAA) | derived |

Ceuta/Melilla have IPV rows but aggregated stock, so no CCAA-mart row.

## mart_provincia_anual (2001–2025; 51 = 50 provincias + Ceuta y Melilla)

Same stock/population columns as above plus `cpro` (2-digit code,
`51+52` for the Ceuta y Melilla aggregate) and `share_no_principal`.
No price columns — INE publishes no provincial IPV. Plus `pop_source`
(padron ≤2021 / censo_anual ≥2022 — Censo Anual de Población static CSV
68521, verified 2025 national = ECP exact),
`hogares` (2021+ ECP, 2014–20 ECH, 2011 exact census), `viv_por_hogar`, plus `hogares_2001_proxy` /
`viv_por_hogar_2001_proxy` (principales proxy, ±2.1% validated tolerance).

## censo2011_bcn

Same 2011 split for Barcelona demarcation (188 municipios with DIBA
presence; 122 small ones under the census threshold). Barcelona city 2011:
88,259 vacant (10.9%) + 38,769 secundaria.

## valor_municipal_madrid

`codigo` (INE 4-digit), `municipio`, `anyo`, `eur_m2` — Libre, Madrid
municipios with published appraisals (28, capital complete 2005–2025).

## censo2011_val

Same split for 9 Valencia focus municipios (coast + capitals) — the
second-home coast (Torrevieja 51%) vs vacant towns (Dénia 31%).

## censo2011_tenencia

`ccaa`, `provincia`, `tamano`, `tenencia`, `hogares` — 2011 household size
× tenure (pagada/hipoteca/herencia/alquilada/cedida/otra). Mortgaged anchor
5,940,928.

## censo2011_vintage

`ccaa`, `provincia`, `tipo` (principal/secundaria/vacia), `vintage`
construction band, `viviendas` — 2011 only; boom fringe directly observable.

## censo2011_mad

`municipio`, `tipo` (Total/familiar/principal/no principal/secundaria/
vacía/colectiva), `viviendas_2011` — 2011 split for the 28 valor municipios.

## muni_bcn

`municipio`, `anyo`, `poblacion`, `sale_eur_m2` (M19, 2013–),
`rent_month` (M23, 2005–), `vacant_reg` (H9a, 2018–), `tourist` (H18a,
2015–), `rent_burden`/`mortgage_burden` % (M11d/M11e, 2015–2022), `starts`/
`completions` dwellings (M12/M13, 2012–2024) — 310 municipios incl.
Barcelona city, joined to Padrón via `muni_key()`.

## muni_madrid

`municipio`, `anyo`, `eur_m2`, `poblacion` — valor joined to Padrón
municipal (DPOP 2881; 28 municipios, 2005–2025; explicit name aliases).
No municipal stock: per-capita housing still unavailable at this grain.

## muni_vlc

`municipio`, `anyo`, `poblacion` (DPOP 2903; 266 municipios, 1996–2025),
`rent_eur_m2` (SERPAVI `ALQM2_LV_M_VC` median, 2011–2024),
`dwellings_2011`/`vacant_2011` (Censo 2011; on the 2011 row only, never
repeated). No sale prices — no reachable municipal source. Censo
homonyms (`l'Alcúdia`, `Oliva`) carry no vacancy. Joined via `muni_key()`.

## muni_sev

Same design as `muni_vlc` for Sevilla (DPOP 2895; 106 municipios,
1996–2025): `municipio`, `anyo`, `poblacion`, `rent_eur_m2` (SERPAVI
2011–2024), `dwellings_2011`/`vacant_2011` (2011 row only). City is
'Sevilla (ciudad)'. No censo homonyms in the Sevilla key set.

## muni_all

National merge of all 52 DPOP municipal tables: `municipio`, `provincia`
(DPOP table name), `cpro` (via `mart_provincia_anual` names + 51/52 for
Ceuta/Melilla), `anyo` (1996–2025), `poblacion`, `rent_eur_m2` (SERPAVI
2011–2024; Granada Pinar/Píñar twins keep population only), 2011 vacancy
(2011 rows only; 3 national censo homonym keys + 52 cross-province
homonym keys skipped). 235,376 rows, 8,136 municipios.

## barrios_madrid

`distrito`, `barrio`, `anyo` (2007–2025), `tipo`
(Total/Nuevas/Usadas), `eur_m2` (precio medio declarado registral).
Straight mirror of the bank export; suppressed cells null; literal 0.0
passed through (Aeropuerto 2025 degenerate cell).

## barrios_sevilla

SIM/IPRA barrio rental references: `idg`, `id_distrito`, `distrito`,
`id_barrio`, `barrio`, `anyo` (2016–2022), `ipra_eur_m2` (monthly €/m²
built). 756 barrio-year rows; 37 missing cells. Annual labels use rolling
three-year contract windows; the 2022 update uses 2019–2021 contracts.

## barrios_sevilla_compra

SIM cross-sectional purchase indicators: same barrio keys,
`compra_colectiva_eur_m2`, `compra_unifamiliar_eur_m2`. 108 barrios; 31
unifamiliar values missing. The service supplies no reference period or
calculation method; do not treat these as an annual transaction series.

## sevilla_oferta_zona

Ayuntamiento yearbook 2025 table 7.3.9: `provider` (Fotocasa/Idealista),
`zona` (publisher's own geography), `anyo` (2024), `mes` (1–12),
`precio_oferta_eur_m2`. 336 rows; 11 Fotocasa districts and 17 Idealista
zones retained separately. These are monthly asking prices, not transactions.

## Provincial launches and foreclosures

`desahucios_provincia` (`provincia` mart names, `anyo`, `trimestre`,
`lanz_total`, `lanz_hipoteca`, `lanz_lau`, `lanz_otros`, `ej_hipotecarias`):
3,850 rows = 50 provinces × 77 quarters. Launch causes are additive to the
total except one upstream off-by-one cell pinned in verify. No Ceuta/Melilla
rows; national TOTAL skipped. Launches since 2013Q1, filings since 2007Q1.

## SERPAVI district rents

`serpavi_distritos` (`cpro`, `provincia`, `codigo` 5-digit municipio,
`municipio`, `distrito` 7-digit CUDIS, `anyo` 2011–2024, `medida` same 20 as
municipal, `valor`): 1,099,206 populated cells across 9,680 districts in
7,332 municipios. District names are unpublished (codes only); secciones
censales skipped (census-vintage instability).

## Barcelona INCASÒL rent tables

`barrios_bcn_lloguer_anual` (`ambit` ciutat/districte/barri, `codi`
BCN/D01–D10/B01–B73, `nom`, `anyo` 2000–2025, `contractes`, `lloguer_mitja`
(€/month), `lloguer_m2` (€/m²/month), `superficie` (m²)): 2,184 rows = 84
areas × 26 years. Barri cells before 2013 are null; city + districts are
complete. `barrios_bcn_lloguer_trimestral` adds `trimestre` (1–4): 4,984
rows; barris from 2014, 2026 holds published quarters only. Suppressed
(<6 contracts) and unpublished cells are null. Filed-contract records from
INCASÒL deposits, not asking prices.

## Barcelona registered sales

`barrios_bcn_compraventes` (`ambit`, `codi`, `nom`, `anyo`, `trimestre`):
`trx_nou_lliure`, `trx_nou_protegit`, `trx_usat`, `trx_total`; `sup_*` mean
areas; `preu_nou/usat/total` mean prices (thousands of €); `eur_m2_*` mean
prices per built m²; 2026-only `eur_m2_{nou,usat}_{max,min}`. 2,520 rows
(84 areas × 30 quarters: 2018–2019 + 2021–2025 full, 2026 partial). Zero
prices/areas are stored null (suppressed below 3 contracts); transaction
counts keep real zeros. City total includes non-geolocated records.

## Sevilla SIM context tables

`sevilla_sim_poblacion_hogares` is long-form barrio context keyed by
`idg`, `id_distrito`, `distrito`, `id_barrio`, `barrio`, and `anyo`
(2015–2021), with `poblacion` and `hogares` (756 rows; 108 barrios × 7
years). Both measures have explicit year fields.

`sevilla_sim_vivienda` is a one-row-per-barrio (108 rows) SIM snapshot:
family dwellings by collective/unifamiliar type and shares; mean age,
construction-quality score and built area by type; estimated rehabilitation
need/count and share; and principal, secondary and uninhabited dwelling
counts and shares. These component layers do not specify a reference year;
nulls are preserved.

`sevilla_sim_turismo` has one row per barrio (108 rows), active tourist-purpose
dwellings and SIM pressure percentages at 2008, 2021-02, 2021-08 and 2022-02,
plus registered dwelling/place totals without an explicit date. Pressure cells
with no source value remain null. These are snapshot observations, not an
annual series. The SIM accessibility layer is district-grain only and is not
included in the barrio mart.

## valor_tasado_anual

Full annual means (all `terr_key`: `P<cpro>` / `C<flat-ccaa>` / `NACIONAL` /
`C51+52`, both regímenes): `terr_key`, `anyo`, `regimen`, `eur_m2`, `n_trim`.

## censo2021_viviendas

2021 census dwellings by provincia × tipo × construction band: `cpro`,
`provincia`, `tipo` (Total/principal/no principal), `banda`, `viviendas`.
Anchor uses Total × Total only (26,623,708); tipo split unchecked (definitional).

## serpavi_municipal

SERPAVI (MIVAU) municipal rents from rental-deposit tax data, long melt:
`cpro`, `provincia`, `codigo` (5-digit INE), `municipio`, `anyo`
(2011–2024), `medida` (20: ALQM2_LV_M/25/75_VC/VU €/m²/month,
ALQTBID12_* €/month, SLVM2_* surface m², BI_ALVHEPCO_* contract counts),
`valor`. Populated cells only (716,889; 7,331 municipios; 2,555 with 2024
median rent). Validated vs DIBA: Pearson 0.825 (202 Barcelona municipios).

## censo2021_intensidad

2021 census dwellings by electricity-consumption intensity, municipal
grain: `codigo` (5-digit INE, 999-suffix = Resto aggregate), `municipio`,
`provincia_cod`, `medida` (18 measures: Viviendas totales, Viviendas
vacías, Mediana consumo anual, 15 consumption bands), `valor`. Objective
vacancy (below-threshold consumption) — replaces the classic
principal/secundaria/vacía split. 3,139 named municipios + 46 Resto.
Anchors: total 26,623,708, vacías 3,828,307.

## migra_anual

Foreign/Spanish immigration flows by provincia × year (`provincia`,
`anyo`, `nacionalidad` Total/Española/Extranjero, `flujo`), plus Nacional
and Ceuta-y-Melilla aggregates. Annual (FK_Periodo 28), 2008–2021.

## padron_extranjeros

Annual foreign resident stocks (`cpro`, `provincia`, `anyo`,
`extranjeros`), 1998–2022. Bartik shares base; surge half queued.

## padron_extranjeros_origen

Full origin × sex detail (`nacionalidad`, `cpro`, `provincia`, `sexo`,
`anyo`, `personas`): 137 nacionalidades (18 rollups duplicate leaves),
1998–2022. Origin-level shares base for the shift-share design.

## dim_territorio

`cpro`, `provincia`, `ccaa` — canonical mapping (MIVAU codes, INE names).

## ipc_anual

INE general CPI (base 2021), CCAA + Nacional (+ Ceuta/Melilla separately):
`territorio`, `anyo`, `ipc` (annual mean), `n_months` (completeness flag).
Deflator for real-terms levels — join on territory/year, never average
across territories.
