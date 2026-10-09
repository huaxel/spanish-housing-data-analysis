---
title: Vacancia
---

# Vivienda vacía (Censo 2021, consumo eléctrico)

El censo 2021 sustituyó el reparto clásico principal/secundaria/vacía por
una clasificación **objetiva basada en el consumo eléctrico**: viviendas
con consumo por debajo del umbral de ocupación. Grano municipal (3,139
municipios nombrados + agregados "Resto"). Total nacional: 3.83M vacías
(14.4%).
[Panorama nacional](/) · [Comparar territorios](/comparar/) · [Renta](/renta/) · [Municipios](/municipios/).

## Mapa de vacancia por municipio

```sql vac_munis
select codigo, municipio, vac_pct
from housing.vacancy_municipal
order by vac_pct desc
```

<AreaMap
  data={vac_munis}
  geoJsonUrl='/geo/municipios.geojson'
  geoId='CODIGOINE'
  areaCol=codigo
  value=vac_pct
  valueFmt=num1
  title="Vivienda vacía por municipio, Censo 2021 (%)"
  height=560
  startingLat=40.2
  startingLong=-3.7
  startingZoom=6
/>

<DataTable data={vac_munis} rows=20>
  <Column id=municipio title="Municipio"/>
  <Column id=vac_pct title="% vacía" fmt="num1"/>
</DataTable>

## Los más vacíos (2021)

```sql top_vac
select municipio, vac_pct
from housing.vacancy_municipal
where vac_pct > 60
order by vac_pct desc
limit 15
```

<BarChart data={top_vac} x=municipio y=vac_pct
  yFmt="num1" title="Municipios con >60% de vivienda vacía"/>

Nota: los municipios pequeños sin suficientes viviendas se agregan en
"Resto de la provincia". La vacancia del interior (Galicia 28.8% de media,
Castilla y León 19.4%) contrasta con Madrid (6.3%) — el overhang que el
análisis del ratio y las rentas documentan. Fuente:
`docs/explorations/ratio_ccaa.md`.
---
*Instantánea de datos: 2026-10-09 · Censo 2021, vacancia por consumo eléctrico · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
