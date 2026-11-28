-- Alternative calculation: average the two paths through crossed endpoint
-- weights and composition, rather than multiplying the midpoint by a change.
with counts as (
    select split_part(Nombre, '. ', 1) territory, d.Anyo yr,
           sum(d.Valor) filter (where split_part(Nombre, '. ', 2)='Total') total,
           sum(d.Valor) filter (where split_part(Nombre, '. ', 2) in ('1','2')) small
    from read_json_auto(?) t, unnest(t.Data) c(d)
    where d.FK_Periodo=22 and split_part(Nombre, '. ', 1)<>'Total Nacional'
    group by territory, yr
), shares as (
    select *, small/total s, total/sum(total) over (partition by yr) w
    from counts
), scenarios as (
    select before.yr first_year, after.yr last_year, sum(before.w*before.s) base,
           sum(after.w*after.s) observed, sum(before.w*after.s) new_shares,
           sum(after.w*before.s) new_weights,
           count(*) filter (where after.small*before.total>before.small*after.total) rising
    from shares before join shares after on before.territory=after.territory and before.yr<after.yr
    group by before.yr, after.yr
)
select first_year, last_year, 100*base, 100*observed, 100*(observed-base),
       50*((new_shares-base)+(observed-new_weights)) within_pp,
       50*((new_weights-base)+(observed-new_shares)) reweighting_pp, rising
from scenarios
order by first_year, last_year
