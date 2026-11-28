-- Run from the repository root. Keep the tax universe separate from total stock.
with stock as (
    select lpad(COD_PROV, 2, '0') cpro, NOM_PROV provincia, ANIO::int anyo,
           sum(NUM_VIVIENDAS::bigint) filter (where CATEGORIA_PARQUE='Totales') total,
           sum(NUM_VIVIENDAS::bigint) filter (where CATEGORIA_PARQUE='Principal') principal,
           sum(NUM_VIVIENDAS::bigint) filter (where CATEGORIA_PARQUE='No_Principal') nonprincipal
    from read_csv('data/raw/parque_viviendas.csv', delim=';', all_varchar=true)
    where lpad(COD_PROV, 2, '0') in ('03','08','28','46') and ANIO in ('2023','2024','2025')
    group by 1,2,3
), tax_use as (
    select cpro, anyo, n_disposicion
    from read_parquet('data/raw/parquet/aeat_viviendas_uso.parquet')
    where cpro in ('03','08','28','46') and anyo in (2023,2024)
      and grano in ('provincia','ccaa_uniprovincial')
)
select b.cpro, b.provincia, b.anyo,
       b.total-a.total total_change, b.principal-a.principal principal_change,
       b.nonprincipal-a.nonprincipal nonprincipal_change,
       t1.n_disposicion-t0.n_disposicion tax_at_disposal_change
from stock a join stock b on a.cpro=b.cpro and a.anyo+1=b.anyo
left join tax_use t0 on t0.cpro=a.cpro and t0.anyo=a.anyo
left join tax_use t1 on t1.cpro=b.cpro and t1.anyo=b.anyo
order by b.anyo, b.cpro
