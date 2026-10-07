---
title: Municipios
---

# Municipios: Madrid y Barcelona

El grano municipal muestra lo que la media autonómica esconde.
[Panorama nacional](/) · [Comparar territorios](/comparar/).

## Madrid: la capital se despega del sur

Valor tasado de vivienda libre (€/m², 2005–2025, 28 municipios).
El sur cayó ~50–55% y nunca recuperó precios nominales de 2007;
el noroeste y la capital sí. Precios de oferta tasada, no compraventas.

```sql lista_mad
select distinct municipio
from housing.muni_madrid
order by municipio
```

<Dropdown data={lista_mad} name=munis_mad value=municipio
  title="Municipios de Madrid" multiple=true
  defaultValue={["Madrid", "Parla", "Pozuelo de Alarcón", "Fuenlabrada"]}/>

```sql serie_mad
select municipio, anyo, eur_m2, poblacion
from housing.muni_madrid
where municipio in ${inputs.munis_mad.value}
order by anyo, municipio
```

<LineChart data={serie_mad} x=anyo y=eur_m2 series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Valor tasado (€/m²): capital y corona"/>

<LineChart data={serie_mad} x=anyo y=poblacion series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Población municipal"/>

```sql resumen_mad
with extremos as (
  select municipio,
         min(case when eur_m2 is not null then anyo end) as desde,
         max(case when eur_m2 is not null then anyo end) as hasta
  from housing.muni_madrid
  where municipio in ${inputs.munis_mad.value}
  group by municipio
)
select e.municipio, e.desde, e.hasta,
       (select eur_m2 from housing.muni_madrid
         where municipio = e.municipio and anyo = e.desde) as valor_desde,
       (select eur_m2 from housing.muni_madrid
         where municipio = e.municipio and anyo = e.hasta) as valor_hasta
from extremos e
order by municipio
```

<DataTable data={resumen_mad} rows=20>
  <Column id=municipio title="Municipio"/>
  <Column id=desde title="Desde" fmt="0"/>
  <Column id=valor_desde title="€/m² inicial" fmt="num0"/>
  <Column id=hasta title="Hasta" fmt="0"/>
  <Column id=valor_hasta title="€/m² final" fmt="num0"/>
</DataTable>

Crecer no es revalorizarse: Rivas (+74% población) y Parla (+39%) absorben
gente sin recuperar precios; la capital (+12%) es la que más se aprecia.
Ver [Madrid capital vs corona](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/madrid_municipios.md).

## Barcelona: la metrópoli tensionada y su corona

Demarcación de Barcelona (Diputació + Padrón, 2007–2024): venta (€/m²,
desde 2013), alquiler (€/mes, desde 2005) y esfuerzo medio (alquiler o
hipoteca nueva sobre renta bruta, 2015–2022). Los esfuerzos son medias
DIBA: niveles duros, no distribuciones.

```sql lista_bcn
select distinct municipio
from housing.muni_bcn
order by municipio
```

<Dropdown data={lista_bcn} name=munis_bcn value=municipio
  title="Municipios de Barcelona" multiple=true
  defaultValue={["Barcelona", "L'Hospitalet de Llobregat", "Badalona", "Santa Coloma de Gramenet"]}/>

```sql serie_bcn
select municipio, anyo, sale_eur_m2, rent_month, rent_burden, mortgage_burden, tourist
from housing.muni_bcn
where municipio in ${inputs.munis_bcn.value}
order by anyo, municipio
```

<LineChart data={serie_bcn} x=anyo y=sale_eur_m2 series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  emptySet="pass" emptyMessage="Sin precios de venta en la selección (disponibles desde 2013)."
  title="Precio de venta (€/m², desde 2013)"/>

<LineChart data={serie_bcn} x=anyo y=rent_month series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Alquiler (€/mes)"/>

<LineChart data={serie_bcn} x=anyo y=rent_burden series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="pct1" handleMissing="gap" markers=true
  emptySet="pass" emptyMessage="Sin datos de esfuerzo en la selección (ventana 2015–2022)."
  title="Esfuerzo del alquiler (s/ renta bruta)"/>

```sql resumen_bcn
with extremos as (
  select municipio,
         min(case when sale_eur_m2 is not null then anyo end) as desde_venta,
         max(case when sale_eur_m2 is not null then anyo end) as hasta_venta,
         min(case when rent_month is not null then anyo end) as desde_alq,
         max(case when rent_month is not null then anyo end) as hasta_alq
  from housing.muni_bcn
  where municipio in ${inputs.munis_bcn.value}
  group by municipio
)
select e.municipio,
       e.desde_venta, e.hasta_venta,
       (select sale_eur_m2 from housing.muni_bcn
         where municipio = e.municipio and anyo = e.desde_venta) as venta_desde,
       (select sale_eur_m2 from housing.muni_bcn
         where municipio = e.municipio and anyo = e.hasta_venta) as venta_hasta,
       e.desde_alq, e.hasta_alq,
       (select rent_month from housing.muni_bcn
         where municipio = e.municipio and anyo = e.desde_alq) as alquiler_desde,
       (select rent_month from housing.muni_bcn
         where municipio = e.municipio and anyo = e.hasta_alq) as alquiler_hasta,
       (select max(rent_burden) from housing.muni_bcn
         where municipio = e.municipio) as esfuerzo_max
from extremos e
order by municipio
```

<DataTable data={resumen_bcn} rows=20>
  <Column id=municipio title="Municipio"/>
  <Column id=venta_desde title="Venta inicial (€/m²)" fmt="num0"/>
  <Column id=venta_hasta title="Venta final (€/m²)" fmt="num0"/>
  <Column id=alquiler_desde title="Alquiler inicial (€/mes)" fmt="num0"/>
  <Column id=alquiler_hasta title="Alquiler final (€/mes)" fmt="num0"/>
  <Column id=esfuerzo_max title="Esfuerzo máx. alquiler" fmt="pct1"/>
</DataTable>

La corona está más tensionada por hipoteca que la ciudad (pisos más baratos,
rentas mucho más bajas) y el turismo es hiperlocal: Barcelona ciudad concentra
miles de pisos turísticos; Santa Coloma, decenas. Detalle en
[Barcelona: metrópoli tensionada](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/barcelona_municipios.md).

## Datos y cobertura

Series municipales con huecos según fuente y año; el guion es dato ausente,
nunca cero. El valor tasado madrileño y los precios DIBA no son comparables
entre sí (distintas fuentes y metodologías): cada metro se lee por separado.

---
*Instantánea de datos: 2026-10-07 · Madrid 2005–2025, Barcelona 2007–2024; el guion es dato ausente · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
