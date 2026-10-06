# Project plan

## Question and deliverable

How has the evolution of Spanish housing prices related to the amount of
housing stock built and to the increase of population / number of households?

Deliver: an Evidence explorer over versioned Parquet marts; an auditable
fetch→build→verify pipeline; a coverage/limitations report. Causal claims
("building X homes would have lowered prices by Y") and forecasts are
explicit extensions, not v1.

## Scope

- Time: 2001–2025 (census-anchored stock series; IPV from 2007; Padrón to 2021, ECP at CCAA grain / Censo Anual at province grain from 2022 — provincia mart runs 2001–2025).
- Geography: national + CCAA + provincia. Prices join at CCAA/national only —
  INE publishes no provincial IPV (see methods §1).
- Units: counts, ratios (dwellings per 1,000 inhabitants, dwellings per
  household, share of non-principal dwellings), quality-adjusted price
  *indices* (IPV) plus appraised price *levels* (€/m², valor tasado).

## Source queue

| # | Source | Status |
| --- | --- | --- |
| 1 | MIVAU Parque de Viviendas (VDP002_01, CSV) | Pinned, in marts |
| 2 | INE IPV medias anuales CCAA (Tempus3 80271) | Pinned, in marts |
| 3 | INE Padrón Revisión (Tempus3 2852/2853, 1996–2021) | Pinned, in marts |
| 4 | INE Censo viviendas 2001/2011 (jaxi CSV) | Pinned, anchor checks pending |
| 5 | INE ECP población (2022+) | DONE 2026-10-06 — CCAA/nacional (56940); provincial (56945) API-blocked, see sources |
| 6 | MIVAU valor tasado (€/m² levels) | DONE 2026-10-06 — Libre annual means in marts (prov + CCAA), 0.95 YoY corr vs IPV |
| 7 | Households | DONE 2026-10-06 — ECP hogares 2021+ with tamaño detail (`viv_por_hogar`, `share_1persona`); ECH annual pre-2021 + census anchors queued |
| 8 | INE Censo viviendas 2021 | DONE 2026-10-06 — viewer export (tpx=59521) via playwright-cli; totals within 0.77% (build asserts <1%); tipo split diverges, unchecked |
| 9 | INE ECV renta hogares (Tempus3 9949) | DONE 2026-10-06 — CCAA mean net income, `afford_90m2_years` in CCAA mart |
| 10 | INE Hipotecas (HPT) + Transmisiones | DONE 2026-10-06 — mortgage volumes/tickets + transaction liquidity in marts |
| 11 | INE Turísticas (VTE) | DONE 2026-10-06 — registered tourist dwellings (Dec snapshot) in marts |
| 12 | ECP edad/tamaño detail + Censo 2011 vintage/tenencia | DONE 2026-10-06 — 20–34 cohort, 1-person share; 2011 vacancy/vintage splits |
| 13 | Municipios (Madrid valor tasado + padrón; DIBA Barcelona) | DONE 2026-10-06 — `muni_madrid` / `muni_bcn` tables, municipal explorer pages |
| 14 | Households pre-2021 | DONE 2026-10-06 — ECH annual 2014–20 (jaxi p274 static files) + 2011 exact + 2001 proxy; no 2013 (serie starts 2014) |
| 15 | INE IPC deflator (real-terms levels) | DONE 2026-10-06 — general index (base 2021) CCAA+Nacional in `ipc_anual`; Madrid real: capital −7.5%, south −28 to −38% |
| 16 | INE EM inmigración (Tempus3 24322) | DONE 2026-10-06 — foreign/Spanish inflows by provincia 2008–2021 in `migra_anual`; cycle 567k→248k→666k |

## Milestones

1. Pipeline v1 (done 2026-10-05): fetch/build/verify green, marts + coverage.
2. Evidence explorer v1 (done 2026-10-06): nacional + CCAA + comparar + municipios pages.
3. Source completions 5–16 (done 2026-10-06): queue fully DONE — IPC,
   ECH, censo 2021 anchor, migration flows, each with manifest pin +
   methods note.
4. Households layer (done 2026-10-06): dwellings-per-household by
   provincia — 2011 exact, ECH 2014–20, ECP 2021+, 2001 proxy.
5. Review: independent read of methods + limitations before any public
   release — STILL OPEN (required before sharing beyond workers.dev).
   **Package ready: [`docs/review_brief.md`](review_brief.md)** — scope,
   ground rules, reproduction commands, disclosed limitations, and the
   adversarial questions (including the IV read plan step 1 that the merge
   skipped). Blocked only on an available independent reviewer.

## Status 2026-10-06 (evening)

All 16 queued sources live; marts verified end-to-end twice from scratch
(byte-identical re-fetch). Analysis now spans window correlations → FE
panel (wild bootstrap, lags, migration control) → quarterly timing →
real-terms levels, all pointing one way (demand drivers, supply
descriptors). Explorer deployed (workers.dev + `/comparar`, `/municipios`,
real-€ chart); custom domain waits on zone scope. Causal designs scoped
in the identification memo — migration shift-share needs share
archaeology; nothing causal merges before milestone 5's independent read.

## Exclusions (v1)

No causal attribution of price moves to construction volumes (the one
causal estimate — migration exposure → prices, commissioned 2026-10-06 —
lives in synthesis + the IV note with its threats, not as a general
license); no municipal-level claims from provincial aggregates; no
splicing of index bases.
Population from 2022 comes from ECP (methodology differs from Padrón — the
2021 overlap is quantified in `coverage.json`, never silently spliced).
Provincial ECP is API-blocked, so the provincia mart's 2022–2025 population
comes from the Censo Anual de Población static CSV (verified 2025 national = ECP
exact; probe in docs/explorations/censo_anual_probe.md); CCAA/national run to 2025.
