# Precios, stock y población (2007–2025)

Evolución del precio de la vivienda (IPV, índice base 2025) frente a las
viviendas por cada 1.000 habitantes. Ámbito nacional; por CCAA en la
[página de comunidades](ccaa).

```sql nacional
select anyo, viviendas_total, poblacion, pop_source, viv_por_1000_hab,
       hogares, viv_por_hogar, eur_m2_libre, afford_90m2_years,
       pob_20_34, share_20_34, ipv_general, ipv_nueva, ipv_segunda_mano
from mart_ccaa_anual
where ccaa = 'Nacional'
order by anyo
```

<Value data={nacional} column=ipv_general agg=max/>
<Value data={nacional} column=viv_por_1000_hab agg=max/>

## El precio cae, el stock por habitante no

Entre 2007 y 2013 el IPV nacional cayó ~36% mientras las viviendas por cada
1.000 habitantes siguieron subiendo: el stock sobrevivió a la demanda y se
siguió terminando. A partir de 2014 los precios se recuperan con el stock
per cápita estancado. Co-movimientos descriptivos, no causalidad —
ver [métodos](../docs/methods.md) (en el repo).

<LineChart
  data={nacional}
  x=anyo
  y=ipv_general
  title="IPV general (índice, base 2025)"
/>

<LineChart
  data={nacional}
  x=anyo
  y=viv_por_1000_hab
  title="Viviendas por 1.000 habitantes"
/>

<LineChart
  data={nacional}
  x=anyo
  y=viv_por_hogar
  title="Viviendas por hogar (desde 2021)"
/>

<LineChart
  data={nacional}
  x=anyo
  y=eur_m2_libre
  title="Valor tasado vivienda libre (€/m²)"
/>

<LineChart
  data={nacional}
  x=anyo
  y=afford_90m2_years
  title="Años de renta neta para 90 m²"
/>

<LineChart
  data={nacional}
  x=anyo
  y=share_20_34
  title="Cuota de 20–34 años en la población"
/>

```sql nueva_segunda
select anyo, ipv_nueva, ipv_segunda_mano
from mart_ccaa_anual
where ccaa = 'Nacional'
order by anyo
```

<LineChart
  data={nueva_segunda}
  x=anyo
  y={['ipv_nueva', 'ipv_segunda_mano']}
  title="IPV nueva vs segunda mano"
/>

<DataTable data={nacional}/>
