# Data dictionary

## mart_ccaa_anual (2007–2025; 18 = 17 CCAA + Nacional)

| Column | Meaning | Origin |
| --- | --- | --- |
| ccaa | INE CCAA name (or `Nacional`) | INE / aggregation |
| anyo | reference year | all sources |
| viviendas_total / _principales / _no_principales | dwelling counts | MIVAU parque, summed over provinces |
| poblacion | inhabitants (1-Jan) | Padrón ≤2021, ECP ≥2022 (CCAA rows); Nacional: padrón sum / ECP direct |
| pop_source | `padron` or `ecp` — never compare across the seam without the overlap note | methods §1 |
| hogares | households in family dwellings (NULL before 2021) | ECP (CCAA direct; Nacional direct) |
| viv_por_hogar | dwellings per household (NULL before 2021) | derived |
| viv_por_1000_hab | dwellings per 1,000 inhabitants | derived |
| ipv_general / ipv_nueva / ipv_segunda_mano | quality-adjusted price index, base 2025 | INE IPV rows (never averaged) |
| eur_m2_libre | mean appraised €/m², vivienda libre (annual mean of published quarters) | MIVAU valor tasado |
| pob_20_34 / share_20_34 | residents aged 20–34 / share of población (1-Jan) | ECP single-year detail, parsed bands |
| hip_viv_num / hip_ticket_miles | mortgages on dwellings / mean capital (thousands EUR; NULL before 2003) | INE HPT (complete years only) |
| renta_hogar_neta | mean net household income, income year (NULL for 2025: ECV lags) | INE ECV |
| afford_90m2_years | years of net income for 90 m² at Libre €/m² | derived (AFFORD_M2=90) |
| eur_m2_n_trim | quarters averaged (completeness flag — partial years visible) | derived |
| vt_source | `ccaa_direct` / `prov_direct` / `ccaa_fill` (28/30/31/33) / `prov_fill` (Balears/Cantabria/Rioja CCAA) | derived |

Ceuta/Melilla have IPV rows but aggregated stock, so no CCAA-mart row.

## mart_provincia_anual (2001–2021; 51 = 50 provincias + Ceuta y Melilla)

Same stock/population columns as above plus `cpro` (2-digit code,
`51+52` for the Ceuta y Melilla aggregate) and `share_no_principal`.
No price columns — INE publishes no provincial IPV. Plus `pop_source`,
`hogares` (2021 only overlaps padrón window), `viv_por_hogar`.

## valor_tasado_anual

Full annual means (all `terr_key`: `P<cpro>` / `C<flat-ccaa>` / `NACIONAL` /
`C51+52`, both regímenes): `terr_key`, `anyo`, `regimen`, `eur_m2`, `n_trim`.

## dim_territorio

`cpro`, `provincia`, `ccaa` — canonical mapping (MIVAU codes, INE names).
