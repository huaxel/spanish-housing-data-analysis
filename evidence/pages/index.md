---
title: Nacional
---

# Precios, stock y población (2007–2025)

Evolución del precio de la vivienda (IPV, índice base 2025) frente a las
viviendas por cada 1.000 habitantes. Ámbito nacional; detalle regional en
[comunidades autónomas](/ccaa/). También puedes [comparar dos territorios](/comparar/),
y bajar al [grano municipal](/municipios/) en Madrid y Barcelona, ver la
[renta de alquiler por municipio](/renta/) (SERPAVI, 2011–2024), o la
[vivienda vacía por consumo eléctrico](/vacancia/) (Censo 2021).

```sql nacional
select anyo, viviendas_total, poblacion, pop_source, viv_por_1000_hab,
       hogares, viv_por_hogar, eur_m2_libre, afford_90m2_years,
       pob_20_34, share_20_34, hip_viv_num, ipv_general, ipv_nueva, ipv_segunda_mano
from housing.mart_ccaa_anual
where ccaa = 'Nacional'
order by anyo
```

```sql maximos
select max(ipv_general) as ipv_general,
       max(viv_por_1000_hab) as viv_por_1000_hab
from housing.mart_ccaa_anual
where ccaa = 'Nacional'
```

Máximos de la serie: IPV <Value data={maximos} column=ipv_general fmt="num1"/>;
viviendas por 1.000 habitantes <Value data={maximos} column=viv_por_1000_hab fmt="num1"/>.

## El precio cae, el stock por habitante no

Entre 2007 y 2013 el IPV nacional cayó ~36% mientras las viviendas por cada
1.000 habitantes siguieron subiendo: el stock sobrevivió a la demanda y se
siguió terminando. A partir de 2014 los precios se recuperan con el stock
per cápita estancado. Co-movimientos descriptivos, no causalidad —
ver [métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md) (en el repo).

<LineChart
  data={nacional}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=ipv_general
  yFmt="num1"
  title="IPV general (índice, base 2025)"
/>

```sql nueva_segunda
select anyo, ipv_nueva as "Nueva", ipv_segunda_mano as "Segunda mano"
from housing.mart_ccaa_anual
where ccaa = 'Nacional'
order by anyo
```

<LineChart
  data={nueva_segunda}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y={['Nueva', 'Segunda mano']}
  yFmt="num1"
  title="IPV nueva vs segunda mano"
/>

## Stock y hogares

<LineChart
  data={nacional}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=viv_por_1000_hab
  yFmt="num1"
  title="Viviendas por 1.000 habitantes"
/>

<LineChart
  data={nacional}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=viv_por_hogar
  yFmt="num2"
  title="Viviendas por hogar (censo 2011, ECH, ECP)"
/>

## Valor tasado y esfuerzo de renta

El valor tasado no es un precio de compraventa. El esfuerzo expresa años de
renta neta del hogar para 90 m², sin intereses ni otros costes de adquisición.

<LineChart
  data={nacional}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=eur_m2_libre
  yFmt="num0"
  title="Valor tasado vivienda libre (€/m²)"
/>

```sql nacional_real
select m.anyo, round(m.eur_m2_libre * i100.ipc / i.ipc, 0) as eur_m2_2025
from housing.mart_ccaa_anual m
join housing.ipc_anual i on i.territorio = 'Nacional' and i.anyo = m.anyo
join housing.ipc_anual i100 on i100.territorio = 'Nacional' and i100.anyo = 2025
where m.ccaa = 'Nacional' and m.eur_m2_libre is not null
order by m.anyo
```

En euros de 2025 (IPC base 2021) la recuperación es menor de lo que el
nominal sugiere: el nivel nacional sigue un 27% por debajo de 2007 —
y en Madrid ni siquiera existe recuperación (capital −7,5% real).

<LineChart
  data={nacional_real}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=eur_m2_2025
  yFmt="num0"
  title="Valor tasado en euros de 2025 (€/m²)"
/>

<LineChart
  data={nacional}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=afford_90m2_years
  yFmt="num1"
  title="Años de renta neta para 90 m²"
/>

## Población joven

<LineChart
  data={nacional}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=share_20_34
  yFmt="pct1"
  title="Cuota de 20–34 años en la población"
/>

## Crédito hipotecario

<LineChart
  data={nacional}
  x=anyo
  xFmt="0"
  xAxisTitle="Año"
  y=hip_viv_num
  yFmt="num0"
  title="Hipotecas sobre viviendas constituidas"
/>

## Desahucios y ejecuciones hipotecarias

Lanzamientos practicados por los juzgados (CGPJ, 50 provincias, 2013–):
cada lanzamiento es un inmueble cuya entrega se acuerda, sea o no vivienda
— indicador de tensión, no recuento de desahucios de inquilinos. El colapso
de 2020 es la moratoria pandémica, no una mejora del mercado. Las
ejecuciones hipotecarias presentadas arrancan en 2007.

```sql desahucios_anual
select anyo, 'Hipoteca' as causa, sum(lanz_hipoteca) as lanzamientos
from housing.desahucios_provincia group by anyo
union all
select anyo, 'Alquiler (LAU)' as causa, sum(lanz_lau) as lanzamientos
from housing.desahucios_provincia group by anyo
union all
select anyo, 'Otras' as causa, sum(lanz_otros) as lanzamientos
from housing.desahucios_provincia group by anyo
order by anyo, causa
```

<LineChart data={desahucios_anual} x=anyo y=lanzamientos series=causa
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Lanzamientos por causa (nacional)"/>

```sql ejecuciones_anual
select anyo, sum(ej_hipotecarias) as ejecuciones
from housing.desahucios_provincia
group by anyo order by anyo
```

<LineChart data={ejecuciones_anual} x=anyo y=ejecuciones
  xFmt="0" xAxisTitle="Año" yFmt="num0" handleMissing="gap" markers=true
  title="Ejecuciones hipotecarias presentadas (nacional, desde 2007)"/>

## Datos y cobertura

Cada guion indica un dato no disponible; no se imputa ni se interpreta como cero.
La población cambia de fuente entre Padrón y ECP; consulta la columna de origen.
Puedes ordenar las columnas y descargar la tabla.

<DataTable data={nacional} rows=20>
  <Column id=anyo title="Año" fmt="0"/>
  <Column id=viviendas_total title="Viviendas" fmt="num0"/>
  <Column id=poblacion title="Población" fmt="num0"/>
  <Column id=pop_source title="Fuente de población"/>
  <Column id=viv_por_1000_hab title="Viviendas / 1.000 hab." fmt="num1"/>
  <Column id=hogares title="Hogares" fmt="num0"/>
  <Column id=viv_por_hogar title="Viviendas / hogar" fmt="num2"/>
  <Column id=eur_m2_libre title="Valor tasado (€/m²)" fmt="num0"/>
  <Column id=afford_90m2_years title="Renta para 90 m² (años)" fmt="num1"/>
  <Column id=pob_20_34 title="Población de 20–34 años" fmt="num0"/>
  <Column id=share_20_34 title="Cuota de 20–34 años" fmt="pct1"/>
  <Column id=hip_viv_num title="Hipotecas sobre viviendas" fmt="num0"/>
  <Column id=ipv_general title="IPV general (2025 = 100)" fmt="num1"/>
  <Column id=ipv_nueva title="IPV nueva (2025 = 100)" fmt="num1"/>
  <Column id=ipv_segunda_mano title="IPV usada (2025 = 100)" fmt="num1"/>
</DataTable>

---
*Instantánea de datos: 2026-10-07 · cobertura nacional 2007–2025 · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
