-- SERPAVI rents (MIVAU, tax-deposit based): median EUR/m2 by municipio.
-- 2011-2024; populated cells only (2,555 municipios at 2024).
select
    provincia,
    municipio,
    anyo,
    valor as rent_eur_m2
from serpavi_municipal
where medida = 'ALQM2_LV_M_VC'
order by anyo, municipio