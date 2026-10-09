-- Province construction-era mix: capital vs rest (property-weighted).
select case when b.ine_municipality = '41091' then 'Sevilla capital' else 'Resto provincia' end as ambito,
       case when b.year_start is null then 'Sin año válido'
            when b.year_start <= 1950 then 'Hasta 1950'
            when b.year_start <= 1970 then '1951–1970'
            when b.year_start <= 1990 then '1971–1990'
            when b.year_start <= 2010 then '1991–2010'
            else '2011 en adelante' end as era,
       sum(b.dwelling_properties) as inmuebles
from buildings b
where b.dwelling_properties > 0
group by ambito, era
order by ambito, era
