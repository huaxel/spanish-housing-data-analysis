# Cadastre era profile vs SIM rehabilitation need per Sevilla barrio

Added 2026-10-09. Descriptive cross-check joining the property-weighted
construction-era profile ([cadastre eras](cadastre_eras.md)) with SIM's
estimated rehabilitation need and its year-like construction reference.
Artifact: `artifacts/cadastre_era_rehab.json` (exploration:
`explorations/cadastre_era_rehab.py`).

## Method

The era side is the same record-date proxy as the era exploration: each BU
record's earliest component construction year assigned to its declared
housing properties. The SIM side comes from the public EMVISESA/Ayuntamiento
SIM layers (see [barrios_sevilla](barrios_sevilla.md)):
`rehabilitacion_estimada_pct` (estimated share of dwellings in need of
rehabilitation, from an **undated** layer with **undocumented derivation**)
and `antiguedad_colectiva_anos` (a **year-like construction reference** for
collective housing, not elapsed age; snapshot year unknown). Every barrio
weighs equally. No causal claim, no significance testing.

Coverage: 107 barrios have an era profile, 108 have SIM rows, and **101
join** with a non-null rehabilitation value. Six era barrios lack a SIM
rehabilitation value (Macarena Tres Huertas-Macarena Cinco, El Prado-Parque
María Luisa, Las Almenas, Los Arcos, La Corza, Heliópolis); Valdezorras
(05061) is SIM-only.

## Findings

**Older-building barrios have systematically higher estimated rehabilitation
need.**

| Measure | Spearman | Pearson | n |
|---|---|---|---|
| Median construction year vs rehab need | −0.503 | −0.504 | 101 |
| Pre-1951 share vs rehab need | −0.383 | −0.218 | 101 |
| SIM construction reference vs rehab need | −0.555 | −0.560 | 101 |
| Cadastre median year vs SIM reference year | **+0.849** | +0.858 | 101 |

Two points deserve emphasis:

1. **Cross-validation of the two age measures.** The cadastre record-date
   proxy and SIM's independent year-like construction reference agree
   strongly (Spearman +0.849). Two unrelated data sources rank barrio
   housing age almost the same way, which raises confidence in the era
   profile as an age ordering despite its record-level limitations.

2. **The SIM rehab-age association may be partly mechanical.** SIM's own
   reference year correlates −0.555 with its rehab estimate. If the rehab
   estimate is derived from age and quality fields inside SIM, that
   correlation is co-derivation, not independent confirmation. The cadastre
   era profile, coming from a different source, makes the −0.503 correlation
   the more meaningful cross-check — same direction, slightly weaker.

**Rehabilitation need by median-year terciles** (mean SIM rehab %):

| Group | n | Median-year range | Mean rehab | Median rehab |
|---|---|---|---|---|
| Oldest third | 33 | 1943–1971 | 56.0 | 56 |
| Middle third | 35 | 1971–1978 | 50.1 | 53 |
| Newest third | 33 | 1978–2002 | **19.1** | 14 |

The gradient is not gradual: the middle tercile (median 1971–1978) is nearly
as needy as the oldest third, and the cliff falls between ~1978 and newer
stock.

**Highest estimated need (SIM 99–100%)** concentrates in 1960s–70s mass
housing north and east of the centre — El Cerezo, El Rocío, El Torrejón,
Polígono Norte, Zodiaco, San Pablo A y B, El Carmen, Los Pájaros, Las
Letanías — plus La Barzola (1943, 58.9% pre-1951). The pre-1951 historic
core (Casco Antiguo, Triana) is *not* among the extreme-need barrios: the
weaker pre-1951-share correlation (−0.383 Spearman, −0.218 Pearson)
reflects that split, echoing the non-monotone pattern of the
[age–rent gradient](cadastre_age_rent.md).

## Limitations

- SIM's rehabilitation estimate is an undated, undocumented-derivation
  indicator; its levels should not be read as measured shares of substandard
  housing, and any SIM-internal correlation may be mechanical.
- The SIM construction reference has no documented snapshot year and mixes
  collective-housing typologies; it is used here only as a rank ordering.
- The cadastre age is a record-date proxy (earliest component year per BU
  record weighted by declared properties), not observed dwelling age; see
  the [era profile limitations](cadastre_eras.md).
- Descriptive cross-section at barrio level: no causal claim, no
  significance testing, no adjustment for renovation, tenure or ownership.

## Relation to existing work

The [age–rent exploration](cadastre_age_rent.md) showed construction age
does not order rents. Here the same era profile *does* order estimated
rehabilitation need. Together: old stock splits into a maintained, expensive
core and a needy mid-century periphery — age alone does not determine
either outcome, but mid-century mass housing concentrates need.
