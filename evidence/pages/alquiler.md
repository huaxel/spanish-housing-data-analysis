---
title: Alquiler
---

<script>
  import { ajusteGrafico } from '../../components/chartOptions.js';
</script>

# El registro del alquiler: stock declarado y flujo de fianzas

Dos registros oficiales cuentan el alquiler en España y no miden lo mismo.
SERPAVI cuenta los **contratos declarados** en el IRPF: un stock de contratos
vigentes en el año fiscal. El registro de fianzas de INCASÒL cuenta **altas y
bajas** de depósitos: un flujo de actividad registral. Leídos juntos responden
una pregunta concreta —¿se está reduciendo el alquiler?— y estorban si se
confunden.

[Nacional](/) · [Renta y esfuerzo](/renta/) · [Política de alquiler](/politica/) · [Qué no está disponible](/incertidumbre/).

## El stock declarado sube, y no solo en Barcelona

```sql contratos_grandes
select anyo,
       municipio,
       coalesce(contratos_colectiva, 0) + coalesce(contratos_unifamiliar, 0) as contratos
from housing.serpavi_contratos
where municipio in ('Madrid', 'Barcelona', 'Valencia')
order by anyo, municipio
```

<LineChart echartsOptions={ajusteGrafico()}
  data={contratos_grandes}
  x=anyo
  y=contratos
  series=municipio
  yFmt="num0"
  title="Contratos de alquiler declarados en el IRPF (SERPAVI)"
/>

<EvidencePanel data={contratos_grandes} chart="alquiler-contratos-grandes"
  columns={["anyo", "municipio", "contratos"]}
  files={["data/raw/parquet/serpavi_municipal.parquet"]}
  definition="Contratos de alquiler declarados en el IRPF por municipio y año fiscal, suma de vivienda colectiva y unifamiliar."
  coverage="SERPAVI (MIVAU), 2011–2024, municipios de Madrid, Barcelona y València. Celdas suprimidas no se imputan." />

Entre los **308** municipios con serie completa de vivienda colectiva
(**2015–2024**) y al menos **1.000** contratos declarados en 2024, **los 308**
terminan por encima de donde empezaron y **295** suben todos los años. La
mediana crece un **59,4%**; el menor, un **17,9%**. Los mercados más grandes:

| Municipio | 2015 | 2024 | Cambio |
| --- | ---: | ---: | ---: |
| Madrid | 191.435 | 300.447 | +56,9% |
| Barcelona | 104.971 | 140.872 | +34,2% |
| València | 39.267 | 65.742 | +67,4% |

```sql crecimiento_grandes
with serie as (
  select codigo, anyo, coalesce(contratos_colectiva, 0) as c
  from housing.serpavi_contratos
  where anyo between 2015 and 2024
), completa as (select codigo from serie group by 1 having count(*) = 10),
agg as (
  select codigo,
         any_value(case when anyo = 2015 then c end) as primero,
         any_value(case when anyo = 2024 then c end) as ultimo
  from serie join completa using (codigo)
  group by 1
)
select municipio,
       round(100.0 * (ultimo - primero) / primero, 1) as crecimiento,
       ultimo as contratos_2024
from agg join (select distinct codigo, municipio from housing.serpavi_contratos) using (codigo)
where ultimo >= 20000
order by contratos_2024 desc
limit 12
```

<BarChart echartsOptions={ajusteGrafico()}
  data={crecimiento_grandes}
  x=municipio
  y=crecimiento
  swapXY=true
  yFmt="num1"
  title="Crecimiento de los contratos declarados, 2015–2024 (%), mayores mercados"
/>

<EvidencePanel data={crecimiento_grandes} chart="alquiler-crecimiento-grandes"
  columns={["municipio", "crecimiento", "contratos_2024"]}
  files={["data/raw/parquet/serpavi_municipal.parquet"]}
  definition="Cambio porcentual de los contratos declarados entre 2015 y 2024 en municipios con serie completa y al menos 20.000 contratos en 2024."
  coverage="SERPAVI (MIVAU), 2015–2024, 12 mayores mercados de alquiler declarado. No es una tasación de precios ni una medida de oferta." />

Hay dos advertencias que sobreviven a esa amplitud. Son contratos
**declarados**: una mejora del cumplimiento fiscal eleva el recuento sin que
haya más viviendas alquiladas. Y quedan fuera los municipios por debajo del
umbral, donde la supresión estadística y el peso de la vivienda unifamiliar
hacen la serie poco informativa.

## Las altas de fianza bajan en Cataluña

El flujo va en dirección contraria al stock. En Barcelona las altas de fianza
de alquiler habitual bajaron de **57.158** (**2021**) a **30.789** (**2025**), y
el saldo neto se estrechó hasta **534** en 2025, el menor año positivo de la
ventana. Ese saldo es actividad registral: no es el aumento anual de viviendas
alquiladas. Comparado con el cambio del stock declarado, coincide una sola vez
(2024, **94** de diferencia) y en 2020 cambia de signo.

```sql bcn_saldo_vs_stock
select cast(anyo as varchar) as anyo,
       'Saldo neto de fianzas (INCASÒL)' as serie,
       saldo_fianzas as contratos
from rental_registers.bcn_depositos_vs_stock
union all
select cast(anyo as varchar) as anyo,
       'Cambio anual del stock declarado (SERPAVI)' as serie,
       cambio_stock_declarado as contratos
from rental_registers.bcn_depositos_vs_stock
where cambio_stock_declarado is not null
order by anyo, serie
```

<BarChart echartsOptions={ajusteGrafico()}
  data={bcn_saldo_vs_stock}
  x=anyo
  y=contratos
  series=serie
  type=grouped
  yFmt="num0"
  title="Barcelona: saldo neto de fianzas (INCASÒL) frente al cambio anual del stock declarado (SERPAVI)"
/>

<EvidencePanel data={bcn_saldo_vs_stock} chart="alquiler-bcn-saldo-vs-stock"
  columns={["anyo", "serie", "contratos"]}
  files={["data/raw/cat_incasol_saldos_municipis.xlsx", "data/raw/parquet/serpavi_municipal.parquet"]}
  definition="Comparación anual en Barcelona ciudad entre el saldo neto de fianzas de alquiler habitual (altas menos bajas, INCASÒL) y la variación anual de contratos declarados en el IRPF (SERPAVI)."
  coverage="Barcelona municipio, 2019–2025 en INCASÒL y 2019–2024 en SERPAVI (2025 aún no publicado en SERPAVI; no se imputa)." />

Las tres lecturas compatibles —alquileres más largos, menos contratos nuevos o
menos altas registradas— no se pueden separar con estos datos. Lo que sí se
descarta: el registro turístico no absorbe esa caída. Las viviendas turísticas
registradas en Cataluña se mueven en una banda estacional entre **45.709** y
**63.199** y en mayo de 2026 eran **51.305**, por debajo de su máximo de 2020 y
de su propio valor de mayo de 2025 (**56.851**).

```sql cat_vut_banda
select periodo, viviendas_turisticas
from rental_registers.cat_vut_banda
order by periodo
```

<LineChart echartsOptions={ajusteGrafico()}
  data={cat_vut_banda}
  x=periodo
  y=viviendas_turisticas
  yFmt="num0"
  title="Viviendas turísticas estimadas en Cataluña (INE VTE, 2020–2026)"
/>

<EvidencePanel data={cat_vut_banda} chart="alquiler-cat-vut-banda"
  columns={["periodo", "viviendas_turisticas"]}
  files={["data/raw/parquet/vut_municipal.parquet"]}
  definition="Estimación experimental del INE de viviendas turísticas anunciadas en plataformas digitales en Cataluña por corte."
  coverage="INE VTE, 13 cortes entre agosto de 2020 y mayo de 2026 en Cataluña. Es una estimación de plataformas, no un registro de licencias ni una reclasificación desde el alquiler de temporada." />

## Qué no se puede concluir

- **Ni oferta ni disponibilidad.** Ninguna de las dos series cuenta viviendas
  ofrecidas ni disponibles; el registro de fianzas no es la oferta de alquiler.
- **Comparación, no reclasificación.** Vivienda turística y alquiler de
  temporada son categorías legales distintas y ningún registro enlaza una
  vivienda con la otra.
- **Cumplimiento.** Un aumento de contratos declarados puede reflejar mejor
  declaración, no más alquiler. La serie es fiscal, no una encuesta de uso.
- **Granularidad.** Las series por municipio son anuales; no dicen nada sobre
  precios, calidad ni duración de los contratos.

Detalle reproducible: [saldos y stock por año](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/occupancy_catalonia_deposit_balances.md).

---
*Instantánea de datos: 2026-11-28 · SERPAVI 2011–2024, fianzas INCASÒL 2019–2026 · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/occupancy_availability.md).*
