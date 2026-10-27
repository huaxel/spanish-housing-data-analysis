---
title: Comparar municipios
---

# Dos municipios, los mismos años

Compara una medida cada vez, con la **misma fuente, definición y años
publicados para ambos municipios**. Los años no compartidos se muestran como
huecos, no se rellenan ni se ocultan en la cobertura. Esto no empareja viviendas
u hogares equivalentes: composición, ubicación y muestras pueden diferir.
No es un ranking de asequibilidad ni una estimación causal.

[Tu municipio](/perfil/) · [Comparar comunidades](/comparar/) ·
[Municipios y ciudades](/municipios/) · [Stock y acceso](/acceso/)

```sql municipios_comparables
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

<Dropdown data={municipios_comparables} name=municipio_a value=codigo label=etiqueta
  title="Municipio A (nombre, provincia o código)" defaultValue="28079" />
<Dropdown data={municipios_comparables} name=municipio_b value=codigo label=etiqueta
  title="Municipio B (nombre, provincia o código)" defaultValue="08019" />

```sql metricas_comparables
select 'alquiler' as metrica, 'Alquiler mediano SERPAVI' as etiqueta,
       '€/m²/mes nominales' as unidad, 'MIVAU · SERPAVI · vivienda colectiva' as fuente,
       'Diferencia en €/m²/mes, no variación porcentual' as unidad_diferencia
union all
select 'ingresos', 'Renta neta media del hogar ADRH', '€/hogar/año nominales',
       'INE · ADRH · todos los hogares', 'Diferencia en €/hogar/año, no variación porcentual'
union all
select 'proxy', 'Alquiler / renta (proxy revisado)', '% de renta anual media',
       'SERPAVI + ADRH · cruce revisado', 'Diferencia en puntos porcentuales, no cambio porcentual'
```

<Dropdown data={metricas_comparables} name=metrica_municipal value=metrica label=etiqueta
  title="Medida (misma definición para A y B)" defaultValue="alquiler" />

```sql base_comparacion
select codigo, anyo, 'alquiler' as metrica, eur_m2_mes as valor from housing.perfil_alquiler
union all
select codigo, anyo, 'ingresos', renta_neta_hogar from profile_income.municipal
union all
select codigo, anyo, 'proxy', ratio_pct from access.rent_income
```

```sql anyos_comparables
select distinct cast(anyo as integer) as anyo,
       cast(cast(anyo as integer) as varchar) as etiqueta
from ${base_comparacion}
order by anyo
```

<Dropdown data={anyos_comparables} name=desde_municipal value=anyo label=etiqueta
  title="Desde (incluido)" order="anyo asc" defaultValue={2015} />
<Dropdown data={anyos_comparables} name=hasta_municipal value=anyo label=etiqueta
  title="Hasta (incluido)" order="anyo asc" defaultValue={2023} />

Si inviertes los años, se ordenan. No cambiamos la ventana a los últimos datos
de cada municipio: elegir un año sin publicación de una fuente produce un
hueco explícito. Elegir el mismo municipio dos veces muestra una sola serie
y no calcula una diferencia entre mercados. Los nombres son etiquetas;
**las uniones usan códigos INE**. No se armonizan cambios de límites,
fusiones o segregaciones históricas. Los agregados Resto no son seleccionables.

```sql seleccion_comparable
select 'A' as lado, codigo, municipio, provincia, fuente_nombre
from ${municipios_comparables} where codigo = '${inputs.municipio_a.value}'
union all
select 'B', codigo, municipio, provincia, fuente_nombre
from ${municipios_comparables} where codigo = '${inputs.municipio_b.value}'
```

<DataTable data={seleccion_comparable} rows=2>
  <Column id=lado title="Selección" />
  <Column id=municipio title="Municipio" />
  <Column id=provincia title="Provincia" />
  <Column id=codigo title="Código INE" />
  <Column id=fuente_nombre title="Fuente del nombre" />
</DataTable>

```sql medida_aplicada
select * from ${metricas_comparables}
where metrica = '${inputs.metrica_municipal.value}'
```

<DataTable data={medida_aplicada} rows=1>
  <Column id=etiqueta title="Medida activa" />
  <Column id=unidad title="Unidad de los valores" />
  <Column id=fuente title="Fuente para ambos municipios" />
  <Column id=unidad_diferencia title="Cómo leer A − B" />
</DataTable>

## Los años comunes y los que quedan fuera

```sql calendario_comparable
with limites as (
  select least(cast('${inputs.desde_municipal.value}' as integer), cast('${inputs.hasta_municipal.value}' as integer)) as desde,
         greatest(cast('${inputs.desde_municipal.value}' as integer), cast('${inputs.hasta_municipal.value}' as integer)) as hasta
), calendario as (
  select a.anyo from limites l, range(l.desde, l.hasta + 1) a(anyo)
), pares as (
  select c.anyo, a.valor as valor_a, b.valor as valor_b
  from calendario c
  left join ${base_comparacion} a
    on a.anyo = c.anyo and a.codigo = '${inputs.municipio_a.value}'
    and a.metrica = '${inputs.metrica_municipal.value}'
  left join ${base_comparacion} b
    on b.anyo = c.anyo and b.codigo = '${inputs.municipio_b.value}'
    and b.metrica = '${inputs.metrica_municipal.value}'
)
select *, valor_a is not null and valor_b is not null as comun,
       case when valor_a is null and valor_b is null then 'Sin dato para ambos'
            when valor_a is null then 'Solo B: excluido del gráfico'
            when valor_b is null then 'Solo A: excluido del gráfico'
            when '${inputs.municipio_a.value}' = '${inputs.municipio_b.value}' then 'Mismo municipio: una serie'
            else 'Año común: incluido' end as estado,
       case when valor_a is not null and valor_b is not null
             and '${inputs.municipio_a.value}' <> '${inputs.municipio_b.value}'
            then valor_a - valor_b end as diferencia_a_menos_b
from pares
order by anyo
```

```sql cobertura_comparable
select min(anyo) as desde, max(anyo) as hasta, count(*) as anyos_solicitados,
       count(valor_a) as anyos_a, count(valor_b) as anyos_b,
       count(*) filter (where comun) as anyos_comunes,
       count(*) filter (where not comun) as anyos_excluidos,
       string_agg(cast(cast(anyo as integer) as varchar), ', ' order by anyo) filter (where comun) as lista_comunes,
       case when count(*) filter (where comun) = 0 then 'Sin años comunes: no hay comparación'
            when '${inputs.municipio_a.value}' = '${inputs.municipio_b.value}' then 'Mismo municipio: sin contraste A − B'
            else 'Comparación descriptiva en años comunes' end as estado
from ${calendario_comparable}
```

<DataTable data={cobertura_comparable} rows=1>
  <Column id=desde title="Desde aplicado" fmt="0" />
  <Column id=hasta title="Hasta aplicado" fmt="0" />
  <Column id=anyos_solicitados title="Años solicitados" fmt="num0" />
  <Column id=anyos_a title="Con dato en A" fmt="num0" />
  <Column id=anyos_b title="Con dato en B" fmt="num0" />
  <Column id=anyos_comunes title="Comunes" fmt="num0" />
  <Column id=anyos_excluidos title="Excluidos del gráfico" fmt="num0" />
  <Column id=lista_comunes title="Años comunes exactos (puede haber huecos)" />
  <Column id=estado title="Estado de la comparación" />
</DataTable>

Los ceros publicados cuentan como datos; **un dato ausente no es cero**.
No tratamos el intervalo entre el primer y último dato común como una serie
completa: la lista muestra los años exactos. La muestra de años comunes puede
cambiar al cambiar de medida. Con pocos años comunes no se describe una
trayectoria completa; sin años comunes no se calcula una diferencia.

```sql serie_comun
with pares as (select * from ${calendario_comparable}), elegidos as (
  select * from ${seleccion_comparable}
  where lado = 'A' or '${inputs.municipio_a.value}' <> '${inputs.municipio_b.value}'
)
select p.anyo, e.lado, e.codigo, e.municipio,
       e.lado || ' · ' || e.municipio || ' · ' || e.codigo as serie,
       m.metrica, m.unidad,
       case when p.comun then case when e.lado = 'A' then p.valor_a else p.valor_b end end as valor
from pares p cross join elegidos e cross join ${medida_aplicada} m
order by p.anyo, e.lado
```

<LineChart data={serie_comun} x=anyo y=valor series=serie
  xFmt="0" yFmt="num2" xAxisTitle="Año de la medida" handleMissing="gap" markers=true
  title="La misma medida en los años publicados para ambos municipios" />

<EvidencePanel data={serie_comun} chart="comparar-municipios-serie"
  columns={["metrica", "unidad", "anyo", "lado", "codigo", "municipio", "serie", "valor"]}
  files={["data/raw/serpavi_bd.xlsx", "data/raw/adrh_renta_municipal.csv"]}
  definition="Valores de la medida activa en los mismos años para A y B; los demás años se conservan como huecos."
  coverage="Fuentes posibles del selector: SERPAVI y ADRH; la unidad y fuente activas se muestran arriba. El proxy solo usa el cruce ya revisado, no ingresos independientes para rellenarlo. Misma definición no implica muestras de hogares o viviendas equivalentes." />

<DataTable data={calendario_comparable} rows=14>
  <Column id=anyo title="Año solicitado" fmt="0" />
  <Column id=valor_a title="Dato publicado A" fmt="num2" />
  <Column id=valor_b title="Dato publicado B" fmt="num2" />
  <Column id=estado title="Cobertura del año" />
  <Column id=diferencia_a_menos_b title="A − B (unidad indicada arriba)" fmt="num2" />
</DataTable>

Esta tabla conserva también los datos individuales de años excluidos. En el
gráfico y su descarga ambos valores quedan nulos cuando falta uno, para no
comparar trayectorias construidas con años distintos. No se interpolan huecos,
no se calculan cambios entre extremos sustitutos y no se produce una media
que cambie silenciosamente de muestra. A − B es una diferencia de niveles
del mismo año, no un efecto causal, una prueba estadística ni un ranking.

## Contexto censal: una instantánea separada

```sql contexto_comparable
with contexto as (
  select e.lado, c.poblacion, c.viviendas, c.hogares, c.secciones_suprimidas, v.vac_pct
  from ${seleccion_comparable} e
  left join housing.perfil_censo c on c.codigo = e.codigo
  left join housing.vacancy_municipal v on v.codigo = e.codigo
), filas as (
  select lado, 1 as orden, 'Población censal' as indicador, 'Personas' as unidad, poblacion as valor,
         case when poblacion is null then 'Sin dato en esta fuente' else 'Dato publicado' end as estado
  from contexto
  union all
  select lado, 2, 'Viviendas censales', 'Viviendas', viviendas,
         case when viviendas is not null then 'Dato publicado' when secciones_suprimidas > 0 then 'No mostrado: secciones suprimidas' else 'Sin dato en esta fuente' end
  from contexto
  union all
  select lado, 3, 'Hogares censales', 'Hogares', hogares,
         case when hogares is not null then 'Dato publicado' when secciones_suprimidas > 0 then 'No mostrado: secciones suprimidas' else 'Sin dato en esta fuente' end
  from contexto
  union all
  select lado, 4, 'Vacancia eléctrica', '% del parque censal', vac_pct,
         case when vac_pct is null then 'Sin dato en esta fuente' else 'Dato publicado' end
  from contexto
)
select orden, indicador, unidad, 2021 as anyo_censo,
       max(valor) filter (where lado='A') as valor_a,
       max(valor) filter (where lado='B') as valor_b,
       max(estado) filter (where lado='A') as estado_a,
       max(estado) filter (where lado='B') as estado_b
from filas group by orden, indicador, unidad
order by orden
```

<DataTable data={contexto_comparable} rows=4>
  <Column id=indicador title="Contexto histórico" />
  <Column id=anyo_censo title="Año censal" fmt="0" />
  <Column id=unidad title="Unidad" />
  <Column id=valor_a title="A" fmt="num2" />
  <Column id=estado_a title="Estado A" />
  <Column id=valor_b title="B" fmt="num2" />
  <Column id=estado_b title="Estado B" />
</DataTable>

Población, viviendas y hogares son del Censo al inicio de 2021; la vacancia
eléctrica usa consumo de 2020. No son series anuales ni contexto actual
actualizado con los selectores de mercado. Se retienen las supresiones de
secciones, sin publicar sumas parciales como totales. La vacancia no mide
habitabilidad ni oferta disponible. No dividimos alquiler reciente entre
hogares antiguos ni deducimos necesidades de construcción de estas cifras.

## Límites que siguen importando

- SERPAVI describe la tipología de vivienda colectiva declarada fiscalmente,
  no todas las ofertas ni viviendas idénticas. El número y composición de
  contratos de los dos municipios pueden diferir.
- ADRH es renta neta media de todos los hogares, no renta de inquilinos,
  mediana ni una distribución de cargas. En municipios pequeños puede llevar
  sustituciones comarcales o provinciales del publicador sin bandera por fila;
  aquí no se añaden sustituciones ni se identifican las filas afectadas.
- El proxy es el cruce revisado del mismo año; no se recalcula con ingresos
  independientes y **no es una tasa de sobrecarga**.
- Los importes son nominales; comparar años no equivale a comparar poder
  adquisitivo real. No se añaden precios de tasación o de oferta de otras
  fuentes como si fueran el mismo precio de compraventa.
- Coincidir en código, año y definición no armoniza límites históricos ni
  controla composición, centralidad o demanda. Esta herramienta compara
  publicaciones compatibles, no mercados causalmente emparejados.

[Método y cobertura](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/municipal_profile.md#matched-municipality-comparison) ·
[Fuentes](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/sources.md)
