---
title: Incertidumbre
---

# No detectar no es demostrar ausencia

Los cuatro modelos municipales de turismo en Barcelona ilustran la
diferencia entre una estimación pequeña, un intervalo de incertidumbre y
una prueba que no rechaza cero. **Ninguno identifica un efecto causal.**
[Acceso a la vivienda](/acceso/) · [Panorama nacional](/).

## Tamaño y precisión, sin elegir la especificación más favorable

```sql modelos_turismo
select model_key, outcome, specification, b, se, normal_lo, normal_hi,
       wild_p_zero, n, clusters, bootstrap_reps
from inference.tourism_panel
order by outcome, specification
```

<DataTable data={modelos_turismo} rows=4>
  <Column id=outcome title="Resultado"/>
  <Column id=specification title="Controles"/>
  <Column id=b title="Coeficiente (pp)" fmt="num3"/>
  <Column id=se title="SE agrupado (pp)" fmt="num3"/>
  <Column id=normal_lo title="Rango normal aprox. 95%: inferior (pp)" fmt="num3"/>
  <Column id=normal_hi title="Rango normal aprox. 95%: superior (pp)" fmt="num3"/>
  <Column id=wild_p_zero title="Wild-p: H₀ coeficiente = 0" fmt="num3"/>
  <Column id=n title="Observaciones municipio-año" fmt="num0"/>
  <Column id=clusters title="Municipios (grupos)" fmt="num0"/>
</DataTable>

**Unidades:** puntos porcentuales de crecimiento interanual del precio de
venta o alquiler, por una vivienda turística registrada adicional por cada
1.000 habitantes respecto al año anterior. No son euros por m², porcentajes
de nivel de precios ni un efecto de retirar todas las viviendas turísticas.
La exposición cambia también cuando cambia la población; no equivale
necesariamente a una nueva licencia.

Municipio y año tienen efectos fijos; la segunda especificación añade
crecimiento de población. Los errores estándar se agrupan por municipio.
Los intervalos de la tabla son los ya publicados por el estimador:
coeficiente ± 1,96 errores estándar (CR1). Son **aproximaciones normales**,
no intervalos invertidos de la prueba wild-bootstrap ni rangos causales.
Cada intervalo es individual: no hay cobertura conjunta de los cuatro.

El wild-p aplica una prueba bilateral de coeficiente cero con bootstrap de
residuos agrupados, imponiendo esa hipótesis nula. No es la probabilidad de
que el coeficiente sea cero. Sus percentiles de estadísticos t bajo cero
**no son percentiles del coeficiente**; no los convertimos en un intervalo
bootstrap de efectos.

## Sensibilidad a una magnitud elegida, no prueba de equivalencia

<Slider name=magnitud title="Magnitud exploratoria por unidad de exposición (pp)"
  min=0.1 max=2 step=0.1 defaultValue=0.5 fmt="num1" size="full"/>

El valor inicial es ilustrativo y editable, **no un umbral económico
preespecificado**. Cambiarlo después de ver resultados no establece efectos
pequeños. Para una conclusión de equivalencia harían falta una magnitud
justificada antes del análisis y una prueba con inferencia adecuada.

```sql banda_turismo
with limite as (
  select try_cast('${inputs.magnitud}' as double) as margen_pp
)
select m.outcome, m.specification, l.margen_pp,
       m.normal_lo, m.normal_hi,
       greatest(abs(m.normal_lo), abs(m.normal_hi)) as extremo_absoluto_pp,
       case when m.normal_lo >= -l.margen_pp and m.normal_hi <= l.margen_pp
            then 'Sí: solo rango normal aproximado'
            else 'No: rango normal aproximado rebasa la banda' end as contenido_en_banda
from ${modelos_turismo} m cross join limite l
where l.margen_pp between 0.1 and 2
order by m.outcome, m.specification
```

<DataTable data={banda_turismo} rows=4 emptyMessage="Magnitud inválida: revisa el control.">
  <Column id=outcome title="Resultado"/>
  <Column id=specification title="Controles"/>
  <Column id=margen_pp title="Banda simétrica elegida (±pp)" fmt="num1"/>
  <Column id=extremo_absoluto_pp title="Extremo absoluto del rango normal (pp)" fmt="num3"/>
  <Column id=contenido_en_banda title="¿Rango normal dentro de la banda?"/>
</DataTable>

Es una comparación geométrica de intervalos, **no una prueba de equivalencia,
un cálculo de potencia ni una conclusión bootstrap**. Si el rango rebasa
la banda, esta aproximación no descarta asociaciones fuera de ella. Si está
contenido, tampoco demuestra un efecto causal pequeño: el diseño, la
medición y la inferencia siguen limitándolo. No se recomputan regresiones
al mover el control.

## Inversión en magnitudes candidatas: puntos probados

Para cada valor candidato `c` probamos `H₀: coeficiente = c` con el mismo
bootstrap wild de residuos agrupados que la columna anterior (Rademacher por
municipio, 1.999 réplicas, semilla fija). La rejilla se fijó **antes de esta inversión** — no es un registro previo a
examinar los resultados ya publicados del panel —: de **-2,0 a +2,0** puntos
porcentuales en pasos de **0,1** (41 candidatos), simétrica y mayor que
cualquier rango normal publicado. Una
única secuencia de perturbaciones se reutiliza para todos los candidatos
(números aleatorios comunes), de modo que los p-valores son comparables.

```sql inversion_modelos
select distinct model_key,
       outcome || ' · ' || specification as modelo_label
from inference.tourism_inversion
order by outcome, model_key
```

<Dropdown data={inversion_modelos} name=inv_modelo value=model_key
  label=modelo_label title="Modelo" defaultValue="sale_tour_only"/>

```sql inversion_candidatos
select candidate_c, wild_p,
       case when keep_95 then 'No rechazada' else 'Rechazada' end as decision_95
from inference.tourism_inversion
where model_key = '${inputs.inv_modelo.value}'
order by candidate_c
```

<DataTable data={inversion_candidatos} rows=41>
  <Column id=candidate_c title="Magnitud candidata c (pp)" fmt="num2"/>
  <Column id=wild_p title="Wild-p de H₀: coeficiente = c" fmt="num3"/>
  <Column id=decision_95 title="Nivel nominal 95%" align=center/>
</DataTable>

```sql inversion_resumen
select outcome, specification, b, se,
       accepted_min_c, accepted_max_c, accepted_count, warnings
from inference.tourism_inversion_meta
order by outcome, specification
```

<DataTable data={inversion_resumen} rows=4>
  <Column id=outcome title="Resultado"/>
  <Column id=specification title="Controles"/>
  <Column id=b title="Coeficiente (pp)" fmt="num3"/>
  <Column id=se title="SE agrupado (pp)" fmt="num3"/>
  <Column id=accepted_min_c title="Menor c no rechazado (pp)" fmt="num3"/>
  <Column id=accepted_max_c title="Mayor c no rechazado (pp)" fmt="num3"/>
  <Column id=accepted_count title="Candidatos no rechazados" fmt="num0"/>
  <Column id=warnings title="Avisos de rejilla"/>
</DataTable>

El candidato `c = 0` reproduce exactamente el `wild_p_zero` de la primera
tabla: es la misma prueba con la misma semilla y réplicas. Una celda marcada
«No rechazada» significa que la prueba wild no rechaza esa magnitud al nivel
nominal del 5%; el rango `[accepted_min_c, accepted_max_c]` es el de los
puntos probados no rechazados. **Esto es una lista de puntos probados, no un
intervalo de confianza continuo**: no interpolamos entre candidatos, no lo
convertimos en un rango causal de efectos, y no es una prueba de equivalencia
ni de que «no haya efecto». Si el conjunto aceptado toca un extremo de la
rejilla, el aviso indica que puede extenderse más allá; si ningún candidato
fue aceptado, no hay puntos probados que declarar (nulo, no cero).

## Cuántas viviendas turísticas estima el INE

El panel de Barcelona emplea viviendas turísticas de la DIBA por habitante.
Por separado, la [estadística experimental del INE](https://www.ine.es/experimental/viv_turistica/experimental_viv_turistica.htm)
estima **stock**: en mayo de 2026, **341.001 viviendas turísticas** (**1,28%** de
las viviendas censadas) y 1.714.702 plazas. Entre los municipios con un
porcentaje positivo publicado y código municipal, la mediana es
**0,61%**, el percentil 90 llega a **3,38%** y el máximo a **33,33%**; el
**5,30%** supera el 5%. Los diez mayores stocks concentran el **18,47%** del
total asignable (Madrid, 10.836).

El INE filtra anuncios de plataformas y elimina duplicados. Puede incluir
alojamientos sin licencia y omitir otros que no se anuncian en las plataformas
observadas: no es un registro de licencias ni un mínimo garantizado. Los
**8.131 códigos municipales** del fichero del INE coinciden con los del mapa
del proyecto y cubren el **100%** de la estimación publicada de mayo. Es
cobertura geográfica del dato, no cobertura del mercado ni de las rentas.
Estas cifras no identifican un efecto sobre el alquiler residencial.
Detalle en la [nota metodológica](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/vut_stock.md).
En el [cruce nacional por código municipal](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/vut_rent_overlap.md),
la relación con el alquiler de SERPAVI es más clara en niveles que en cambios.
Entre 2022 y 2024, en los **703 municipios** donde se observan ambas medidas de
alquiler, la correlación de rangos entre el cambio del porcentaje de viviendas
turísticas y el crecimiento del alquiler es **0,120** con SERPAVI y **0,104**
con el índice de precios del INE (IPVA). Ese periodo cruza un cambio de censo.
Si se divide el aumento o descenso del número de viviendas turísticas por un
mismo parque municipal (el del censo de 2021), las correlaciones suben a
**0,167** y **0,133**, respectivamente, en los mismos municipios. La relación
sigue siendo débil también al excluir Andalucía, donde el INE revisó el
recuento de agosto de 2024. Al separar los periodos tampoco aparece una
relación de signo estable: para el mismo crecimiento del alquiler de 2023 a
2024, la correlación es ligeramente negativa con el cambio turístico de 2020
a 2021 y ligeramente positiva con el de 2021 a 2022, tanto con SERPAVI como
con IPVA. Si se mide el cambio neto de agosto de 2020 a agosto de 2022 en
esos mismos municipios, sin usar el recuento intermedio, la correlación con
el crecimiento del alquiler de 2023 a 2024 se acerca a cero en ambas series.
Ninguno de estos contrastes estima el efecto de las viviendas
turísticas sobre los precios.

## Dos series oficiales de alquiler que no coinciden en magnitud

En los **701 municipios** con datos en 2019 y 2024, la mediana de las subidas
es **+11,62%** según el índice de precios de alquiler del INE (IPVA) y
**+22,09%** según la renta mediana por metro cuadrado de vivienda colectiva
(SERPAVI). El orden de las subidas es parecido (Spearman **0,758**), pero la
brecha mediana dentro de cada municipio es de **−10,64 puntos porcentuales**
(IPVA menos SERPAVI). El IPVA incluye también viviendas unifamiliares. Ambas
estadísticas usan fuentes tributarias: ni su acuerdo prueba que sean dos
mediciones independientes ni la brecha identifica su causa. Véanse los
[otros periodos y el cruce por código municipal](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/ipva_rent_index.md).

## ¿El saldo del registro de fianzas mide el aumento de vivienda alquilada?

Otra comprobación entre medidas, esta vez del lado del registro. Los saldos de
fianzas de INCASÒL cuentan altas y bajas; SERPAVI cuenta contratos declarados
en el IRPF. Si el primero estimara el cambio anual del segundo, ambas series
se moverían juntas. No lo hacen.

| Barcelona, alquiler habitual | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Saldo neto de fianzas (INCASÒL) | +3.586 | −4.820 | +9.661 | +9.073 | +6.510 | +2.724 |
| Cambio de contratos declarados (SERPAVI) | +2.742 | +2.414 | +3.419 | +2.689 | +4.766 | +2.630 |

Coinciden una sola vez (**2024**, a **94** de distancia) y discrepan en el
resto; en 2020 el registro perdió contratos mientras el stock declarado
crecía. El saldo supera en magnitud al cambio del stock en todos los años
solapados, así que tampoco sirve como estimación escalada. Miden cosas
distintas —altas y bajas registradas frente a contratos vigentes en un año
fiscal— y no se publica ninguna reconciliación: léase el saldo como actividad
registral, no como aumento de vivienda alquilada. Véanse los
[saldos por año](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/occupancy_catalonia_deposit_balances.md).

## Qué sigue sin resolverse

- Las licencias responden a demanda y regulación; la asociación ajustada
  no identifica qué ocurriría con otra política turística.
- Las restricciones de licencias reducen la variación disponible; los
  registros no captan toda la actividad ni las camas ocupadas.
- Venta y alquiler usan muestras distintas y solo Barcelona. Los análisis
  provinciales SERPAVI son otro diseño, no una réplica nacional del panel.
- La incertidumbre muestral no incluye errores de registro, cambios de
  composición de contratos ni sesgos sistemáticos del modelo.
- Las correlaciones municipales o provinciales no reciben intervalos
  inventados a partir de estos cuatro modelos.

La inversión de pruebas bootstrap sobre la rejilla preespecificada está
implementada en la sección anterior: publica solo los puntos probados y sus
avísos, sin inventar intervalos continuos ni reestimar los modelos. Aquí
seguimos mostrando únicamente inferencia ya calculada y sus límites; **los
cuatro modelos no se han reestimado**.

[Fuente, derivación y verificación](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/uncertainty.md).

---
*Instantánea de datos: 2026-10-09 · cuatro modelos municipales de turismo, Barcelona · [fuentes y métodos](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/uncertainty.md).*
