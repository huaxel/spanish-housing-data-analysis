---
title: Alquiler e ingresos
---

# Cuánta renta municipal se va en firmar un contrato

La mediana de alquiler de firma cuesta cerca del 14% de la renta neta
media del municipio — una cifra plana desde 2015 que **subestima lo que
ocurre en las grandes ciudades**, donde el contrato se come una quinta
parte y subiendo. Esta página presenta el proxy SERPAVI/ADRH aceptado el
2026-10-09: un indicador de mercado de firma, **no** una tasa de
sobrecarga.
[Panorama nacional](/) · [Acceso](/acceso/) · [Renta (€/m²)](/renta/) · [Municipios](/municipios/).

## El indicador, en tres cifras

```sql mediana_extremos
with m as (
  select anyo, count(*) n, median(ratio_pct) med
  from access.rent_income
  where ratio_pct is not null
  group by anyo
), s as (
  select round(100.0 * count(*) filter (where anyo = 2023 and ratio_pct >= 20)
        / count(*) filter (where anyo = 2023), 1) as share_20_2023
  from access.rent_income
  where ratio_pct is not null
)
select
  max(med) filter (where anyo = 2015) as mediana_2015,
  max(med) filter (where anyo = 2023) as mediana_2023,
  max(n) filter (where anyo = 2023) as municipios_2023,
  max(share_20_2023) as share_20_2023
from m, s
```

En 2023 el municipio mediano con datos publica un contrato mediano de
<Value data={mediana_extremos} column=mediana_2023 fmt="num1"/>%
de la renta neta media de sus hogares; en 2015 era
<Value data={mediana_extremos} column=mediana_2015 fmt="num1"/>%,
y el <Value data={mediana_extremos} column=share_20_2023 fmt="num1"/>% de
municipios supera ya el 20%. La cobertura es
<Value data={mediana_extremos} column=municipios_2023 fmt="num0"/> municipios
(los que SERPAVI publica; los pequeños están suprimidos).

## La mediana no se mueve; las grandes ciudades sí

```sql serie_proxy
select anyo, 'Mediana municipal' as grupo, round(median(ratio_pct), 1) as ratio_pct
from access.rent_income
where ratio_pct is not null
group by anyo
union all
select anyo, municipio as grupo, round(ratio_pct, 1) as ratio_pct
from access.rent_income
where codigo in ('28079', '08019', '46250', '41091', '29067')
  and ratio_pct is not null
order by anyo
```

<LineChart data={serie_proxy} x=anyo y=ratio_pct series=grupo
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  title="Alquiler de firma como % de la renta neta media anual del hogar"/>

El alquiler mediano de firma y la renta media municipal crecieron al
mismo ritmo entre 2015 y 2023, así que la mediana del ratio es plana.
Pero las cinco grandes ciudades parten por encima y todas ganan
porcentaje: Barcelona pasa de ~20,7% a ~22,0% y Valencia de ~16,0% a
~18,7%. La renta media creció ~30% en esas ciudades; el contrato mediano
creció más.

## Dónde pesa más el contrato (2023)

```sql top_proxy
select municipio, cpro, contratos, round(alquiler_med, 0) as alquiler_med,
       round(renta_neta_hogar, 0) as renta_neta_hogar, ratio_pct
from access.rent_income
where anyo = 2023 and contratos >= 50 and ratio_pct is not null
order by ratio_pct desc
limit 15
```

<BarChart data={top_proxy} x=municipio y=ratio_pct
  yFmt="num1" title="Ratio alquiler/renta 2023 (≥50 contratos)"/>

<DataTable data={top_proxy} rows=15>
  <Column id=municipio title="Municipio"/>
  <Column id=contratos title="Contratos (VC)" fmt="num0"/>
  <Column id=alquiler_med title="Alquiler mediano (€/mes)" fmt="num0"/>
  <Column id=renta_neta_hogar title="Renta neta media (€/año)" fmt="num0"/>
  <Column id=ratio_pct title="Ratio (%)" fmt="num1"/>
</DataTable>

La costa turística malagueña encabeza con ratio en torno a 22–32%:
mercados de firma caros sobre rentas medias locales más bajas.

## Alquiler frente a renta: el mapa del esfuerzo de firma

```sql scatter_proxy
select municipio, round(renta_neta_hogar / 12.0, 0) as renta_mensual,
       round(alquiler_med, 0) as alquiler_med, contratos, ratio_pct
from access.rent_income
where anyo = 2023 and contratos >= 50 and ratio_pct is not null
order by alquiler_med desc
limit 20
```

<BarChart data={scatter_proxy} x=municipio y=alquiler_med
  yFmt="num0" title="Alquiler mediano de firma más alto (€/mes, 2023)"/>

<DataTable data={scatter_proxy} rows=20>
  <Column id=municipio title="Municipio"/>
  <Column id=renta_mensual title="Renta neta media mensual (€)" fmt="num0"/>
  <Column id=alquiler_med title="Alquiler mediano (€/mes)" fmt="num0"/>
  <Column id=contratos title="Contratos (VC)" fmt="num0"/>
  <Column id=ratio_pct title="Ratio (% de renta anual)" fmt="num1"/>
</DataTable>

Los alquileres de firma más altos del país no son proporcionalmente los
más esforzados: el ratio depende de la renta media local (todos los
hogares, no solo inquilinos), y los mercados turísticos combinan
contrato caro con renta media más baja.

## Qué no mide este indicador

- **No es una tasa de sobrecarga.** El denominador es la renta neta
  media de **todos** los hogares del municipio (ADRH, registros
  administrativos), no la de quienes alquilan — tiende a ser menor.
- **El numerador es el mercado de firma:** contratos nuevos y
  renovaciones declarados ante Hacienda (fianzas SERPAVI, vivienda
  colectiva). El stock de inquilinos sentados paga menos y no aparece.
- Sin suministros ni otros costes de vivienda; renta neta antes de
  alquiler imputado.
- **Cobertura sesgada a municipios con suficientes contratos**
  (1.877–2.415 de 8.139 por año): los pequeños y rurales faltan, y desde
  2020 ADRH puede sustituir la renta de municipios de menos de 100
  habitantes por la media comarcal/provincial (regla de difusión,
  no marcada por fila).
- Comparar municipios es comparar mercados distintos; la mediana
  municipal de un año cambia también porque entra y sale cobertura.

Fuente: SERPAVI (MIVAU) y ADRH (INE), construido por
`scripts/build_rent_income.py` sobre la tabla `access.rent_income`;
semántica aceptada y documentada en `docs/housing_access.md`.

---
*Proxy de mercado de firma, 2015–2023 · SERPAVI + ADRH · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
