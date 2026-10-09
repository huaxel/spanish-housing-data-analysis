-- Municipal construction-era mix per Andalusian capital (property-weighted).
select m.municipio as ciudad,
       case when b.year_start is null then 'Sin año válido'
            when b.year_start <= 1950 then 'Hasta 1950'
            when b.year_start <= 1970 then '1951–1970'
            when b.year_start <= 1990 then '1971–1990'
            when b.year_start <= 2010 then '1991–2010'
            else '2011 en adelante' end as era,
       sum(b.dwelling_properties) as inmuebles
from buildings b join municipios m on b.ine_municipality = m.ine_municipality
where b.dwelling_properties > 0
group by ciudad, era
order by ciudad, era
