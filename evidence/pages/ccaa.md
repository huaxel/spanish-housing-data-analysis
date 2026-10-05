# Comunidades autónomas

```sql lista_ccaa
select distinct ccaa
from mart_ccaa_anual
where ccaa != 'Nacional'
order by 1
```

<Dropdown data={lista_ccaa} name=ccaa value=ccaa title="Comunidad"/>

```sql ficha
select anyo, viviendas_total, poblacion, pop_source, viv_por_1000_hab,
       hogares, viv_por_hogar, eur_m2_libre, renta_hogar_neta,
       afford_90m2_years, ipv_general, ipv_nueva, ipv_segunda_mano
from mart_ccaa_anual
where ccaa = '${inputs.ccaa.value}'
order by anyo
```

```sql provincias
select anyo, provincia, viv_por_1000_hab, share_no_principal
from mart_provincia_anual
where ccaa = '${inputs.ccaa.value}'
order by anyo, provincia
```

<LineChart
  data={ficha}
  x=anyo
  y=ipv_general
  title="IPV general (${inputs.ccaa.value})"
/>

<LineChart
  data={ficha}
  x=anyo
  y=viv_por_1000_hab
  title="Viviendas por 1.000 habitantes (${inputs.ccaa.value})"
/>

<LineChart
  data={ficha}
  x=anyo
  y=viv_por_hogar
  title="Viviendas por hogar (${inputs.ccaa.value}, desde 2021)"
/>

<LineChart
  data={ficha}
  x=anyo
  y=eur_m2_libre
  title="Valor tasado vivienda libre, €/m² (${inputs.ccaa.value})"
/>

<LineChart
  data={ficha}
  x=anyo
  y=afford_90m2_years
  title="Años de renta neta para 90 m² (${inputs.ccaa.value})"
/>

<LineChart
  data={provincias}
  x=anyo
  y=viv_por_1000_hab
  series=provincia
  title="Provincias: viviendas por 1.000 habitantes"
/>

<DataTable data={ficha}/>
