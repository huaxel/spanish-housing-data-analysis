-- Independent oracle: verify cumulative windows and 2025 using the deficit
-- sidecar, and earlier annual windows using the original publisher CSV.
with residents as (
    select case when split_part(Nombre, '. ', 1) in ('Ceuta','Melilla') then 'Ceuta y Melilla'
                else split_part(Nombre, '. ', 1) end place,
           d.Anyo yr, sum(d.Valor::bigint) residents
    from read_json_auto($people) t, unnest(t.Data) c(d)
    where d.FK_Periodo=19 and not starts_with(Nombre, 'Total Nacional.')
      and trim(Nombre) like '%. Total. Todas las edades. Total. Población en viviendas familiares. Número.'
    group by place, yr
), initial_households as (
    select case when split_part(Nombre, '. ', 1) in ('Ceuta','Melilla') then 'Ceuta y Melilla'
                else split_part(Nombre, '. ', 1) end place,
           d.Anyo yr, sum(d.Valor::bigint) households
    from read_json_auto($households) t, unnest(t.Data) c(d)
    where d.FK_Periodo=19 and split_part(Nombre, '. ', 2)='Total'
    group by place, yr
), stocks as (
    select coalesce(NOM_PROV, 'Ceuta y Melilla') place,
           coalesce(lpad(COD_PROV, 2, '0'), '51+52') cpro,
           ANIO::int yr, NUM_VIVIENDAS::bigint homes
    from read_csv($stock_csv, delim=';', all_varchar=true)
    where CATEGORIA_PARQUE='Totales' and ANIO::int between 2020 and 2024
), windows as (
    select window_key, provincia, cpro, household_start_year, household_end_year,
           household_change, stock_change, gap_stock
    from comparisons
    union all
    select '2025', b.provincia, b.cpro, a.household_end_year, b.household_end_year,
           b.household_change-a.household_change, b.stock_change-a.stock_change,
           b.gap_stock-a.gap_stock
    from comparisons a join comparisons b using (cpro)
    where a.window_key='2021-2024' and b.window_key='2021-2025'
    union all
    select b.yr::varchar, b.place, b.cpro, b.yr, b.yr+1,
           h1.households-h0.households, b.homes-a.homes,
           (h1.households-h0.households)-(b.homes-a.homes)
    from stocks a join stocks b on a.cpro=b.cpro and a.yr+1=b.yr
    join initial_households h0 on h0.place=b.place and h0.yr=b.yr
    join initial_households h1 on h1.place=b.place and h1.yr=b.yr+1
)
select window_key, provincia, cpro, p1.residents-p0.residents people_change,
       household_change, stock_change, gap_stock,
       p1.residents*h.households/p0.residents-h.households-stock_change fixed_gap,
       sum(gap_stock) over w as national_gap,
       sum(p1.residents*h.households/p0.residents-h.households-stock_change) over w as local_baseline,
       sum(p1.residents-p0.residents) over w * sum(h.households) over w
           / sum(p0.residents) over w - sum(stock_change) over w as national_baseline
from windows c
join residents p0 on p0.place=c.provincia and p0.yr=c.household_start_year
join residents p1 on p1.place=c.provincia and p1.yr=c.household_end_year
join initial_households h on h.place=c.provincia and h.yr=c.household_start_year
window w as (partition by window_key)
order by window_key, cpro
