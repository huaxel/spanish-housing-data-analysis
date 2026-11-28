-- Reconstruct crossed resident/headship scenarios directly from publisher JSON.
with people as (
    select d.Fecha as ref_ms, d.Anyo yr, d.Valor pop
    from read_json_auto(?) src, unnest(src.Data) c(d)
    where d.FK_Periodo=22 and src.COD='ECP329968'
), households as (
    select d.Fecha as ref_ms, d.Valor hh
    from read_json_auto(?) src, unnest(src.Data) c(d)
    where src.COD='ECP355533' and d.FK_Periodo=22
), matched as (
    select yr, pop, hh from people join households using (ref_ms)
), crossed as (
    select a.yr first_year, b.yr last_year, a.hh initial, b.hh final,
           b.pop*a.hh/a.pop as more_people_only,
           a.pop*b.hh/b.pop as new_size_only
    from matched a cross join matched b where a.yr<b.yr
)
select first_year, last_year, final-initial as net_household_change,
       ((more_people_only-initial)+(final-new_size_only))/2 as population_component,
       ((new_size_only-initial)+(final-more_people_only))/2 as size_component
from crossed
order by first_year, last_year
