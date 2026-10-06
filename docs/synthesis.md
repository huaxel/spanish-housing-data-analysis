# Synthesis: prices, stock, and people in Spain (2001–2025)

Core question: how has the evolution of Spanish housing prices related to
the amount of housing stock built and to population/household growth?
Evidence: 30 pinned sources, 20 mart tables, 24 explorations — all
descriptive, no causal claims (the one causal estimate is the commissioned
IV, separately qualified below). Start from the national spine, then the
split.

## The spine (Nacional)

| año | IPV | €/m² | viv/1000 | viv/hogar | 90 m² en años renta | hipotecas |
| --- | --- | --- | --- | --- | --- | --- |
| 2007 | 83 | 2,056 | 532 | — | 6.4 | 1,239k |
| 2013 | 54 | 1,495 | 544 | — | 5.2 | 200k |
| 2021 | 74 | 1,658 | 564 | 1.44 | 4.6 | 418k |
| 2025 | 100 | 2,128 | 552 | 1.39 | 4.4† | 498k |

†2024 income year (ECV lag). Source: `mart_ccaa_anual`, ccaa = Nacional.

Three regimes, three different price drivers:

1. **Boom–bust (2007–13): credit, not bricks.** Prices −36% while stock
   *grew* everywhere and per-capita stock *rose* (532→544). Mortgage counts
   fell 84%. The overhang narrative is backwards: the bust looks like a credit stop
   on top of mostly still-needed stock.
2. **Stagnation–recovery (2013–19): demography diverges.** Prices recover
   while the 20–34 cohort collapses 9.0M→7.7M and population stagnates.
   Per-capita stock peaks (564) — the only moment "too many homes" is
   arithmetically true, and only in emptying regions.
3. **Tightening (2021–25): households outrun everything.** Stock still grows
   (+380k), but households grow faster (+982k): 0.23–0.90 dwellings per new
   household in *every* CCAA. Per-capita and per-household stock fall while
   prices rise ~36% — against *rising* rates. This is the only regime where
   the naive supply story fits, and it fits everywhere at once.

The long arc in dwellings per household: 1.48 (2001, proxy) → 1.40 (2011)
→ 1.41 (2014) → 1.42 (2020) → 1.44 (2021) → 1.39 (2025). Fragmentation
loosened the 2000s, the bust left the loosest stock on record, the 2010s
reconsumed the slack one hundredth at a time, and the post-2021 surge in
household formation has now pushed past even the 2011 tightness — in the
opposite direction from prices in every regime but the last.

## Causal extension: migration exposure raises prices (commissioned IV)

First causal estimate in this project (design A from the identification
memo): shift-share instrument (1998 origin levels × leave-one-out
national waves) for foreign net inflow per 1,000 inhabitants →
valor-tasado YoY %, provincia panel 2002–2021, province + year FE,
SEs clustered by provincia (G=50).

| | base | + province trends | drop Madrid/Barcelona |
| --- | --- | --- | --- |
| 2SLS | +0.67 (0.11) | +0.76 (0.12) | +0.65 (0.12) |
| first-stage F | 47.7 | 56.3 | 35.5 |
| AR 95% set | [0.35, 1.00] | [0.40, 1.15] | [0.25, 1.05] |

One point faster inflow growth raises appraised prices ~0.7pp that year
— 4–5× the OLS association (+0.14), stable to trends and top-2
dominance. Candidate reasons: measurement attenuation in OLS
(inflows mixed with outflows/deaths/naturalizations), LATE compliers in
tight markets — or residual exclusion failure, which the trends spec
argues against but cannot kill. The pooled number is bust-driven:
2002–13 gives +0.84 (first-stage F = 88) while 2014–21 has no first
stage at all (F = 0.13 — post-crisis flows decoupled from 1998
settlement geography), so the recovery half of the story stays
descriptive. Full threats + read record in
[the IV note](docs/explorations/iv_migration.md); estimator machinery in
`src/spanish_housing/` (tested); numbers pinned in
`explorations/iv_results.json` (re-run reproduces it deterministically).

## The split (why national ratios mislead)

- **Madrid** (absolute scarcity): 429 dwellings/1000, 12% non-primary (2025; was 19% in 2007),
  young-migrant refill, worst affordability (6.2y). Municipally: capital
  +30% vs south never recovered nominally (Parla −13%, Fuenlabrada +0.5%
  in 18y) — and neither recovered really (capital −7.5%, south −28 to
  −38% in 2025 euros); 2011 south was already vacancy (Parla 6%,
  Torrejón 8%). Needs net new stock.
- **Coastal Valencia** (composition crisis, decomposed): 720+ dwellings/1000
  at 44–46% non-primary = a second-home coast (Torrevieja 51%, Benidorm 43%)
  *plus* vacant towns (Dénia 31%), tourist flats a 4.3% footnote. Needs
  mobilization, not just construction.
- **Barcelona** (burdened metropolis): city +65% sale / +68% rents 2013–24
  (+33% real — the recovery was real, unlike Madrid's), 51% rent burden,
  64% new-mortgage burden; corona more stretched (Sant Adrià 72%); 10k
  tourist flats in the city vs 28 in Santa Coloma; 514 starts in 13 years
  there. Built on absorbing a 10.9% 2011 vacancy. Within-municipio tourist
  changes don't track subsequent price/rent moves at all (municipal panel
  null, wild-p 0.45–0.94) — the footnote, confirmed.
- **Interior** (Galicia, Castilla y León, Asturias): 650–770/1000, shrinking
  young cohorts, mild prices — abundance without demand. The 2021
  electricity-based vacancy makes the abundance concrete: Galicia 28.8%
  vacant vs Madrid 6.3% (4.5×), and the vacancy share tracks the ratio
  rise across CCAA (Pearson +0.52, n=17).

## What predicts prices? Honestly: no single ratio

- Absorption ratio (built per new person): pooled rank −0.41 CCAA,
  −0.38 provincial (n=153, was −0.06 before the 2021–25 window became
  observable). The 2021–25 provincial window is the most negative yet
  (−0.42, CI [−0.64, −0.14]) — in the scarcity regime, provinces that
  built more per new person saw smaller price rises. Descriptor of
  regimes, not predictor — the denominator is demand itself.
- Provincial absorption panel (50 provinces × 2002–2025, first time past
  2021 thanks to the Censo Anual extension): negative everywhere, wild-
  robust nowhere (S0 −0.025, wild-p 0.42; S1 2021–25 −0.21, wild-p 0.55)
  — consistent with the CCAA panel: the naive t overstates precision.
- The two-group ratio split: national viv/1000 flatness hides scarcity CCAA
  (Madrid −29.7, Cataluña −27.6) vs overstock (+100…+130 interior), and
  the **electricity-based vacancy** (2021 census, 59531) confirms the
  overstock is objectively empty: Galicia 28.8% vacant vs Madrid 6.3%.
- Rents (SERPAVI, municipal 2011–2024): DIBA cross-validated (Pearson
  0.825); gross yield 3.6% in Barcelona vs 4.6% corona median; tourist
  intensity does not predict rents at any grain (municipal null,
  provincial level = scale artifact, Spearman 0.016).
- Credit volumes track the bust; household formation tracks the tightening;
  incomes outran prices over the full period (affordability 6.2→4.4 years
  despite record prices) while concentrating pain in magnets.
- The missing covariates, in order: LTV/effort distributions, age×income
  joint detail, transaction prices at municipal grain (the repo has
  appraisal + DIBA transactions; valor-referencia and construction-flow
  probes are parked with reopen conditions).

## Reproduce everything

`make gates` rebuilds marts from pinned inputs; `explorations/*.py`
regenerate every number above into `artifacts/`; each claim links to a
script, a mart column, and a methods section. That chain — not any single
chart — is the deliverable.
