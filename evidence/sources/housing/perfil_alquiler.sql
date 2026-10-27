-- Collective-housing SERPAVI measures only, code x tax year.
-- Keep all published municipal keys, even when these measures are missing.
-- Duplicate selected measures are withheld rather than silently averaged.
select codigo, anyo,
       case when count(*) filter (where medida = 'ALQM2_LV_M_VC') = 1
            then max(valor) filter (where medida = 'ALQM2_LV_M_VC') end as eur_m2_mes,
       case when count(*) filter (where medida = 'BI_ALVHEPCO_TVC') = 1
            then max(valor) filter (where medida = 'BI_ALVHEPCO_TVC') end as contratos
from serpavi_municipal
group by codigo, anyo
