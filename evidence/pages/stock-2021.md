---
title: Stock y hogares 2021
---

# Sevilla municipal: stock, hogares y alquiler con referencia 2021

[Stock físico por barrios](/stock/) · [Municipios](/municipios/) · [Acceso](/acceso/)

Una alternativa **municipal**, separada del piloto catastral actual por barrios.
Usa viviendas y hogares del Censo con referencia al **1 de enero de 2021**, y
alquiler declarado de **todo el ejercicio fiscal 2021**. Mismo año de referencia
no significa la misma fecha exacta ni una muestra de contratos equivalente.
El contexto de uso eléctrico corresponde a **2020**, no a disponibilidad actual.
No se añade una regresión, reconstrucción histórica del BU ni efecto causal.

```sql cobertura_alineada
select count(*) as municipios_contexto, count(hogares) as hogares_publicados,
       count(viviendas) as stock_validado, count(renta_vc) as alquiler_validado,
       count(*) filter(where perfil_completo) as perfiles_completos,
       count(*) filter(where estado_stock='duplicate' or estado_renta='duplicate') as claves_ambiguas,
       count(*) filter(where estado_stock='label_mismatch' or estado_renta='label_mismatch') as etiquetas_incompatibles
from alignment.perfiles
```

<DataTable data={cobertura_alineada} rows=1>
  <Column id=municipios_contexto title="Municipios del censo de hogares" fmt="num0"/>
  <Column id=hogares_publicados title="Con hogares publicados" fmt="num0"/>
  <Column id=stock_validado title="Con stock nominal validado" fmt="num0"/>
  <Column id=alquiler_validado title="Con alquiler VC validado" fmt="num0"/>
  <Column id=perfiles_completos title="Con los tres datos" fmt="num0"/>
  <Column id=claves_ambiguas title="Claves duplicadas, excluidas" fmt="num0"/>
  <Column id=etiquetas_incompatibles title="Etiquetas incompatibles, excluidas" fmt="num0"/>
</DataTable>

Se conserva el universo municipal del censo de hogares, no solo la muestra con
alquiler. La unión exige código INE, provincia, ejercicio y medida correctos,
una fila por clave y etiquetas municipales compatibles. Un dato ausente,
duplicado o incompatible permanece nulo; **no es cero ni un municipio sin vivienda**.

## Qué geografía cubre la muestra de alquiler

```sql seleccion_alineada
with universo as (
    select count(*) as n, count(hogares) as n_hogares,
           sum(hogares) as hogares_total
    from alignment.perfiles
), grupos as (
    select true as con_renta, 'Con alquiler VC validado' as grupo
    union all select false, 'Sin alquiler VC validado'
), resumen as (
    select g.con_renta, g.grupo, count(p.codigo) as municipios,
           count(p.hogares) as municipios_hogares,
           case when count(p.codigo)=0 then 0 else sum(p.hogares) end as hogares_publicados,
           count(p.viviendas) as municipios_stock
    from grupos g left join alignment.perfiles p
      on (p.renta_vc is not null)=g.con_renta
    group by g.con_renta, g.grupo
)
select r.grupo, r.municipios,
       r.municipios*1.0/nullif(u.n,0) as cuota_municipios,
       r.municipios_hogares, r.hogares_publicados,
       case when u.n>0 and u.n_hogares=u.n and u.hogares_total>0
            then r.hogares_publicados*1.0/u.hogares_total end as cuota_hogares,
       r.municipios_stock,
       case when u.n=0 then 'sin_universo'
            when u.n_hogares<u.n then 'denominador_incompleto'
            when u.hogares_total=0 then 'denominador_cero'
            else 'completo' end as estado_cuota_hogares
from resumen r cross join universo u
order by r.con_renta desc
```

<DataTable data={seleccion_alineada} rows=2>
  <Column id=grupo title="Disponibilidad del dato de alquiler"/>
  <Column id=municipios title="Municipios" fmt="num0"/>
  <Column id=cuota_municipios title="Cuota del universo municipal" fmt="pct1"/>
  <Column id=municipios_hogares title="Municipios con hogares publicados" fmt="num0"/>
  <Column id=hogares_publicados title="Suma de hogares publicados" fmt="num0"/>
  <Column id=cuota_hogares title="Cuota de hogares: universo completo" fmt="pct1"/>
  <Column id=municipios_stock title="Municipios con stock individual" fmt="num0"/>
  <Column id=estado_cuota_hogares title="Estado del denominador de hogares"/>
</DataTable>

Contar municipios y localizar hogares son dos lecturas distintas de la cobertura.
La suma incluye **hogares de todas las tenencias**, no solo arrendatarios.
La cuota de hogares solo se calcula si todos los municipios tienen un recuento
publicado y el total es positivo. Si faltan recuentos, la suma es parcial y la
cuota permanece nula; un grupo sin municipios sí tiene una suma conocida de cero.

**Esta cuota no mide cobertura de contratos ni de hogares arrendatarios**, ni
garantiza representatividad de las viviendas VC. No se ponderan medianas de renta
con estos hogares para estimar un alquiler provincial, ni se imputan alquileres
a municipios sin dato. La falta de stock individual se cuenta aparte, sin
repartir `Resto de Sevilla`.

## Tenencia: contexto limitado a cuatro ciudades

```sql tenencia_alineada
select * from alignment.tenencia_contexto order by codigo
```

<DataTable data={tenencia_alineada} rows=4>
  <Column id=codigo title="Código INE"/>
  <Column id=municipio title="Municipio publicado"/>
  <Column id=principales title="Viviendas principales convencionales, enero 2021" fmt="num0"/>
  <Column id=propiedad title="En propiedad" fmt="num0"/>
  <Column id=alquiler title="En alquiler, unidad vivienda" fmt="num0"/>
  <Column id=otro title="Otro régimen" fmt="num0"/>
  <Column id=estado title="Completitud de celdas publicadas"/>
</DataTable>

Fuente: [INE, tabla censal 59529](https://www.ine.es/jaxi/Tabla.htm?tpx=59529&L=0).
Su publicación municipal se limita a capitales y municipios de más de 50.000
habitantes: en Sevilla aparecen estas cuatro ciudades. Las demás no tienen
un cero de alquiler; **no están cubiertas por esta tabla**.

Son **viviendas familiares principales convencionales**, no hogares ni contratos.
El alquiler censal abarca tipologías fuera de las VC de SERPAVI. No se usa este
recuento como denominador de la muestra provincial, ni se extrapola a los
municipios restantes. Un dato no publicado permanece nulo; una celda publicada
como cero sí conserva ese cero.

La tenencia combina registros tributarios y de titularidad con **imputación
basada en frecuencias de la ECEPOV** ([metodología censal, páginas 85–86](https://www.ine.es/censos2021/censos2021_meto.pdf)).
Una tabla censal y la encuesta no son dos comprobaciones independientes.
`celdas_completas` significa que están publicados los cuatro recuentos, **no que
todos se hayan observado directamente**. La clasificación describe tenencia,
no vivienda habitable o disponible para alquilar hoy.

## Capital: no confundir ciudad y provincia

```sql capital_alineada
select * from alignment.perfiles where codigo='41091'
```

<DataTable data={capital_alineada} rows=1>
  <Column id=codigo title="Código INE municipal"/>
  <Column id=municipio title="Municipio"/>
  <Column id=hogares title="Hogares censales, enero 2021" fmt="num0"/>
  <Column id=viviendas title="Viviendas censales, enero 2021" fmt="num0"/>
  <Column id=vacias_consumo title="Vacías por consumo de 2020" fmt="num0"/>
  <Column id=renta_vc title="Mediana SERPAVI VC, 2021 €/m²/mes" fmt="num2"/>
</DataTable>

El código identifica Sevilla ciudad, aunque algunos capítulos usan la etiqueta
`Sevilla (ciudad)`. No se utiliza un agregado provincial también llamado Sevilla.
Los hogares son **hogares censales publicados**, no población dividida por un
tamaño supuesto, viviendas principales ni familias fiscales.

## Perfiles municipales y datos que faltan

```sql perfiles_alineados
select * from alignment.perfiles order by municipio
```

<DataTable data={perfiles_alineados} rows=12>
  <Column id=codigo title="Código INE"/>
  <Column id=municipio title="Municipio censal"/>
  <Column id=hogares title="Hogares, enero 2021" fmt="num0"/>
  <Column id=viviendas title="Stock nominal, enero 2021" fmt="num0"/>
  <Column id=vacias_consumo title="Vacías según consumo de 2020" fmt="num0"/>
  <Column id=renta_vc title="SERPAVI VC 2021, €/m²/mes" fmt="num2"/>
  <Column id=estado_stock title="Estado de la unión de stock"/>
  <Column id=estado_renta title="Estado de la unión de alquiler"/>
</DataTable>

**El stock censal no es oferta disponible:** su definición puede incluir viviendas
construidas como tales que ahora se utilizan como oficinas u otros locales.
No se resta este stock del BU actual para inferir construcción o demolición.
La tipología **VC de SERPAVI** no cubre todas las viviendas alquiladas y no es
el concepto censal de establecimientos colectivos. No se suman categorías
anidadas de hogares o consumo eléctrico ni se rellena el alquiler no publicado.

La clasificación de vacías usa ausencia de contrato eléctrico o consumo muy
bajo según el umbral municipal. No demuestra habitabilidad, voluntad de
alquilar, acceso legal, precio aceptable ni disponibilidad efectiva. El consumo
anual de la pandemia es distinto de ocupación o disponibilidad actuales.

## Agregados que no se reparten

```sql agregados_alineados
select * from alignment.agregados_excluidos order by fuente,codigo,medida
```

<DataTable data={agregados_alineados} rows=8>
  <Column id=fuente title="Fuente"/>
  <Column id=codigo title="Código de agregado"/>
  <Column id=municipio title="Ámbito agregado, no municipio"/>
  <Column id=medida title="Medida publicada"/>
  <Column id=valor_publicado title="Valor publicado sin repartir"/>
</DataTable>

`Resto de Sevilla` se mantiene aparte. No se reparte entre municipios pequeños
por área, población, hogares o huellas catastrales actuales. La falta de stock
individual y la falta de alquiler son pérdidas de cobertura distintas.

Este perfil mejora la coherencia del año de referencia, **no resuelve causalidad,
selección de contratos, vivienda no apta o demanda no satisfecha**. Los valores
son descripciones municipales, no un déficit/excedente de viviendas utilizables.

[Fuentes, fechas y reproducción](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/stock_alignment.md).

---
*Instantánea de datos: 2026-10-09 · Censo 2021 (1-ene-2021), alquiler fiscal 2021, consumo eléctrico 2020 · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/stock_alignment.md).*
