-- Censo 2021 vacancy by electricity consumption (INE 59531).
-- Objective vacancy: dwellings with consumption below the occupancy
-- threshold. 3,139 named municipios + 46 Resto aggregates.
select
    codigo,
    municipio,
    round(100.0 * vac / tot, 2) as vac_pct
from (
    select
        codigo,
        max(municipio) as municipio,
        sum(case when medida = 'Viviendas totales' then valor end) as tot,
        sum(case when medida = 'Viviendas vacías' then valor end) as vac
    from censo2021_intensidad
    group by codigo
)
where tot is not null and vac is not null
order by vac_pct desc