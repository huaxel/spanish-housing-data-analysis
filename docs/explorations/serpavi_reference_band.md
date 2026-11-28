# The published rent reference and what it can discriminate

**Date:** 2026-11-27 · **Status:** descriptive exploration, no legal claim

SERPAVI is the state rent-reference system (MIVAU tax-deposit exploitation), the
index Housing Law 12/2023 points at when a CCAA declares a *zona de mercado
residencial tensionado*. Unlike a threshold formula, it publishes a band per
municipio (median, P25, P75) rather than a point. This note asks what that band
can and cannot tell apart. Reproduction:

```bash
uv run python explorations/serpavi_reference_band.py
# -> artifacts/serpavi_reference_band.json
```

Read everything below as a description of the published statistic. The P25/P75
are the spread of contract rents **inside** a municipio, so the band measures
within-municipio heterogeneity. It is **not** a confidence interval for the
reference, **not** an uncertainty band around a legal ceiling, and **not**
evidence about any individual lease.

## The band is wide, and it stays wide

Relative inner width `(P75 − P25) / median`, `vivienda colectiva`:

| Year | Measure | n | p10 | p50 | p90 | share > 0.30 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2011 | EUR/m² | 1,722 | 0.380 | 0.528 | 0.758 | 97.9% |
| 2018 | EUR/m² | 2,029 | 0.328 | 0.449 | 0.633 | 94.6% |
| 2024 | EUR/m² | 2,555 | 0.317 | 0.453 | 0.616 | 92.4% |
| 2011 | EUR/month | 1,722 | 0.286 | 0.425 | 0.629 | 86.5% |
| 2024 | EUR/month | 2,555 | 0.228 | 0.334 | 0.462 | 66.1% |

`vivienda unifamiliar` is wider still — median 0.672, p90 1.012 in 2024 — and it
is published for **more** municipios than the colectiva measure (3,020 vs 2,555).
The stratum with the least discriminating power has the broadest coverage.

The obvious objection is that a municipal band is *supposed* to be wide: a
municipio contains flats and penthouses, old and new. That is exactly the point.
The descriptive claim is not "the reference is noisy" but "the municipio is not
the grain at which the rent is homogeneous", and the law declares zones at
municipal grain while distinguishing dwellings at dwelling grain. Quote the
EUR/month figures for the legal quantity; the EUR/m² measure is roughly 35%
wider for a metric reason (rent per m² varies more than rent per dwelling).

## The width is heterogeneity, not sampling

If the band were estimation noise it would collapse as the published contract
count rises. It does not (2024, EUR/m², EUR `vivienda colectiva`):

| Contract-count quintile | contracts (min–max) | mean relative IQR |
| --- | --- | ---: |
| 1 | 10–23 | 0.509 |
| 2 | 23–63 | 0.476 |
| 3 | 63–171 | 0.459 |
| 4 | 172–543 | 0.442 |
| 5 | 543–300,447 | 0.447 |

Spearman(contracts, relative width) = **−0.090**. A `1/√N` shrinkage from
N ≈ 15 to N ≈ 1,296 would narrow the band roughly nine-fold; the observed
narrowing is 1.14-fold. The width is the spread of the contracts themselves —
which is also why more contracts do not help: they describe a wider market, not
a better-measured one.

## Neighbours are not separable

Within a province, neighbouring municipios' bands overlap heavily — 80,324 of
103,220 pairs (**77.8%**) in 2024. Overlap is *highest* where the policy actually
bites:

| Settlement size (2021 dwellings) | pairs | overlapping | share |
| --- | ---: | ---: | ---: |
| 500–2k | 9,662 | 8,258 | 85.5% |
| 2k–10k | 22,376 | 18,832 | 84.2% |
| 10k–50k | 3,048 | 2,677 | 87.8% |
| >50k | 76 | 71 | 93.4% |

Overlap is expected where markets genuinely resemble each other, so this is a
statement about discriminating power, not about error: a municipal reference
band is usually compatible with its neighbour's, which means the municipal level
alone does not pin a rent down.

## Coverage is population-heavy and territory-thin

2024: **2,512 of 8,132 municipios (30.9%)** carry a published colectiva median,
but they hold **44.36M of 48.59M people (91.3%)**. The blind spot is villages —
4,796 of 4,981 municipios under 1,000 inhabitants have no median — plus
population-share gaps in coastal provinces (Castellón 54.9%, Alicante 57.0% of
provincial population, same €/m²-median basis as the 91.3% national figure).
This is the inverse of a sector map: the reference speaks for people, not for
places.

## The three published measures do not cohere exactly

`EUR/month ÷ (EUR/m² × median surface)` has median **0.956** in 2024 (p10 0.872,
p90 1.027), drifting from 0.972 in 2011. Three published summaries of the same
municipal rent therefore disagree by ~4–5% on average and ~13% in the lower tail.
This is consistent with taking medians of three separately aggregated series
rather than deriving one from another, and it is a caution for any chained
calculation that mixes them. It is not a defect claim.

## Where real contract data exist, the reference sits below — and that gap moves

Catalonia publishes INCASÒL rental-deposit records (new habitual contracts,
municipal mean EUR/month). Joining them to the SERPAVI EUR/month band — same
unit, different populations:

| Year | municipios | observed/reference p50 | observed above reference P75 | observed below reference P25 |
| --- | ---: | ---: | ---: | ---: |
| 2022 | 401 | 1.162 | 48.1% | 0.7% |
| 2023 | 388 | 1.191 | 58.5% | 0.5% |
| 2024 | 397 | 1.185 | 52.4% | 0.0% |

One-sided, but a single year cannot say why. Three probes, on the same join:

1. **Mean versus median does not explain it.** A lognormal fitted to the
   published P25/P75 implies a mean/median ratio of 1.032 (p10 1.020, p90 1.053)
   on the matched municipios. The observed gap is 1.185.
2. **The gap is not constant in time.** On the 183 municipios present in every
   year 2011–2024 (a balanced panel, so coverage changes cannot drive it):

   | Year | level gap p25 | p50 |
   | --- | ---: | ---: |
   | 2011 | 1.037 | 1.075 |
   | 2013 | 1.004 | 1.058 |
   | 2018 | 1.149 | 1.204 |
   | 2024 | 1.106 | 1.160 |

   The gap is smallest when rents were flat or falling (2011–2014), widens
   through the 2015–2018 repricing wave, and plateaus afterwards. A fixed
   definitional offset would not move with the cycle.
3. **It is not a municipal cross-section either.** Spearman between the 2024
   gap and each municipio's own 2019–2023 rent growth is **+0.012** (n = 364):
   the cycle moves the aggregate gap, but does not sort municipios.

Read together: most of the level gap is consistent with the **standing stock of
tax-declared rents lagging a repricing new-contract flow** — which is what a
reference built from declarations *should* do, and it is not a fault in either
source. A residual of roughly 5–6% remains in the flat-rent years, unexplained
by mean-versus-median or by the municipal cycle. Separating that residual needs
contract-level surfaces (INCASÒL publishes municipal means only), so it is left
open rather than guessed.

**What must not be quoted:** the 1.185 ratio as a shortfall, a breach, or proof
that any cap binds. It is two different populations measured on different
bases, and most of the difference is the reprice cycle.

## What this does and does not establish

- **Does:** the published rent reference is a within-municipio distribution whose
  inner band is wide, heterogeneous in origin, and usually compatible with
  neighbouring municipios; its coverage follows population, not territory; and
  where independent contract records exist, they sit above it by an amount that
  moves with the repricing cycle rather than by a fixed amount.
- **Does not:** say anything about an individual lease, a specific ceiling, or
  whether any zona tensionada declaration was or was not justified. Neither the
  legal margin for a given dwelling nor the contract-level microdata that would
  settle the population question is in this repository.

## Reproducibility note

The band, coverage and internal-arithmetic numbers are pinned as audited claims
in `scripts/audit_claims.py` under the `serpavi_reference_band` group. The
balanced-panel path and the two explanation probes are deliberately *not* SQL
claims: they need the INCASÒL parquet, which a fresh clone builds only after
`make build`, and a missing file should not fail the audit. They are pinned by
re-running `explorations/serpavi_reference_band.py`, which is deterministic.

## Relation to the Brussels profile study

The `four-prices` project found that a statutory reference-rent formula and a
published registered-rent median are not comparable without declaring a dwelling
profile: across nine neutral profiles the 120% threshold moves by a factor of
1.671, and 202 of 288 sectors change status. Spain's ambiguity has a different
source — the published band's width — but the same consequence: the legal margin
and the published distribution are of the same order, so a single number quoted
at the administrative grain outruns what the statistic supports. Whether the two
ambiguities are the *same phenomenon* is a comparative question, not something
established here.
