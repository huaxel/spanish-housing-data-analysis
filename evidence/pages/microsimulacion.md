---
title: Microsimulación distributiva · ECV 2025
---

<script>
  import { ajusteGrafico } from '../../components/chartOptions.js';
</script>

# Microsimulación distributiva de políticas de alquiler (ECV 2025)

¿Cuánto cuesta cada política de vivienda, a qué quintiles de renta llega y
cuántos hogares saca realmente de la sobrecarga (>40% de la renta neta)?

Esta página simula **en primera ronda estática** cinco palancas concretas sobre
los **29.263 hogares válidos** (3.660 inquilinos a precio de mercado) de los
microdatos oficiales de la **Encuesta de Condiciones de Vida (ECV 2025, INE)**,
aplicando exactamente el algoritmo de sobrecarga de Eurostat (`LC-ILC 39-09 rev.1`).

> **Límite metodológico clave:** es aritmética distributiva de primera ronda
> (sin respuesta de oferta ni movilidad residencial, salvo la sensibilidad
> explícita de traslación del 50% al alquiler en el Bono Joven). No se exportan
> microdatos: todas las celdas cumplen `>= 30` hogares y `>= 50` personas.

## 1. Comparación de escenarios (alquiler de mercado)

```sql esc_resumen
select scenario_name as "Escenario",
       overburden_40_mkt_pct as "Sobrecarga >40% (%)",
       effort_30_mkt_pct as "Esfuerzo >30% (%)",
       hh_lifted_out_40 as "Hogares que salen >40%",
       fiscal_cost_meur as "Coste fiscal (M€/año)",
       fiscal_eur_per_hh_lifted as "€/año por hogar rescatado",
       relief_to_q1_q2_pct as "Alivio a Q1–Q2 (%)"
from ecv_microsim.scenarios
```

<DataTable data={esc_resumen} rows=10 wrapTitles=true>
  <Column id="Escenario" />
  <Column id="Sobrecarga >40% (%)" fmt="num2" />
  <Column id="Esfuerzo >30% (%)" fmt="num2" />
  <Column id="Hogares que salen >40%" fmt="num0" />
  <Column id="Coste fiscal (M€/año)" fmt="num1" />
  <Column id="€/año por hogar rescatado" fmt="num0" />
  <Column id="Alivio a Q1–Q2 (%)" fmt="num1" />
</DataTable>

<EvidencePanel data={esc_resumen} chart="microsimulacion-escenarios"
  columns={["Escenario", "Sobrecarga >40% (%)", "Esfuerzo >30% (%)", "Hogares que salen >40%", "Coste fiscal (M€/año)", "€/año por hogar rescatado", "Alivio a Q1–Q2 (%)"]}
  files={["data/raw/ine_ecv_2025.zip"]}
  definition="Simulación estática de primera ronda sobre microdatos INE ECV 2025 (29.263 hogares válidos, ponderados por DB090/RB050) con umbral Eurostat >40% y esfuerzo >30%."
  coverage="Hogares en alquiler de mercado (HH021 = 3). Asume 100% de cobertura administrativa (take-up); los presupuestos reales con cupo reducen tanto el coste como el alcance." />

### Tres hallazgos inmediatos

1. **La traslación al precio casi duplica el coste efectivo del Bono Joven:**
   con 0% de traslación, el Bono Joven (250 €/mes, 18–35 años, renta ≤ 3× IPREM)
   cuesta **1.796 M€/año** a cobertura plena y saca a **202.337 hogares** de la
   sobrecarga (**8.878 €/hogar**). Si los propietarios capturan el 50% en rentas
   más altas, el coste por hogar rescatado salta a **15.714 €/año**.
2. **Un tope general (−5%, calibrado al rango empírico de Cataluña) es barato
   en presupuesto, pero poco focalizado:** sin gasto fiscal directo saca a
   **89.550 hogares** de la sobrecarga (`26,8% → 24,5%`), pero **el 52,7% del
   ahorro total en euros recae en los quintiles Q3–Q5** (solo el 47,3% llega a
   Q1–Q2), antes de descontar la caída de nuevos contratos observada en
   [Cataluña](/politica/).
3. **Un escudo progresivo de esfuerzo (tope 30% en Q1–Q2, máx. 400 €/mes)
   domina en eficiencia:** cuesta **3.866 M€/año** (menos que una ayuda plana de
   250 € a Q1–Q2: 5.116 M€), reduce la sobrecarga del alquiler de mercado del
   **26,8% al 10,1%** (**666.040 hogares** rescatados) y logra el menor coste
   por hogar rescatado (**5.804 €/año**).

## 2. Impacto por quintil de renta equivalente (Q1 = 20% más pobre, Q5 = 20% más rico)

```sql por_quintil
select quintile_label as quintil,
       scenario_name as escenario,
       post_over40_pct as sobrecarga_pct,
       delta_over40_pp as cambio_pp,
       relief_meur as alivio_meur
from ecv_microsim.by_quintile
order by quintile, scenario_id
```

<BarChart echartsOptions={ajusteGrafico()}
  data={por_quintil}
  x=quintil
  y=sobrecarga_pct
  series=escenario
  type=grouped
  yFmt="num1"
  title="Tasa de sobrecarga (>40%) en alquiler de mercado por quintil de renta (%)"
/>

<EvidencePanel data={por_quintil} chart="microsimulacion-quintiles"
  columns={["quintil", "escenario", "sobrecarga_pct", "cambio_pp", "alivio_meur"]}
  files={["data/raw/ine_ecv_2025.zip"]}
  definition="Tasa de sobrecarga (>40%) tras cada escenario por quintil de renta equivalente (escala OCDE modificada, ponderación RB050)."
  coverage="Inquilinos a precio de mercado (ECV 2025). Todas las celdas Q1–Q5 superan los umbrales mínimos de divulgación (>=30 hogares, >=50 personas)." />

```sql alivio_quintil
select quintile_label as quintil,
       scenario_name as escenario,
       relief_meur as alivio_meur
from ecv_microsim.by_quintile
where scenario_id != 'baseline'
order by quintile, scenario_id
```

<BarChart echartsOptions={ajusteGrafico()}
  data={alivio_quintil}
  x=quintil
  y=alivio_meur
  series=escenario
  type=grouped
  yFmt="num0"
  title="Ahorro / alivio anual recibido por los inquilinos por quintil (M€/año)"
/>

<EvidencePanel data={alivio_quintil} chart="microsimulacion-alivio-quintiles"
  columns={["quintil", "escenario", "alivio_meur"]}
  files={["data/raw/ine_ecv_2025.zip"]}
  definition="Volumen anual de ahorro efectivo para hogares inquilinos (M€/año) distribuido por quintil de renta equivalente."
  coverage="En Bono Joven (50% traslación), el alivio neto mostrado es la mitad del gasto fiscal; el resto se asume capturado por el alquiler." />

Ver también: [Evaluación de zonas tensionadas en Cataluña](/politica/) ·
[Registro de afirmaciones públicas](/afirmaciones/) ·
[Acceso y sobrecarga observada](/acceso/).
