# Synthesis: prices, stock, and people in Spain (2001–2025)

Core question: how has the evolution of Spanish housing prices related to
the amount of housing stock built and to population/household growth?
Evidence: five pinned sources, two marts, four explorations — all descriptive,
no causal claims. Start from the national spine, then the split.

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

## The split (why national ratios mislead)

- **Madrid** (absolute scarcity): 429 dwellings/1000, 14% non-primary,
  young-migrant refill, worst affordability (6.2y). Municipally: capital
  +30% vs south never recovered nominally (Parla −13%, Fuenlabrada +0.5%
  in 18y); 2011 south was already vacancy (Parla 6%, Torrejón 8%).
  Needs net new stock.
- **Coastal Valencia** (composition crisis, decomposed): 720+ dwellings/1000
  at 44–46% non-primary = a second-home coast (Torrevieja 51%, Benidorm 43%)
  *plus* vacant towns (Dénia 31%), tourist flats a 4.3% footnote. Needs
  mobilization, not just construction.
- **Barcelona** (burdened metropolis): city +65% sale / +68% rents 2013–24,
  51% rent burden, 64% new-mortgage burden; corona more stretched (Sant
  Adrià 72%); 10k tourist flats in the city vs 28 in Santa Coloma; 514
  starts in 13 years there. Built on absorbing a 10.9% 2011 vacancy.
- **Interior** (Galicia, Castilla y León, Asturias): 650–770/1000, shrinking
  young cohorts, mild prices — abundance without demand.

## What predicts prices? Honestly: no single ratio

- Absorption ratio (built per new person): pooled rank −0.41 CCAA, −0.06
  provincial, mute in 2021–25. Descriptor of regimes, not predictor —
  the denominator is demand itself.
- Credit volumes track the bust; household formation tracks the tightening;
  incomes outran prices over the full period (affordability 6.2→4.4 years
  despite record prices) while concentrating pain in magnets.
- The missing covariates, in order: vacant-vs-touristic split, LTV/effort
  distributions, municipal grain, age×income joint detail.

## Reproduce everything

`make gates` rebuilds marts from pinned inputs; `explorations/*.py`
regenerate every number above into `artifacts/`; each claim links to a
script, a mart column, and a methods section. That chain — not any single
chart — is the deliverable.
