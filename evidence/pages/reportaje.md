---
title: Más viviendas; más hogares todavía
---

# Más viviendas; más hogares todavía

**España no tiene una sola crisis de vivienda.** Entre 2007 y 2013, los precios cayeron mientras el parque por habitante crecía. Desde 2021, el parque también crece, pero los hogares lo hacen más deprisa. Y detrás de la media nacional conviven territorios con menos viviendas por habitante y otros con más stock no principal.

La pregunta no es solo cuántas viviendas hay. Es **dónde están, quién puede usarlas y qué hogares las necesitan**. Los datos disponibles describen el desajuste; no permiten calcular cuántas casas habría que construir ni cuánto bajarían los precios.

*Una investigación interactiva sobre precios, población y vivienda en España, 2001–2025. [Explora las fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md) · [Consulta el panorama completo](/).*

**El recorrido:** el desplome tras la burbuja, las diferencias territoriales y el crecimiento de hogares desde 2021. Después, qué añaden el registro fiscal y los datos sobre costes de vivienda.

## 1. Tras la burbuja, el parque crecía y los precios se hundieron

Entre 2007 y 2013, el índice de precios de vivienda (IPV) cayó alrededor de un 36%. A la vez, el parque modelado por habitante pasó de 532 a 544 viviendas por cada mil personas. No es una paradoja: contar viviendas no dice dónde están, si se pueden ocupar o quién puede pagarlas.

```sql ciclo_nacional
select anyo, ipv_general, viv_por_1000_hab, hip_viv_num
from housing.mart_ccaa_anual
where ccaa = 'Nacional' and anyo between 2007 and 2025
order by anyo
```

<LineChart data={ciclo_nacional} x=anyo y=ipv_general
  xFmt="0" xAxisTitle="Año" yFmt="num0" markers=true handleMissing="gap"
  title="Precio de la vivienda: IPV nacional (2025 = 100)" />

<LineChart data={ciclo_nacional} x=anyo y=viv_por_1000_hab
  xFmt="0" xAxisTitle="Año" yFmt="num0" markers=true handleMissing="gap"
  title="Viviendas por cada 1.000 habitantes" />

El crédito también se desplomó: las hipotecas constituidas sobre viviendas pasaron de 1,238,890 en 2007 a 199,703 en 2013. Ese movimiento coincide con el cambio de precios, pero el recuento no mide las condiciones del préstamo ni demuestra cuánto causó el crédito. La fotografía censal de 2011 registró 768k viviendas construidas entre 2002 y 2011 que estaban vacías entonces. El excedente localizado puede coexistir con falta de vivienda en otros lugares. Fuentes: IPV, INE; parque modelado, MIVAU; hipotecas constituidas, INE; vacancia por antigüedad, Censo de Viviendas 2011.

> **Lo que sí sabemos:** el stock nacional por habitante no cayó durante el desplome. **Lo que no sabemos con esta comparación:** cuánto pesó el crédito frente a la localización, la calidad, el empleo o la demanda.

## 2. La media nacional esconde dos mapas distintos

Viviendas por habitante y evolución de precios no cuentan la misma historia en todas partes. Madrid y Cataluña parten de un menor stock modelado por habitante; Galicia presenta más vivienda vacía en la medición censal de 2021. Ese contraste es una pista para investigar, no una clasificación de territorios con “demasiadas” o “demasiadas pocas” casas.

```sql geografia
select ccaa, anyo, viv_por_1000_hab, ipv_general
from housing.mart_ccaa_anual
where ccaa in ('Madrid, Comunidad de', 'Cataluña', 'Galicia', 'Nacional')
  and anyo in (2007, 2013, 2021, 2025)
order by ccaa, anyo
```

```sql stock_geo
select ccaa, anyo, viv_por_1000_hab
from housing.mart_ccaa_anual
where ccaa in ('Madrid, Comunidad de', 'Cataluña', 'Galicia', 'Nacional')
  and anyo between 2007 and 2025
order by anyo, ccaa
```

<LineChart data={stock_geo} x=anyo y=viv_por_1000_hab series=ccaa
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="La vivienda por habitante diverge entre comunidades" />

```sql vac_municipios
select codigo, municipio, vac_pct, vac_pct as "Vacía (%)"
from housing.vacancy_municipal
order by vac_pct desc
```

<AreaMap
  data={vac_municipios}
  geoJsonUrl='/geo/municipios.geojson'
  geoId='CODIGOINE'
  areaCol=codigo
  value={'Vacía (%)'}
  valueFmt=num1
  basemap={'https://tile.openstreetmap.org/{z}/{x}/{y}.png'}
  attribution='© OpenStreetMap'
  title="Vivienda clasificada como vacía por consumo eléctrico, Censo 2021 (%)"
  height=560
  startingLat=40.2
  startingLong=-3.7
  startingZoom=6
/>

El mapa lleva el contraste al territorio municipal, pero retrata una sola medición de 2021: el indicador identifica baja ocupación según consumo eléctrico, no viviendas habitables, disponibles o asequibles. Los registros agregados como «Resto de la provincia» no corresponden a un municipio cartografiable y no aparecen en el mapa. Galicia registra 28,8% y Madrid 6,3%; la diferencia es una invitación a investigar, no un inventario de oferta movilizable. Fuente: INE, Censo 2021; [definición y comparación autonómica](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/ratio_ccaa.md). Los precios del IPV solo están disponibles aquí a nivel autonómico, no provincial. [Explora el mapa y sus datos completos](/vacancia/).

<DataTable data={geografia} rows=20>
  <Column id=ccaa title="Territorio" />
  <Column id=anyo title="Año" fmt="0" />
  <Column id=viv_por_1000_hab title="Viviendas / 1.000 habitantes" fmt="num1" />
  <Column id=ipv_general title="IPV (2025 = 100)" fmt="num1" />
</DataTable>

Para explorar ciudades y barrios —con fuentes y coberturas distintas— consulta [municipios](/municipios/) y [vacancia](/vacancia/). No extrapolamos el dato autonómico a sus municipios.

## 3. Desde 2021, los hogares crecen más deprisa que el parque

```sql balance_nacional
select
  max(viviendas_total) filter (where anyo = 2024)
    - max(viviendas_total) filter (where anyo = 2020) as parque_neto,
  max(hogares) filter (where anyo = 2025)
    - max(hogares) filter (where anyo = 2021) as hogares_netos
from housing.mart_ccaa_anual
where ccaa = 'Nacional' and anyo between 2020 and 2025
```

Durante los años de actividad 2021–2024, el parque modelado aumentó en
<Value data={balance_nacional} column=parque_neto fmt="num0"/> viviendas netas;
los hogares ECP aumentaron en <Value data={balance_nacional} column=hogares_netos fmt="num0"/>.
En todas las comunidades, las adiciones netas de parque fueron menores que el aumento neto de hogares.

**Las fechas importan:** el parque se mide al 31 de diciembre y los hogares al
1 de enero. Para comparar la actividad de 2021–2024, restamos parque al cierre
de 2020 del parque al cierre de 2024, y hogares al inicio de 2021 de los hogares
al inicio de 2025. Son límites de año correspondientes, no la misma fecha exacta.
Comparar las etiquetas 2021 y 2025 de ambas fuentes describiría intervalos distintos.
La [referencia oficial del parque](https://www.ine.es/dyngs/IOE/fichaProg.htm?cid=1259946014126)
y el [explorador de déficit](/deficit/) documentan esta convención y la ventana ampliada.

Esto es un cambio de ritmo descriptivo, no una estimación causal. Las cifras comparan **variaciones netas** —no viviendas construidas y hogares recién formados— y el parque incluye segundas residencias y viviendas vacías. La serie de hogares cambia de fuente y método en torno a 2021; usamos solo hogares ECP desde ese inicio, sin restar hogares ECH de 2020. Las revisiones y anclajes censales del parque siguen limitando la lectura de sus cambios.

```sql aportes_anuales
with niveles as (
  select anyo, viviendas_total, hogares
  from housing.mart_ccaa_anual
  where ccaa = 'Nacional' and anyo between 2020 and 2025
), cambios as (
  select a.anyo,
         s1.viviendas_total - s0.viviendas_total as parque_neto,
         h1.hogares - h0.hogares as hogares_netos
  from range(2021, 2025) a(anyo)
  left join niveles s0 on s0.anyo = a.anyo - 1
  left join niveles s1 on s1.anyo = a.anyo
  left join niveles h0 on h0.anyo = a.anyo
  left join niveles h1 on h1.anyo = a.anyo + 1
)
select anyo, 'Parque modelado (neto)' as serie, parque_neto as unidades from cambios
union all
select anyo, 'Hogares ECP (neto)' as serie, hogares_netos as unidades from cambios
order by anyo, serie
```

<BarChart data={aportes_anuales} x=anyo y=unidades series=serie
  xFmt="0" xAxisTitle="Año de actividad" yFmt="num0"
  title="Cambios por año de actividad: hogares y parque neto" />

Cada barra de parque compara cierres de diciembre; cada barra de hogares,
inicios de enero que delimitan el año indicado. No son viviendas terminadas
frente a hogares que buscan casa. Si falta un extremo anual, el cambio queda
vacío, sin saltar a otro año. La primera variación de hogares usa enero de
2021 y enero de 2022, ambos ECP.

```sql cobertura_ccaa
with extremos as (
  select ccaa,
         max(viviendas_total) filter (where anyo = 2020) as parque_inicial,
         max(viviendas_total) filter (where anyo = 2024) as parque_final,
         max(hogares) filter (where anyo = 2021) as hogares_iniciales,
         max(hogares) filter (where anyo = 2025) as hogares_finales
  from housing.mart_ccaa_anual
  where anyo in (2020, 2021, 2024, 2025)
  group by ccaa
), cambios as (
  select ccaa, parque_final - parque_inicial as parque_neto,
         hogares_finales - hogares_iniciales as hogares_netos
  from extremos
  where parque_inicial > 0 and parque_final > 0
    and hogares_iniciales > 0 and hogares_finales > 0
)
select ccaa, parque_neto, hogares_netos,
       round(parque_neto / nullif(hogares_netos, 0), 2) as viv_por_hogar_neto
from cambios
where ccaa != 'Nacional' and hogares_netos > 0
order by viv_por_hogar_neto
```

<BarChart data={cobertura_ccaa} x=ccaa y=viv_por_hogar_neto swapXY
  yFmt="num2" title="Parque neto por aumento neto de hogares · actividad 2021–2024" />

Solo se muestran comunidades con ambos extremos completos y positivos y crecimiento neto de hogares positivo; no se interpolan datos ausentes. Con estos límites de año, en cada comunidad el cociente queda por debajo de una vivienda neta por hogar neto. No es una cuota de hogares sin casa: combina dos cambios agregados, y el parque incluye unidades no principales. El [comparador territorial](/comparar/) permite revisar y descargar las series; la cifra no identifica el efecto de construir más.

```sql cierre
select h.anyo, s.anyo as anyo_parque, s.viviendas_total, h.hogares,
       s.viviendas_total * 1.0 / nullif(h.hogares, 0) as viv_por_hogar
from housing.mart_ccaa_anual h
left join housing.mart_ccaa_anual s
  on s.ccaa = h.ccaa and s.anyo = h.anyo - 1
where h.ccaa = 'Nacional' and h.anyo between 2021 and 2025
order by h.anyo
```

<LineChart data={cierre} x=anyo y=viv_por_hogar
  xFmt="0" xAxisTitle="Año de los hogares (1 de enero)" yFmt="num2" markers=true handleMissing="gap"
  title="Parque al cierre del año anterior / hogares ECP al inicio del año" />

La caída de viviendas por hogar después de 2021 refuerza la pregunta sobre disponibilidad, pero el cociente cuenta todo el parque. No dice qué unidades son habitables, dónde se encuentran ni si son asequibles. El gráfico empieza con hogares ECP de enero de 2021 y parque de diciembre de 2020: cada punto usa límites de año correspondientes, no el cociente de dos etiquetas anuales iguales. No se unen fuentes distintas de hogares. En las [series históricas](/), el valor de 2001 es un proxy y 2020–2021 no es un salto anual homogéneo.

**[¿Por qué hay distintas cifras de déficit?](/deficit/)** Compara las restas, sus fechas y la cobertura de viviendas terminadas.

## Lo que el registro fiscal aclara —y lo que no

El censo de consumo eléctrico señala viviendas con baja ocupación; otra fuente oficial permite mirar el uso declarado por personas físicas. En 2024, la estadística de la AEAT basada en el IRPF clasificó las viviendas declaradas en el territorio fiscal común como habituales, arrendadas en algún momento del ejercicio o a disposición de sus titulares. Esta última categoría suele incluir segundas residencias, pero también puede incluir viviendas vacías: **no equivale a oferta disponible**.

```sql aeat_usos
with base as (
  select sum(n_total) as total,
         sum(n_habitual) as habitual,
         sum(n_arrendadas) as arrendadas,
         sum(n_disposicion) as disposicion
  from housing.aeat_viviendas_uso
  where anyo = 2024 and grano in ('provincia', 'ccaa_uniprovincial')
)
select 'Habitual' as uso, 100.0 * habitual / total as porcentaje from base
union all
select 'Arrendada en algún momento del año', 100.0 * arrendadas / total from base
union all
select 'A disposición del titular', 100.0 * disposicion / total from base
```

<BarChart data={aeat_usos} x=uso y=porcentaje swapXY
  yFmt="num1" title="Uso declarado de viviendas de personas físicas, 2024 (%)" />

<DataTable data={aeat_usos} rows=3>
  <Column id=uso title="Uso declarado" />
  <Column id=porcentaje title="Porcentaje del total" fmt="num2" />
</DataTable>

La cobertura excluye País Vasco, Navarra, Ceuta y Melilla; los totales se calculan sumando las filas de provincia y comunidad uniprovincial para no duplicar territorios. La unidad publicada es una vivienda equivalente, ponderada por titularidad y días de uso: no es un recuento simple de unidades físicas únicas. El uso fiscal tampoco equivale a ocupación efectiva; “arrendada” puede incluir alquiler de temporada o turístico, mientras “a disposición” no separa segunda vivienda y vacancia. La fuente mejora la descripción de la composición del parque, pero no cuenta casas actualmente habitables, disponibles y asequibles donde crecen los hogares. [Metodología y cobertura AEAT](https://sede.agenciatributaria.gob.es/Sede/estadisticas/estadisticas-impuesto/estadistica-viviendas-declaradas-irpf/metodologia/preguntas-frecuentes.html).

## ¿Quién soporta el coste?

Contar viviendas no basta para describir el acceso. Eurostat mide el porcentaje de personas que viven en hogares donde los costes de vivienda, netos de ayudas, superan el 40% de la renta disponible también neta de ayudas. Incluye suministros, mantenimiento e intereses hipotecarios; excluye la amortización del préstamo. Fuente: [Eurostat, tabla ilc_lvho07b](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07b/default/table) y [definición oficial](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:Housing_cost_overburden_rate).

```sql carga_por_renta
select group_code, group_label, survey_year, rate_pct, status
from access.overburden
where breakdown = 'income'
  and survey_year = (
    select max(survey_year) from access.overburden
    where breakdown = 'income' and rate_pct is not null
  )
order by group_code
```

<BarChart data={carga_por_renta} x=group_label y=rate_pct swapXY
  yFmt="num1" title="Personas en hogares con sobrecarga de vivienda, por grupo de ingresos (%)" />

<DataTable data={carga_por_renta} rows=10>
  <Column id=group_label title="Grupo de ingresos (incluye total)" />
  <Column id=survey_year title="Año de encuesta" fmt="0" />
  <Column id=rate_pct title="Personas en hogares sobrecargados (%)" fmt="num1" />
  <Column id=status title="Bandera de calidad" />
</DataTable>

Último año de encuesta con dato publicado: <Value data={carga_por_renta} column=survey_year fmt="0"/>. Es un indicador nacional por **personas**, no por hogares; los quintiles son de renta disponible equivalente. El año de encuesta se conserva (los ingresos suelen referirse al año anterior). Las celdas y banderas publicadas se conservan: un dato ausente no es cero y no se rellena con otro año. El total nacional no es un quintil. Las diferencias no son pruebas de significación estadística. La encuesta no identifica la carga local ni mide a hogares que no llegaron a formarse. [Definición, cobertura y desglose por tenencia y edad](/acceso/).

Por eso estos datos **no permiten afirmar** que construir una cantidad determinada reduciría los precios en una cantidad concreta. Tampoco permiten concluir que movilizar el stock no principal bastaría. Sí muestran por qué una cifra agregada de viviendas no resuelve por sí sola la pregunta de acceso.

### Qué evidencia cambiaría esta lectura

La hipótesis de escasez de oferta utilizable se debilitaría si, en las mismas zonas y años donde crecen los hogares y la carga económica, los datos mostrasen que aumenta al mismo ritmo la vivienda habitable que realmente se ofrece a precios accesibles. Para estimar efectos sobre precios haría falta, además, comparar mercados semejantes con cambios de oferta distintos, comprobar tendencias previas y medir crédito e ingresos. Esta investigación no dispone de esa combinación de datos ni identifica ese efecto.

### Cómo leer esta investigación

- El IPV es un índice de precios, no euros por metro cuadrado; no se empalman bases incompatibles.
- El valor tasado en euros no es el precio de compraventa.
- Padrón, ECH, ECP y Censo Anual tienen alcances y metodologías distintos; los cambios de fuente se señalan, no se ocultan.
- Vivienda no principal y vacancia eléctrica no son sinónimos de oferta disponible.
- Las correlaciones, tendencias y comparaciones descritas no identifican efectos causales.

[Fuentes, definiciones y cobertura](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/sources.md) · [Métodos y limitaciones](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md) · [Descargar y explorar datos](/comparar/) · [Análisis de acceso](/acceso/) · [Busca tu municipio](/perfil/).

---
*Instantánea de datos: 2026-10-09. Las comunidades y provincias no son unidades intercambiables; cada cifra conserva su geografía, año y fuente.*
