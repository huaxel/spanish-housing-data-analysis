---
title: Escenarios de compra
---

# Comprar: efectivo inicial y cuota no son lo mismo

Un escenario hipotético para separar la entrada, los gastos y la carga de
la deuda. **No son condiciones de un banco, una estimación de compradores
reales ni una recomendación financiera.** Los valores iniciales son ejemplos
editables, no cifras observadas ni requisitos legales.
[Acceso a la vivienda](/acceso/) · [Panorama nacional](/).

## Supuestos editables

<Slider name=precio title="Precio de compra (€)" min=50000 max=1000000 step=5000 defaultValue=250000 showInput=true fmt="num0" size="full"/>
<Slider name=financiado title="Parte del precio financiada (%)" min=0 max=100 step=1 defaultValue=80 showInput=true fmt="num0" size="full"/>
<Slider name=plazo title="Plazo (años)" min=1 max=40 step=1 defaultValue=30 showInput=true fmt="num0" size="full"/>
<Slider name=tipo title="Tipo nominal anual fijo supuesto (%)" min=0 max=10 step=0.25 defaultValue=3 fmt="num2" size="full"/>
<Slider name=gastos title="Impuestos y gastos iniciales supuestos (% del precio)" min=0 max=20 step=0.5 defaultValue=10 fmt="num1" size="full"/>
<Slider name=ingresos title="Ingreso neto anual del hogar supuesto (€)" min=12000 max=180000 step=1000 defaultValue=36000 showInput=true fmt="num0" size="full"/>
<Slider name=ahorro title="Ahorro líquido disponible supuesto (€)" min=0 max=500000 step=1000 defaultValue=50000 showInput=true fmt="num0" size="full"/>
<Slider name=otras_deudas title="Otras cuotas de deuda mensuales (€)" min=0 max=3000 step=50 defaultValue=0 showInput=true fmt="num0" size="full"/>

La financiación se aplica al precio; **suponemos que no limita una tasación
inferior**. Un préstamo real puede usar otra base y exigir condiciones
adicionales. Los impuestos y gastos varían por comunidad, tipo de inmueble
y comprador: el porcentaje elegido agrupa todos los costes iniciales como
una hipótesis, no calcula impuestos específicos ni bonificaciones. No se
financian esos gastos en el escenario. El ahorro indicado debe ser la parte
que se quiere destinar a la compra; no reservamos un fondo de emergencia.

<!-- Inputs are bounded numeric Sliders, never free-text SQL. Cast and filter
     again so invalid/nonfinite values cannot produce a plausible result. -->
```sql supuestos_compra
with valores as (
  select try_cast('${inputs.precio}' as double) as precio,
         try_cast('${inputs.financiado}' as double) as financiado_pct,
         try_cast('${inputs.plazo}' as double) as plazo_anyos,
         try_cast('${inputs.tipo}' as double) as tipo_pct,
         try_cast('${inputs.gastos}' as double) as gastos_pct,
         try_cast('${inputs.ingresos}' as double) as ingreso_anual,
         try_cast('${inputs.ahorro}' as double) as ahorro,
         try_cast('${inputs.otras_deudas}' as double) as otras_deudas
)
select *, precio * financiado_pct / 100.0 as prestamo,
       precio - precio * financiado_pct / 100.0 as entrada,
       precio * gastos_pct / 100.0 as gastos_iniciales,
       ingreso_anual / 12.0 as ingreso_mensual,
       cast(plazo_anyos * 12 as integer) as meses
from valores
where precio between 50000 and 1000000
  and financiado_pct between 0 and 100
  and plazo_anyos between 1 and 40 and plazo_anyos = floor(plazo_anyos)
  and tipo_pct between 0 and 10
  and gastos_pct between 0 and 20
  and ingreso_anual between 12000 and 180000
  and ahorro between 0 and 500000
  and otras_deudas between 0 and 3000
```

```sql efectivo_compra
select precio, prestamo, entrada, gastos_iniciales,
       entrada + gastos_iniciales as efectivo_necesario,
       ahorro,
       greatest(entrada + gastos_iniciales - ahorro, 0) as falta_efectivo,
       greatest(ahorro - entrada - gastos_iniciales, 0) as ahorro_restante
from ${supuestos_compra}
```

## Antes de firmar: efectivo

<DataTable data={efectivo_compra} rows=1 emptyMessage="Supuestos inválidos: revisa los controles.">
  <Column id=precio title="Precio (€)" fmt="num0"/>
  <Column id=prestamo title="Préstamo (€)" fmt="num0"/>
  <Column id=entrada title="Entrada no financiada (€)" fmt="num0"/>
  <Column id=gastos_iniciales title="Gastos iniciales supuestos (€)" fmt="num0"/>
  <Column id=efectivo_necesario title="Efectivo necesario (€)" fmt="num0"/>
  <Column id=ahorro title="Ahorro disponible (€)" fmt="num0"/>
  <Column id=falta_efectivo title="Falta de efectivo (€)" fmt="num0"/>
  <Column id=ahorro_restante title="Ahorro restante (€)" fmt="num0"/>
</DataTable>

Una cuota compatible con los ingresos no elimina la barrera de la entrada.
El exceso de ahorro y la falta de efectivo se muestran por separado; no
interpretamos uno como negativo del otro ni como aprobación crediticia.

```sql cuotas_compra
with tipos as (
  select * from (values (0, 'Tipo elegido'), (1, 'Tipo + 1 pp'), (2, 'Tipo + 2 pp')) as t(aumento_pp, escenario)
), bases as (
  select s.*, t.*, s.tipo_pct + t.aumento_pp as tipo_escenario_pct,
         (s.tipo_pct + t.aumento_pp) / 1200.0 as tasa_mensual
  from ${supuestos_compra} s cross join tipos t
), pagos as (
  select *, case
    when prestamo = 0 then 0
    when tasa_mensual = 0 then prestamo / meses
    else prestamo * tasa_mensual / (1 - power(1 + tasa_mensual, -meses))
  end as cuota_mensual
  from bases
)
select escenario, aumento_pp, tipo_escenario_pct, meses, prestamo,
       ingreso_mensual, cuota_mensual, otras_deudas,
       100.0 * cuota_mensual / ingreso_mensual as cuota_ingreso_pct,
       100.0 * (cuota_mensual + otras_deudas) / ingreso_mensual as deuda_ingreso_pct,
       ingreso_mensual - cuota_mensual - otras_deudas as tras_deuda,
       cuota_mensual * meses as pagos_hipoteca_total,
       greatest(cuota_mensual * meses - prestamo, 0) as intereses_total
from pagos
order by aumento_pp
```

## Después: cuota e hipótesis de tipos

<DataTable data={cuotas_compra} rows=3 emptyMessage="Supuestos inválidos: no calculamos cuotas.">
  <Column id=escenario title="Escenario hipotético"/>
  <Column id=tipo_escenario_pct title="Tipo nominal anual (%)" fmt="num2"/>
  <Column id=cuota_mensual title="Cuota mensual (€)" fmt="num2"/>
  <Column id=otras_deudas title="Otras deudas al mes (€)" fmt="num2"/>
  <Column id=cuota_ingreso_pct title="Cuota / ingreso neto (%)" fmt="num1"/>
  <Column id=deuda_ingreso_pct title="Toda deuda / ingreso neto (%)" fmt="num1"/>
  <Column id=tras_deuda title="Ingreso tras cuotas (€)" fmt="num2"/>
  <Column id=intereses_total title="Intereses de toda la hipoteca (€)" fmt="num0"/>
</DataTable>

<BarChart data={cuotas_compra} x=escenario y=cuota_mensual
  yFmt="num0" title="Cuota mensual: tres tipos hipotéticos (€)"/>

Los aumentos son **puntos porcentuales**, no porcentajes relativos. Cada fila
es una hipoteca nueva con el mismo capital y plazo y un tipo constante durante
toda su vida: **no simula una revisión futura de una hipoteca variable**.
Utilizamos cuotas mensuales constantes con amortización francesa y tipo
nominal anual dividido entre meses. El tipo no es TAE: no añade comisiones,
seguros vinculados ni otros productos. No suponemos un umbral de aprobación.

El ingreso mensual es ingreso anual dividido en mensualidades iguales: no
modela pagas extraordinarias, inestabilidad laboral ni inflación. Ingreso
tras cuotas **no es dinero libre para ahorrar**: todavía faltan suministros,
comunidad, seguros, mantenimiento y todos los gastos de vida. El coste total
de intereses supone conservar la hipoteca hasta el final sin amortizaciones
anticipadas ni cambios de tipo. No se redondean cuotas antes de calcularlo.

## No confundir con los datos de sobrecarga

Aquí la cuota incluye **capital e intereses**, pero omite otros costes de
vivienda. Eurostat incluye suministros e intereses, no la devolución de
capital. Por tanto, el cociente cuota/ingresos de este escenario no es el
indicador EU-SILC y no permite contar hogares sobrecargados. Tampoco compara
compra y alquiler en coste económico total ni mide rentabilidad.

## Contexto regional, separado del escenario

Estas referencias observadas proceden de los marts existentes. **No alimentan
los controles ni el cálculo anterior**: una renta regional media no es la
renta de un comprador primerizo, y un valor tasado regional no es el precio
de una vivienda concreta. El mismo año económico se usa en ambas columnas.

```sql referencias_compra
select ccaa, anyo, eur_m2_libre, renta_hogar_neta
from housing.mart_ccaa_anual
where anyo = 2024
  and ccaa in ('Madrid, Comunidad de', 'Cataluña', 'Comunitat Valenciana')
order by ccaa
```

<DataTable data={referencias_compra} rows=3>
  <Column id=ccaa title="Comunidad (no ciudad)"/>
  <Column id=anyo title="Año económico" fmt="0"/>
  <Column id=eur_m2_libre title="Valor tasado medio (€/m²)" fmt="num0"/>
  <Column id=renta_hogar_neta title="Ingreso neto medio del hogar (€/año)" fmt="num0"/>
</DataTable>

Fuentes: MIVAU valor tasado e INE ECV, ingreso alineado con el año económico.
Medias, no distribuciones de compradores; no se atribuyen a cada municipio.

[Modelo, comprobaciones y límites](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/purchase_scenarios.md).
