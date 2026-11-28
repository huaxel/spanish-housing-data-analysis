-- Independent comparison based on publisher labels and exact timestamps.
with household as (
    select split_part(Nombre, '. ', 1) territory, d.Fecha ref_ms, d.Valor::bigint hh
    from read_json_auto(?) src, unnest(src.Data) c(d)
    where split_part(Nombre, '. ', 2)='Total' and d.FK_Periodo=22
      and not starts_with(Nombre, 'Total Nacional.')
), observations as (
    select territory, d.Anyo yr, hh, d.Valor::bigint pop
    from read_json_auto(?) src, unnest(src.Data) c(d)
    join household on d.Fecha=ref_ms and split_part(Nombre, '. ', 1)=territory
    where trim(Nombre) like '%. Total. Todas las edades. Total. Población en viviendas familiares. Número.'
)
select a.yr as from_year, b.yr as to_year, a.territory,
       b.hh-a.hh as hh_change, b.pop-a.pop as people_change,
       a.pop*b.hh>b.pop*a.hh as people_per_household_fell
from observations a join observations b on a.territory=b.territory and a.yr<b.yr
order by from_year, to_year, territory
