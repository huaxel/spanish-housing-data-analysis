-- Canonical province labels; keep Ceuta and Melilla separate for municipal codes.
select cpro, provincia
from dim_territorio
where regexp_full_match(cpro, '[0-9]{2}') and cpro not in ('51', '52')
union all select '51', 'Ceuta'
union all select '52', 'Melilla'
