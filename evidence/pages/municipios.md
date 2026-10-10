---
title: Municipios
---

# Municipios: toda España

El grano municipal muestra diferencias que las medias regionales esconden,
pero las fuentes no son iguales entre ciudades: Madrid usa valor tasado;
Barcelona combina registros de venta, alquiler y esfuerzo; Valencia y Sevilla
secciones se centran en alquiler y población. **Lee cada ciudad dentro de su
propia serie; no compares niveles entre fuentes como si fueran una medida
común.**

[Panorama nacional](/) · [Comunidades autónomas](/ccaa/) ·
[Comparar territorios](/comparar/) · [Acceso y cargas de hogares](/acceso/).

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

### Madrid por barrios: brechas en precios registrales

Precio medio declarado registral (€/m², Banco de datos del Ayuntamiento,
2007–2025, Total/Nuevas/Usadas). Elige primero el distrito. Los barrios
con menos de 15 compraventas no publican dato (guion, nunca cero).
Detalle en
[Madrid por barrios](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/barrios_madrid.md).

```sql distritos_bar
select distinct distrito
from housing.barrios_madrid
where distrito != 'Ciudad de Madrid'
order by distrito
```

<Dropdown data={distritos_bar} name=distrito_bar value=distrito
  title="Distrito" defaultValue="01. Centro"/>

```sql lista_bar
select distinct barrio
from housing.barrios_madrid
where distrito = '${inputs.distrito_bar.value}'
order by barrio
```

<Dropdown data={lista_bar} name=barrios_sel value=barrio
  title="Barrios" multiple=true
  defaultValue={["041. Recoletos", "012. Embajadores"]}/>

```sql serie_bar
select barrio, anyo, eur_m2
from housing.barrios_madrid
where distrito = '${inputs.distrito_bar.value}'
  and barrio in ${inputs.barrios_sel.value}
  and tipo = 'Total'
order by anyo, barrio
```

<LineChart data={serie_bar} x=anyo y=eur_m2 series=barrio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Precio registral (€/m²): barrios del distrito"/>

Recoletos multiplica por siete a San Cristóbal: la brecha intraurbana es
mayor que la intermunicipal. Precios declarados en escritura, no oferta.

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

### Barcelona por barrios: contratos de fianza INCASÒL

La Generalitat publica la explotación de las fianzas de alquiler depositadas
(número de contratos, renta media, €/m² y superficie): ciudad + 10 distritos
2000–2025 y 73 barrios en anual desde 2013 y en trimestral desde 2014. Son
contratos registrados, no precios de oferta; los ámbitos con menos de seis
contratos no publican dato (hueco, nunca cero). El último año/trimestre solo
trae lo publicado hasta la fecha.

```sql serie_distritos_bcn
select nom as distrito, anyo, lloguer_m2, contractes
from housing.barrios_bcn_lloguer_anual
where ambit = 'districte'
order by anyo, distrito
```

<LineChart data={serie_distritos_bcn} x=anyo y=lloguer_m2 series=distrito
  xFmt="0" xAxisTitle="Año" yFmt="num2" handleMissing="gap" markers=true
  title="Alquiler contractual (€/m²/mes): distritos"/>

```sql barris_bcn
select distinct nom as barrio
from housing.barrios_bcn_lloguer_anual
where ambit = 'barri'
order by barrio
```

<Dropdown data={barris_bcn} name=barris_bcn value=barrio
  title="Barrios" multiple=true
  defaultValue={["la Barceloneta", "el Raval", "el Barri Gòtic"]}/>

```sql serie_barris_bcn
select nom as barrio, anyo, lloguer_m2, contractes
from housing.barrios_bcn_lloguer_anual
where ambit = 'barri'
  and nom in ${inputs.barris_bcn.value}
order by anyo, barrio
```

<LineChart data={serie_barris_bcn} x=anyo y=lloguer_m2 series=barrio
  xFmt="0" xAxisTitle="Año" yFmt="num2" handleMissing="gap" markers=true
  title="Alquiler contractual (€/m²/mes): barrios (desde 2013)"/>

```sql serie_trim_bcn
select anyo * 10 + trimestre as periodo, nom as barrio, lloguer_m2
from housing.barrios_bcn_lloguer_trimestral
where ambit = 'barri'
  and nom in ${inputs.barris_bcn.value}
order by periodo, barrio
```

<LineChart data={serie_trim_bcn} x=periodo y=lloguer_m2 series=barrio
  xFmt="0" xAxisTitle="Año-trimestre (20241 = T1 2024)" yFmt="num2"
  handleMissing="gap" markers=true
  title="Alquiler contractual trimestral (€/m²/mes): barrios"/>

```sql serie_compra_bcn
select anyo * 10 + trimestre as periodo, nom as barrio, eur_m2_total, trx_total
from housing.barrios_bcn_compraventes
where ambit = 'barri'
  and nom in ${inputs.barris_bcn.value}
order by periodo, barrio
```

<LineChart data={serie_compra_bcn} x=periodo y=eur_m2_total series=barrio
  xFmt="0" xAxisTitle="Año-trimestre (20241 = T1 2024)" yFmt="num0"
  handleMissing="gap" markers=true
  title="Precio registrado (€/m² construido): barrios (2018–2019, 2021–; precios con <3 contratos ausentes)"/>

Precios de escrituras inscritas (Registradores), no oferta. Sin 2020
(hueco de publicación) y serie iniciada en 2018; el total ciudad incluye
registros sin geolocalizar.

```sql rendimiento_bcn
select s.nom as barrio,
       100.0 * max(r.lloguer_m2) * 12.0 / avg(s.eur_m2_total) as rendimiento
from housing.barrios_bcn_compraventes s
join housing.barrios_bcn_lloguer_anual r
  on r.codi = s.codi and r.anyo = s.anyo
where s.ambit = 'barri' and r.ambit = 'barri'
  and s.anyo = 2024 and r.anyo = 2024
  and s.nom in ${inputs.barris_bcn.value}
group by s.nom
order by rendimiento desc
```

<BarChart data={rendimiento_bcn} x=barrio y=rendimiento swapXY
  yFmt="num1" title="Rentabilidad bruta 2024 (%): alquiler nuevo anualizado / precio registrado"/>

Rentas de contratos nuevos sobre precios de escritura: la periferia rinde
más porque el suelo es barato, no porque alquilar sea caro.

```sql tendencia_yield_bcn
select s.anyo as anyo,
       quantile_disc(100.0 * r.lloguer_m2 * 12.0 / s.sale_m2, 0.5) as mediana
from (select codi, anyo, avg(eur_m2_total) as sale_m2
      from housing.barrios_bcn_compraventes
      where ambit = 'barri' and eur_m2_total is not null
      group by codi, anyo) s
join (select codi, anyo, lloguer_m2 from housing.barrios_bcn_lloguer_anual
      where ambit = 'barri' and lloguer_m2 is not null) r
  on r.codi = s.codi and r.anyo = s.anyo
where s.anyo <= 2024
group by s.anyo order by s.anyo
```

<LineChart data={tendencia_yield_bcn} x=anyo y=mediana
  xFmt="0" xAxisTitle="Año (sin 2020: hueco de publicación)" yFmt="num1"
  handleMissing="gap" markers=true
  title="Rentabilidad bruta mediana (%): subió hasta 2023, cedió en 2024"/>

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

### Sevilla por barrios: IPRA de contratos depositados

El SIM municipal expone el Índice de Precio de Alquiler Residencial
(IPRA), €/m² construido/mes, derivado de fianzas AVRA. Años 2016–2022:
cada valor usa ventana móvil de tres años (no contratos de ese año solo).
No es el alquiler anunciado ni comparable directamente con SERPAVI.
El SIM también ofrece un indicador de precio de compra por tipo de vivienda,
pero sin período de referencia publicado: se muestra aparte y no como serie
anual ni precio actual. Ver [metodología y cobertura](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/barrios_sevilla.md).

```sql distritos_ipra_sev
select distinct distrito
from housing.barrios_sevilla
order by distrito
```

<Dropdown data={distritos_ipra_sev} name=distrito_ipra_sev value=distrito
  title="Distrito (IPRA)" defaultValue="CASCO ANTIGUO"/>

```sql barrios_ipra_sev
select distinct barrio
from housing.barrios_sevilla
where distrito = '${inputs.distrito_ipra_sev.value}'
order by barrio
```

<Dropdown data={barrios_ipra_sev} name=barrios_ipra_sev value=barrio
  title="Barrios (IPRA)" multiple=true
  defaultValue={["ALFALFA", "ARENAL"]}/>

```sql serie_ipra_sev
select barrio, anyo, ipra_eur_m2
from housing.barrios_sevilla
where distrito = '${inputs.distrito_ipra_sev.value}'
  and barrio in ${inputs.barrios_ipra_sev.value}
order by anyo, barrio
```

<LineChart data={serie_ipra_sev} x=anyo y=ipra_eur_m2 series=barrio
  xFmt="0" xAxisTitle="Ventana IPRA" yFmt="num2" handleMissing="gap" markers=true
  title="IPRA (€/m² construido/mes; ventana móvil de 3 años)"/>

```sql compra_sim_sev
select barrio, compra_colectiva_eur_m2, compra_unifamiliar_eur_m2
from housing.barrios_sevilla_compra
where distrito = '${inputs.distrito_ipra_sev.value}'
order by compra_colectiva_eur_m2 desc nulls last
```

<DataTable data={compra_sim_sev} rows=20>
  <Column id=barrio title="Barrio"/>
  <Column id=compra_colectiva_eur_m2 title="Colectiva €/m²" fmt="num0"/>
  <Column id=compra_unifamiliar_eur_m2 title="Unifamiliar €/m²" fmt="num0"/>
</DataTable>

Indicador transversal del SIM, no lleva período de referencia publicado;
no compararlo como serie con precios registrales o de oferta.

### Oferta de segunda mano por zonas, 2024

Anuario municipal: precios **ofertados** mensuales de Fotocasa (11 distritos)
e Idealista (17 zonas). Los ámbitos de ambos portales son diferentes; el
selector los mantiene separados. No son precios de transacción ni de barrio.

```sql providers_sev_oferta
select distinct provider from housing.sevilla_oferta_zona order by provider
```

<Dropdown data={providers_sev_oferta} name=provider_sev_oferta value=provider
  title="Portal" defaultValue="Fotocasa"/>

```sql zonas_sev_oferta
select distinct zona
from housing.sevilla_oferta_zona
where provider = '${inputs.provider_sev_oferta.value}'
order by zona
```

<Dropdown data={zonas_sev_oferta} name=zonas_sev_oferta value=zona
  title="Distrito/zona" multiple=true defaultValue={["Casco Antiguo"]}/>

```sql serie_sev_oferta
select zona, mes, precio_oferta_eur_m2
from housing.sevilla_oferta_zona
where provider = '${inputs.provider_sev_oferta.value}'
  and zona in ${inputs.zonas_sev_oferta.value}
order by mes, zona
```

<LineChart data={serie_sev_oferta} x=mes y=precio_oferta_eur_m2 series=zona
  xFmt="0" xAxisTitle="Mes de 2024" yFmt="num0" handleMissing="gap" markers=true
  title="Precio ofertado segunda mano (€/m²)"/>

### Sevilla: contexto de vivienda y hogares por barrio

Capas del SIM municipal, separadas de los precios. Población y hogares
residentes tienen años explícitos (2015–2021). Las capas de uso, tipología y
necesidad estimada de rehabilitación no publican año de referencia en sus
campos; no se presentan como datos actuales. Presión turística: viviendas
activas en portales en 2008, febrero/agosto de 2021 y febrero de 2022; los
conteos registrados no llevan fecha explícita. Los nulos se conservan.

```sql distritos_context_sev
select distinct distrito
from housing.sevilla_sim_vivienda
order by distrito
```

<Dropdown data={distritos_context_sev} name=distrito_context_sev value=distrito
  title="Distrito (contexto SIM)" defaultValue="CASCO ANTIGUO"/>

```sql barrios_context_sev
select distinct barrio
from housing.sevilla_sim_vivienda
where distrito = '${inputs.distrito_context_sev.value}'
order by barrio
```

<Dropdown data={barrios_context_sev} name=barrios_context_sev value=barrio
  title="Barrios (contexto SIM)" multiple=true defaultValue={["ALFALFA", "ARENAL"]}/>

```sql serie_context_pob_sev
select barrio, anyo, poblacion, hogares
from housing.sevilla_sim_poblacion_hogares
where distrito = '${inputs.distrito_context_sev.value}'
  and barrio in ${inputs.barrios_context_sev.value}
order by anyo, barrio
```

<LineChart data={serie_context_pob_sev} x=anyo y=poblacion series=barrio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Población residente (SIM)"/>

<LineChart data={serie_context_pob_sev} x=anyo y=hogares series=barrio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Hogares residentes (SIM)"/>

```sql contexto_vivienda_sev
select barrio, viviendas_familiares_uso, principales_pct, secundarias_pct,
       deshabitadas_pct, colectivas_pct, unifamiliares_pct,
       rehabilitacion_estimada_pct, antiguedad_colectiva_anos,
       calidad_colectiva, superficie_colectiva_m2
from housing.sevilla_sim_vivienda
where distrito = '${inputs.distrito_context_sev.value}'
  and barrio in ${inputs.barrios_context_sev.value}
order by barrio
```

<DataTable data={contexto_vivienda_sev} rows=30>
  <Column id=barrio title="Barrio"/>
  <Column id=viviendas_familiares_uso title="Viviendas familiares" fmt="num0"/>
  <Column id=principales_pct title="Principales %" fmt="num1"/>
  <Column id=secundarias_pct title="Secundarias %" fmt="num1"/>
  <Column id=deshabitadas_pct title="Deshabitadas %" fmt="num1"/>
  <Column id=colectivas_pct title="Colectivas %" fmt="num1"/>
  <Column id=unifamiliares_pct title="Unifamiliares %" fmt="num1"/>
  <Column id=rehabilitacion_estimada_pct title="Necesidad estimada de rehabilitación %" fmt="num1"/>
  <Column id=antiguedad_colectiva_anos title="Referencia anual colectiva (SIM)" fmt="0"/>
  <Column id=calidad_colectiva title="Calidad constructiva colectiva" fmt="num2"/>
  <Column id=superficie_colectiva_m2 title="Superficie colectiva (m²)" fmt="num0"/>
</DataTable>

La referencia constructiva SIM contiene valores de año, no edades transcurridas;
el nombre interno heredado termina en `_anos`, pero no restamos un año de
referencia desconocido. Para polígonos y fechas constructivas individuales,
ver el [piloto de stock físico catastral](/stock/).

```sql turismo_contexto_sev
select barrio,
       vft_2008, vft_2008_pct,
       vft_2021_02, vft_2021_02_pct,
       vft_2021_08, vft_2021_08_pct,
       vft_2022_02, vft_2022_02_pct,
       vft_registradas, vft_registradas_plazas
from housing.sevilla_sim_turismo
where distrito = '${inputs.distrito_context_sev.value}'
  and barrio in ${inputs.barrios_context_sev.value}
order by barrio
```

<DataTable data={turismo_contexto_sev} rows=30>
  <Column id=barrio title="Barrio"/>
  <Column id=vft_2008 title="Activas 2008" fmt="num0"/>
  <Column id=vft_2008_pct title="Presión 2008 %" fmt="num1"/>
  <Column id=vft_2021_02 title="Activas feb-2021" fmt="num0"/>
  <Column id=vft_2021_02_pct title="Presión feb-2021 %" fmt="num1"/>
  <Column id=vft_2021_08 title="Activas ago-2021" fmt="num0"/>
  <Column id=vft_2021_08_pct title="Presión ago-2021 %" fmt="num1"/>
  <Column id=vft_2022_02 title="Activas feb-2022" fmt="num0"/>
  <Column id=vft_2022_02_pct title="Presión feb-2022 %" fmt="num1"/>
  <Column id=vft_registradas title="Registradas (sin fecha)" fmt="num0"/>
  <Column id=vft_registradas_plazas title="Plazas registradas (sin fecha)" fmt="num0"/>
</DataTable>

El SIM publica problemas de accesibilidad solo a escala de distrito/municipio,
no por barrio; no se imputan ni redistribuyen esos valores. Descripciones,
fuentes y limitaciones en [la ficha metodológica de Sevilla](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/barrios_sevilla.md).

## Toda España: 8.136 municipios

Padrón municipal de las 52 tablas DPOP (1996–2025) con la renta mediana
SERPAVI (2011–2024) y la vacancia del Censo 2011. Elige primero la
provincia y después los municipios. Detalle en
[Todos los municipios](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/municipios_nacional.md).

```sql provincias_all
select distinct provincia
from housing.muni_all
order by provincia
```

<Dropdown data={provincias_all} name=prov_all value=provincia
  title="Provincia" defaultValue="Madrid"/>

```sql lista_all
select distinct municipio
from housing.muni_all
where provincia = '${inputs.prov_all.value}'
order by municipio
```

<!-- Trust boundary: both inputs feed SQL interpolation, but prov_all is a
  constrained Dropdown over mart values and munis_all over the filtered
  list — never free text. -->
<Dropdown data={lista_all} name=munis_all value=municipio
  title="Municipios" multiple=true
  defaultValue={["Madrid (ciudad)"]}/>

```sql serie_all
select municipio, anyo, poblacion, rent_eur_m2
from housing.muni_all
where provincia = '${inputs.prov_all.value}'
  and municipio in ${inputs.munis_all.value}
order by anyo, municipio
```

<LineChart data={serie_all} x=anyo y=rent_eur_m2 series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  title="Alquiler mediano SERPAVI (€/m²/mes)"/>

<LineChart data={serie_all} x=anyo y=poblacion series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Población municipal"/>

```sql vacancia_all
select municipio, dwellings_2011, vacant_2011,
       100.0 * vacant_2011 / nullif(dwellings_2011, 0) as pct_vacia
from housing.muni_all
where anyo = 2011 and dwellings_2011 is not null
  and provincia = '${inputs.prov_all.value}'
  and municipio in ${inputs.munis_all.value}
order by pct_vacia desc
```

<DataTable data={vacancia_all} rows=20>
  <Column id=municipio title="Municipio"/>
  <Column id=dwellings_2011 title="Viviendas 2011" fmt="num0"/>
  <Column id=vacant_2011 title="Vacías 2011" fmt="num0"/>
  <Column id=pct_vacia title="% vacía" fmt="num1"/>
</DataTable>

Sin precios de venta a este grano en ninguna provincia (solo Madrid y
Barcelona tienen series propias, arriba). Relaciones descriptivas.

### Distritos censales: la mediana SERPAVI bajo el municipio

La misma base tributaria SERPAVI, a grano de distrito censal (2011–2024,
mediana de colectiva en €/m²/mes). Los distritos son códigos oficiales sin
nombre publicado: se leen como posición dentro del municipio. Solo celdas
publicadas; el hueco es supresión estadística.

```sql provincias_dist
select distinct provincia
from housing.serpavi_distritos
order by provincia
```

<Dropdown data={provincias_dist} name=prov_dist value=provincia
  title="Provincia (distritos)" defaultValue="Madrid"/>

```sql munis_dist
select distinct municipio
from housing.serpavi_distritos
where provincia = '${inputs.prov_dist.value}'
order by municipio
```

<Dropdown data={munis_dist} name=munis_dist value=municipio
  title="Municipio (distritos)" defaultValue="Madrid"/>

```sql lista_dist
select distinct distrito
from housing.serpavi_distritos
where provincia = '${inputs.prov_dist.value}'
  and municipio = '${inputs.munis_dist.value}'
order by distrito
```

<Dropdown data={lista_dist} name=distritos_sel value=distrito
  title="Distritos" multiple=true
  defaultValue={["2807904", "2807907"]}/>

```sql serie_dist
select distrito, anyo, valor as mediana_m2
from housing.serpavi_distritos
where provincia = '${inputs.prov_dist.value}'
  and municipio = '${inputs.munis_dist.value}'
  and distrito in ${inputs.distritos_sel.value}
  and medida = 'ALQM2_LV_M_VC'
order by anyo, distrito
```

<LineChart data={serie_dist} x=anyo y=mediana_m2 series=distrito
  xFmt="0" xAxisTitle="Año" yFmt="num2" handleMissing="gap" markers=true
  title="Alquiler mediano colectiva (€/m²/mes): distritos censales"/>

## Datos y cobertura

Series municipales con huecos según fuente y año; el guion es dato ausente,
nunca cero. El valor tasado madrileño y los precios DIBA no son comparables
entre sí (distintas fuentes y metodologías): cada metro se lee por separado.
Valencia no tiene precios de venta municipales: solo alquiler SERPAVI,
población y vacancia 2011. Sevilla, igual: Padrón 1996–2025, alquiler
2011–2024, vacancia 2011, sin venta.

---
*Instantánea de datos: 2026-10-09 · Madrid 2005–2025, Barcelona 2007–2024, toda España 1996–2025 (alquiler 2011–2024, sin venta); el guion es dato ausente · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
