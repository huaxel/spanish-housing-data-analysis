# Cadastre era profile vs SIM building-condition scores per Sevilla barrio

Added 2026-10-09. Descriptive cross-check joining the property-weighted
construction-era profile ([cadastre eras](cadastre_eras.md)) with SIM's
`calidad_colectiva` / `calidad_unifamiliar` scores and the rehabilitation
estimate. Artifact: `artifacts/cadastre_era_quality.json` (exploration:
`explorations/cadastre_era_quality.py`).

## Method

The era side is the same record-date proxy as the era exploration. The SIM
side comes from the public SIM layers (see
[barrios_sevilla](barrios_sevilla.md)); the scores have no documented
derivation, scale direction or reference year. Every barrio weighs equally.
No causal claim, no significance testing.

Coverage: **107 barrios** join with `calidad_colectiva` (no nulls);
`calidad_unifamiliar` covers only **77** (30 null barrios, listed in the
artifact). The rehabilitation estimate joins for 101 barrios as in the
[rehabilitation cross-check](cadastre_era_rehab.md).

## Findings

**The SIM quality score and the SIM rehabilitation estimate are
near-collinear — they are not independent measures.**

| Measure | Spearman | Pearson | n |
|---|---|---|---|
| `calidad_colectiva` vs SIM rehab estimate | **+0.874** | +0.865 | 101 |
| Median construction year vs `calidad_colectiva` | −0.277 | −0.224 | 107 |
| Median construction year vs `calidad_unifamiliar` | −0.119 | −0.042 | 77 |

A score of 7 is the top of the observed `calidad_colectiva` range (3.2–7.0).
Empirically, higher scores sit in barrios with higher estimated
rehabilitation need, so whatever "calidad" denotes in SIM's internal scale,
it tracks *need/deficiency*, not condition quality in the everyday sense —
or the rehab estimate is derived from it. Either way, the +0.874
correlation means the SIM rehab check in the
[rehabilitation exploration](cadastre_era_rehab.md) and this score cannot
count as two independent confirmations of anything.

**Age ordering is present but weaker than for rehabilitation need.**
Mean `calidad_colectiva` by median-year terciles: oldest 5.37, middle 5.29,
newest 4.86 — a gentle monotone gradient (older → higher score → tracks
more need), compared with the steeper rehab gradient (56/50/19) in the
rehabilitation exploration.

**Extremes overlap the rehabilitation top list exactly.**

| Lowest scores (tracks least need) | Score | Median year |  | Highest scores | Score | Median year |
|---|---|---|---|---|---|---|
| El Prado-Parque María Luisa | 3.24 | 1950 |  | La Barzola | 7.0 | 1943 |
| San Bernardo | 3.56 | 1994 |  | Polígono Norte | 7.0 | 1966 |
| Tabladilla-La Estrella | 3.59 | 1981 |  | Las Letanías | 6.99 | 1972 |
| La Buhaira | 3.69 | 1979 |  | El Carmen | 6.98 | 1963 |
| El Porvenir | 3.75 | 1980 |  | San Pablo A y B | 6.93 | 1963 |

The five highest-score barrios are the same 99–100% rehab-need barrios
identified before. The low-score list is mostly 1979–1994 construction;
El Prado (1950) is the one old-stock outlier with a low score and a missing
rehab value.

## Limitations

- SIM's score has no documented derivation, direction or reference year;
  the direction statement above is empirical (via the rehab collinearity),
  not sourced.
- Near-collinearity with the rehab estimate forbids treating SIM's age,
  quality and rehab fields as independent variables of a single indicator
  family.
- The cadastre age is a record-date proxy, not observed dwelling age; see
  the [era profile limitations](cadastre_eras.md).
- `calidad_unifamiliar` covers only 77 barrios and correlates weakly with
  age; no conclusion is drawn from it.

## Relation to existing work

This closes the triad started by the [age–rent](cadastre_age_rent.md) and
[rehabilitation](cadastre_era_rehab.md) explorations: construction age does
not order rents, orders rehabilitation need strongly, and orders the SIM
condition score weakly — with the caveat that the last two measures are the
same underlying SIM information.
