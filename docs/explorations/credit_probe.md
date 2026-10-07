# Credit-supply probe: is there a public Cajas-exposure series? (2026-10-07)

Feasibility probe for the design the IV reads kept pointing at: territorial
variation in Cajas de Ahorros credit expansion (2002–07) and sudden stop
(2008–13) as the confounder — or the treatment — behind the migration→price
gradient. Question: does a **public** Cajas × provincia × time credit series
exist? Verdict: **no — blocked without confidential microdata or archival
branch-share reconstruction.**

## What exists and why it is not enough

- **INE Hipotecas press releases** (monthly, the source of our `hip_*`
  mart columns): lender split (bancos / cajas / otras) at **CCAA grain
  only** (e.g. Jan-2012 release: national 64.7/18.9/16.4%). No provincial
  lender split, ever.
- **BdE Boletín Estadístico ch. 4** (supervisory returns): cuadros 4.28/4.29
  give provincial credit/deposit **totals**; instrument detail (4.5/4.3)
  without lender × province cross. The lender dimension and the province
  dimension never meet in a public table.
- **Our marts**: mortgage counts/tickets by provincia (INE, from 2003),
  national rates only (from 2009). No lender split at any grain.
- **Literature** (e.g. bank-consolidation work on 2007–11): uses the BdE
  **Central Credit Register + confidential supervisory returns** —
  province-level Cajas market shares, 1995 branch networks, FROB-era
  consolidation maps. None of it public. The commonly cited cross-section
  fact (cajas ≈ 40% of banking assets end-2009; 217BE construction
  exposure, ~100BE problematic; 37→12 cajas in 13 months) has no public
  provincial panel behind it.

## The one unblocked path (archival, not commissioned)

Pre-1989 branching restrictions + the 1989 liberalization mean 1995
Cajas branch shares by province would proxy pre-boom exposure — the
literature uses exactly this (Jan-1995 shares). Source would be CECA
Anuarios Estadísticos (paper, likely in BdE/BNE libraries), requiring
hand digitization province by province. Real work, uncertain payoff, and
branch share ≠ mortgage-flow share (Cajamar/Almería-style rural-co-op
markets break the mapping: Almería is cooperativa-dominated at 36.5%).

## Recommendation

Do not commission a credit-supply IV yet. Two honest options: (a) a
library/archive sprint for CECA 1995 branch shares, scoped as its own
probe with a kill criterion (no usable series in one sprint → park);
(b) treat the credit cycle as the descriptive half it already is
(`credit_cycle.md`) and keep the causal program parked. The migration IV
reads already tell us the confounder's address — we just cannot meter it
from public data.
