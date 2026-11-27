---
title: Registro de afirmaciones públicas
---

# Registro de afirmaciones sobre vivienda en España

El debate público sobre vivienda gira en torno a media docena de cifras que se
repiten sin su definición. Este registro contrasta las siete afirmaciones más
habituales directamente contra las series oficiales fijadas en el repositorio y
muestra **qué definición cambia la respuesta**.

Cada fila enlaza a su página de análisis completo y expone sus fuentes exactas
en el panel de evidencia.

## 1. Veredicto por afirmación

```sql ledger_claims
select topic as "Tema",
       public_claim as "Afirmación habitual",
       verdict as "Veredicto",
       pinned_finding as "Dato fijado en el repositorio",
       what_breaks_claim as "Dónde falla o se matiza",
       deep_dive_path as "Análisis"
from claim_ledger.claims
order by claim_id
```

<DataTable data={ledger_claims} rows=10 wrapTitles=true>
  <Column id="Tema" />
  <Column id="Afirmación habitual" />
  <Column id="Veredicto" />
  <Column id="Dato fijado en el repositorio" />
  <Column id="Dónde falla o se matiza" />
  <Column id="Análisis" contentType=link />
</DataTable>

<EvidencePanel data={ledger_claims} chart="afirmaciones-veredictos"
  columns={["Tema", "Afirmación habitual", "Veredicto", "Dato fijado en el repositorio", "Dónde falla o se matiza"]}
  files={["data/raw/parque_viviendas.csv", "data/raw/ipv_ccaa_anual.json", "data/raw/censo2021_intensidad.csv", "data/raw/cat_incasol_municipis_trimestral_lloguer.xlsx", "data/raw/cat_incasol_municipis_trimestral_contractes.xlsx"]}
  definition="Contrastación directa de siete afirmaciones del debate público contra marts DuckDB y artefactos fijados por SHA-256."
  coverage="Datos oficiales INE, MIVAU e INCASÒL (2001–2026T2 según serie). Ninguna cifra se extrapola fuera de su ámbito territorial o temporal." />

## 2. Puentes metodológicos: por qué cambian las cifras según la definición

Cuando dos informes oficiales o dos titulares citan números distintos sobre el
mismo problema, la diferencia casi siempre está en la ventana temporal, el
denominador o la definición del concepto (neto vs bruto, nominal vs real, media
nacional vs territorio).

```sql ledger_bridges
select c.topic as "Tema",
       b.definition as "Definición / especificación",
       b.value_num as "Valor",
       b.unit as "Unidad",
       b.why_it_differs as "Por qué cambia la lectura"
from claim_ledger.claim_bridges b
join claim_ledger.claims c on c.claim_id = b.claim_id
order by b.claim_id, b.definition
```

<DataTable data={ledger_bridges} rows=20 wrapTitles=true>
  <Column id="Tema" />
  <Column id="Definición / especificación" />
  <Column id="Valor" fmt="num2" />
  <Column id="Unidad" />
  <Column id="Por qué cambia la lectura" />
</DataTable>

<EvidencePanel data={ledger_bridges} chart="afirmaciones-puentes"
  columns={["Tema", "Definición / especificación", "Valor", "Unidad", "Por qué cambia la lectura"]}
  files={["data/raw/parque_viviendas.csv", "data/raw/censo2021_intensidad.csv", "data/raw/cat_incasol_municipis_trimestral_lloguer.xlsx", "data/raw/cat_incasol_temporada_mun.xlsx"]}
  definition="Tabla de conciliación que compara definiciones alternativas de déficit, vacancia, asequibilidad y control de alquileres."
  coverage="Todos los valores proceden de los marts locales verificados por scripts/build_claim_ledger.py --check." />

## Cómo citar o auditar este registro

Todas las cifras de esta página se regeneran de forma determinista con
`uv run python scripts/build_claim_ledger.py` y se verifican contra los marts
con `scripts/build_claim_ledger.py --check`. Ver también:
[Déficit](/deficit/) · [Vacancia 2021](/vacancia/) · [Zonas tensionadas en Cataluña](/politica/) · [Microsimulación ECV](/microsimulacion/).
