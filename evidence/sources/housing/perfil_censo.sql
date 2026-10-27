-- Census 2021 context, aggregated only within the original municipal codes.
-- Never publish partial dwelling/household sums when any section is withheld.
select cpro || cmun as codigo,
       2021 as anyo,
       count(*) as secciones,
       count(*) filter (where suprimido) as secciones_suprimidas,
       case when count(t1_1) = count(*) then sum(t1_1) end as poblacion,
       case when count(t18_1) = count(*) and not bool_or(suprimido)
            then sum(t18_1) end as viviendas,
       case when count(t21_1) = count(*) and not bool_or(suprimido)
            then sum(t21_1) end as hogares
from censo2021_secciones
group by cpro, cmun
