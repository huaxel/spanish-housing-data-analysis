-- Province municipal totals: records and declared properties per municipality.
select m.municipio as municipio,
       count(*) as registros,
       sum(b.dwelling_properties) as inmuebles
from buildings b join municipios m on b.ine_municipality = m.ine_municipality
where b.dwelling_properties > 0
group by municipio
order by inmuebles desc
