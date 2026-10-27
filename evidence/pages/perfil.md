---
title: Tu municipio
---

# Tu municipio: qué sabemos y qué falta

Una ficha local de población, viviendas, alquiler e ingresos, **sin puntuación
sintética de asequibilidad**. Cada indicador conserva su año, unidad y cobertura.
No sustituimos un dato municipal ausente por la media provincial o autonómica.

[Reportaje](/reportaje/) · [Municipios y ciudades](/municipios/) ·
[Alquiler e ingresos](/renta-ingresos/) · [Stock y acceso](/acceso/)

```sql municipios_perfil
with nombres_adrh as (
  select codigo, municipio,
         row_number() over (partition by codigo order by anyo desc) as posicion
  from profile_income.municipal
), codigos as (
  select codigo from housing.perfil_catalogo
  union select codigo from profile_income.municipal
), nombres as (
  select c.codigo,
         coalesce(nullif(h.municipio, 'Municipio sin nombre en SERPAVI'),
                  a.municipio, 'Municipio sin nombre publicado') as municipio,
         p.provincia,
         case when h.provincia is not null then 'SERPAVI'
              when a.municipio is not null then 'ADRH'
              else 'Sin nombre publicado' end as fuente_nombre
  from codigos c
  left join housing.perfil_catalogo h on h.codigo = c.codigo
  left join nombres_adrh a on a.codigo = c.codigo and a.posicion = 1
  left join housing.perfil_provincias p on p.cpro = left(c.codigo, 2)
  where regexp_full_match(c.codigo, '[0-9]{5}') and right(c.codigo, 3) != '999'
)
select codigo, municipio, provincia, fuente_nombre,
       municipio || ' · ' || coalesce(provincia || ' · ', '') || codigo as etiqueta
from nombres
order by etiqueta
```

<Dropdown data={municipios_perfil} name=municipio_perfil value=codigo label=etiqueta
  title="Busca tu municipio por nombre, provincia o código INE" defaultValue="28079" />

```sql identidad_perfil
select codigo, municipio, provincia, fuente_nombre
from ${municipios_perfil}
where codigo = '${inputs.municipio_perfil.value}'
```

<DataTable data={identidad_perfil} rows=1>
  <Column id=municipio title="Municipio" />
  <Column id=provincia title="Provincia (código INE)" />
  <Column id=codigo title="Código INE" />
  <Column id=fuente_nombre title="Fuente del nombre municipal" />
</DataTable>

El selector reúne códigos del Censo, SERPAVI y ADRH, incluidos municipios sin
alquiler publicado. Conserva el nombre de SERPAVI cuando existe y usa ADRH
para los demás; la fuente del nombre se muestra en la ficha. La provincia
se identifica por el prefijo del código, manteniendo Ceuta y Melilla separadas.
Los nombres son etiquetas: **las uniones usan el código INE**, no coincidencias
entre nombres. La ficha no armoniza cambios de límites, fusiones o segregaciones;
compartir código no garantiza una geografía histórica constante.

**[Compara dos municipios en los mismos años](/comparar-municipios/)**: una medida cada vez, con los años excluidos a la vista y sin mezclar fuentes.

## Una ficha, varias fechas

Los cortes de mercado son los últimos años con algún dato de cada fuente en el
conjunto exportado, **no el último dato disponible de cada municipio**. Si falta
el valor local en ese corte, queda vacío: no retrocedemos a un año antiguo.
El Censo conserva su referencia histórica; no describe el parque actual.

```sql cortes_perfil
select
  (select max(anyo) from housing.perfil_alquiler where eur_m2_mes is not null) as anyo_alquiler,
  (select max(anyo) from profile_income.municipal where renta_neta_hogar is not null) as anyo_ingresos,
  (select max(anyo) from access.rent_income where ratio_pct is not null) as anyo_proxy
```

```sql indicadores_perfil
with elegido as (
  select codigo from ${identidad_perfil}
), censo as (
  select c.* from housing.perfil_censo c join elegido e on e.codigo = c.codigo
), vacancia as (
  select v.* from housing.vacancy_municipal v join elegido e on e.codigo = v.codigo
), alquiler as (
  select a.* from housing.perfil_alquiler a join elegido e on e.codigo = a.codigo
), ingresos as (
  select i.* from profile_income.municipal i join elegido e on e.codigo = i.codigo
), cruce as (
  select r.* from access.rent_income r join elegido e on e.codigo = r.codigo
), filas as (
  select 1 as orden, 'Población censal' as indicador, 2021 as anyo,
         (select poblacion from censo) as valor, 'Personas' as unidad,
         'INE · Censo por secciones' as fuente,
         'Suma municipal; no es población actual' as alcance
  union all
  select 2, 'Viviendas censales', 2021, (select viviendas from censo), 'Viviendas',
         'INE · Censo por secciones',
         'Total retenido solo si todas las secciones publican el dato'
  union all
  select 3, 'Hogares censales', 2021, (select hogares from censo), 'Hogares',
         'INE · Censo por secciones',
         'Total retenido solo si todas las secciones publican el dato'
  union all
  select 4, 'Vacancia eléctrica', 2021, (select vac_pct from vacancia), '% del parque censal',
         'INE · Censo, consumo eléctrico',
         'Consumo de 2020; no habitabilidad ni oferta disponible'
  union all
  select 5, 'Alquiler mediano', p.anyo_alquiler,
         (select eur_m2_mes from alquiler where anyo = p.anyo_alquiler), '€/m²/mes nominales',
         'MIVAU · SERPAVI · vivienda colectiva', 'Mercado declarado; no todos los alquileres'
  from ${cortes_perfil} p
  union all
  select 6, 'Renta neta media del hogar', p.anyo_ingresos,
         (select renta_neta_hogar from ingresos where anyo = p.anyo_ingresos), '€/hogar/año nominales',
         'INE · ADRH · serie municipal completa', 'Todos los hogares; no renta de inquilinos'
  from ${cortes_perfil} p
  union all
  select 7, 'Alquiler / renta (proxy)', p.anyo_proxy,
         (select ratio_pct from cruce where anyo = p.anyo_proxy), '% de renta anual media',
         'SERPAVI + ADRH · cruce del mismo año', 'No es una tasa de sobrecarga'
  from ${cortes_perfil} p
)
select f.*,
       case when valor is not null then 'Dato publicado'
            when orden in (2, 3) and (select secciones_suprimidas from censo) > 0
              then 'No mostrado: hay secciones suprimidas'
            when orden = 6 then 'Sin dato en este corte ADRH'
            when orden = 7 then 'Sin dato en este corte del cruce'
            else 'Sin dato en este corte' end as estado
from filas f
order by orden
```

<DataTable data={indicadores_perfil} rows=7>
  <Column id=indicador title="Indicador" />
  <Column id=anyo title="Año de referencia" fmt="0" />
  <Column id=valor title="Valor (vacío = sin dato)" fmt="num2" />
  <Column id=unidad title="Unidad" />
  <Column id=estado title="Estado del dato" />
  <Column id=fuente title="Fuente" />
  <Column id=alcance title="Cobertura y límite" />
</DataTable>

**Un dato ausente no es cero.** Puede faltar por cobertura, secreto estadístico
o porque la medida no se publique. Un cero publicado se conserva. No conocemos
la causa exacta de cada ausencia. Si una sección censal oculta viviendas u
hogares, no presentamos la suma de las otras como total municipal. La población
puede seguir publicada en esas secciones.

La vacancia eléctrica no es una reserva de vivienda habitable o disponible.
Los agregados «Resto de la provincia» se excluyen del selector y nunca se reparten
entre municipios. El contexto censal por secciones y la tabla de consumo son
productos distintos: no se restan ni se fuerza su igualdad.

**Ingresos sin exigir datos de alquiler.** La renta neta media del hogar viene
ahora de la serie municipal ADRH completa, no del cruce con SERPAVI. Puede haber
renta publicada y no haber alquiler ni proxy. Un valor ausente en ADRH se
conserva como ausente, sin atribuir una causa precisa: el fichero retenido no
distingue secreto estadístico de otras ausencias.

ADRH describe todos los hogares, no solo inquilinos. Desde 2020 puede sustituir
la renta de municipios de menos de 100 habitantes por una media comarcal o
provincial, sin bandera por fila; **la ficha no introduce nuevas sustituciones**
ni identifica qué filas llevan esa regla. El proxy sigue usando exclusivamente
el cruce SERPAVI/ADRH ya verificado, sin ampliarlo ni recalcularlo con esta serie.
Sus ingresos y alquiler son del mismo año. Una renta disponible aquí no rellena
un proxy ausente ni permite combinar el alquiler reciente con ingresos antiguos.

## La historia del alquiler, con sus huecos

```sql historia_alquiler_perfil
with calendario as (
  select range as anyo
  from range(
    (select cast(min(anyo) as bigint) from housing.perfil_alquiler),
    (select cast(max(anyo) + 1 as bigint) from housing.perfil_alquiler)
  )
)
select c.anyo, a.eur_m2_mes, a.contratos
from calendario c
left join housing.perfil_alquiler a
  on a.anyo = c.anyo and a.codigo = '${inputs.municipio_perfil.value}'
order by c.anyo
```

<LineChart data={historia_alquiler_perfil} x=anyo y=eur_m2_mes
  xFmt="0" xAxisTitle="Ejercicio fiscal" yFmt="num2" markers=true handleMissing="gap"
  title="Alquiler mediano declarado · vivienda colectiva (€/m²/mes nominales)" />

<EvidencePanel data={historia_alquiler_perfil} chart="perfil-alquiler"
  columns={["anyo", "eur_m2_mes", "contratos"]}
  files={["data/raw/serpavi_bd.xlsx"]}
  definition="Alquiler mediano declarado de vivienda colectiva por metro cuadrado y mes, en euros nominales."
  coverage="Municipio seleccionado por código INE. El calendario conserva años ausentes; contratos publicados no representan todo el mercado. Sin homogeneizar cambios de límites." />

<DataTable data={historia_alquiler_perfil} rows=14>
  <Column id=anyo title="Año" fmt="0" />
  <Column id=eur_m2_mes title="Mediana (€/m²/mes)" fmt="num2" />
  <Column id=contratos title="Contratos declarados VC" fmt="num0" />
</DataTable>

Los años sin observación permanecen en la tabla y cortan la línea; no se
interpolan. El número de contratos es el publicado para vivienda colectiva,
no una estimación del tamaño de todo el mercado local. La ausencia de una línea
no implica alquiler gratuito ni ausencia de hogares arrendatarios.

## La renta de todos los hogares, aunque no haya alquiler publicado

```sql historia_ingresos_perfil
with calendario as (
  select range as anyo
  from range(
    (select cast(min(anyo) as bigint) from profile_income.municipal),
    (select cast(max(anyo) + 1 as bigint) from profile_income.municipal)
  )
)
select c.anyo, i.renta_neta_hogar
from calendario c
left join profile_income.municipal i
  on i.anyo = c.anyo and i.codigo = '${inputs.municipio_perfil.value}'
order by c.anyo
```

<LineChart data={historia_ingresos_perfil} x=anyo y=renta_neta_hogar
  xFmt="0" xAxisTitle="Año de ingresos" yFmt="num0" markers=true handleMissing="gap"
  title="ADRH: renta neta media anual del hogar (euros nominales)" />

<EvidencePanel data={historia_ingresos_perfil} chart="perfil-ingresos"
  columns={["anyo", "renta_neta_hogar"]}
  files={["data/raw/adrh_renta_municipal.csv"]}
  definition="Renta neta media anual por hogar de ADRH, independiente de que exista alquiler publicado."
  coverage="Todos los hogares del ámbito de ADRH, no solo inquilinos. Se conservan supresiones; pueden existir sustituciones territoriales del publicador sin bandera por fila. Euros nominales, no renta real." />

<DataTable data={historia_ingresos_perfil} rows=9>
  <Column id=anyo title="Año de ingresos" fmt="0" />
  <Column id=renta_neta_hogar title="Renta neta media (€/hogar/año)" fmt="num0" />
</DataTable>

La serie no depende de que SERPAVI publique contratos para ese municipio.
Son medias administrativas de todos los hogares en el ámbito de ADRH,
**no ingresos de inquilinos, medianas, renta por persona ni renta de encuesta ECV**.
Los euros son nominales: su cambio no es automáticamente una ganancia de poder
adquisitivo. Los huecos se conservan y no se reconstruyen límites municipales
históricos.

## El cruce alquiler e ingresos, sin mezclar años

```sql historia_proxy_perfil
with calendario as (
  select range as anyo
  from range(
    (select cast(min(anyo) as bigint) from access.rent_income),
    (select cast(max(anyo) + 1 as bigint) from access.rent_income)
  )
)
select c.anyo, r.alquiler_med, r.renta_neta_hogar, r.ratio_pct
from calendario c
left join access.rent_income r
  on r.anyo = c.anyo and r.codigo = '${inputs.municipio_perfil.value}'
order by c.anyo
```

<LineChart data={historia_proxy_perfil} x=anyo y=ratio_pct
  xFmt="0" xAxisTitle="Ejercicio fiscal" yFmt="num1" markers=true handleMissing="gap"
  title="Proxy de mercado: alquiler mediano / renta neta media (%)" />

<EvidencePanel data={historia_proxy_perfil} chart="perfil-proxy"
  columns={["anyo", "alquiler_med", "renta_neta_hogar", "ratio_pct"]}
  files={["data/raw/serpavi_bd.xlsx", "data/raw/adrh_renta_municipal.csv"]}
  definition="Proxy revisado de alquiler mediano mensual anualizado sobre renta neta media anual del hogar del mismo año."
  coverage="Solo el cruce SERPAVI/ADRH ya verificado. La serie de ingresos independiente no rellena el proxy. No es una tasa de sobrecarga ni renta específica de inquilinos." />

<DataTable data={historia_proxy_perfil} rows=9>
  <Column id=anyo title="Año" fmt="0" />
  <Column id=alquiler_med title="Alquiler mediano (€/mes)" fmt="num0" />
  <Column id=renta_neta_hogar title="Renta neta media (€/hogar/año)" fmt="num0" />
  <Column id=ratio_pct title="Proxy (%)" fmt="num2" />
</DataTable>

El proxy compara un contrato mediano con la renta media de todos los hogares;
no observa el presupuesto de un hogar concreto, no incorpora suministros y
**no es una tasa de sobrecarga**. No aplicamos tasas nacionales de ECV a este
municipio. Para condiciones de compra, el [simulador](/compra/) ofrece escenarios
hipotéticos, no resultados observados de compradores locales.

[Fuentes y cobertura](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/sources.md) ·
[Método de la ficha](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/municipal_profile.md) ·
[Limitaciones de acceso](/acceso/)

---
*Las fechas de descarga y versiones fijadas se detallan en los paneles de evidencia. Los años de cada indicador se muestran por separado; no constituyen una fotografía del mercado actual.*
