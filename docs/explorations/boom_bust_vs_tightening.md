# Boom-bust vs tightening: two Spanish housing regimes

Computed by `explorations/boom_bust_tightening.py` from the pinned marts
(raw output: `artifacts/exploration_01.json`, git-ignored). Descriptive
co-movements only — no causal claims.

## Nacional snapshots

| año | IPV | €/m² libre | viv/1000 hab | viv/hogar |
| --- | --- | --- | --- | --- |
| 2007 | 83.2 | 2,056 | 531.7 | — |
| 2013 | 53.5 | 1,495 | 543.6 | — |
| 2019 | 69.3 | 1,641 | 562.7 | — |
| 2021 | 73.3 | 1,658 | 563.9 | 1.441 |
| 2025 | 100.0 | 2,128 | 551.6 | 1.388 |

## Regime 1 — bust (2007–2013): prices fall, stock doesn't

Every CCAA added dwellings, yet IPV fell 23–46%. The quality-adjusted index
fell *further* than appraisal levels almost everywhere (Cataluña −45.5% vs
−29.2%) — consistent with composition shift toward cheaper stock/areas, not
just cheaper homes. Per-capita stock rose in 14/17 CCAA (overbuilding +
depopulation, extreme in Galicia +49 and Castilla y León +46 per 1,000) but
*fell* in Cataluña, Madrid and Balears: population kept growing there even
as prices collapsed. Steepest price falls hit the big demand-collapse
markets (Cataluña, Aragón, Madrid, −42 to −46%); thinnest falls the interior
(Extremadura −23%).

## Regime 2 — tightening (2021–2025): households outrun construction

**Every CCAA built fewer dwellings than the households it added**
(0.23–0.90 dwellings per new household). Tightest: Comunitat Valenciana
(0.23), Canarias (0.25), Murcia (0.27), Cataluña (0.31). Loosest: Asturias
(0.90, still shrinking its household base slowly). Nationally viv/hogar fell
1.44→1.39 and viv/1000 fell 564→552 while IPV rose ~36%.

The cross-section is suggestive but not mechanical: Balears (+€1,147/m²) and
Madrid (+€1,009) combined mid-range absorption (0.5/0.47) with high demand;
Extremadura (+€76) barely moved despite 0.59. Prices reflect *who wants to
live where and with what credit*, not just unit counts — the next layer is
household size/age structure (ECP age detail is already fetched in raw JSON)
and, for levels-vs-incomes, an income source still to be pinned.

## Update: the overhang was one-fifth brand-new (`censo2011_vintage`)

2011 vacant stock by construction vintage: **22.3% built 2002–11** (768k
unsold boom flats), 29.4% from the 1960s–70s, the rest older. The bust
overhang was mostly *old* vacancy plus a new fringe — except in the boom
belt: Almería 45%, Toledo 42%, Guadalajara 39%, Alicante 33%, Castellón
29% of vacant stock brand-new. Where the cranes were, the overhang was
unsold product; elsewhere, structural vacancy.

## Limits of this cut

- 2021–2025 absorption uses ECP households (resident, family dwellings) vs
  MIVAU stock (all dwellings incl. second/vacant): ratio <1 partly reflects
  household shrinkage (fewer people per home), not pure shortage.
- CCAA grain hides Madrid-city vs Meseta, coast vs interior dynamics.
- No income/credit variables yet — affordability proper is out of reach.
