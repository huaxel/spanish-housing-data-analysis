-- SERPAVI declared rental contracts (MIVAU, income-tax exploitation): number of
-- contracts in force per municipio and tax year, 2011-2024. Collective and
-- single-family housing are separate published measures; populated cells only
-- (blank cells are statistical suppression).
select
    codigo,
    provincia,
    municipio,
    anyo,
    cast(max(case when medida = 'BI_ALVHEPCO_TVC' then valor end) as bigint)
        as contratos_colectiva,
    cast(max(case when medida = 'BI_ALVHEPCO_TVU' then valor end) as bigint)
        as contratos_unifamiliar
from serpavi_municipal
where medida in ('BI_ALVHEPCO_TVC', 'BI_ALVHEPCO_TVU')
group by 1, 2, 3, 4
order by anyo, municipio
