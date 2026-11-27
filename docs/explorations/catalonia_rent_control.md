# Catalonia rent-control zones (Ley 12/2023): quasi-experimental evaluation

## Question and scope

Under Spain's Housing Law (Ley 12/2023), Catalonia declared two staggered waves
of *zonas de mercado residencial tensionado* (ZMRT):

- **Wave 1 (140 municipalities):** BOE-A-2024-5214 (published 2024-03-15, effective
  2024-03-16; first full treated quarter `2024Q2`).
- **Wave 2 (131 municipalities):** BOE-A-2024-20576 (published 2024-10-09, effective
  2024-10-10; first full treated quarter `2024Q4`).
- **Never-treated (677 municipalities):** remaining Catalan municipalities.

This evaluation uses official INCASÒL administrative rental deposit records
(`fiances`) across all 947 Catalan municipalities, quarterly from `2019Q1` to
`2026Q2`, measuring three observable margins simultaneously:

1. **Habitual contractual rent (`log_rent`):** mean monthly contractual rent
   (€/month) for newly filed habitual-residence contracts. Suppressed by the
   Generalitat when a municipality has `<= 5` contracts in a quarter (encoded as
   `0` in the source XLSX, coerced to `null` here).
2. **Habitual contract flow (`log_contracts`):** count of newly filed habitual
   rental contracts.
3. **Seasonal rental share (`temporada_share`):** seasonal deposit contracts
   divided by total (habitual + seasonal) deposit contracts, available
   `2023Q1–2026Q2`.

## Identification designs and sample

To avoid comparing metropolitan rental markets with zero-contract rural villages,
the regression sample restricts to **active rental markets** (municipalities with
at least 12 published quarterly rent observations in `2019–2023`: 139 Wave 1,
124 Wave 2, 64 never-treated). All specifications absorb municipality fixed
effects and quarter fixed effects (or `comarca × quarter` FE in Design D), with
CR1V standard errors clustered by municipality and 999-replicate Rademacher wild
cluster bootstrap-t p-values (`seed=20261127`).

| Design | Control & horizon | Rent (`log_rent`) | Contracts (`log_contracts`) | Seasonal share (`pp`) | Pre-2024 placebo `t` (rent / contracts) |
| --- | --- | --- | --- | --- | --- |
| **A: Wave 1 vs Wave 2** | Not-yet-treated, `2019Q1–2024Q3` | **−3.79%** (`wild_p=0.001`) | **−12.61%** (`wild_p=0.001`) | **+1.42 pp** (`wild_p=0.005`) | −0.97 / −0.90 |
| **B: Wave 1 vs Never** | Active controls, `2019Q1–2026Q2` | **−6.19%** (`wild_p=0.001`) | **−17.10%** (`wild_p=0.001`) | **+1.91 pp** (`wild_p=0.001`) | +2.06 / −1.00 |
| **C: Wave 2 vs Never** | Active controls, `2019Q1–2026Q2` | **−5.55%** (`wild_p=0.001`) | −7.00% (`wild_p=0.068`) | +0.73 pp (`wild_p=0.154`) | +1.45 / −1.36 |
| **D: Within-Comarca FE** | All active, `comarca × quarter` FE | **−5.30%** (`wild_p=0.001`) | **−10.66%** (`wild_p=0.001`) | **+0.89 pp** (`wild_p=0.035`) | +2.01 / +0.63 |

## Falsification and limitations

- **Pre-trends:** Design A (Wave 1 vs Wave 2 before Wave 2 entered force) has
  null 2023Q2 placebos on both rent (`t = −0.97`) and contracts (`t = −0.90`),
  and only 1 of 7 event-study pre-leads exceeds `|t| = 1.96`. Design B and C show
  positive pre-treatment rent placebos (`+2.06`, `+1.45`) — treated markets were
  rising *faster* than controls before the cap, so the post-cap drop reverses the
  pre-trend rather than continuing it. On contract flows, Designs B and C fail
  event-study pre-trend flatness (3 significant pre-leads), so contract-volume
  magnitudes should be anchored on Design A (`−12.6%`) and Design D (`−10.7%`,
  within-comarca placebo `t = +0.63`).
- **What contract counts do *not* separate:** A fall in newly filed habitual
  contracts combines (1) **lower tenant turnover / longer stays** (incumbents
  renewing rather than moving), (2) **substitution into seasonal or room
  rentals** (partially captured by `temporada_share`, which rises +0.9 to +1.9 pp
  in Wave 1), and (3) **withdrawal to sale or vacancy**. Deposit counts cannot
  separate (1) from (3) without spell-level microdata.
- **No independent external review yet:** Unlike the v1 descriptive synthesis,
  this policy-evaluation module is newly introduced and should be treated as an
  auditable quasi-experimental working paper until it completes its own
  independent read.

## Reproduction

```bash
uv run python scripts/fetch_catalonia_rent_control.py --offline
uv run python explorations/catalonia_rent_control.py
```

Pinned inputs: `data/raw/cat_incasol_municipis_trimestral_contractes.xlsx`,
`data/raw/cat_incasol_municipis_trimestral_lloguer.xlsx`,
`data/raw/cat_incasol_temporada_mun.xlsx`, `data/raw/boe_zmrt_cat_wave1.xml`,
`data/raw/boe_zmrt_cat_wave2.xml`. Output artifact:
`artifacts/catalonia_rent_control.json`.
