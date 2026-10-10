---
title: Comparar territorios
---

# Comparar territorios

Dos territorios, el mismo periodo y las mismas unidades.
[Panorama nacional](/) · [Detalle por comunidad](/ccaa/) ·
[Grano municipal](/municipios/).
Puedes elegir **Nacional** como referencia.

```sql territorios
select distinct ccaa
from housing.mart_ccaa_anual
order by ccaa
```

```sql anyos
select distinct cast(anyo as integer) as anyo,
       'Año ' || cast(cast(anyo as integer) as varchar) as etiqueta
from housing.mart_ccaa_anual
order by anyo
```

<Dropdown data={territorios} name=territorio_a value=ccaa
  title="Territorio A" order="ccaa asc" defaultValue="Madrid, Comunidad de"/>
<Dropdown data={territorios} name=territorio_b value=ccaa
  title="Territorio B" order="ccaa asc" defaultValue="Comunitat Valenciana"/>
<Dropdown data={anyos} name=desde value=anyo label=etiqueta
  title="Desde" order="anyo asc" defaultValue={2007}/>
<Dropdown data={anyos} name=hasta value=anyo label=etiqueta
  title="Hasta" order="anyo asc" defaultValue={2025}/>

El intervalo incluye ambos extremos. Si inviertes los años, se ordenan
automáticamente; si eliges el mismo territorio dos veces, se muestra una sola serie.

<!-- Trust boundary: territorio/desde/hasta interpolate here, but every value
  originates from a constrained Dropdown populated by distinct mart values —
  never free text. A free-text input must never be interpolated into SQL. -->
```sql comparacion
select ccaa, anyo, ipv_general, viv_por_1000_hab, viv_por_hogar,
       eur_m2_libre, afford_90m2_years, share_20_34, hip_viv_num, pop_source
from housing.mart_ccaa_anual
where ccaa in ('${inputs.territorio_a.value}', '${inputs.territorio_b.value}')
  and anyo between
      least(cast('${inputs.desde.value}' as integer), cast('${inputs.hasta.value}' as integer))
      and greatest(cast('${inputs.desde.value}' as integer), cast('${inputs.hasta.value}' as integer))
order by anyo, ccaa
```

```sql periodo
select min(anyo) as desde, max(anyo) as hasta
from ${comparacion}
```

**Periodo aplicado:** <Value data={periodo} column=desde fmt="0"/>–<Value data={periodo} column=hasta fmt="0"/>.

```sql resumen_periodo
with extremos as (
  select least(cast('${inputs.desde.value}' as integer), cast('${inputs.hasta.value}' as integer)) as desde,
         greatest(cast('${inputs.desde.value}' as integer), cast('${inputs.hasta.value}' as integer)) as hasta
),
base as (
  select lower(replace(replace(ccaa, 'á', 'a'), 'ü', 'u')) as territorio, anyo,
         metrica, valor,
         anyo = (select desde from extremos) as es_desde,
         anyo = (select hasta from extremos) as es_hasta
  from (
    select ccaa, anyo, 'IPV general (índice, 2025 = 100)' as metrica, ipv_general as valor from housing.mart_ccaa_anual
    union all
    select ccaa, anyo, 'Viviendas / 1.000 hab.' as metrica, viv_por_1000_hab as valor from housing.mart_ccaa_anual
    union all
    select ccaa, anyo, 'Viviendas / hogar' as metrica, viv_por_hogar as valor from housing.mart_ccaa_anual
    union all
    select ccaa, anyo, 'Valor tasado (€/m²)' as metrica, eur_m2_libre as valor from housing.mart_ccaa_anual
    union all
    select ccaa, anyo, 'Renta para 90 m² (años)' as metrica, afford_90m2_years as valor from housing.mart_ccaa_anual
    union all
    select ccaa, anyo, 'Cuota 20–34 años' as metrica, share_20_34 as valor from housing.mart_ccaa_anual
    union all
    select ccaa, anyo, 'Hipotecas sobre viviendas' as metrica, hip_viv_num as valor from housing.mart_ccaa_anual
  )
  where ccaa in ('${inputs.territorio_a.value}', '${inputs.territorio_b.value}')
    and anyo in (select desde from extremos union select hasta from extremos)
),
orden as (
  select *, case metrica
    when 'IPV general (índice, 2025 = 100)' then 1
    when 'Viviendas / 1.000 hab.' then 2
    when 'Viviendas / hogar' then 3
    when 'Valor tasado (€/m²)' then 4
    when 'Renta para 90 m² (años)' then 5
    when 'Cuota 20–34 años' then 6
    else 7 end as orden_metrica,
    row_number() over (partition by metrica order by territorio) as orden_territorio
  from (
    select territorio, metrica,
           max(case when es_desde then valor end) as valor_desde,
           max(case when es_hasta then valor end) as valor_hasta
    from base group by territorio, metrica
  )
)
select territorio, metrica, valor_desde, valor_hasta,
       valor_hasta - valor_desde as cambio_absoluto,
       case when valor_desde <> 0 then 100.0 * (valor_hasta - valor_desde) / nullif(valor_desde, 0) end as cambio_pct,
       orden_metrica, orden_territorio
from orden
order by orden_metrica, orden_territorio
```

```sql diferencia_territorios
with a as (
  select * from ${resumen_periodo}
  where territorio = lower(replace(replace('${inputs.territorio_a.value}', 'á', 'a'), 'ü', 'u'))
),
b as (
  select * from ${resumen_periodo}
  where territorio = lower(replace(replace('${inputs.territorio_b.value}', 'á', 'a'), 'ü', 'u'))
)
select a.metrica,
       a.valor_hasta as a_hasta, b.valor_hasta as b_hasta,
       a.valor_hasta - b.valor_hasta as diferencia_a_menos_b,
       a.orden_metrica
from a join b using (metrica)
where a.metrica <> 'IPV general (índice, 2025 = 100)'
order by a.orden_metrica
```

## Resumen del periodo

Cada indicador se calcula solo con **los años extremos seleccionados**: un
guion significa que el dato no existe en ese año concreto, aunque la serie sí
tenga valores intermedios. El cambio en puntos no es un porcentaje salvo en la
cuota joven; el IPV también tiene base 2025 = 100 en cada territorio.
Los cambios que cruzan 2021 mezclan fuentes: los hogares pasan de ECH a
ECP y la población de Padrón a ECP. Esos tramos describen niveles
publicados, no variaciones homogéneas.

<DataTable data={resumen_periodo} rows=20>
  <Column id=territorio title="Territorio"/>
  <Column id=metrica title="Indicador"/>
  <Column id=valor_desde title="Año inicial"/>
  <Column id=valor_hasta title="Año final"/>
  <Column id=cambio_absoluto title="Cambio (puntos)"/>
  <Column id=cambio_pct title="Cambio (%)" fmt="num1"/>
</DataTable>

### Diferencia directa al año final (A − B)

El IPV no entra en esta resta: cada territorio tiene su propia base
2025 = 100, así que una diferencia de puntos de índice entre territorios
no es una brecha de precios. Las hipotecas son recuentos absolutos: su
diferencia refleja también el tamaño de cada territorio.

<DataTable data={diferencia_territorios} rows=20>
  <Column id=metrica title="Indicador"/>
  <Column id=a_hasta title="A al final"/>
  <Column id=b_hasta title="B al final"/>
  <Column id=diferencia_a_menos_b title="A − B"/>
</DataTable>

## Tendencia de precios

El IPV mide evolución, no niveles de precio: cada territorio tiene su propia
base **2025 = 100**. Una línea más alta no significa que comprar allí sea más caro.

<LineChart data={comparacion} x=anyo y=ipv_general series=ccaa
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  title="IPV general (2025 = 100 en cada territorio)"/>

## Stock y hogares

<LineChart data={comparacion} x=anyo y=viv_por_1000_hab series=ccaa
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  title="Viviendas por 1.000 habitantes"/>

```sql hogares_disponibles
select * from ${comparacion}
where exists (select 1 from ${comparacion} where viv_por_hogar is not null)
```

<LineChart data={hogares_disponibles} x=anyo y=viv_por_hogar series=ccaa
  xFmt="0" xAxisTitle="Año" yFmt="num2" handleMissing="gap" markers=true
  emptySet="pass" emptyMessage="Sin datos de viviendas por hogar en el periodo seleccionado (disponibles desde 2021)."
  title="Viviendas por hogar (desde 2021)"/>

## Valor tasado y esfuerzo de renta

El valor tasado (€/m²) permite comparar niveles, pero no es un precio de
compraventa. El esfuerzo expresa años de renta neta del hogar para 90 m²,
sin intereses ni otros costes de adquisición.

<LineChart data={comparacion} x=anyo y=eur_m2_libre series=ccaa
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Valor tasado de vivienda libre (€/m²)"/>

```sql esfuerzo_disponible
select * from ${comparacion}
where exists (select 1 from ${comparacion} where afford_90m2_years is not null)
```

<LineChart data={esfuerzo_disponible} x=anyo y=afford_90m2_years series=ccaa
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  emptySet="pass" emptyMessage="Sin datos de esfuerzo de renta en el periodo seleccionado."
  title="Años de renta neta para 90 m²"/>

## Población joven y crédito

<LineChart data={comparacion} x=anyo y=share_20_34 series=ccaa
  xFmt="0" xAxisTitle="Año" yFmt="pct1" handleMissing="gap" markers=true
  title="Cuota de 20–34 años en la población"/>

<LineChart data={comparacion} x=anyo y=hip_viv_num series=ccaa
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Hipotecas sobre viviendas constituidas"/>

Las hipotecas son recuentos absolutos, no tasas por habitante: el tamaño del
territorio influye en la comparación.

## Datos y cobertura

Un guion indica un dato no disponible, nunca cero. Si una serie no tiene
observaciones para un indicador, no se dibuja; consulta ambas en la tabla.
La población cambia de fuente entre Padrón y ECP. Las relaciones son
descriptivas, no causales.

<DataTable data={comparacion} rows=20>
  <Column id=ccaa title="Territorio"/>
  <Column id=anyo title="Año" fmt="0"/>
  <Column id=ipv_general title="IPV general (2025 = 100)" fmt="num1"/>
  <Column id=viv_por_1000_hab title="Viviendas / 1.000 hab." fmt="num1"/>
  <Column id=viv_por_hogar title="Viviendas / hogar" fmt="num2"/>
  <Column id=eur_m2_libre title="Valor tasado (€/m²)" fmt="num0"/>
  <Column id=afford_90m2_years title="Renta para 90 m² (años)" fmt="num1"/>
  <Column id=share_20_34 title="Cuota de 20–34 años" fmt="pct1"/>
  <Column id=hip_viv_num title="Hipotecas sobre viviendas" fmt="num0"/>
  <Column id=pop_source title="Fuente de población"/>
</DataTable>

---
*Instantánea de datos: 2026-10-09 · cobertura 2007–2025 según el periodo elegido · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
