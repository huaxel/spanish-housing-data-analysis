---
title: Alquiler e ingresos
---

# Cuánta renta municipal se va en firmar un contrato

La mediana de alquiler de firma cuesta cerca del 14% de la renta neta
media del municipio — una cifra plana desde 2015 que **subestima lo que
ocurre en las grandes ciudades**, donde el contrato se come una quinta
parte y subiendo. Esta página presenta el proxy SERPAVI/ADRH aceptado el
2026-10-09: un indicador de mercado de firma, **no** una tasa de
sobrecarga.
[Panorama nacional](/) · [Acceso](/acceso/) · [Renta (€/m²)](/renta/) · [Municipios](/municipios/).

## El indicador, en tres cifras

```sql mediana_extremos
with m as (
  select anyo, count(*) n, median(ratio_pct) med
  from access.rent_income
  where ratio_pct is not null
  group by anyo
), s as (
  select round(100.0 * count(*) filter (where anyo = 2023 and ratio_pct >= 20)
        / count(*) filter (where anyo = 2023), 1) as share_20_2023
  from access.rent_income
  where ratio_pct is not null
)
select
  max(med) filter (where anyo = 2015) as mediana_2015,
  max(med) filter (where anyo = 2023) as mediana_2023,
  max(n) filter (where anyo = 2023) as municipios_2023,
  max(share_20_2023) as share_20_2023
from m, s
```

En 2023 el municipio mediano con datos publica un contrato mediano de
<Value data={mediana_extremos} column=mediana_2023 fmt="num1"/>%
de la renta neta media de sus hogares; en 2015 era
<Value data={mediana_extremos} column=mediana_2015 fmt="num1"/>%,
y el <Value data={mediana_extremos} column=share_20_2023 fmt="num1"/>% de
municipios supera ya el 20%. La cobertura es
<Value data={mediana_extremos} column=municipios_2023 fmt="num0"/> municipios
(los que SERPAVI publica; los pequeños están suprimidos).

## La mediana no se mueve; las grandes ciudades sí

```sql serie_proxy
select anyo, 'Mediana municipal' as grupo, round(median(ratio_pct), 1) as ratio_pct
from access.rent_income
where ratio_pct is not null
group by anyo
union all
select anyo, municipio as grupo, round(ratio_pct, 1) as ratio_pct
from access.rent_income
where codigo in ('28079', '08019', '46250', '41091', '29067')
  and ratio_pct is not null
order by anyo
```

<LineChart data={serie_proxy} x=anyo y=ratio_pct series=grupo
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  title="Alquiler de firma como % de la renta neta media anual del hogar"/>

El alquiler mediano de firma y la renta media municipal crecieron al
mismo ritmo entre 2015 y 2023, así que la mediana del ratio es plana.
Pero las cinco grandes ciudades parten por encima y todas ganan
porcentaje: Barcelona pasa de ~20,7% a ~22,0% y Valencia de ~16,0% a
~18,7%. La renta media creció ~30% en esas ciudades; el contrato mediano
creció más.

## Dónde pesa más el contrato (2023)

```sql top_proxy
select municipio, cpro, contratos, round(alquiler_med, 0) as alquiler_med,
       round(renta_neta_hogar, 0) as renta_neta_hogar, ratio_pct
from access.rent_income
where anyo = 2023 and contratos >= 50 and ratio_pct is not null
order by ratio_pct desc
limit 15
```

<BarChart data={top_proxy} x=municipio y=ratio_pct swapXY
  yFmt="num1" title="Ratio alquiler/renta 2023 (≥50 contratos)"/>

<DataTable data={top_proxy} rows=15>
  <Column id=municipio title="Municipio"/>
  <Column id=contratos title="Contratos (VC)" fmt="num0"/>
  <Column id=alquiler_med title="Alquiler mediano (€/mes)" fmt="num0"/>
  <Column id=renta_neta_hogar title="Renta neta media (€/año)" fmt="num0"/>
  <Column id=ratio_pct title="Ratio (%)" fmt="num1"/>
</DataTable>

La costa turística malagueña encabeza con ratio en torno a 22–32%:
mercados de firma caros sobre rentas medias locales más bajas.

## El mapa del esfuerzo de firma: alquiler frente a renta

```sql scatter_proxy
select municipio, round(renta_neta_hogar / 12.0, 0) as renta_mensual,
       round(alquiler_med, 0) as alquiler_med, contratos, ratio_pct
from access.rent_income
where anyo = 2023 and contratos >= 50 and ratio_pct is not null
```

<ScatterPlot data={scatter_proxy} x=renta_mensual y=alquiler_med
  xFmt="num0" yFmt="num0" pointSize=6 tooltipTitle=municipio
  xAxisTitle="Renta neta media mensual del hogar (€)"
  yAxisTitle="Alquiler mediano de firma (€/mes)"
  title="Municipios con al menos 50 contratos, 2023"
  echartsOptions={{
    series: [{
      markLine: {
        silent: true,
        symbol: 'none',
        animation: false,
        lineStyle: { type: 'dashed', color: '#94a3b8', width: 1 },
        label: { show: true, position: 'insideEndTop', fontSize: 11, color: '#64748b' },
        data: [
          [
            { name: '15% de la renta anual', coord: [2000, 300] },
            { coord: [8000, 1200] }
          ],
          [
            { name: '20% de la renta anual', coord: [2000, 400] },
            { coord: [6000, 1200] }
          ],
          [
            { name: '25% de la renta anual', coord: [2000, 500] },
            { coord: [4800, 1200] }
          ]
        ]
      }
    }]
  }}/>

Arriba a la derecha, municipios ricos con contratos caros. Las líneas
discontinuas son ratios constantes: 15, 20 y 25% de la renta neta media
anual. Los puntos por encima de la línea del 20% son el esfuerzo de
firma extremo — contrato caro sobre rentas medias más bajas, con la
renta media de todos los hogares (no solo inquilinos) fijando el eje
horizontal. Los alquileres de firma más altos del país no son
proporcionalmente los más esforzados:

```sql top_alquiler
select municipio, round(renta_neta_hogar / 12.0, 0) as renta_mensual,
       round(alquiler_med, 0) as alquiler_med, contratos, ratio_pct
from access.rent_income
where anyo = 2023 and contratos >= 50 and ratio_pct is not null
order by alquiler_med desc
limit 12
```

<DataTable data={top_alquiler} rows=12>
  <Column id=municipio title="Municipio"/>
  <Column id=renta_mensual title="Renta neta media mensual (€)" fmt="num0"/>
  <Column id=alquiler_med title="Alquiler mediano (€/mes)" fmt="num0"/>
  <Column id=contratos title="Contratos (VC)" fmt="num0"/>
  <Column id=ratio_pct title="Ratio (% de renta anual)" fmt="num1"/>
</DataTable>

## La distribución, no solo la mediana

```sql dist_proxy
select ratio_pct
from access.rent_income
where anyo = 2023 and contratos >= 50 and ratio_pct is not null
```

<Histogram data={dist_proxy} x=ratio_pct xFmt="num1"
  xAxisTitle="Ratio alquiler/renta 2023 (%)"
  title="Distribución municipal del ratio de firma (≥50 contratos)"/>

La cola derecha es el mapa del esfuerzo: once municipios — la costa
malagueña, el cinturón de Barcelona y Pasaia — superan el 22% de la renta
media local, y solo Benahavís pasa del 25%.

## El mapa del ratio de firma

```sql mapa_proxy
select codigo, municipio, ratio_pct,
       ratio_pct as "Alquiler / renta (%)"
from access.rent_income
where anyo = 2023 and contratos >= 50 and ratio_pct is not null
```

<AreaMap
  data={mapa_proxy}
  geoJsonUrl='/geo/municipios.geojson'
  geoId='CODIGOINE'
  areaCol=codigo
  value={'Alquiler / renta (%)'}
  valueFmt=num1
  basemap={'https://tile.openstreetmap.org/{z}/{x}/{y}.png'}
  attribution='© OpenStreetMap'
  title="Ratio alquiler de firma / renta neta media, 2023 (≥50 contratos)"
  height=560
  startingLat=40.2
  startingLong=-3.7
  startingZoom=6
/>

Solo se colorean los municipios con datos (1.569 de 8.131); el resto
queda sin color porque SERPAVI no publica renta mediana allí. Los
municipios pequeños de menos de 100 habitantes pueden llevar la media
comarcal/provincial de ADRH en lugar de renta propia (regla de difusión
2020+, no marcada por fila).

## Qué no mide este indicador

- **No es una tasa de sobrecarga.** El denominador es la renta neta
  media de **todos** los hogares del municipio (ADRH, registros
  administrativos), no la de quienes alquilan — tiende a ser menor.
- **El numerador es el mercado de firma:** contratos nuevos y
  renovaciones declarados ante Hacienda (fianzas SERPAVI, vivienda
  colectiva). El stock de inquilinos sentados paga menos y no aparece.
- Sin suministros ni otros costes de vivienda; renta neta antes de
  alquiler imputado.
- **Cobertura sesgada a municipios con suficientes contratos**
  (1.877–2.415 de 8.139 por año): los pequeños y rurales faltan, y desde
  2020 ADRH puede sustituir la renta de municipios de menos de 100
  habitantes por la media comarcal/provincial (regla de difusión,
  no marcada por fila).
- Comparar municipios es comparar mercados distintos; la mediana
  municipal de un año cambia también porque entra y sale cobertura.

Fuente: SERPAVI (MIVAU) y ADRH (INE), construido por
`scripts/build_rent_income.py` sobre la tabla `access.rent_income`;
semántica aceptada y documentada en `docs/housing_access.md`.

---
*Proxy de mercado de firma, 2015–2023 · SERPAVI + ADRH · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
