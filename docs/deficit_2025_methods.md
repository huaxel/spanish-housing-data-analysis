# Hogares, parque y terminadas: comprobaciones del saldo de 2025

Nota de métodos del [explorador de déficit](../evidence/pages/deficit.md).
El [método del explorador](deficit_explainer.md) documenta además los selectores,
la presentación de valores ausentes y la base DuckDB que alimenta las tablas.
Estos resultados adicionales no cambian esa base.

## Qué información comparten las dos medidas de oferta

El [README del parque del MIVAU](https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/Info/Readme_VDP002_01.pdf),
página 1, secciones «Descripción general» y «Periodicidad de actualización»,
explica que el Ministerio actualiza el parque a fin de diciembre a partir de los
censos. Incorpora viviendas terminadas y viviendas creadas por rehabilitación,
y da de baja las que desaparecen. La [ficha del programa estadístico para la
estimación de 2025](https://www.ine.es/dyngs/IOE/fichaProg.htm?cid=1259946014126)
confirma el anclaje en el Censo de Viviendas de 2021 y el uso de fuentes
administrativas para esas altas y bajas.

El mismo README identifica como fuentes la Estadística de Vivienda Libre, la
de Vivienda y Rehabilitación Protegidas, las licencias municipales y los visados
de dirección de obra. La suma de terminadas que restamos de los hogares usa
las estimaciones mensuales de vivienda libre del
[VDP005_01](https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/Info/Readme_VDP005_01.pdf)
y las calificaciones definitivas de vivienda protegida del
[VDP007_01](https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/Info/Readme_VDP007_01.pdf),
según el criterio de la tabla de actividad del boletín del Ministerio. El README
de vivienda libre describe estimación e imputación; el de protegida describe un
hito administrativo. Una celda publicada no equivale a un recuento comprobado
de viviendas que entraron ese mes en el mercado.

**La dependencia está documentada a nivel de las operaciones estadísticas.**
No encontramos en los documentos consultados una fórmula que permita seguir
cada celda mensual publicada hasta cada estimación provincial del parque, ni
identificar la contribución de las rehabilitaciones, bajas o revisiones a la
pequeña diferencia entre las series. Esa diferencia tampoco cuenta demoliciones.

## Octubre: composición de los hogares, no un nuevo saldo de parque

**El dato trimestral no actualiza el saldo.** A 1 de octubre de 2026, el
[INE estimó provisionalmente](https://ine.es/dyngs/Prensa/ECP3T26.htm)
**19.953.529 hogares** en viviendas familiares, **244.014 más** que un año
antes. De ese aumento neto, **220.295** correspondieron a hogares de una o
dos personas: algo más de nueve de cada diez. Es una diferencia entre
recuentos, no un seguimiento de hogares nuevos: un hogar puede cambiar de
tamaño sin cambiar de vivienda. No se combina esta cifra de octubre con el
parque de diciembre de 2025.

Madrid, Comunitat Valenciana, Andalucía y Cataluña sumaron el **64,74%**
del aumento neto entre octubre de 2025 y octubre de 2026. Pero el peso de
los hogares de una o dos personas no se limita a esas comunidades: en el
resto del país representaron el **98,34%** del aumento neto conjunto. Fueron
más de la mitad del aumento en los **19 territorios** (las comunidades
autónomas y Ceuta y Melilla). En cada comparación de octubre a octubre
desde la que termina en 2022, esto ocurrió en al menos **18 de los 19**.

Entre octubre de 2021 y octubre de 2026, los hogares de una o dos personas
pasaron del **55,96%** al **57,77%** del total nacional. Su proporción subió
en los **19 territorios**. Al descomponer el cambio, el aumento de la
proporción dentro de cada territorio aportó **+1,84 puntos porcentuales**;
el cambio en el peso de cada territorio en el total nacional restó **0,03
puntos**. El cálculo usa el promedio de los pesos y de las proporciones de
ambas fechas para separar ambos componentes. No identifica por qué cambió
el tamaño de los hogares.

**Más población y menos personas por hogar.** En esas mismas fechas, la
media bajó de **2,51** a **2,48 personas por hogar**. El cálculo divide
la [población en viviendas familiares del INE](https://www.ine.es/jaxiT3/Tabla.htm?t=60130)
por el número de hogares de la misma fecha, sin contar residentes en
establecimientos colectivos. En una descomposición contable, el menor tamaño
medio representa el **19,16%** del aumento neto de hogares entre octubre de
2021 y octubre de 2026, y el **30,28%** entre octubre de 2025 y octubre de
2026. El resto corresponde al aumento de la población en viviendas familiares.
Se promedian los dos órdenes posibles del cálculo (cambiar primero población
o tamaño). No estima cuántas viviendas hacen falta ni por qué se forman hogares.

**Más hogares incluso con menos residentes.** Entre octubre de 2021 y
2026 bajó el tamaño medio del hogar en **46 de 52 territorios**
([provincias, Ceuta y Melilla](https://www.ine.es/jaxiT3/Tabla.htm?t=60133)).
En Badajoz, Cáceres, Córdoba, Jaén y Zamora aumentó el
número de hogares pese a caer la población en viviendas familiares. En
Zamora, por ejemplo, el cambio fue de **+1.457 hogares** y **−2.437 residentes**.
En el último año de ese periodo, la misma divergencia se observó en Cáceres
y Melilla. Comparar solo la población habría pasado por alto ese aumento
del número de hogares; no dice si había viviendas disponibles para ellos.

## Enero y diciembre: comparaciones alineadas con el parque

Por territorio, el aumento de hogares con tamaño inicial fijo es
`(población final − población inicial) × hogares iniciales / población inicial`.
El saldo resta el cambio observado del parque total a ese resultado. La suma
de saldos territoriales conserva los negativos; solo el cálculo de concentración
suma los positivos. Para Ceuta y Melilla se agregan hogares y población antes
de calcular el tamaño medio, porque el parque se publica conjuntamente.

**¿Y si el tamaño medio del hogar no hubiera cambiado?** En la ventana
2021–2025, los hogares aumentaron más que el parque en **49 de 51**
unidades territoriales (Ceuta y Melilla cuentan juntas). Eso ocurrió también
en **5 de las 6** unidades donde cayó la población en viviendas familiares.
Aquí se usan los hogares y residentes de enero, no los de octubre, y se
comparan con el parque de diciembre de 2020 y de diciembre de 2025.

Si se aplica a la población final de cada territorio el tamaño medio de sus
hogares de enero de 2021, manteniendo el mismo parque publicado, el saldo
es positivo en **27 de 51**. Para la ventana 2021–2024, la misma comparación
pasa de **50** a **24**. Es un ejercicio contable: el parque incluye
viviendas no principales y esta comparación no mide cuántas viviendas
estaban disponibles, eran asequibles o hacían falta.

Al sumar los saldos territoriales de 2021–2025, la diferencia observada
entre el aumento de hogares y el del parque es **746.612**. Con el tamaño
medio inicial de cada territorio, la diferencia sería de unos **359.113**.
Si se usa en cambio un solo tamaño medio inicial para toda España, resulta
**368.210**. En ambos escenarios el parque se mantiene tal como se publicó:
solo cambia el cálculo del número de hogares. El saldo se reduce a cerca de
la mitad, pero sigue siendo positivo. No es un recuento de viviendas que faltan.

**Un saldo menor, pero más concentrado.** Madrid, Barcelona, Valencia y
Alicante tuvieron los mayores saldos positivos en ambas ventanas, también
al fijar el tamaño medio inicial de los hogares de cada territorio. En
2021–2025, su saldo conjunto bajó de **314.532** a unos **249.788**, pero su
peso en la suma de los saldos positivos subió del **42,10%** al **57,78%**:
el resto se redujo más. En 2021–2024, el peso pasó del **43,18%** al
**60,28%**. Estos porcentajes excluyen los saldos negativos del denominador;
no se calculan sobre el saldo neto nacional.

**El año 2025 por separado.** Entre enero de 2025 y enero de 2026, España
sumó **240.932 hogares**. Entre los diciembres inmediatamente anteriores,
el parque estimado creció en **94.791 viviendas**. La diferencia fue de
**146.141**. Si se fija el tamaño medio de los hogares de cada territorio
al de enero de 2025, la diferencia baja a unos **86.631**. Sigue siendo
positiva en **43 de 51** territorios, frente a **50 de 51** en los datos
observados. Este cálculo reinicia la referencia en enero de 2025: no se
obtiene restando los dos saldos acumulados con tamaño fijo de enero de 2021.

| Año natural | Hogares menos aumento del parque: observado | Con el tamaño de hogar de enero de ese año |
| --- | ---: | ---: |
| 2021 | +186.648 | −66.226 |
| 2022 | +188.926 | +139.332 |
| 2023 | +120.905 | +116.068 |
| 2024 | +103.992 | +94.359 |
| 2025 | +146.141 | +86.631 |

El saldo observado repuntó en 2025 tras dos años de descensos. El saldo con
tamaño fijo, en cambio, siguió bajando desde 2022. En cada fila se fija por
separado el tamaño de enero de cada territorio: los saldos observados se
pueden sumar, pero los de tamaño fijo no reproducen el escenario acumulado
con una única referencia inicial. Ninguno mide la necesidad de vivienda.

**De dónde sale el repunte.** Entre 2024 y 2025 el saldo aumentó en
**42.149**. El menor crecimiento del parque sumó **+7.531** al saldo.
El cambio de población, valorado al tamaño del hogar de enero de cada año,
aportó **−15.260**. La diferencia restante, asociada al cambio de tamaño
medio durante cada año, aportó **+49.878**. Es un desglose contable, no
causal. El saldo aumentó en **40 de 51** territorios; Madrid aportó
**+12.234**, el mayor aumento provincial.

**El repunte también aparece al restar las terminadas.** Las cifras
publicadas bajaron de **100.980** en 2024 a **93.650** en 2025. Al restarlas
al aumento de hogares, el saldo pasó de **105.334** a **147.282**, un
incremento de **41.948**, muy parecido al del saldo con el parque. Ambos años
tienen valores publicados en todas las celdas requeridas. Las terminadas no descuentan las bajas del parque. Además, el
Ministerio incorpora las terminadas al estimar el parque: la coincidencia
no constituye una validación independiente (véanse las fuentes más abajo).

Las dos restas también coinciden en la dirección del cambio en los
**51 territorios**: ambas aumentaron en **40**. Eso no quiere decir que
siempre den el mismo signo para el saldo de 2025. En Soria, la única
excepción ese año, el saldo fue de **+14** frente al crecimiento neto
del parque y de **−15** frente a las terminadas.

**La coincidencia no se debe solo a que ambas restas usan los mismos hogares.**
Al comparar las dos medidas de oferta por separado, el crecimiento neto del
parque y las terminadas se movieron en la misma dirección de 2024 a 2025 en
**50 de 51 territorios**. La única excepción fue Toledo: el crecimiento del
parque varió en **+19 viviendas**, y las terminadas en **−41**.
El ejercicio quita el componente de hogares compartido en la resta,
pero no la dependencia entre las dos fuentes de oferta.

El [piloto de ocupación de cuatro provincias](occupancy_province_pilot.md)
contrasta el parque total con la estimación de viviendas principales y con
el uso declarado en el IRPF. Ninguna de esas series mide la oferta disponible.

## Reproducción

```sh
uv run python explorations/ecp_households.py
uv run python explorations/ecp_households.py --check
uv run pytest -q tests/test_ecp_households.py
make audit
```

El artefacto `artifacts/ecp_households.json` separa `population_accounting`,
`local_family_accounting`, `aligned_stock_comparison`, `annual_gap_change` y
`completion_crosscheck_2024_2025`. La prueba de ventanas contrasta los extremos
con el CSV de parque y con el comparador ya verificado. La prueba de terminadas
recalcula los totales territoriales a partir de los dos CSV del Ministerio.
