select anyo,
       mes,
       printf('%d-%02d', anyo, mes) as periodo,
       irav_pct as variacion_anual_pct
from irav_nacional
order by anyo, mes
