-- Include census municipalities with no published rental market measure.
-- Latest SERPAVI display names are labels, never join keys or a boundary crosswalk.
with nombres as (
    select codigo, municipio, provincia,
           row_number() over (
               partition by codigo order by anyo desc, municipio, provincia
           ) as posicion
    from (select distinct codigo, municipio, provincia, anyo from serpavi_municipal)
), codigos as (
    select cpro || cmun as codigo from censo2021_secciones
    union
    select codigo from serpavi_municipal
)
select c.codigo,
       coalesce(n.municipio, 'Municipio sin nombre en SERPAVI') as municipio,
       n.provincia,
       coalesce(n.municipio, 'Municipio sin nombre en SERPAVI') || ' · ' ||
       coalesce(n.provincia || ' · ', '') || c.codigo as etiqueta
from codigos c
left join nombres n on n.codigo = c.codigo and n.posicion = 1
where regexp_full_match(c.codigo, '[0-9]{5}') and right(c.codigo, 3) != '999'
order by etiqueta
