---
title: Vacancia
---

# Vivienda vacía (Censo 2021, consumo eléctrico)

El Censo 2021 estimó la vivienda vacía con un indicador basado en el
consumo eléctrico: viviendas por debajo del umbral de ocupación. Es una
clasificación operacional, no una inspección de habitabilidad ni de oferta
actual. Grano municipal (3,139 municipios nombrados + agregados "Resto").
Total nacional publicado: 3.83M (14.4%).
[Panorama nacional](/) · [Comparar territorios](/comparar/) · [Renta](/renta/) · [Municipios](/municipios/).

## Mapa de vacancia por municipio

```sql vac_munis
select codigo, municipio, vac_pct, vac_pct as "Vacía (%)"
from housing.vacancy_municipal
order by vac_pct desc
```

<AreaMap
  data={vac_munis}
  geoJsonUrl='/geo/municipios.geojson'
  geoId='CODIGOINE'
  areaCol=codigo
  value={'Vacía (%)'}
  valueFmt=num1
  basemap={'https://tile.openstreetmap.org/{z}/{x}/{y}.png'}
  attribution='© OpenStreetMap'
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

## Mayor proporción clasificada como vacía (2021)

```sql top_vac
select municipio, vac_pct
from housing.vacancy_municipal
where vac_pct > 60
order by vac_pct desc
limit 15
```

<BarChart data={top_vac} x=municipio y=vac_pct swapXY
  yFmt="num1" title="Municipios con >60% clasificada como vacía"/>

Nota: los municipios pequeños sin suficientes viviendas se agregan en
"Resto de la provincia". La proporción clasificada como vacía es alta en
Galicia (28.8% de media) y Castilla y León (19.4%), frente a Madrid (6.3%).
Es evidencia de baja ocupación según este indicador, no una medida de
viviendas habitables, disponibles o movilizables. Interprétala junto a los
límites del [stock y acceso](/acceso/), no como oferta inmediata. Fuente:
`docs/explorations/ratio_ccaa.md`.
---
*Instantánea de datos: 2026-10-09 · Censo 2021, vacancia por consumo eléctrico · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
