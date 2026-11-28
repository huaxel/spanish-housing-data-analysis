-- Separate source oracle: pivot published October cells, then use an exact
-- join on prior year so a missing October cannot silently change the interval.
with counts as (
    select split_part(Nombre, '. ', 1) territory, d.Anyo yr,
           sum(d.Valor::bigint) filter (where split_part(Nombre, '. ', 2)='Total') total,
           sum(d.Valor::bigint) filter (where split_part(Nombre, '. ', 2) in ('1','2')) small
    from read_json_auto(?) t, unnest(t.Data) c(d)
    where d.FK_Periodo=22 and split_part(Nombre, '. ', 1)<>'Total Nacional'
    group by territory, yr
), changes as (
    select cur.yr, cur.territory, cur.total-prev.total as net_change,
           cur.small-prev.small as small_change
    from counts cur join counts prev on cur.territory=prev.territory and cur.yr=prev.yr+1
)
select yr, territory, net_change, small_change
from changes
order by yr, net_change desc, territory
