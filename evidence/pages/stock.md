---
title: Stock físico
---

# Qué vivienda existe y dónde: Sevilla, capitales andaluzas y provincia

Polígonos, fechas constructivas y superficies del Catastro, no solo ratios
regionales. [Acceso](/acceso/) · [Municipios](/municipios/) · [Perfil municipal 2021](/stock-2021/) · [Panorama nacional](/).

```sql fecha_stock
select snapshot_date from stock.snapshot
```

Instantánea municipal INSPIRE BU publicada:
<Value data={fecha_stock} column=snapshot_date/>.
Código catastral **41900**, código INE **41091**: no son intercambiables.
Autor y propietario: Dirección General del Catastro, Ministerio de Hacienda.
Las secciones de capitales y provincia al final usan los mismos proxies
con grano municipal.

## Lectura rápida: físico no significa disponible

Esta página describe el parque físico y compara sus proxies con alquileres de
otro periodo. **Stock declarado ≠ vivienda disponible; correlación ≠ efecto de
oferta.** Las cifras siguientes se calculan con las mismas consultas del
informe reproducible, no se copian a mano.

```sql lectura_stock_renta
select a.variable, a.n as n_sin_ajuste, a.spearman as rho_sin_ajuste,
       i19.n as n_ingreso_2019, i19.distrito_ingreso as rho_ingreso_2019,
       i20.n as n_ingreso_2020, i20.distrito_ingreso as rho_ingreso_2020,
       case when i19.distrito_ingreso is null or i20.distrito_ingreso is null
              then 'Algún ajuste no está definido'
            when a.n <> i19.n or a.n <> i20.n
              then 'Muestras distintas: consulte cobertura'
            else 'Misma muestra; asociación descriptiva' end as lectura
from ${asociaciones_stock_renta} a
left join ${sensibilidad_stock_ingreso} i19 on a.variable = i19.variable and i19.anyo_ingreso = 2019
left join ${sensibilidad_stock_ingreso} i20 on a.variable = i20.variable and i20.anyo_ingreso = 2020
order by case when a.variable = 'Densidad sobre geometría SIM' then 0 else 1 end, a.variable
```

<DataTable data={lectura_stock_renta} rows=3>
  <Column id=variable title="Proxy físico, no oferta disponible"/>
  <Column id=n_sin_ajuste title="Barrios, sin ajuste" fmt="num0"/>
  <Column id=rho_sin_ajuste title="Spearman global, sin ajuste" fmt="num3"/>
  <Column id=n_ingreso_2019 title="Barrios con ingreso de 2019" fmt="num0"/>
  <Column id=rho_ingreso_2019 title="Distrito + ingreso de 2019" fmt="num3"/>
  <Column id=n_ingreso_2020 title="Barrios con ingreso de 2020" fmt="num0"/>
  <Column id=rho_ingreso_2020 title="Distrito + ingreso de 2020" fmt="num3"/>
  <Column id=lectura title="Lectura y cobertura"/>
</DataTable>

Las columnas ajustadas correlacionan **residuos de rangos globales** tras el
ajuste por distrito e ingreso, no cambios de alquiler por unidad de stock.
Cada ajuste se compara con su propia línea base de la misma muestra en el
panel detallado de abajo; los tamaños aquí impiden ocultar pérdidas de barrios.
La fecha ponderada asigna a todo el conteo de inmuebles el año mínimo del
registro BU: **no es la edad observada de cada vivienda**. Se muestran ambas
ponderaciones y ejercicios de ingreso, sin elegir la variante más favorable.

Incluso una asociación positiva entre densidad física y alquiler puede reflejar
ubicación, demanda o composición. No demuestra que añadir vivienda encarezca
el alquiler, ni que el parque existente satisfaga la demanda. La omisión de
distritos prueba sensibilidad geográfica, no significación ni causalidad.

**Siguiente brecha de datos:** stock, hogares y alquiler de fechas y geografías
comparables, junto con evidencia de ocupación y disponibilidad efectiva. Más
controles sobre estas instantáneas no reconstruyen esa información ausente.
La geometría inválida y los registros no asignados permanecen visibles en la
cobertura; no se interpretan como barrios sin vivienda.

## Qué cuenta cada fila

Un registro BU agrupa construcciones de una parcela catastral, potencialmente
con varias huellas y usos. `numberOfDwellings` cuenta inmuebles destinados a
vivienda asociados a esa parcela: **no son hogares, viviendas ocupadas ni
viviendas disponibles**. Los análisis físicos siguientes seleccionan
registros con al menos un inmueble destinado a vivienda, incluidos usos mixtos.

La huella es superficie sobre el terreno; `grossFloorArea` es superficie
bruta construida del registro y puede incluir locales y otros usos. **No
multiplicamos la huella por plantas ni llamamos a la superficie bruta
superficie residencial o tamaño medio de vivienda.** No conocemos la
superficie de cada vivienda a partir de este agregado.

## Cobertura espacial: no esconder lo que no se puede asignar

```sql cobertura_stock
select match_status, count(*) as registros,
       count(dwelling_properties) as registros_con_conteo,
       sum(dwelling_properties) as inmuebles_vivienda,
       sum(case when dwelling_properties > 0 then 1 else 0 end) as registros_con_vivienda
from stock.buildings
group by match_status
order by match_status
```

<DataTable data={cobertura_stock} rows=8>
  <Column id=match_status title="Asignación espacial"/>
  <Column id=registros title="Registros BU" fmt="num0"/>
  <Column id=registros_con_conteo title="Con conteo publicado" fmt="num0"/>
  <Column id=inmuebles_vivienda title="Inmuebles destinados a vivienda" fmt="num0"/>
  <Column id=registros_con_vivienda title="Registros con vivienda" fmt="num0"/>
</DataTable>

Para asignar un registro exigimos que puntos interiores de **todas sus
componentes de huella** pertenezcan de forma única al mismo barrio SIM.
`matched` cumple esta regla; `crosses_barrios`, `partly_outside_barrios`,
`outside_barrios` o `ambiguous` no se reparten ni se fuerzan al barrio más
cercano. Los registros no asignados permanecen en el total municipal.

Esto es una regla de localización por puntos, **no una intersección exacta
ni reparto proporcional**: una componente grande puede cruzar un límite.
Las delimitaciones SIM y el stock catastral tienen vintages distintos. La
asignación espacial no mide acceso a transporte, empleo ni servicios.

```sql stock_barrios
select a.idg, a.barrio, a.distrito, a.area_km2,
       count(b.refcat) as registros_con_vivienda,
       sum(b.dwelling_properties) as inmuebles_vivienda,
       sum(b.dwelling_properties) / nullif(a.area_km2, 0) as vivienda_por_km2,
       sum(b.footprint_m2) / 10000.0 as huella_ha,
       sum(b.gross_floor_m2) / 1000000.0 as superficie_bruta_km2,
       count(b.gross_floor_m2) as registros_con_superficie,
       quantile_disc(b.year_start, 0.5) as mediana_anyo_minimo,
       count(b.year_start) as registros_con_fecha,
       sum(case when b.year_start <> b.year_end then 1 else 0 end) as registros_fechas_distintas,
       a.geometry_quality
from stock.barrios a
left join stock.buildings b on a.idg = b.barrio_id
  and b.match_status = 'matched' and b.dwelling_properties > 0
group by a.idg, a.barrio, a.distrito, a.area_km2, a.geometry_quality
order by a.barrio
```

## Geometría publicada: correcciones y exclusiones explícitas

```sql calidad_geometria_stock
select geometry_quality, count(*) as barrios,
       sum(source_overlap_m2) as solape_componentes_m2
from stock.barrios group by geometry_quality order by geometry_quality
```

<DataTable data={calidad_geometria_stock} rows=4>
  <Column id=geometry_quality title="Calidad de la geometría SIM"/>
  <Column id=barrios title="Barrios" fmt="num0"/>
  <Column id=solape_componentes_m2 title="Área duplicada de componentes, corregida (m²)" fmt="num2"/>
</DataTable>

Las componentes válidas de una misma geometría SIM pueden solaparse: su
**unión explícita** evita contar dos veces el área. No se reparan anillos
inválidos. Un barrio con `invalid_topology` queda sin área ni asignación
espacial y no se dibuja; su identificador y contexto de hogares se conservan.
Los BU sin asignación siguen en los totales municipales. `outside_barrios`
puede incluir registros en geografía excluida, no solo fuera de la ciudad.
La precisión de área usa el sistema métrico original; no mide área en grados.

## Distribución espacial del stock declarado

<AreaMap data={stock_barrios} geoJsonUrl='/geo/sevilla_barrios.geojson'
  geoId='IDG' areaCol=idg value=vivienda_por_km2 valueFmt=num0
  basemap={"https://tile.openstreetmap.org/{z}/{x}/{y}.png"}
  attribution={'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>; DGC + SIM/EMVISESA'}
  title="Inmuebles destinados a vivienda asignados por km² de geometría SIM válida"
  height=520 startingLat=37.39 startingLong=-5.99 startingZoom=12/>

El denominador es el área de la **geometría SIM publicada y validada**, con
solapes internos disueltos. No se ha validado como el área administrativa
completa del barrio ni como suelo residencial. Son unidades catastrales
**asignadas**; no es densidad de residentes ni de hogares. Un
barrio sin registros elegibles asignados conserva valores nulos en lugar
de afirmar que no existe vivienda.

<DataTable data={stock_barrios} rows=12>
  <Column id=barrio title="Barrio SIM"/>
  <Column id=distrito title="Distrito"/>
  <Column id=registros_con_vivienda title="Registros con vivienda" fmt="num0"/>
  <Column id=inmuebles_vivienda title="Inmuebles destinados a vivienda" fmt="num0"/>
  <Column id=vivienda_por_km2 title="Asignados / km² de geometría SIM" fmt="num0"/>
  <Column id=huella_ha title="Huella de esos registros (ha)" fmt="num2"/>
  <Column id=superficie_bruta_km2 title="Superficie bruta, todos sus usos (km²)" fmt="num3"/>
  <Column id=registros_con_superficie title="Con superficie publicada" fmt="num0"/>
  <Column id=mediana_anyo_minimo title="Mediana año mínimo por registro" fmt="0"/>
  <Column id=registros_con_fecha title="Con año mínimo válido" fmt="num0"/>
  <Column id=geometry_quality title="Calidad de geometría"/>
</DataTable>

## Año mínimo del registro: sensibilidad al peso

```sql fechas_stock_ponderadas
with pesos_por_anyo as (
  select barrio_id as idg, year_start, sum(dwelling_properties) as peso
  from stock.buildings
  where match_status = 'matched' and dwelling_properties > 0 and year_start is not null
  group by barrio_id, year_start
), acumulados as (
  select *, sum(peso) over(partition by idg order by year_start
                          rows between unbounded preceding and current row) as peso_acumulado,
            sum(peso) over(partition by idg) as peso_total
  from pesos_por_anyo
)
select idg, min(year_start) filter(where 2*peso_acumulado >= peso_total)
         as mediana_anyo_minimo_ponderada,
       max(peso_total) as inmuebles_con_fecha
from acumulados group by idg
```

```sql stock_fechas_sensibilidad
select s.idg, s.barrio, s.distrito, s.mediana_anyo_minimo,
       f.mediana_anyo_minimo_ponderada, s.registros_con_fecha,
       s.inmuebles_vivienda, coalesce(f.inmuebles_con_fecha,0) as pesos_con_fecha,
       s.inmuebles_vivienda - coalesce(f.inmuebles_con_fecha,0) as pesos_sin_fecha,
       1.0 * coalesce(f.inmuebles_con_fecha,0) / nullif(s.inmuebles_vivienda,0)
         as fraccion_peso_con_fecha
from ${stock_barrios} s left join ${fechas_stock_ponderadas} f on s.idg = f.idg
order by s.barrio
```

<DataTable data={stock_fechas_sensibilidad} rows=12>
  <Column id=barrio title="Barrio SIM"/>
  <Column id=mediana_anyo_minimo title="Mediana mínima, igual peso por BU" fmt="0"/>
  <Column id=mediana_anyo_minimo_ponderada title="Mediana mínima BU, peso por inmuebles" fmt="0"/>
  <Column id=registros_con_fecha title="Registros con fecha" fmt="num0"/>
  <Column id=inmuebles_vivienda title="Inmuebles declarados asignados" fmt="num0"/>
  <Column id=pesos_con_fecha title="Peso incluido en la mediana" fmt="num0"/>
  <Column id=pesos_sin_fecha title="Peso excluido por fecha ausente" fmt="num0"/>
  <Column id=fraccion_peso_con_fecha title="Fracción del peso con fecha" fmt="pct1"/>
</DataTable>

<ScatterPlot data={stock_fechas_sensibilidad} x=mediana_anyo_minimo y=mediana_anyo_minimo_ponderada
  xFmt="0" yFmt="0" xAxisTitle="Año mínimo BU: mediana con igual peso por registro"
  yAxisTitle="Año mínimo BU: mediana ponderada por inmuebles"/>

Ambas medianas usan registros asignados con inmuebles destinados a vivienda y
año mínimo válido. La primera pesa cada BU igual; la segunda usa su conteo
publicado de inmuebles como peso. Es la **mediana discreta inferior**: el primer
año cuya suma acumulada alcanza la mitad del peso, también cuando hay dos años
centrales distintos. No se promedian esos años ni se expanden filas de viviendas.

**Todo el peso hereda el año mínimo del registro BU**, que puede agrupar varias
construcciones y usos mixtos. No sabemos la fecha de cada inmueble ni si la
construcción más antigua era residencial. Por tanto, esto es una sensibilidad
del proxy de fecha del registro, **no una mediana de edad de las viviendas**.
Se excluye el peso de registros sin año válido, sin imputar fechas. Los conteos
nulos o cero no aportan peso ni se convierten en viviendas observadas.

## Fechas constructivas: distribución real de registros, no de viviendas

```sql cohortes_stock
with clasificados as (
  select case when year_start is null then 'Sin año mínimo válido'
              when year_start <= 1940 then 'Hasta 1940'
              when year_start <= 1960 then '1941–1960'
              when year_start <= 1980 then '1961–1980'
              when year_start <= 2000 then '1981–2000'
              when year_start <= 2020 then '2001–2020'
              else '2021 en adelante' end as cohorte,
         case when year_start is null then 7 when year_start <= 1940 then 1
              when year_start <= 1960 then 2 when year_start <= 1980 then 3
              when year_start <= 2000 then 4 when year_start <= 2020 then 5 else 6 end as orden,
         year_start, year_end
  from stock.buildings where dwelling_properties > 0
)
select cohorte, orden, count(*) as registros,
       sum(case when year_start <> year_end then 1 else 0 end) as fechas_distintas
from clasificados group by cohorte, orden order by orden
```

<BarChart data={cohortes_stock} x=cohorte y=registros yFmt="num0"
  title="Registros BU con vivienda por año mínimo de construcción"/>

<DataTable data={cohortes_stock} rows=7>
  <Column id=cohorte title="Año mínimo del registro"/>
  <Column id=registros title="Registros, igual peso" fmt="num0"/>
  <Column id=fechas_distintas title="Año mínimo y máximo distintos" fmt="num0"/>
</DataTable>

Las fechas mínima y máxima representan las construcciones más antigua y
más reciente agrupadas en el registro. **No asignamos esa fecha mínima a
cada vivienda ni la interpretamos como fecha de toda la parcela.** Aquí cada
registro pesa igual; un bloque y una vivienda unifamiliar no representan el
mismo número de viviendas. La distribución incluye registros sin asignación
espacial; no está limitada a la muestra del mapa.

### Contraste: distribución ponderada por unidades catastrales declaradas

Cuando ponderamos por el número de inmuebles declarados con uso residencial
(`dwelling_properties`), la distribución cambia sensiblemente respecto al conteo
de registros BU: las eras de bloques residenciales colectivos (1971–1990) concentran
el 37,9% del parque total, mientras que las construcciones de antes de 1951
representan sólo el 6,7% de los inmuebles pese a constituir el 19,8% de los
registros físicos de parcela.

```sql eras_inmuebles_stock
select case when year_start is null then 'Sin año válido'
            when year_start <= 1950 then 'Hasta 1950'
            when year_start <= 1970 then '1951–1970'
            when year_start <= 1990 then '1971–1990'
            when year_start <= 2010 then '1991–2010'
            else '2011 en adelante' end as era,
       case when year_start is null then 6
            when year_start <= 1950 then 1
            when year_start <= 1970 then 2
            when year_start <= 1990 then 3
            when year_start <= 2010 then 4
            else 5 end as orden,
       count(*) as registros,
       sum(dwelling_properties) as inmuebles,
       1.0 * sum(dwelling_properties) / sum(sum(dwelling_properties)) over () as fraccion_inmuebles
from stock.buildings
where dwelling_properties > 0
group by era, orden
order by orden
```

<BarChart data={eras_inmuebles_stock} x=era y=inmuebles yFmt="num0"
  title="Inmuebles declarados con vivienda por era de construcción BU"/>

<DataTable data={eras_inmuebles_stock} rows=6>
  <Column id=era title="Era constructiva"/>
  <Column id=registros title="Registros BU" fmt="num0"/>
  <Column id=inmuebles title="Inmuebles declarados" fmt="num0"/>
  <Column id=fraccion_inmuebles title="Fracción del parque" fmt="pct1"/>
</DataTable>

```sql calidad_fechas_stock
select date_quality, count(*) as registros,
       sum(case when dwelling_properties > 0 then 1 else 0 end) as con_vivienda
from stock.buildings group by date_quality order by date_quality
```

<DataTable data={calidad_fechas_stock} rows=4>
  <Column id=date_quality title="Calidad de fecha"/>
  <Column id=registros title="Registros BU" fmt="num0"/>
  <Column id=con_vivienda title="Con vivienda" fmt="num0"/>
</DataTable>

Los años ausentes o mal formados se conservan como nulos con bandera; no
los convertimos en cero ni corregimos dígitos por conjetura. La fecha de
alta del registro catastral tampoco se usa como fecha de construcción.

## Superficie construida: separar parcelas pequeñas y grandes conjuntos

```sql superficies_stock
with clasificados as (
  select case when gross_floor_m2 is null then 'Sin superficie publicada'
              when gross_floor_m2 < 200 then 'Menos de 200 m²'
              when gross_floor_m2 < 500 then '200 a menos de 500 m²'
              when gross_floor_m2 < 2000 then '500 a menos de 2.000 m²'
              when gross_floor_m2 < 10000 then '2.000 a menos de 10.000 m²'
              else '10.000 m² o más' end as intervalo,
         case when gross_floor_m2 is null then 6 when gross_floor_m2 < 200 then 1
              when gross_floor_m2 < 500 then 2 when gross_floor_m2 < 2000 then 3
              when gross_floor_m2 < 10000 then 4 else 5 end as orden
  from stock.buildings where dwelling_properties > 0
)
select intervalo, orden, count(*) as registros
from clasificados group by intervalo, orden order by orden
```

<BarChart data={superficies_stock} x=intervalo y=registros yFmt="num0"
  title="Superficie bruta por registro BU con vivienda, todos sus usos"/>

Cada registro pesa igual y puede contener varias viviendas o construcciones.
Esta distribución incluye los registros no asignados a barrios. No es una
distribución de tamaños individuales de vivienda ni de superficie habitable.

## Relacionar stock y demanda sin inventar contemporaneidad

```sql demanda_stock
select s.barrio, s.inmuebles_vivienda,
       h0.hogares as hogares_2015, h1.hogares as hogares_2021,
       h1.hogares - h0.hogares as cambio_hogares_2015_2021
from ${stock_barrios} s
left join housing.sevilla_sim_poblacion_hogares h0 on s.idg = h0.idg and h0.anyo = 2015
left join housing.sevilla_sim_poblacion_hogares h1 on s.idg = h1.idg and h1.anyo = 2021
order by s.barrio
```

<DataTable data={demanda_stock} rows=10>
  <Column id=barrio title="Barrio"/>
  <Column id=inmuebles_vivienda title="Unidades catastrales asignadas, instantánea indicada" fmt="num0"/>
  <Column id=hogares_2015 title="Hogares SIM 2015" fmt="num0"/>
  <Column id=hogares_2021 title="Hogares SIM 2021" fmt="num0"/>
  <Column id=cambio_hogares_2015_2021 title="Cambio neto de hogares, 2015–2021" fmt="num0"/>
</DataTable>

Las columnas muestran contextos de **distintos años y distintas unidades**.
No dividimos el stock actual por hogares antiguos, no estimamos absorción,
ni atribuimos un aumento del stock a construcción reciente. Para una prueba
contemporánea hacen falta hogares y stock de fechas comparables.

## Stock y alquiler: asociación, no explicación

Comparación exploratoria entre la instantánea catastral indicada arriba y
el IPRA de actualización **2022**, que resume contratos **2019–2021**.
El IPRA es alquiler mensual por m² construido, no precio de oferta ni mediana
SERPAVI. Son niveles de distintos vintages, no cambios simultáneos de stock
y alquiler ni una predicción retrospectiva. La selección del stock actual
puede reflejar supervivencia y modificaciones posteriores a los contratos.

```sql stock_renta
with alquiler as (
  select idg, count(*) as filas_alquiler,
         max(barrio) as barrio_alquiler, max(distrito) as distrito_alquiler,
         max(ipra_eur_m2) as ipra_eur_m2
  from housing.barrios_sevilla where anyo = 2022 group by idg
)
select s.*, coalesce(r.filas_alquiler, 0) as filas_alquiler,
       case when r.filas_alquiler = 1 and r.barrio_alquiler = s.barrio
                 and r.distrito_alquiler = s.distrito
            then r.ipra_eur_m2 end as ipra_eur_m2
from ${stock_barrios} s left join alquiler r on s.idg = r.idg
```

```sql cobertura_stock_renta
select count(*) as barrios_contexto,
       count(ipra_eur_m2) as alquiler_validado,
       count(*) filter(where ipra_eur_m2 is not null and vivienda_por_km2 is not null)
         as pares_densidad,
       count(*) filter(where ipra_eur_m2 is not null and mediana_anyo_minimo is not null)
         as pares_fecha,
       count(*) filter(where filas_alquiler > 1) as claves_alquiler_ambiguas
from ${stock_renta}
```

<DataTable data={cobertura_stock_renta} rows=1>
  <Column id=barrios_contexto title="Barrios de contexto" fmt="num0"/>
  <Column id=alquiler_validado title="IPRA con clave y etiquetas validadas" fmt="num0"/>
  <Column id=pares_densidad title="Pares con densidad" fmt="num0"/>
  <Column id=pares_fecha title="Pares con fecha" fmt="num0"/>
  <Column id=claves_alquiler_ambiguas title="Claves IPRA duplicadas, excluidas" fmt="num0"/>
</DataTable>

Solo se acepta una fila IPRA por clave y año, con barrio y distrito iguales
a los de la geometría. Un valor ausente, duplicado o mal etiquetado queda
nulo, sin elegir una observación arbitraria ni multiplicar los pares.

<ScatterPlot data={stock_renta} x=vivienda_por_km2 y=ipra_eur_m2
  xAxisTitle="Asignados / km² de geometría SIM válida"
  yAxisTitle="IPRA 2022, €/m²/mes (contratos 2019–2021)"/>

<ScatterPlot data={stock_renta} x=mediana_anyo_minimo y=ipra_eur_m2
  xFmt="0" xAxisTitle="Mediana de año mínimo por registro BU"
  yAxisTitle="IPRA 2022, €/m²/mes (contratos 2019–2021)"/>

```sql stock_renta_largo
select idg, barrio, distrito, 'Densidad sobre geometría SIM' as variable,
       vivienda_por_km2 as x, ipra_eur_m2 as y
from ${stock_renta} where vivienda_por_km2 is not null and ipra_eur_m2 is not null
union all
select idg, barrio, distrito, 'Mediana del año mínimo' as variable,
       mediana_anyo_minimo as x, ipra_eur_m2 as y
from ${stock_renta} where mediana_anyo_minimo is not null and ipra_eur_m2 is not null
union all
select p.idg, p.barrio, p.distrito, 'Año mínimo BU, peso por inmuebles' as variable,
       f.mediana_anyo_minimo_ponderada as x, p.ipra_eur_m2 as y
from ${stock_renta} p join ${fechas_stock_ponderadas} f on p.idg = f.idg
where f.mediana_anyo_minimo_ponderada is not null and p.ipra_eur_m2 is not null
```

```sql asociaciones_stock_renta
with rangos as (
  select *, rank() over(partition by variable order by x)
              + (count(*) over(partition by variable, x) - 1) / 2.0 as rx,
            rank() over(partition by variable order by y)
              + (count(*) over(partition by variable, y) - 1) / 2.0 as ry
  from ${stock_renta_largo}
), centrados as (
  select *, rx - avg(rx) over(partition by variable, distrito) as dx,
            ry - avg(ry) over(partition by variable, distrito) as dy,
            count(*) over(partition by variable, distrito) as n_distrito
  from rangos
)
select variable, count(*) as n, count(distinct distrito) as distritos,
       count(*) filter(where n_distrito = 1) as barrios_sin_par_distrital,
       case when count(*) > 1 and stddev_pop(x) > 0 and stddev_pop(y) > 0
            then corr(x, y) end as pearson,
       case when count(*) > 1 and stddev_pop(rx) > 0 and stddev_pop(ry) > 0
            then corr(rx, ry) end as spearman,
       case when count(*) > 1 and stddev_pop(dx) > 0 and stddev_pop(dy) > 0
            then corr(dx, dy) end as rangos_centrados_distrito
from centrados group by variable order by variable
```

<DataTable data={asociaciones_stock_renta} rows=3>
  <Column id=variable title="Resumen físico"/>
  <Column id=n title="Barrios completos, igual peso" fmt="num0"/>
  <Column id=distritos title="Distritos" fmt="num0"/>
  <Column id=barrios_sin_par_distrital title="Sin otro barrio del mismo distrito" fmt="num0"/>
  <Column id=pearson title="Pearson global" fmt="num3"/>
  <Column id=spearman title="Spearman global, empates promediados" fmt="num3"/>
  <Column id=rangos_centrados_distrito title="Correlación de rangos centrados por distrito" fmt="num3"/>
</DataTable>

Cada barrio pesa igual. La última columna resta a cada rango **global**
la media de su distrito y correlaciona esos residuos. No es la media de
correlaciones distritales ni un Spearman recalculado dentro de cada distrito.
Los distritos con un solo barrio aportan residuos cero. Sin variación
suficiente se devuelve nulo, no una correlación inventada.

Este centrado elimina diferencias entre medias distritales de los rangos,
pero **no controla ingresos, centralidad dentro del distrito, selección de
contratos ni cambios posteriores**. Tampoco convierte la asociación en
causal: siguen siendo proxies agregados con vintages distintos.

```sql omision_distrito_stock_renta
with distritos as (
  select distinct variable, distrito as distrito_omitido from ${stock_renta_largo}
), muestras as (
  select d.variable, d.distrito_omitido, p.x, p.y
  from distritos d left join ${stock_renta_largo} p
    on d.variable = p.variable and d.distrito_omitido <> p.distrito
), rangos as (
  select *, rank() over(partition by variable, distrito_omitido order by x)
       + (count(*) over(partition by variable, distrito_omitido, x) - 1) / 2.0 as rx,
       rank() over(partition by variable, distrito_omitido order by y)
       + (count(*) over(partition by variable, distrito_omitido, y) - 1) / 2.0 as ry
  from muestras
)
select variable, distrito_omitido, count(x) as n,
       case when count(x) > 1 and stddev_pop(rx) > 0 and stddev_pop(ry) > 0
            then corr(rx, ry) end as spearman
from rangos group by variable, distrito_omitido order by variable, distrito_omitido
```

<DataTable data={omision_distrito_stock_renta} rows=12>
  <Column id=variable title="Resumen físico"/>
  <Column id=distrito_omitido title="Distrito excluido"/>
  <Column id=n title="Barrios restantes" fmt="num0"/>
  <Column id=spearman title="Spearman recalculado sin ese distrito" fmt="num3"/>
</DataTable>

Se recalculan los rangos después de excluir cada distrito. Esta tabla es
una **sensibilidad a la composición geográfica**, no un intervalo de
confianza, prueba de significación ni corrección de confusión espacial.
No añadimos p-valores ni escogemos la especificación que dé más asociación.

Con esta capa se puede investigar composición y localización del stock.
Sigue sin observarse disponibilidad, calidad efectiva, ocupación, ingresos
individuales ni la decisión de ofrecer una vivienda en el mercado.
[Fuentes y controles](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/cadastre_stock.md).

## Sensibilidad a ingresos familiares: misma muestra

Usamos por separado los ingresos familiares declarados de **2019** y **2020**
publicados por el SIM: **renta media neta en euros**, no alquiler, salario bruto
ni ingresos específicos de inquilinos. La agregación a barrio es la del
publicador; los pesos de agregación de secciones no están documentados.
No calculamos medias de secciones ni una tasa de esfuerzo a partir de estos datos.

```sql stock_ingreso_pares
with ingresos as (
  select idg, anyo, count(*) as filas_ingreso, max(barrio) as barrio,
         max(distrito) as distrito, max(renta_neta_eur) as renta_neta_eur
  from income.barrios_income where anyo in (2019,2020) group by idg, anyo
)
select p.*, years.anyo as anyo_ingreso, coalesce(i.filas_ingreso,0) as filas_ingreso,
       case when i.filas_ingreso = 1 and i.barrio = p.barrio and i.distrito = p.distrito
                 and isfinite(i.renta_neta_eur) and i.renta_neta_eur > 0
            then i.renta_neta_eur end as ingreso
from ${stock_renta_largo} p cross join (values (2019),(2020)) years(anyo)
left join ingresos i on p.idg = i.idg and years.anyo = i.anyo
```

```sql cobertura_stock_ingreso
select variable, anyo_ingreso, count(*) as pares_stock_ipra,
       count(ingreso) as completos, count(*) - count(ingreso) as excluidos_ingreso,
       count(*) filter(where filas_ingreso > 1) as claves_ingreso_ambiguas
from ${stock_ingreso_pares} group by variable, anyo_ingreso order by variable, anyo_ingreso
```

<DataTable data={cobertura_stock_ingreso} rows=6>
  <Column id=variable title="Resumen físico"/>
  <Column id=anyo_ingreso title="Ejercicio de ingresos" fmt="0"/>
  <Column id=pares_stock_ipra title="Pares stock–IPRA" fmt="num0"/>
  <Column id=completos title="Con ingreso validado" fmt="num0"/>
  <Column id=excluidos_ingreso title="Excluidos por ingreso" fmt="num0"/>
  <Column id=claves_ingreso_ambiguas title="Claves de ingreso duplicadas" fmt="num0"/>
</DataTable>

```sql sensibilidad_stock_ingreso_todas
with completos as (
  select * from ${stock_ingreso_pares} where ingreso is not null
), distritos as (
  select distinct variable, anyo_ingreso, distrito as distrito_omitido from completos
), muestras as (
  select variable, anyo_ingreso, null::varchar as distrito_omitido, idg, distrito, x, y, ingreso
  from completos
  union all
  select d.variable, d.anyo_ingreso, d.distrito_omitido, p.idg, p.distrito, p.x, p.y, p.ingreso
  from distritos d left join completos p on d.variable = p.variable
    and d.anyo_ingreso = p.anyo_ingreso and d.distrito_omitido <> p.distrito
), rangos as (
  select *, rank() over(partition by variable, anyo_ingreso, distrito_omitido order by x)
       + (count(*) over(partition by variable, anyo_ingreso, distrito_omitido, x) - 1) / 2.0 as rx,
       rank() over(partition by variable, anyo_ingreso, distrito_omitido order by y)
       + (count(*) over(partition by variable, anyo_ingreso, distrito_omitido, y) - 1) / 2.0 as ry,
       rank() over(partition by variable, anyo_ingreso, distrito_omitido order by ingreso)
       + (count(*) over(partition by variable, anyo_ingreso, distrito_omitido, ingreso) - 1) / 2.0 as ri
  from muestras
), centrados as (
  select *, rx - avg(rx) over(partition by variable, anyo_ingreso, distrito_omitido, distrito) as dx,
       ry - avg(ry) over(partition by variable, anyo_ingreso, distrito_omitido, distrito) as dy,
       ri - avg(ri) over(partition by variable, anyo_ingreso, distrito_omitido, distrito) as di
  from rangos
), proyeccion as (
  select *, sum(di*di) over(partition by variable, anyo_ingreso, distrito_omitido) as ii,
       sum(dx*dx) over(partition by variable, anyo_ingreso, distrito_omitido) as xx,
       sum(dy*dy) over(partition by variable, anyo_ingreso, distrito_omitido) as yy,
       sum(dx*di) over(partition by variable, anyo_ingreso, distrito_omitido)
         / nullif(sum(di*di) over(partition by variable, anyo_ingreso, distrito_omitido),0) as bx,
       sum(dy*di) over(partition by variable, anyo_ingreso, distrito_omitido)
         / nullif(sum(di*di) over(partition by variable, anyo_ingreso, distrito_omitido),0) as beta_y
  from centrados
), residuos as (
  select *, dx - bx*di as ex, dy - beta_y*di as ey from proyeccion
)
select variable, anyo_ingreso, distrito_omitido, count(x) as n, count(distinct distrito) as distritos,
       case when stddev_pop(rx)>0 and stddev_pop(ry)>0 then corr(rx,ry) end as spearman_misma_muestra,
       case when stddev_pop(dx)>0 and stddev_pop(dy)>0 then corr(dx,dy) end as distrito_misma_muestra,
       case when max(ii)>0 and sum(ex*ex)>1e-12*max(xx) and sum(ey*ey)>1e-12*max(yy)
            then corr(ex,ey) end as distrito_ingreso,
       case when count(x)=0 then 'Sin barrios completos'
            when max(ii)=0 then 'Sin variación de ingreso intradistrital'
            when sum(ex*ex)<=1e-12*max(xx) or sum(ey*ey)<=1e-12*max(yy)
            then 'Sin variación residual suficiente' else 'Asociación descriptiva' end as estado
from residuos group by variable, anyo_ingreso, distrito_omitido
order by variable, anyo_ingreso, distrito_omitido
```

```sql sensibilidad_stock_ingreso
select variable, anyo_ingreso, n, distritos, spearman_misma_muestra,
       distrito_misma_muestra, distrito_ingreso, estado
from ${sensibilidad_stock_ingreso_todas} where distrito_omitido is null
order by variable, anyo_ingreso
```

<DataTable data={sensibilidad_stock_ingreso} rows=6>
  <Column id=variable title="Resumen físico"/>
  <Column id=anyo_ingreso title="Ejercicio de ingresos" fmt="0"/>
  <Column id=n title="Mismos barrios en las tres columnas" fmt="num0"/>
  <Column id=distritos title="Distritos" fmt="num0"/>
  <Column id=spearman_misma_muestra title="Spearman sin ajuste, misma muestra" fmt="num3"/>
  <Column id=distrito_misma_muestra title="Rangos ajustados por distrito" fmt="num3"/>
  <Column id=distrito_ingreso title="Rangos ajustados por distrito e ingreso" fmt="num3"/>
  <Column id=estado title="Estado del ajuste"/>
</DataTable>

Los rangos **globales**, con empates promediados, se recalculan sobre los
barrios completos de cada variable y ejercicio. Las tres asociaciones de cada
fila usan exactamente esa muestra, con igual peso por barrio. El último ajuste
resta primero las medias distritales de los rangos y proyecta los residuos de
stock y alquiler sobre el rango de ingreso también centrado por distrito.
Correlaciona los residuos finales: no es un Spearman entre residuos reranqueados.
Sin variación de ingreso intradistrital o sin variación residual suficiente,
se devuelve nulo; la tolerancia relativa evita correlaciones de ruido numérico.
Una muestra vacía no genera una asociación.

Mostramos ambos ejercicios sin seleccionar el resultado preferido. **Ajustar
por ingreso no elimina la desalineación temporal**: stock catastral actual,
contratos IPRA 2019–2021 e ingresos de un ejercicio concreto. No identifica
causalidad, disponibilidad, selección de contratos ni calidad/localización
no observada dentro del distrito. Tampoco mide asequibilidad individual.
[Definición y límites del ingreso](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/sevilla_income.md).


### Omitir un distrito y volver a ajustar

```sql omision_distrito_stock_ingreso
select * from ${sensibilidad_stock_ingreso_todas} where distrito_omitido is not null
order by variable, anyo_ingreso, distrito_omitido
```

```sql resumen_omision_stock_ingreso
select variable, anyo_ingreso, count(*) as omisiones,
       count(distrito_ingreso) as omisiones_validas,
       count(*) - count(distrito_ingreso) as omisiones_nulas,
       min(n) as n_minimo, max(n) as n_maximo,
       min(distrito_ingreso) as asociacion_minima,
       max(distrito_ingreso) as asociacion_maxima
from ${omision_distrito_stock_ingreso}
group by variable, anyo_ingreso order by variable, anyo_ingreso
```

<DataTable data={resumen_omision_stock_ingreso} rows=6>
  <Column id=variable title="Resumen físico"/>
  <Column id=anyo_ingreso title="Ejercicio de ingresos" fmt="0"/>
  <Column id=omisiones title="Distritos omitidos" fmt="num0"/>
  <Column id=omisiones_validas title="Ajustes definidos" fmt="num0"/>
  <Column id=omisiones_nulas title="Ajustes nulos, no ceros" fmt="num0"/>
  <Column id=n_minimo title="Mínimo de barrios restantes" fmt="num0"/>
  <Column id=n_maximo title="Máximo de barrios restantes" fmt="num0"/>
  <Column id=asociacion_minima title="Mínimo al omitir un distrito" fmt="num3"/>
  <Column id=asociacion_maxima title="Máximo al omitir un distrito" fmt="num3"/>
</DataTable>

Se excluye cada distrito presente en la muestra completa de ese ejercicio y
variable. Se **recalculan los rangos y se vuelve a ajustar** por distrito e
ingreso sobre los barrios restantes, con la misma definición que en la muestra
completa. No se reutilizan rangos, medias ni coeficientes del ajuste original.
Las omisiones vacías conservan una fila con n cero y asociación nula; los
ajustes degenerados también permanecen nulos, sin convertirlos en cero.
El rango mostrado usa solo ajustes definidos y muestra cuántos quedaron nulos.

**Son extremos descriptivos de sensibilidad geográfica, no intervalos de
confianza, pruebas de significación ni identificación causal.** Conservar el
signo al omitir distritos no elimina confusión dentro de ellos, selección de
contratos o la desalineación temporal.

<DataTable data={omision_distrito_stock_ingreso} rows=12>
  <Column id=variable title="Resumen físico"/>
  <Column id=anyo_ingreso title="Ejercicio de ingresos" fmt="0"/>
  <Column id=distrito_omitido title="Distrito excluido"/>
  <Column id=n title="Barrios restantes" fmt="num0"/>
  <Column id=distritos title="Distritos restantes" fmt="num0"/>
  <Column id=distrito_ingreso title="Asociación reajustada tras omisión" fmt="num3"/>
  <Column id=estado title="Estado del ajuste"/>
</DataTable>

## Capitales andaluzas: la misma forma de era

El piloto se extiende a Málaga, Granada y Córdoba en grano municipal, con
la misma definición de era ponderada por inmuebles. Las cuatro capitales
comparten el pico de 1971–1990; Granada el más acusado.

```sql capitales_eras
select ciudad, era, sum(inmuebles) as inmuebles
from stock_capitals.eras_municipales
group by ciudad, era
```

<BarChart data={capitales_eras} x=era y=inmuebles series=ciudad
  title="Inmuebles declarados por era y capital"/>

```sql capitales_totales
select ciudad, registros, inmuebles, registros_asignados
from stock_capitals.totales
```

<DataTable data={capitales_totales} rows=4>
  <Column id=ciudad title="Capital"/>
  <Column id=registros title="Registros BU" fmt="num0"/>
  <Column id=inmuebles title="Inmuebles declarados" fmt="num0"/>
  <Column id=registros_asignados title="Registros con barrio/distrito" fmt="num0"/>
</DataTable>

Málaga aporta desglose por barrio (419 oficiales) y Granada por distrito
(8 oficiales, geometría ED50 reproyectada); Córdoba permanece municipal
hasta disponer de geometrías con licencia. Grano municipal en todos los
casos salvo esos desgloses; mismas cautelas de proxy que en Sevilla.

## Provincia de Sevilla: el pico llega una generación después

Los 106 municipios suman 891.374 inmuebles declarados; la capital
concentra el 36,7%. En el conjunto provincial domina la expansión de
1991–2010, no el boom de 1971–1990 de las capitales.

```sql provincia_eras
select ambito, era, sum(inmuebles) as inmuebles
from stock_province.eras_capital_resto
group by ambito, era
```

<BarChart data={provincia_eras} x=era y=inmuebles series=ambito
  title="Capital frente al resto de la provincia por era"/>

```sql provincia_top
select municipio, registros, inmuebles
from stock_province.totales limit 10
```

<DataTable data={provincia_top} rows=10>
  <Column id=municipio title="Municipio"/>
  <Column id=registros title="Registros BU" fmt="num0"/>
  <Column id=inmuebles title="Inmuebles declarados" fmt="num0"/>
</DataTable>

Perfil por municipio disponible en la exploración provincial; grano
municipal en toda la provincia.
