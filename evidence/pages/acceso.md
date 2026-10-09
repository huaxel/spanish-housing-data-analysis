---
title: Acceso a la vivienda
---

# Stock no es acceso

¿Dónde se estrecha el acceso, qué hogares soportan el coste y qué parte del
stock puede utilizarse? Madrid, Barcelona y la costa valenciana muestran
por qué estas preguntas no se resuelven contando viviendas.
[Panorama nacional](/) · [Municipios](/municipios/) · [Alquiler](/renta/) · [Vacancia](/vacancia/) · [Escenarios de compra](/compra/) · [Incertidumbre](/incertidumbre/).

Esta página combina **indicadores descriptivos**, no estima causas ni el
número de viviendas que habría que construir o movilizar. Provincias,
comunidades y municipios se presentan por separado; no representan el mismo
mercado ni se agregan sus precios o medianas.

## Stock provincial: total y uso principal

```sql stock_acceso
select provincia, anyo, viviendas_total, viviendas_principales,
       round(100.0 * viviendas_no_principales / nullif(viviendas_total, 0), 2) as no_principal_pct,
       round(viv_por_hogar, 3) as viv_por_hogar
from housing.mart_provincia_anual
where cpro in ('28', '08', '03', '12', '46') and anyo in (2021, 2025)
order by provincia, anyo
```

<DataTable data={stock_acceso} rows=10>
  <Column id=provincia title="Provincia"/>
  <Column id=anyo title="Año" fmt="0"/>
  <Column id=viviendas_total title="Stock total" fmt="num0"/>
  <Column id=viviendas_principales title="Stock principal modelado" fmt="num0"/>
  <Column id=no_principal_pct title="No principal (%)" fmt="num2"/>
  <Column id=viv_por_hogar title="Total / hogar" fmt="num3"/>
</DataTable>

Fuente: MIVAU parque modelado + hogares ECP. No principal incluye usos
secundarios y vivienda vacía; **no equivale a oferta disponible**. El stock
principal mide uso, no anuncios ni viviendas accesibles para un hogar nuevo.
No restamos vivienda turística: registros turísticos y clasificaciones de
uso no son conjuntos mutuamente excluyentes.

## Vivienda vacía: una instantánea municipal, no oferta inmediata

```sql vacancia_acceso
select codigo, municipio, 2021 as anyo, vac_pct
from housing.vacancy_municipal
where codigo in ('28079', '08019', '08101', '08015', '08245',
                 '46250', '03014', '03031', '03063', '03133')
order by codigo
```

<DataTable data={vacancia_acceso} rows=10>
  <Column id=codigo title="Código INE"/>
  <Column id=municipio title="Municipio"/>
  <Column id=anyo title="Año" fmt="0"/>
  <Column id=vac_pct title="Vacía por consumo eléctrico (%)" fmt="num2"/>
</DataTable>

Fuente: Censo 2021. Consumo bajo no informa sobre habitabilidad, situación
legal, voluntad del propietario, localización respecto al empleo o coste
de rehabilitación. No extrapolamos esta instantánea al stock actual ni la
comparamos como cambio con la clasificación censal anterior. Una celda
ausente es falta de cobertura, no vacancia nula.

## Coste de compra regional: una referencia, no un presupuesto familiar

```sql compra_acceso
select ccaa, anyo as anyo_precio_renta,
       round(eur_m2_libre, 0) as eur_m2_libre,
       round(renta_hogar_neta, 0) as renta_hogar_neta,
       round(afford_90m2_years, 2) as afford_90m2_years
from housing.mart_ccaa_anual
where ccaa in ('Madrid, Comunidad de', 'Cataluña', 'Comunitat Valenciana')
  and anyo = 2024
order by ccaa
```

<DataTable data={compra_acceso} rows=3>
  <Column id=ccaa title="Comunidad (no ciudad)"/>
  <Column id=anyo_precio_renta title="Año económico" fmt="0"/>
  <Column id=eur_m2_libre title="Valor tasado (€/m²)" fmt="num0"/>
  <Column id=renta_hogar_neta title="Renta neta media anual (€)" fmt="num0"/>
  <Column id=afford_90m2_years title="90 m² / renta anual (años)" fmt="num2"/>
</DataTable>

La renta ECV se alinea con el año de ingresos, no con el de encuesta.
Es un cociente de medias para una vivienda de referencia: no mide entrada,
intereses, impuestos ni la carga real de compradores primerizos. No usamos
la renta regional como si fuera la renta de cada municipio.

## Barcelona: esfuerzo medio, no distribución de hogares

```sql cargas_acceso
select municipio, anyo, rent_burden, mortgage_burden
from housing.muni_bcn
where anyo = 2022 and municipio in
  ('Barcelona', 'Badalona', 'Santa Coloma de Gramenet', 'Sant Adrià de Besòs')
order by municipio
```

<DataTable data={cargas_acceso} rows=4>
  <Column id=municipio title="Municipio"/>
  <Column id=anyo title="Año" fmt="0"/>
  <Column id=rent_burden title="Esfuerzo alquiler DIBA (%)" fmt="num1"/>
  <Column id=mortgage_burden title="Esfuerzo nueva hipoteca DIBA (%)" fmt="num1"/>
</DataTable>

Fuente: DIBA; cocientes de costes e ingresos brutos medios. Son indicadores
de esfuerzo de mercado, **no porcentajes de hogares sobrecargados** ni la
media observada de cargas individuales. No se actualizan con precios de
otro año. No disponemos aquí de una distribución por edad e ingresos ni
de indicadores equivalentes para Madrid y la costa valenciana.

Los alquileres de nuevos contratos depositados en INCASÒL y los alquileres
declarados fiscalmente en SERPAVI corresponden a poblaciones distintas.
No tratamos ninguna serie como el coste de una nueva oferta para todos los
hogares, ni como la carga de todos los inquilinos con contratos en vigor.

## España: sobrecarga por ingresos, tenencia y edad

Ahora sí medimos una distribución: porcentaje de **personas que viven en
hogares** cuyos costes totales de vivienda, netos de ayudas, superan el
40% de la renta disponible, también neta de ayudas. Incluye suministros,
mantenimiento e intereses hipotecarios; no incluye amortización de capital.
No es el porcentaje de hogares ni el esfuerzo DIBA anterior.

```sql periodo_sobrecarga
select max(survey_year) as encuesta_anyo
from access.overburden
where rate_pct is not null
```

Último año de encuesta publicado con observaciones:
<Value data={periodo_sobrecarga} column=encuesta_anyo fmt="0"/>.
Conservamos el año de encuesta de Eurostat; los ingresos se refieren en
general al año anterior. No desplazamos toda la tasa al año de ingresos ni
la juntamos con el precio municipal contemporáneo.

```sql sobrecarga_acceso
select breakdown, group_code, group_label, survey_year, rate_pct, status
from access.overburden
where survey_year = (select max(survey_year) from access.overburden where rate_pct is not null)
order by breakdown, group_code
```

```sql sobrecarga_ingresos
select * from ${sobrecarga_acceso} where breakdown = 'income'
```

### Por quintil de ingresos

<DataTable data={sobrecarga_ingresos} rows=6>
  <Column id=group_label title="Quintil (etiqueta Eurostat)"/>
  <Column id=survey_year title="Encuesta" fmt="0"/>
  <Column id=rate_pct title="Personas en hogares sobrecargados (%)" fmt="num1"/>
  <Column id=status title="Bandera de calidad"/>
</DataTable>

El primer quintil corresponde a menores ingresos; el último a mayores.
La renta es disponible equivalente del hogar. No promediamos quintiles para
reconstruir el total: utilizamos el total publicado.

```sql sobrecarga_tenencia
select * from ${sobrecarga_acceso} where breakdown = 'tenure'
```

### Por régimen de tenencia

<DataTable data={sobrecarga_tenencia} rows=5>
  <Column id=group_label title="Tenencia (etiqueta Eurostat)"/>
  <Column id=survey_year title="Encuesta" fmt="0"/>
  <Column id=rate_pct title="Personas en hogares sobrecargados (%)" fmt="num1"/>
  <Column id=status title="Bandera de calidad"/>
</DataTable>

Alquiler de mercado y alquiler reducido/gratuito son categorías distintas.
Propietarios con préstamo no representan compradores primerizos: la
amortización del capital no forma parte del coste utilizado en esta tasa.

```sql sobrecarga_edad
select * from ${sobrecarga_acceso} where breakdown = 'age'
```

### Por edad de la persona, no de quien encabeza el hogar

<DataTable data={sobrecarga_edad} rows=5>
  <Column id=group_label title="Edad (etiqueta Eurostat)"/>
  <Column id=survey_year title="Encuesta" fmt="0"/>
  <Column id=rate_pct title="Personas en hogares sobrecargados (%)" fmt="num1"/>
  <Column id=status title="Bandera de calidad"/>
</DataTable>

Incluye a jóvenes que viven con sus padres. Una carga medida baja no implica
facilidad para emanciparse; no mide a los hogares que no llegaron a formarse.
Los grupos de edad se solapan (adultos y subgrupos jóvenes): no se suman.

Son **tres desgloses marginales nacionales**, no una tabla conjunta de
jóvenes inquilinos de bajos ingresos ni evidencia local de Madrid, Barcelona
o la costa valenciana. Los errores muestrales no se publican en estos
extractos; no calificamos las diferencias como estadísticamente significativas.
Las celdas ausentes quedan nulas. Conservamos las banderas de Eurostat:
`b` indica ruptura de serie; otras banderas se mantienen sin borrarlas.
No completamos una categoría con un año anterior cuando falta en el último.

### Cruce publicado: edad × situación respecto al umbral de pobreza

```sql sobrecarga_edad_pobreza
select age_code, age_label, poverty_code, poverty_label, survey_year, rate_pct, status
from access.overburden_age_poverty
where survey_year = (select max(survey_year) from access.overburden where rate_pct is not null)
order by age_code, poverty_code
```

<DataTable data={sobrecarga_edad_pobreza} rows=10>
  <Column id=age_label title="Edad de la persona (Eurostat)"/>
  <Column id=poverty_label title="Situación respecto al umbral (Eurostat)"/>
  <Column id=survey_year title="Encuesta del cruce" fmt="0"/>
  <Column id=rate_pct title="Tasa dentro de cada grupo (%)" fmt="num1"/>
  <Column id=status title="Calidad del cruce"/>
</DataTable>

Son **celdas conjuntas publicadas directamente**, con sexo total, no una
intersección calculada a partir de los tres desgloses anteriores. El umbral
es el 60% de la mediana nacional de renta disponible equivalente tras
transferencias sociales ([definición Eurostat](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:At-risk-of-poverty_rate)).
No es el primer quintil ni una medida absoluta de pobreza.

El denominador son las **personas de cada combinación de edad y situación**,
no toda la población: la tasa no es la proporción nacional simultáneamente
pobre y sobrecargada. Incluye todas las tenencias y jóvenes que viven con sus
padres. **No identifica jóvenes inquilinos de bajos ingresos**, hogares que
no llegaron a formarse ni condiciones municipales. La renta interviene tanto
en la clasificación como en el denominador de la carga: una diferencia de
tasas no identifica un efecto causal ni diferencias en costes monetarios.
Los grupos de edad se solapan; no se suman ni promedian para obtener un total.

Usamos el mismo último año de encuesta que los marginales, sin rellenar
celdas del cruce con años anteriores. Nulos y banderas se conservan; estas
celdas tampoco proporcionan intervalos muestrales ni pruebas de significación.
El cruce parcial no completa edad × quintil × tenencia ni aporta datos locales.

Fuentes: Eurostat EU-SILC
[ingresos](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07b/default/table),
[tenencia](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07c/default/table),
[edad](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07a/default/table) y
[definición del indicador](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:Housing_cost_overburden_rate).

## Cruce propio ECV: edad × pobreza × tenencia

**Estimación descriptiva propia con microdatos anonimizados INE**, no una
nueva tabla publicada por Eurostat. España, personas en hogares privados;
no representa Madrid, Barcelona, Sevilla ni municipios costeros. El cruce es
por situación respecto al umbral de pobreza, **no por quintiles**.

### Comparación entre edades: alquiler de mercado

Estas son todas las combinaciones no solapadas de edad y pobreza para personas
que viven en hogares de **alquiler a precio de mercado**. La tabla no selecciona
los resultados más altos ni recalcula las tasas; reutiliza las mismas celdas
revisadas del selector. Incluye menores y mayores para no ocultar el contexto.

```sql ecv_comparacion_renta
select survey_year, income_year, age_code, age_label, poverty_code, poverty_label,
       rate_pct, sample_valid_persons, sample_valid_households,
       weighted_missing_cost_loss_pct,
       case status when 'available' then 'Estimación descriptiva disponible'
         when 'empty' then 'Sin personas en la muestra de esta combinación'
         when 'no_valid_cost' then 'Sin costes válidos'
         else 'Tasa no mostrada: muestra o cobertura insuficiente' end as estado,
       nullif(suppression_reasons, '') as motivos
from ecv.joint_burden
where tenure_code = 'RENT_MKT' and age_code <> 'TOTAL' and poverty_code <> 'TOTAL'
order by case age_code when 'Y_LT18' then 0 when 'Y18-24' then 1
  when 'Y25-29' then 2 when 'Y30-64' then 3 else 4 end,
  case poverty_code when 'B_60' then 0 else 1 end
```

<DataTable data={ecv_comparacion_renta} rows=10>
  <Column id=age_label title="Edad en hogares de alquiler de mercado"/>
  <Column id=poverty_label title="Situación respecto al umbral"/>
  <Column id=survey_year title="Encuesta" fmt="0"/>
  <Column id=income_year title="Año de ingresos" fmt="0"/>
  <Column id=rate_pct title="Carga en alquiler de mercado (%)" fmt="num1"/>
  <Column id=sample_valid_persons title="Personas válidas: muestra" fmt="num0"/>
  <Column id=sample_valid_households title="Hogares representados válidos" fmt="num0"/>
  <Column id=weighted_missing_cost_loss_pct title="Peso excluido por coste ausente (%)" fmt="num2"/>
  <Column id=estado title="Estado"/>
  <Column id=motivos title="Motivos de ocultación"/>
</DataTable>

**No es un efecto de la edad ni una comparación causal de alquileres**. La renta
clasifica la pobreza y también entra en el denominador de la carga, por lo que
la asociación tiene un componente mecánico. Las personas comparten hogar y
sus resultados no son independientes. No hay intervalos de diseño ni pruebas
para declarar significativas las diferencias. Las tasas ocultas siguen nulas,
no se imputan ni se reconstruyen. Para los denominadores completos y las marcas
de imputación de cada celda, usa el selector siguiente.

### Detalle y cobertura de una combinación

```sql ecv_edades
select distinct age_code, age_label from ecv.joint_burden
order by case age_code when 'TOTAL' then 0 when 'Y_LT18' then 1
  when 'Y18-24' then 2 when 'Y25-29' then 3 when 'Y30-64' then 4 else 5 end
```

```sql ecv_pobreza
select distinct poverty_code, poverty_label from ecv.joint_burden
order by case poverty_code when 'TOTAL' then 0 when 'B_60' then 1 else 2 end
```

```sql ecv_tenencias
select distinct tenure_code, tenure_label from ecv.joint_burden
order by case tenure_code when 'TOTAL' then 0 when 'RENT_MKT' then 1
  when 'RENT_FR' then 2 when 'OWN_L' then 3 else 4 end
```

<Dropdown data={ecv_edades} name=ecv_edad value=age_label
  title="Edad de la persona (fin del año de ingresos)" defaultValue="18–24 años"/>
<Dropdown data={ecv_pobreza} name=ecv_pobreza_sel value=poverty_label
  title="Situación respecto al umbral nacional" defaultValue="Por debajo del umbral de pobreza"/>
<Dropdown data={ecv_tenencias} name=ecv_tenencia value=tenure_label
  title="Régimen del hogar" defaultValue="Alquiler a precio de mercado"/>

```sql ecv_cruce_seleccionado
select *, case status when 'available' then 'Estimación descriptiva disponible'
  when 'empty' then 'Sin personas en la muestra de esta combinación'
  when 'no_valid_cost' then 'Sin costes válidos'
  when 'marginal_not_published' then 'Tasa no publicada: total solapado'
  else 'Tasa no mostrada: muestra o cobertura insuficiente' end as estado,
  nullif(suppression_reasons, '') as motivos
from ecv.joint_burden
where age_label = '${inputs.ecv_edad.value}'
  and poverty_label = '${inputs.ecv_pobreza_sel.value}'
  and tenure_label = '${inputs.ecv_tenencia.value}'
```

<DataTable data={ecv_cruce_seleccionado} rows=1>
  <Column id=survey_year title="Encuesta" fmt="0"/>
  <Column id=income_year title="Año de ingresos" fmt="0"/>
  <Column id=rate_pct title="Personas sobrecargadas dentro del grupo (%)" fmt="num1"/>
  <Column id=estado title="Estado"/>
  <Column id=motivos title="Motivos de ocultación"/>
</DataTable>

<DataTable data={ecv_cruce_seleccionado} rows=1>
  <Column id=sample_target_persons title="Personas de la muestra: grupo" fmt="num0"/>
  <Column id=sample_valid_persons title="Personas con coste válido" fmt="num0"/>
  <Column id=sample_valid_households title="Hogares distintos representados con coste válido" fmt="num0"/>
  <Column id=weighted_target_persons title="Personas ponderadas: grupo" fmt="num0"/>
  <Column id=weighted_valid_persons title="Personas ponderadas con coste válido" fmt="num0"/>
  <Column id=weighted_missing_cost_loss_pct title="Peso excluido por coste ausente (%)" fmt="num2"/>
</DataTable>

<DataTable data={ecv_cruce_seleccionado} rows=1>
  <Column id=known_imputed_income_target_persons title="Personas de hogares con renta total marcada como imputada" fmt="num0"/>
  <Column id=known_imputed_allowance_target_persons title="Personas de hogares con ayuda bruta marcada como imputada" fmt="num0"/>
</DataTable>

El denominador de la tasa son las **personas con coste válido de la combinación
seleccionada**, ponderadas con RB050; no hogares ni toda la población española.
Los hogares representados son cobertura de muestra, no «hogares jóvenes»
definidos por la edad de quien los encabeza. La renta, pobreza, tenencia y
costes se comparten dentro del hogar: incluye menores y jóvenes co-residentes,
no demuestra que cada joven pague el alquiler o pueda emanciparse. Los hogares
que no llegaron a formarse y la población institucional quedan fuera.

El umbral es 0,60 de la mediana **nacional** de renta disponible equivalente
tras transferencias, calculada antes de excluir costes ausentes; no se recalcula
entre jóvenes o inquilinos. Los costes mensuales se anualizan y se descuentan
ayudas brutas de costes e ingreso; incluyen suministros e intereses hipotecarios,
**no amortización de capital**. La renta participa también en el denominador de
la carga: diferencias entre grupos no son efectos causales ni diferencias de
costes monetarios. La edad es al final del año de ingresos, no en la entrevista.

Las reglas del proyecto se fijaron antes de observar el cruce: **no mostramos
la tasa con menos de 50 personas válidas, menos de 30 hogares distintos válidos,
o más del 5% de peso excluido por costes ausentes**. Son reglas conservadoras
de presentación, no umbrales oficiales Eurostat, garantía de confidencialidad
ni pruebas de precisión. Nulo por ocultación o falta de datos **no es cero**;
la cobertura y motivos permanecen visibles. **Los totales solapados de este
cruce propio solo muestran cobertura, no tasas** (`overlapping_marginal_rate_not_published`),
para que sus tasas y denominadores no permitan reconstruir por resta las tasas
ocultas. Solo publicamos tasas de combinaciones mutuamente excluyentes de edad,
pobreza y tenencia, sin ninguna categoría total. Esto no garantiza que otros
datos públicos permitan o impidan inferencias. **Incluso los propios agregados
pueden revelar lógicamente una tasa oculta por compartir hogares**: por ejemplo,
un grupo adulto con carga nula en todos los hogares también informa sobre sus
menores co-residentes. No ofrecemos reconstrucción automatizada de esas tasas;
la ocultación solo limita qué tasas se presentan directamente. Los motivos técnicos indican
`less_than_50_valid_persons`, `less_than_30_valid_households` o
`over_5pct_weighted_cost_loss`, según corresponda.

La ponderación es descriptiva sobre casos disponibles: no recrea correcciones
en estratos no publicados. **No hay intervalos de diseño ni pruebas de
significación**. Las banderas de renta y ayudas conservan imputación y
procedencia; que otro hogar no lleve esa marca de renta total no certifica que
todos sus componentes sean observados. Los totales y componentes no se suman.

Fuente: [INE ECV, microdatos transversales base 2013](https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736176807&idp=1254735976608&menu=resultados).
[Contrato de método, cobertura y revisión](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/ecv_joint_scope.md).
Los paneles Eurostat anteriores siguen siendo celdas directamente publicadas;
este cruce propio no los sustituye ni infiere sus intersecciones a partir de marginales.

## Robustez descriptiva: separar stock y hogares

En vez de dividir adiciones de viviendas por nuevas personas (inestable
cuando el denominador es pequeño o negativo), mostramos los dos crecimientos
por separado. La brecha es crecimiento del stock menos crecimiento de
hogares, en puntos porcentuales: negativa significa que hogares crecen más
rápido, **no una estimación de déficit de vivienda utilizable**.

```sql cambios_acceso
select a.cpro, a.provincia, a.anyo as desde, b.anyo as hasta,
       a.viviendas_total as stock_inicial, b.viviendas_total as stock_final,
       a.hogares as hogares_inicial, b.hogares as hogares_final,
       100.0 * (b.viviendas_total / a.viviendas_total - 1) as stock_pct,
       100.0 * (b.hogares / a.hogares - 1) as hogares_pct,
       100.0 * (b.viviendas_total / a.viviendas_total - b.hogares / a.hogares) as brecha_pp
from housing.mart_provincia_anual a
join housing.mart_provincia_anual b on a.cpro = b.cpro and b.anyo = 2025
where a.anyo in (2021, 2022) and a.cpro <> '51+52'
  and a.viviendas_total > 0 and a.hogares > 0
  and b.viviendas_total > 0 and b.hogares > 0
order by desde, a.cpro
```

```sql cambios_foco
select provincia, desde, hasta, stock_pct, hogares_pct, brecha_pp
from ${cambios_acceso}
where cpro in ('28', '08', '03', '12', '46')
order by provincia, desde
```

<DataTable data={cambios_foco} rows=10>
  <Column id=provincia title="Provincia"/>
  <Column id=desde title="Desde" fmt="0"/>
  <Column id=hasta title="Hasta" fmt="0"/>
  <Column id=stock_pct title="Stock: cambio (%)" fmt="num2"/>
  <Column id=hogares_pct title="Hogares: cambio (%)" fmt="num2"/>
  <Column id=brecha_pp title="Brecha (pp)" fmt="num2"/>
</DataTable>

```sql sensibilidad_acceso
with totales as (
  select desde, hasta, count(*) as n,
         avg(brecha_pp) as media_provincial_pp,
         sum(stock_inicial) as s0, sum(stock_final) as s1,
         sum(hogares_inicial) as h0, sum(hogares_final) as h1
  from ${cambios_acceso}
  group by desde, hasta
), exclusiones as (
  select t.desde,
         100.0 * ((t.s1 - c.stock_final) / nullif(t.s0 - c.stock_inicial, 0)
                - (t.h1 - c.hogares_final) / nullif(t.h0 - c.hogares_inicial, 0)) as brecha_sin_una
  from totales t join ${cambios_acceso} c on t.desde = c.desde
)
select t.desde, t.hasta, t.n, t.media_provincial_pp,
       100.0 * (t.s1 / t.s0 - t.h1 / t.h0) as brecha_agregada_pp,
       min(e.brecha_sin_una) as exclusion_min_pp,
       max(e.brecha_sin_una) as exclusion_max_pp
from totales t join exclusiones e on t.desde = e.desde
group by t.desde, t.hasta, t.n, t.media_provincial_pp, t.s0, t.s1, t.h0, t.h1
order by t.desde
```

<DataTable data={sensibilidad_acceso} rows=2>
  <Column id=desde title="Desde" fmt="0"/>
  <Column id=hasta title="Hasta" fmt="0"/>
  <Column id=n title="Provincias con ambos extremos" fmt="num0"/>
  <Column id=media_provincial_pp title="Brecha media: igual peso (pp)" fmt="num2"/>
  <Column id=brecha_agregada_pp title="Brecha de sumas (pp)" fmt="num2"/>
  <Column id=exclusion_min_pp title="Sin una provincia: mínimo (pp)" fmt="num2"/>
  <Column id=exclusion_max_pp title="Sin una provincia: máximo (pp)" fmt="num2"/>
</DataTable>

Esta sensibilidad utiliza todas las provincias con ambos extremos salvo
Ceuta y Melilla, no solo los casos elegidos. La media da igual peso a cada
provincia; la brecha de sumas pondera stock y hogares por sus respectivos
niveles iniciales. El intervalo de exclusión recalcula esa brecha omitiendo
cada provincia: **no es un intervalo de confianza**. Las ventanas difieren
en duración; los cambios son acumulados, no tasas anuales. Empezar después
del censo reduce exposición al ancla de revisión, pero no elimina revisiones
del parque modelado. No es robustez de una regresión de precios.

## Qué podemos concluir y qué falta

- **Madrid:** evaluar oferta nueva y accesibilidad a empleo; los ratios no
  identifican por sí solos el efecto de construir ni su localización óptima.
- **Barcelona:** contrastar costes de mercado con ingresos por grupo; un
  esfuerzo medio alto no cuantifica cuántos hogares están sobrecargados.
- **Costa valenciana:** investigar habitabilidad y usos del stock no
  principal antes de llamarlo reserva movilizable. Las provincias no son
  sinónimo de sus municipios costeros.
- **Turismo:** no detectar asociación en un panel no demuestra efectos
  pequeños o inexistentes. La [página de incertidumbre](/incertidumbre/)
  muestra los rangos normales aproximados existentes y sus límites; no
  sustituye una prueba calibrada de equivalencia. Los registros tampoco
  captan toda la actividad.

El [simulador de compra](/compra/) separa efectivo inicial y cuota bajo
supuestos editables, sin convertirlos en resultados de compradores reales.
Siguiente capa: cargas conjuntas y locales por tenencia, edad e ingresos;
estado y localización del stock vacío.
Hasta disponer de fuentes comparables, estas preguntas quedan abiertas.

[Registro de afirmaciones y cobertura](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/housing_access.md).

---
*Instantánea de datos: 2026-10-09 · ECV 2025 (renta 2024), Censo 2021, paneles 2021–2025 según el indicador · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/housing_access.md).*
