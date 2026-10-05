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

Ceuta/Melilla have IPV rows but aggregated stock, so no CCAA-mart row.

## mart_provincia_anual (2001–2021; 51 = 50 provincias + Ceuta y Melilla)

Same stock/population columns as above plus `cpro` (2-digit code,
`51+52` for the Ceuta y Melilla aggregate) and `share_no_principal`.
No price columns — INE publishes no provincial IPV. Plus `pop_source`,
`hogares` (2021 only overlaps padrón window), `viv_por_hogar`.

## dim_territorio

`cpro`, `provincia`, `ccaa` — canonical mapping (MIVAU codes, INE names).
