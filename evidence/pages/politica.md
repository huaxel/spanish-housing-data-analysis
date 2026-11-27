---
title: Política pública · Zonas tensionadas en Cataluña
---

<script>
  import { ajusteGrafico } from '../../components/chartOptions.js';
</script>

# Evaluación de política: zonas tensionadas en Cataluña (Ley 12/2023)

Cataluña activó el tope al alquiler de la Ley 12/2023 en dos olas escalonadas:
**Ola 1** (140 municipios, BOE-A-2024-5214, en vigor desde el 16 de marzo de 2024;
primer trimestre completo `2024Q2`) y **Ola 2** (131 municipios, BOE-A-2024-20576,
en vigor desde el 10 de octubre de 2024; primer trimestre completo `2024Q4`).

A diferencia de los anuncios de portales, los registros de **fiances del INCASÒL**
observan tres márgenes reales a la vez para los 947 municipios catalanes:
**renta contractual media**, **volumen de nuevos contratos habituales** y
**contratos de alquiler de temporada** (desde `2023Q1`).

> **Lectura principal:** los datos no respaldan ninguna caricatura simple. En los
> cuatro diseños cuasi-experimentales, las rentas contractuales firmadas caen
> entre **−3,8% y −6,2%** frente a controles, pero a la vez caen los nuevos
> contratos habituales firmados (**−10,7% a −12,6%** en los diseños más limpios)
> y sube la cuota de contratos de temporada (**+0,9 a +1,9 pp** en la Ola 1).

## 1. Trayectoria trimestral por ola (2019–2026T2)

```sql serie_olas
select wave_label, quarter_label, quarter_idx, rent_weighted_eur, rent_idx_2023,
       contractes_total, contracts_idx_2023, temporada_total, temporada_share_pct
from policy_eval.cat_group_series
order by quarter_idx, wave
```

<LineChart echartsOptions={ajusteGrafico()}
  data={serie_olas}
  x=quarter_label
  y=rent_idx_2023
  series=wave_label
  yFmt="num1"
  title="Renta contractual media ponderada por contratos (índice 2023 = 100)"
/>

<EvidencePanel data={serie_olas} chart="politica-renta-olas"
  columns={["wave_label", "quarter_label", "rent_weighted_eur", "rent_idx_2023"]}
  files={["data/raw/cat_incasol_municipis_trimestral_lloguer.xlsx", "data/raw/cat_incasol_municipis_trimestral_contractes.xlsx", "data/raw/boe_zmrt_cat_wave1.xml", "data/raw/boe_zmrt_cat_wave2.xml"]}
  definition="Media ponderada por contratos de la renta contractual mensual (INCASÒL), normalizada a la media de 2023 = 100 por ola BOE."
  coverage="Todos los municipios catalanes con renta publicada (>5 contratos/trimestre), 2019Q1–2026Q2. Son rentas de nuevos contratos depositados, no anuncios." />

<LineChart echartsOptions={ajusteGrafico()}
  data={serie_olas}
  x=quarter_label
  y=contracts_idx_2023
  series=wave_label
  yFmt="num1"
  title="Nuevos contratos habituales depositados (índice media 2023 = 100)"
/>

<EvidencePanel data={serie_olas} chart="politica-contratos-olas"
  columns={["wave_label", "quarter_label", "contractes_total", "contracts_idx_2023"]}
  files={["data/raw/cat_incasol_municipis_trimestral_contractes.xlsx", "data/raw/boe_zmrt_cat_wave1.xml", "data/raw/boe_zmrt_cat_wave2.xml"]}
  definition="Volumen trimestral de nuevos contratos habituales de alquiler depositados en el INCASÒL, base media trimestral 2023 = 100."
  coverage="947 municipios catalanes, 2019Q1–2026Q2. Una caída de nuevos contratos mezcla menor rotación de inquilinos, desvío a temporada y salidas del mercado." />

```sql serie_temporada
select wave_label, quarter_label, quarter_idx, temporada_total, temporada_share_pct
from policy_eval.cat_group_series
where temporada_share_pct is not null
order by quarter_idx, wave
```

<LineChart echartsOptions={ajusteGrafico()}
  data={serie_temporada}
  x=quarter_label
  y=temporada_share_pct
  series=wave_label
  yFmt="num1"
  title="Cuota de contratos de alquiler de temporada sobre el total (%)"
/>

<EvidencePanel data={serie_temporada} chart="politica-temporada-olas"
  columns={["wave_label", "quarter_label", "temporada_total", "temporada_share_pct"]}
  files={["data/raw/cat_incasol_temporada_mun.xlsx", "data/raw/cat_incasol_municipis_trimestral_contractes.xlsx", "data/raw/boe_zmrt_cat_wave1.xml", "data/raw/boe_zmrt_cat_wave2.xml"]}
  definition="Porcentaje de contratos de alquiler de temporada sobre la suma de contratos habituales y de temporada depositados en el INCASÒL."
  coverage="Serie municipal disponible desde 2023Q1 hasta 2026Q2. No incluye arrendamientos por habitaciones sin depósito separado." />

## 2. Estimaciones DiD y pruebas de falsación

Muestra restringida a **mercados activos** (municipios con al menos 12 trimestres
con renta publicada en 2019–2023: 139 Ola 1, 124 Ola 2, 64 no tensionados).
Todos los modelos absorben efectos fijos de municipio y trimestre (o `comarca ×
trimestre` en el diseño D), con errores agrupados por municipio y *wild cluster
bootstrap-t* (999 réplicas). El placebo adelanta el tratamiento 4 trimestres
(`2023Q2`) usando solo datos previos a la entrada en vigor.

```sql did_tabla
select design_label as "Diseño",
       outcome_label as "Resultado",
       effect_display as "Efecto",
       effect_unit as "Unidad",
       t_cr1v as "t (cluster)",
       wild_p as "p (wild)",
       placebo_t as "Placebo t (2023T2)",
       n_obs as "Obs."
from policy_eval.cat_did_summary
order by design_id, outcome_id
```

<DataTable data={did_tabla} rows=15>
  <Column id="Diseño" />
  <Column id="Resultado" />
  <Column id="Efecto" fmt="num2" />
  <Column id="Unidad" />
  <Column id="t (cluster)" fmt="num2" />
  <Column id="p (wild)" fmt="num3" />
  <Column id="Placebo t (2023T2)" fmt="num2" />
  <Column id="Obs." fmt="num0" />
</DataTable>

<EvidencePanel data={did_tabla} chart="politica-did-resumen"
  columns={["Diseño", "Resultado", "Efecto", "Unidad", "t (cluster)", "p (wild)", "Placebo t (2023T2)", "Obs."]}
  files={["data/raw/cat_incasol_municipis_trimestral_lloguer.xlsx", "data/raw/cat_incasol_municipis_trimestral_contractes.xlsx", "data/raw/cat_incasol_temporada_mun.xlsx", "data/raw/boe_zmrt_cat_wave1.xml", "data/raw/boe_zmrt_cat_wave2.xml"]}
  definition="Estimaciones de diferencias en diferencias (TWFE) por diseño y resultado, con p-valor wild bootstrap y placebo pre-tratamiento."
  coverage="Municipios activos (>=12 trimestres publicados en 2019–2023). Los diseños B y C muestran pre-tendencias significativas en contratos; anclar el volumen en diseños A y D." />

## 3. Estudio de eventos: Ola 1 frente a controles activos (`k = 0` es `2024Q2`)

```sql es_b_rent
select rel_q as trimestre_relativo, pct_approx as efecto_pct,
       round((exp(ci95_low) - 1) * 100, 2) as ic95_inf,
       round((exp(ci95_high) - 1) * 100, 2) as ic95_sup
from policy_eval.cat_event_study
where design_id = 'B_w1_vs_never' and outcome_id = 'log_rent'
order by rel_q
```

<LineChart echartsOptions={ajusteGrafico()}
  data={es_b_rent}
  x=trimestre_relativo
  y={['efecto_pct', 'ic95_inf', 'ic95_sup']}
  xAxisTitle="Trimestres desde 2024Q2 (ref. k = -1)"
  yFmt="num1"
  title="Estudio de eventos · Renta contractual (%), Ola 1 vs no tensionados"
/>

<EvidencePanel data={es_b_rent} chart="politica-es-renta"
  columns={["trimestre_relativo", "efecto_pct", "ic95_inf", "ic95_sup"]}
  files={["data/raw/cat_incasol_municipis_trimestral_lloguer.xlsx", "data/raw/boe_zmrt_cat_wave1.xml"]}
  definition="Coeficientes dinámicos del estudio de eventos en log(renta) convertidos a porcentaje aproximado, con IC 95% agrupado por municipio."
  coverage="Diseño B (Ola 1 vs no tensionados activos), k = -8..+8 respecto a 2024Q2. Referencia normalizada en k = -1 (2024Q1)." />

## Qué sí y qué no prueban estos datos

- **Qué sí muestran:** la contención de rentas contractuales (−3,8% a −6,2%) y la
  caída de nuevos contratos habituales (−10,7% a −12,6% en los diseños más limpios)
  coexisten con un repunte medible de contratos de temporada en la Ola 1.
- **Qué no separan:** una menor firma de contratos habituales mezcla **permanencia
  de inquilinos actuales** (menos rotación) con **retirada de viviendas del
  alquiler habitual**. Sin microdatos de duración contractual no puede atribuirse
  toda la caída de firmas a pérdida neta de oferta ocupada.
- **Estado de revisión:** módulo cuasi-experimental de trabajo; requiere lectura
  independiente antes de incorporarse a la síntesis principal. Ver
  [nota metodológica completa](https://github.com/huaxel/spanish-housing-data-analysis/blob/main/docs/explorations/catalonia_rent_control.md).
