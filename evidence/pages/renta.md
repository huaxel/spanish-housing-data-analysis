---
title: Renta
---

# Renta municipal (SERPAVI)

Renta mediana de alquiler (€/m²/mes) por municipio, 2011–2024, fuente
SERPAVI (MIVAU, explotación fiscal de fianzas de alquiler). Cubre 2,555
municipios en 2024 (los que tienen suficientes contratos; municipios
pequeños suprimidos). Validación: correlación 0.825 con la serie DIBA de
Barcelona (fuentes independientes).
[Panorama nacional](/) · [Comparar territorios](/comparar/) · [Municipios](/municipios/).

## Selecciona municipios

```sql lista_renta
select distinct municipio
from housing.serpavi_rents
order by municipio
```

<Dropdown data={lista_renta} name=munis_renta value=municipio
  title="Municipios con renta" multiple=true
  defaultValue={["Barcelona", "Madrid", "Valencia/València", "Sevilla"]}/>

```sql serie_renta
select anyo, municipio, rent_eur_m2
from housing.serpavi_rents
where municipio in ${inputs.munis_renta.value}
order by anyo, municipio
```

<LineChart data={serie_renta} x=anyo y=rent_eur_m2 series=municipio
  xFmt="0" xAxisTitle="Año" yFmt="num1" handleMissing="gap" markers=true
  title="Renta mediana (€/m²/mes)"/>

## Renta por municipio (2024)

```sql renta_2024
select provincia, municipio, rent_eur_m2
from housing.serpavi_rents
where anyo = 2024
order by rent_eur_m2 desc
limit 20
```

<DataTable data={renta_2024} rows=15>
  <Column id=municipio title="Municipio"/>
  <Column id=rent_eur_m2 title="€/m²/mes" fmt="num1"/>
</DataTable>

## Top y cola

```sql top_renta
select municipio, anyo, rent_eur_m2
from housing.serpavi_rents
where anyo = 2024
order by rent_eur_m2 desc
limit 10
```

<BarChart data={top_renta} x=municipio y=rent_eur_m2
  yFmt="num1" title="Municipios más caros (2024)"/>

Nota: renta mediana de contratos nuevos/renovados declarados a efectos
fiscales (fianzas); subalquiler y renovaciones recientes pueden faltar.
Fuente: `docs/explorations/serpavi.md`.
---
*Instantánea de datos: 2026-10-07 · SERPAVI 2011–2024, contratos declarados · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/methods.md).*
