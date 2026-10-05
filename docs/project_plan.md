# Project plan

## Question and deliverable

How has the evolution of Spanish housing prices related to the amount of
housing stock built and to the increase of population / number of households?

Deliver: an Evidence explorer over versioned Parquet marts; an auditable
fetch→build→verify pipeline; a coverage/limitations report. Causal claims
("building X homes would have lowered prices by Y") and forecasts are
explicit extensions, not v1.

## Scope

- Time: 2001–2025 (census-anchored stock series; IPV from 2007; Padrón to 2021).
- Geography: national + CCAA + provincia. Prices join at CCAA/national only —
  INE publishes no provincial IPV (see methods §1).
- Units: counts, ratios (dwellings per 1,000 inhabitants, share of
  non-principal dwellings), quality-adjusted price *indices*. No €/m² levels
  until valor tasado is pinned.

## Source queue

| # | Source | Status |
| --- | --- | --- |
| 1 | MIVAU Parque de Viviendas (VDP002_01, CSV) | Pinned, in marts |
| 2 | INE IPV medias anuales CCAA (Tempus3 80271) | Pinned, in marts |
| 3 | INE Padrón Revisión (Tempus3 2852/2853, 1996–2021) | Pinned, in marts |
| 4 | INE Censo viviendas 2001/2011 (jaxi CSV) | Pinned, anchor checks pending |
| 5 | INE ECP población (2022+) | DONE 2026-10-06 — CCAA/nacional (56940); provincial (56945) API-blocked, see sources |
| 6 | MIVAU valor tasado (€/m² levels) | TODO — price levels, complements IPV trends |
| 7 | Households | PARTIAL 2026-10-06 — ECP hogares 2021+ in marts (`viv_por_hogar`); ECH annual + tamaño detail + census anchors queued |
| 8 | INE Censo viviendas 2021 | TODO — third anchor; stock already embeds its rebase |

## Milestones

1. Pipeline v1 (done 2026-10-05): fetch/build/verify green, marts + coverage.
2. Evidence explorer v1: national + CCAA pages (price vs stock-per-capita).
3. Source completions 5–8, one at a time, each with manifest pin + methods note.
4. Households layer: dwellings-per-household by provincia (census years first,
   ECH annual second) — the closest observable to "shortage".
5. Review: independent read of methods + limitations before any public release.

## Status 2026-10-06

Pipeline v1 + ECP extension live: CCAA mart 2007–2025 (pop splice quantified),
provincia mart 2001–2021, hogares 2021+. Next: valor tasado (€/m² levels, #6)
or Evidence toolchain fix — the 2022–25 tightening (viv/1000 ↓, viv/hogar ↓,
IPV ↑) is the story to lead the explorer with.

## Exclusions (v1)

No causal attribution of price moves to construction volumes; no
municipal-level claims from provincial aggregates; no splicing of index bases;
no forward-filling of 2022+ population. The 2022–2025 price surge is visible
in IPV but has no population denominator yet — say so on the page, don't
work around it.
