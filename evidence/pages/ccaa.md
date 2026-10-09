---
title: Comunidades autónomas
---

# Comunidades autónomas

Explora una comunidad y sus provincias. [Panorama nacional](/) ·
[Comparar dos territorios](/comparar/) ·
[Municipios](/municipios/).
El IPV es un índice (2025 = 100), no un precio en euros.

```sql lista_ccaa
select distinct ccaa
from housing.mart_ccaa_anual
where ccaa != 'Nacional'
order by 1
```

<Dropdown
  data={lista_ccaa}
  name=ccaa
  value=ccaa
  title="Comunidad autónoma"
  order="ccaa asc"
  defaultValue="Madrid, Comunidad de"
/>

```sql ficha
select anyo, viviendas_total, poblacion, pop_source, viv_por_1000_hab,
       hogares, viv_por_hogar, eur_m2_libre, renta_hogar_neta,
       afford_90m2_years, pob_20_34, share_20_34,
       ipv_general, ipv_nueva, ipv_segunda_mano
from housing.mart_ccaa_anual
where ccaa = '${inputs.ccaa.value}'
order by anyo
```

```sql provincias
select anyo, provincia, viv_por_1000_hab, share_no_principal
from housing.mart_provincia_anual
where ccaa = '${inputs.ccaa.value}'
order by anyo, provincia
```

## Precios

<LineChart
  data={ficha}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=ipv_general
  yFmt="num1"
  title={"IPV general (" + inputs.ccaa.value + ")"}
/>

## Stock y hogares

<LineChart
  data={ficha}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=viv_por_1000_hab
  yFmt="num1"
  title={"Viviendas por 1.000 habitantes (" + inputs.ccaa.value + ")"}
/>

<LineChart
  data={ficha}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=viv_por_hogar
  yFmt="num2"
  title={"Viviendas por hogar (" + inputs.ccaa.value + ", desde 2021)"}
/>

## Valor tasado y esfuerzo de renta

El valor tasado no es un precio de compraventa. El esfuerzo expresa años de
renta neta del hogar para 90 m², sin intereses ni otros costes de adquisición.

<LineChart
  data={ficha}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=eur_m2_libre
  yFmt="num0"
  title={"Valor tasado vivienda libre, €/m² (" + inputs.ccaa.value + ")"}
/>

<LineChart
  data={ficha}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=afford_90m2_years
  yFmt="num1"
  title={"Años de renta neta para 90 m² (" + inputs.ccaa.value + ")"}
/>

## Población joven

<LineChart
  data={ficha}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=share_20_34
  yFmt="pct1"
  title={"Cuota de 20–34 años (" + inputs.ccaa.value + ")"}
/>

## Provincias

La comparación provincial muestra stock por habitante, no precios: el IPV
no está disponible a ese nivel territorial.

<LineChart
  data={provincias}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=viv_por_1000_hab
  series=provincia
  yFmt="num1"
  title="Provincias: viviendas por 1.000 habitantes"
/>

## Datos y cobertura

Cada guion indica un dato no disponible; no se imputa ni se interpreta como cero.
La población cambia de fuente entre Padrón y ECP; consulta la columna de origen.
Puedes ordenar las columnas y descargar la tabla.

<DataTable data={ficha} rows=20>
  <Column id=anyo title="Año" fmt="0"/>
  <Column id=viviendas_total title="Viviendas" fmt="num0"/>
  <Column id=poblacion title="Población" fmt="num0"/>
  <Column id=pop_source title="Fuente de población"/>
  <Column id=viv_por_1000_hab title="Viviendas / 1.000 hab." fmt="num1"/>
  <Column id=hogares title="Hogares" fmt="num0"/>
  <Column id=viv_por_hogar title="Viviendas / hogar" fmt="num2"/>
  <Column id=eur_m2_libre title="Valor tasado (€/m²)" fmt="num0"/>
  <Column id=renta_hogar_neta title="Renta neta del hogar (€)" fmt="num0"/>
  <Column id=afford_90m2_years title="Renta para 90 m² (años)" fmt="num1"/>
  <Column id=pob_20_34 title="Población de 20–34 años" fmt="num0"/>
  <Column id=share_20_34 title="Cuota de 20–34 años" fmt="pct1"/>
  <Column id=ipv_general title="IPV general (2025 = 100)" fmt="num1"/>
  <Column id=ipv_nueva title="IPV nueva (2025 = 100)" fmt="num1"/>
  <Column id=ipv_segunda_mano title="IPV usada (2025 = 100)" fmt="num1"/>
</DataTable>

---
*Instantánea de datos: 2026-10-09 · cobertura por comunidad 2007–2025 · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
