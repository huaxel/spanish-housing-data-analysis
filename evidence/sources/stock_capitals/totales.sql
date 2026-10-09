-- Municipal totals per capital: records, declared properties, matched share.
select m.municipio as ciudad,
       count(*) as registros,
       sum(b.dwelling_properties) as inmuebles,
       sum(case when b.barrio_id is not null then 1 else 0 end) as registros_asignados
from buildings b join municipios m on b.ine_municipality = m.ine_municipality
where b.dwelling_properties > 0
group by ciudad
order by inmuebles desc
