---
title: Qué significa déficit
---

# ¿Cuántas viviendas «faltan»? Depende de qué restes

Restar viviendas terminadas del aumento de hogares no da el mismo resultado
que restar el aumento neto del parque. **Ninguna de las dos restas cuenta
viviendas disponibles ni hogares sin casa.** Este explorador compara las
operaciones, sus fechas y sus huecos; no calcula cuánto habría que construir
ni cuánto bajarían los precios.

[Reportaje](/reportaje/) · [Tu municipio](/perfil/) · [Stock y acceso](/acceso/) ·
[Panorama nacional](/)

```sql ventanas_deficit
select distinct window_key, flow_start, flow_end,
       replace(window_key, '-', '–') || ' (años completos)' as etiqueta
from deficit.comparisons
order by window_key
```

<Dropdown data={ventanas_deficit} name=ventana_deficit value=window_key label=etiqueta
  title="Años de actividad" defaultValue="2021-2024" />

```sql territorios_deficit
select distinct cpro, provincia
from deficit.comparisons
order by case when cpro = 'NACIONAL' then 0 else 1 end, provincia
```

<Dropdown data={territorios_deficit} name=territorio_deficit value=cpro label=provincia
  title="España o provincia (no municipio)" defaultValue="NACIONAL" />

```sql seleccion_deficit
select *
from deficit.comparisons
where window_key = '${inputs.ventana_deficit.value}'
  and cpro = '${inputs.territorio_deficit.value}'
```

## Primero, los relojes

<DataTable data={seleccion_deficit} rows=1>
  <Column id=provincia title="Territorio" />
  <Column id=flow_start title="Primer año de actividad" fmt="0" />
  <Column id=flow_end title="Último año de actividad" fmt="0" />
  <Column id=household_start_year title="Hogares: 1 enero inicial" fmt="0" />
  <Column id=household_end_year title="Hogares: 1 enero final" fmt="0" />
  <Column id=stock_start_year title="Parque: 31 diciembre inicial" fmt="0" />
  <Column id=stock_end_year title="Parque: 31 diciembre final" fmt="0" />
</DataTable>

**Ejemplo de alineación:** la actividad de 2021–2024 se compara con hogares
entre el 1 de enero de 2021 y el 1 de enero de 2025, y con parque entre el
31 de diciembre de 2020 y el 31 de diciembre de 2024. Los límites de año
corresponden, pero no son la misma fecha exacta. Comparar niveles etiquetados
2021 y 2025 en ambas fuentes sería otra ventana, no la suma de terminadas de
2021–2024. [La operación oficial del parque](https://www.ine.es/dyngs/IOE/fichaProg.htm?cid=1259946014126)
define la referencia a fin de diciembre.

Fuentes: hogares ECP (INE), a principios de año; parque modelado (MIVAU), a
fin de año; terminadas mensuales MIVAU, vivienda libre y protegida, sumadas
por año natural. Los cambios de parque incluyen el balance modelado de altas
y bajas, no solo obra nueva. Las revisiones y anclajes censales tampoco son
movimientos orgánicos observados. Los últimos datos de hogares y terminadas
pueden ser provisionales y revisarse.

## Tres cantidades distintas

```sql cantidades_deficit
select 'Hogares: cambio neto' as concepto, household_change as unidades
from ${seleccion_deficit}
union all
select 'Parque: cambio neto', stock_change from ${seleccion_deficit}
union all
select 'Terminadas: suma publicada', completions_observed from ${seleccion_deficit}
```

<BarChart data={cantidades_deficit} x=concepto y=unidades swapXY
  yFmt="num0" title="Hogares, parque y terminadas: unidades, no porcentajes" />

<DataTable data={cantidades_deficit} rows=3>
  <Column id=concepto title="Qué se cuenta" />
  <Column id=unidades title="Unidades (vacío = no calculable)" fmt="num0" />
</DataTable>

El cambio de hogares es **neto**, no el número bruto de hogares recién
formados ni de personas que buscan vivienda. El cambio de parque también
es neto e incluye vivienda principal y no principal. Las terminadas son
un flujo de viviendas finalizadas; no dicen si se han vendido, alquilado,
ocupado o puesto a un precio accesible. No son visados ni viviendas iniciadas.

## La cobertura cambia lo que se puede afirmar

```sql cobertura_deficit
select completion_cells_expected, completion_cells_observed, completion_cells_missing,
       case when completion_cells_missing = 0 then 'Completa en la ventana'
            when completion_cells_observed = 0 then 'Sin observaciones de terminadas'
            else 'Incompleta: suma publicada, no total' end as estado
from ${seleccion_deficit}
```

<DataTable data={cobertura_deficit} rows=1>
  <Column id=completion_cells_expected title="Celdas provincia × mes × régimen esperadas" fmt="num0" />
  <Column id=completion_cells_observed title="Celdas con valor (incluye ceros)" fmt="num0" />
  <Column id=completion_cells_missing title="Celdas ausentes o nulas" fmt="num0" />
  <Column id=estado title="Estado de la suma de terminadas" />
</DataTable>

**Una celda ausente no es cero.** El calendario exige cada provincia, mes y
régimen; también se detectan registros enteramente ausentes. Con huecos, la
suma publicada de terminadas es solo un mínimo de ese flujo, porque sus
recuentos son no negativos. Por eso la resta de hogares menos esa suma es una
**cota superior del saldo**, no un saldo exacto ni una cota del número de
casas que faltan. Si no hay ninguna observación, incluso la suma publicada
queda vacía. Un cero publicado sí se conserva.

## Dos restas, no dos estimaciones de casas necesarias

```sql saldos_deficit
select 'Hogares − cambio neto de parque' as definicion, gap_stock as saldo
from ${seleccion_deficit}
union all
select 'Hogares − terminadas (solo con cobertura completa)', gap_completions
from ${seleccion_deficit}
```

<BarChart data={saldos_deficit} x=definicion y=saldo swapXY
  yFmt="num0" title="Saldos descriptivos; el signo no identifica una necesidad de construcción" />

<DataTable data={seleccion_deficit} rows=1>
  <Column id=gap_stock title="Hogares − cambio de parque" fmt="num0" />
  <Column id=gap_completions title="Hogares − terminadas: exacto si completo" fmt="num0" />
  <Column id=gap_completions_upper title="Hogares − suma publicada: cota superior si incompleto" fmt="num0" />
</DataTable>

Cuando faltan terminadas, el saldo exacto queda vacío y no se dibuja una barra
como si estuviese completo. La cota se muestra aparte. Un saldo negativo es
válido: tampoco demuestra que sobre vivienda utilizable o asequible.
El total de España suma provincias, sin sumar de nuevo el total nacional;
Ceuta y Melilla se combinan en una sola fila, conservando todas sus celdas
mensuales. Un total nacional que requiere un dato provincial ausente se
mantiene nulo; no se oculta cambiando la muestra de provincias.

## Cambia la ventana, no solo la definición

```sql ventanas_comparadas_deficit
select window_key, household_change, stock_change, completions_observed,
       gap_stock, gap_completions, gap_completions_upper, completion_cells_missing
from deficit.comparisons
where cpro = '${inputs.territorio_deficit.value}'
order by window_key
```

<DataTable data={ventanas_comparadas_deficit} rows=2>
  <Column id=window_key title="Años de actividad" />
  <Column id=household_change title="Cambio de hogares" fmt="num0" />
  <Column id=stock_change title="Cambio de parque" fmt="num0" />
  <Column id=completions_observed title="Terminadas: suma publicada" fmt="num0" />
  <Column id=gap_stock title="Saldo vs parque" fmt="num0" />
  <Column id=gap_completions title="Saldo exacto vs terminadas" fmt="num0" />
  <Column id=gap_completions_upper title="Saldo/cota vs terminadas" fmt="num0" />
  <Column id=completion_cells_missing title="Celdas faltantes" fmt="num0" />
</DataTable>

Son acumulados de distinta duración, **no tasas anuales ni una previsión**.
Ampliar la ventana añade actividad y puede incorporar datos más provisionales.
No se ajustan los resultados para que coincidan con una cifra externa.
La [exploración original](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/deficit_vivienda.md)
documenta diferencias de ventana, versión y cobertura frente a CaixaBank
Research. Aquí se conserva su aritmética de hogares menos terminadas como
subtotal/cota cuando hay huecos, sin presentarla como una reproducción exacta
de sus estimaciones ni como hogares sin vivienda.

## La geografía detrás de la suma

```sql provincias_deficit
select cpro, provincia, household_change, stock_change, completions_observed,
       gap_stock, gap_completions, gap_completions_upper, completion_cells_missing
from deficit.comparisons
where window_key = '${inputs.ventana_deficit.value}' and cpro != 'NACIONAL'
order by provincia
```

<DataTable data={provincias_deficit} rows=10>
  <Column id=provincia title="Provincia (Ceuta y Melilla combinadas)" />
  <Column id=household_change title="Cambio de hogares" fmt="num0" />
  <Column id=stock_change title="Cambio de parque" fmt="num0" />
  <Column id=completions_observed title="Terminadas publicadas" fmt="num0" />
  <Column id=gap_stock title="Saldo vs parque" fmt="num0" />
  <Column id=gap_completions title="Saldo exacto vs terminadas" fmt="num0" />
  <Column id=gap_completions_upper title="Saldo/cota vs terminadas" fmt="num0" />
  <Column id=completion_cells_missing title="Celdas faltantes" fmt="num0" />
</DataTable>

La tabla conserva las provincias con saldo negativo y las de cobertura
incompleta. No mezcla municipios con provincias ni convierte un saldo
provincial en un problema de cada localidad. Puedes ordenar y descargar
las tablas para revisar el reparto sin elegir solo los casos extremos.

## Lo que ninguna resta resuelve

- Los hogares que no llegan a formarse no aparecen en el aumento de hogares.
- Las viviendas contadas pueden no estar donde crece la demanda ni ser
  habitables, accesibles legalmente o asequibles.
- No restamos automáticamente turismo o segundas residencias como si los
  usos fueran disjuntos; tampoco se observa aquí el ajuste por compradores
  extranjeros no residentes.
- Ninguna comparación identifica el efecto de construir sobre precios,
  una cantidad óptima de obra nueva ni un pronóstico.

[Método y reproducción](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/deficit_explainer.md) ·
[Fuentes](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/sources.md) ·
[Qué falta para medir acceso](/acceso/)

---
*Instantánea de datos: 2026-10-09. Se conserva la versión fijada de las fuentes; este explorador no actualiza ni pronostica el mercado.*
