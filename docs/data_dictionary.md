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
