# Synthesis: prices, stock, and people in Spain (2001–2025)

Core question: how has the evolution of Spanish housing prices related to
the amount of housing stock built and to population/household growth?
Evidence: 30 pinned sources, 20 mart tables, 24 explorations — all
descriptive, no retained causal claims (the commissioned IV was withdrawn
after independent review, as documented below). Start from the national
spine, then the split. For access rather than stock alone, see the
[housing-access chapter](housing_access.md).

## The spine (Nacional)

| año | IPV | €/m² | viv/1000 | viv/hogar | 90 m² en años renta | hipotecas |
| --- | --- | --- | --- | --- | --- | --- |
| 2007 | 83 | 2,056 | 532 | — | 6.4 | 1,239k |
| 2013 | 54 | 1,495 | 544 | — | 5.2 | 200k |
| 2021 | 74 | 1,658 | 564 | 1.44 | 4.6 | 418k |
| 2025 | 100 | 2,128 | 552 | 1.39 | 4.4† | 498k |

†2024 income year (ECV lag). Source: `mart_ccaa_anual`, ccaa = Nacional.

Three regimes, three different patterns of price and housing-market change:

1. **Boom–bust (2007–13): a credit stop on top of growing stock.**
   Prices −36% while stock *grew* everywhere and per-capita stock *rose*
   (532→544). Mortgage counts fell 84%. This co-movement is descriptively
   incompatible with a *simple national stock-collapse* story, but does not
   establish credit's relative contribution over supply, nor that units
   were needed where built. The 2011 vintage evidence (768k vacant units
   built 2002–11, concentrated in boom areas) is consistent with genuine
   local overhang. Credit and geographic overhang remain competing
   explanations.
2. **Stagnation–recovery (2013–19): demography diverges.** Prices recover
   while the 20–34 cohort collapses 9.0M→7.6M and population stagnates.
   Per-capita stock peaks (564), while population stagnates. That peak
   describes the national ratio; it does not establish that homes were
   usable, available, or located where demand was growing.
3. **Tightening (2021–25): households outrun everything.** Stock still grows
   (+380k net modeled additions), but households grow faster (+982k net
   ECP additions): 0.23–0.90 net dwellings per net new household in
   *every* CCAA. **Terminology correction 2026-10-06 (independent
   review):** both counts are *net* — MIVAU-modeled stock change (not
gross dwellings built) over net ECP household change (not gross
   formations) — and `viv/hogar` counts all dwellings including second
   homes and vacant units, so a falling ratio does not by itself prove a
   usable-home shortage. Per-capita and per-household stock fall while
   prices rise ~36% — against *rising* rates. The supply-demand
   co-movement is strongest here, but calling it "the naive supply
   story fits" overstates what a net-net ratio without availability
evidence can show.

The long arc in dwellings per household: 1.48 (2001, proxy —
viviendas_total/viviendas_principales, not measured households) → 1.40
(2011) → 1.41 (2014) → 1.42 (2020) → 1.44 (2021) → 1.39 (2025).
The ratio fell from 1.48 to 1.40 in the 2000s, rose to 1.44 by 2021,
then fell to 1.39 by 2025. The 2001 point is a proxy with its own
tolerance (worst 2011 disagreement 2.11%); the 2021 ECH→ECP seam makes
the 2020→2021 step non-comparable. Read the measured 2011→2025 movement
(1.40→1.44→1.39) as the comparable arc, not the proxy-anchored endpoints.

## Causal extension: withdrawn after independent read (design A is a negative result)

Removed 2026-10-07 on the milestone-5 independent read (verdict: REMOVE;
read record in [the IV note](explorations/iv_migration.md) and
[the review brief](review_brief.md)). The shift-share IV (repaired
flow instrument: +0.08 pooled, +0.46 bust-only) failed exclusion: 1998
settlement geography coincides with the territorial footprint of the
credit/construction bubble; the trends spec runs hot (+0.20 vs +0.08
base) instead of confirming it; and a second independent read rejected
the repaired design on inference grounds (unidentified in both
directions without calibrated AR). Per the pre-committed protocol the estimate is kept as
a documented negative result, not a softer claim: numbers stay pinned in
`explorations/iv_results.json` (still freshness-checked by `make audit`),
and nothing causal sits in this synthesis until a new design passes its own
read. Design B (Saiz terrain) is likewise null at both grains; the causal
program is on hold, not abandoned — see the identification memo.

## The split (why national ratios mislead)

- **Madrid** (absolute scarcity): 429 dwellings/1000, 12% non-primary (2025; was 19% in 2007),
  young-migrant refill, second-worst affordability (6.2y in 2024, after Balears 6.4). Municipally: capital
  +30% vs south never recovered nominally (Parla −13%, Fuenlabrada +0.5%
  in 18y) — and neither recovered really (capital −7.5%, south −28 to
  −38% in 2025 euros); 2011 south was already vacancy (Parla 6%,
  Torrejón 8%). Motivates evaluating new usable supply; these ratios do not
  establish the effect or optimal location of construction.
- **Coastal Valencia** (composition crisis, decomposed): Alicante province
  peaked at 724 dwellings/1000 (2018; 676 in 2025) with 44% non-primary
  in 2020 (40% in 2025) = a second-home coast (Torrevieja 51%, Benidorm 43%)
  *plus* vacant towns (Dénia 31%), tourist flats a 4.3% footnote. Needs
  investigating mobilization alongside construction; historical non-primary
  stock is not evidence of current, habitable supply available to households.
- **Barcelona** (burdened metropolis): city +65% sale / +68% rents 2013–24
  (+33% real — the recovery was real, unlike Madrid's), 51% rent burden,
  64% new-mortgage burden; corona more stretched (Sant Adrià 72%); 10k
  tourist flats in the city vs 28 in Santa Coloma; 514 starts in 13 years
  there. Entered recovery with 10.9% vacancy in 2011; subsequent absorption
  is not measured by that snapshot. Within-municipio tourist changes show no
  statistically detectable association with price/rent growth (municipal panel
  wild-p 0.49–0.96). This does not establish negligible effects, especially
  under licensing constraints and incomplete registry coverage.
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
  robust nowhere (S0 −0.024, wild-p 0.19; S1 −0.012, wild-p 0.97)
  — consistent with the CCAA panel: the naive t overstates precision.
- The two-group ratio split: national viv/1000 flatness hides scarcity CCAA
  (Madrid −29.7, Cataluña −27.6) vs overstock (+100…+130 interior), and
  the **electricity-based vacancy** measure (2021 census, 59531) shows
  a high vacancy share in Galicia (28.8%) versus Madrid (6.3%); it does
  not establish that vacant homes are habitable or available.
- Rents (SERPAVI, municipal 2011–2024): DIBA cross-validated (Pearson
  0.825, Spearman 0.87); gross yield 3.6% in Barcelona vs 4.6% corona
  median; tourist intensity does not predict rents within municipios
  (no detected association, not an equivalence result) but tracks rent levels across provinces (Pearson 0.62,
  Spearman 0.53 — confounded with coastal demand, not identified). Rent–
  vacancy is substantially negative on ranks (−0.51), consistent with
  overhang, not causal.
- Credit volumes track the bust; household formation tracks the tightening;
  incomes outran prices over the full period (affordability 6.2→4.4 years
  despite record prices) while concentrating pain in magnets.
- The missing covariates, in order: LTV/effort distributions, age×income
  joint detail, transaction prices at municipal grain (the repo has
  appraisal + DIBA transactions; valor-referencia and construction-flow
  probes are parked with reopen conditions).

## Physical-stock extension: what the Sevilla pilot adds

The [physical-stock explorer](../evidence/pages/stock.md) moves beyond regional
stock ratios using cadastral footprints, parcel-grouped construction-date
ranges, declared housing-property counts and gross floor area. A reproducible
reader summary connects physical density and record-date proxies with rents,
while keeping global and district/income-adjusted correlations, income-year
samples and geographic/weighting sensitivities distinct. It does not select
a preferred causal specification.

Physical density is not available supply. A positive density/rent association
can reflect location, demand and composition rather than the price effect of
adding housing. Weighting parcel-grouped record dates by property counts does
not observe individual dwelling ages; gross floor area is not residential-only
floor area. Household context, current stock and rental contracts have different
vintages, so this pilot does not establish a contemporary local stock-demand
balance or retroactively predict rents.

The pilot has since extended beyond Sevilla at municipal grain: the four
capitals share the 1971–1990 construction peak (Granada strongest at 42.1%),
while Sevilla province as a whole peaks a generation later in 1991–2010
(35.6%), with the capital holding 36.7% of provincial properties. Málaga
adds barrio detail and Granada district detail; Córdoba stays municipal
pending licensed geometries. The era conclusions do not travel automatically:
mid-century mass housing concentrates need in Sevilla, but other cities lack
the condition layers to test that.

The next substantive gap is matched-date, matched-geography stock, households
and rent with occupancy/availability evidence—not another control added to
these snapshots ([source hunt](occupancy_availability.md)). [Stock methods](cadastre_stock.md) and
[income definitions](sevilla_income.md) document exclusions, source semantics
and the reproducible report; the central models remain separate.

## Reproduce the analysis

`make gates` rebuilds marts from pinned inputs and runs the project checks.
The scripts in `explorations/*.py` regenerate the reported exploration
outputs in `artifacts/`; run the relevant script to refresh those outputs.
Claims are traceable to scripts, mart columns, and methods sections. That
chain — not any single chart — is the deliverable.
