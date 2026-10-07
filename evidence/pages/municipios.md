---
title: Municipios
---

# Municipios: Madrid, Barcelona, Valencia y Sevilla

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

## Valencia: alquileres y vacancia, sin precios de venta

Padrón municipal (266 municipios, 1996–2025) con la renta mediana SERPAVI
(€/m²/mes, 2011–2024) y la vivienda vacía del Censo 2011. No hay serie de
precios de venta a grano municipal valenciano: ningún espejo regional
publica el valor tasado municipal y el portal estadístico de la Generalitat
no es accesible para la ingesta automática. Detalle en
[Valencia: municipios sin precio de venta](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/valencia_municipios.md).

```sql lista_vlc
select distinct municipio
from housing.muni_vlc
order by municipio
```

<Dropdown data={lista_vlc} name=munis_vlc value=municipio
  title="Municipios de Valencia" multiple=true
  defaultValue={["València", "Torrent", "Gandia", "Sagunt/Sagunto"]}/>

```sql serie_vlc
select municipio, anyo, poblacion, rent_eur_m2
from housing.muni_vlc
where municipio in ${inputs.munis_vlc.value}
order by anyo, municipio
```

<LineChart data={serie_vlc} x=anyo y=rent_eur_m2 series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  title="Alquiler mediano SERPAVI (€/m²/mes)"/>

<LineChart data={serie_vlc} x=anyo y=poblacion series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Población municipal"/>

```sql vacancia_vlc
select municipio, dwellings_2011, vacant_2011,
       100.0 * vacant_2011 / nullif(dwellings_2011, 0) as pct_vacia
from housing.muni_vlc
where anyo = 2011 and dwellings_2011 is not null
  and municipio in ${inputs.munis_vlc.value}
order by pct_vacia desc
```

<DataTable data={vacancia_vlc} rows=20>
  <Column id=municipio title="Municipio"/>
  <Column id=dwellings_2011 title="Viviendas 2011" fmt="num0"/>
  <Column id=vacant_2011 title="Vacías 2011" fmt="num0"/>
  <Column id=pct_vacia title="% vacía" fmt="num1"/>
</DataTable>

La capital y su corona metropolitana concentran los alquileres más altos;
los máximos de vacancia 2011 están en municipios pequeños del interior.
Relaciones descriptivas, no causales.

## Sevilla: la capital tira del alquiler metropolitano

Padrón municipal (106 municipios, 1996–2025) con la renta mediana SERPAVI
(€/m²/mes, 2011–2024) y la vivienda vacía del Censo 2011. Como en Valencia,
no hay serie de precios de venta a grano municipal. Detalle en
[Sevilla: alquileres sin precio de venta](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/sevilla_municipios.md).

```sql lista_sev
select distinct municipio
from housing.muni_sev
order by municipio
```

<Dropdown data={lista_sev} name=munis_sev value=municipio
  title="Municipios de Sevilla" multiple=true
  defaultValue={["Sevilla (ciudad)", "Dos Hermanas", "Alcalá de Guadaíra", "Mairena del Aljarafe"]}/>

```sql serie_sev
select municipio, anyo, poblacion, rent_eur_m2
from housing.muni_sev
where municipio in ${inputs.munis_sev.value}
order by anyo, municipio
```

<LineChart data={serie_sev} x=anyo y=rent_eur_m2 series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  title="Alquiler mediano SERPAVI (€/m²/mes)"/>

<LineChart data={serie_sev} x=anyo y=poblacion series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Población municipal"/>

```sql vacancia_sev
select municipio, dwellings_2011, vacant_2011,
       100.0 * vacant_2011 / nullif(dwellings_2011, 0) as pct_vacia
from housing.muni_sev
where anyo = 2011 and dwellings_2011 is not null
  and municipio in ${inputs.munis_sev.value}
order by pct_vacia desc
```

<DataTable data={vacancia_sev} rows=20>
  <Column id=municipio title="Municipio"/>
  <Column id=dwellings_2011 title="Viviendas 2011" fmt="num0"/>
  <Column id=vacant_2011 title="Vacías 2011" fmt="num0"/>
  <Column id=pct_vacia title="% vacía" fmt="num1"/>
</DataTable>

El Aljarafe (Espartinas, Mairena) y la capital marcan los alquileres más
altos; la vacancia 2011 más alta está en la campiña y las sierras.
Relaciones descriptivas, no causales.

## Datos y cobertura

Series municipales con huecos según fuente y año; el guion es dato ausente,
nunca cero. El valor tasado madrileño y los precios DIBA no son comparables
entre sí (distintas fuentes y metodologías): cada metro se lee por separado.
Valencia no tiene precios de venta municipales: solo alquiler SERPAVI,
población y vacancia 2011. Sevilla, igual: Padrón 1996–2025, alquiler
2011–2024, vacancia 2011, sin venta.

---
*Instantánea de datos: 2026-10-07 · Madrid 2005–2025, Barcelona 2007–2024, Valencia 1996–2025 y Sevilla 1996–2025 (alquiler 2011–2024, sin venta); el guion es dato ausente · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
