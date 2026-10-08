# The credit cycle: the bust's other half

Mortgages on dwellings (HPT 76316/76317, CCAA + provincia, 2003–) and
national rates (76315) put the demand side next to the stock story.
Computed inline from the marts; no separate script (queries below are the
evidence — rerun against `marts.duckdb`).

## Update: liquidity and the nueva collapse (Transmisiones layer)

Transactions (registrars) complete the cycle: 775k (2007) → 313k (2013) →
640k (2024), with the nueva share falling 42% → 21% (spiking to 46% in
2013 as developers dumped new stock into a frozen used market). Mortgages
overshoot transactions throughout (refinancing/subrogations included) —
compare shapes, never levels. The post-2021 recovery transacts *used* homes (79% of 2024 deals) on a stock
that barely grows: churn, not construction, clearing the market.

## Nacional: credit timing fits the bust, not the tightening

| año | hipotecas | ticket medio | tipo medio | IPV |
| --- | --- | --- | --- | --- |
| 2007 | 1,239k | €149k | — | 83.2 |
| 2013 | 200k | €100k | 4.2% | 53.5 |
| 2019 | 361k | €126k | ~2.5% | 69.3 |
| 2024 | 426k | €145k | 3.3% | 88.7 |

Mortgage counts fell **84%** 2007–13 while the stock kept growing — the bust
looks like a credit stop, not a supply flood. Prices fell 36% on vanishing
transactions, not on vacant abundance. Conversely 2021–24: mortgages grew
modestly (+18% from a low base) while prices rose ~20% and rates *rose*
2.2→3.3% — the tightening happened *against* the credit wind, pointing at
real demographic demand (young-migrant refill, fragmentation) rather than
cheap money. The fixed-rate share shift (fijo ≈ variable by 2024 vs
variable-dominated pre-2015) is in `tipos_hipoteca_nacional` for the
follow-up on payment sensitivity.

## Update: leverage geography at the trough (`censo2011_tenencia`)

Mortgaged share of households, 2011: Valencia 36.7%, Murcia 36.2%, Madrid
34.8%, Cataluña 34.1% — against Galicia 23.0%, Asturias 28.4%. The regions
that fell hardest (Cataluña −46%, Madrid −42%, Valencia −32% IPV 2007–13)
were the most leveraged; the mildest falls sat on outright ownership.
5.94M households paid mortgages at the trough (32.9% nationally; rented
only 13.5%). Negative equity's geography is leverage geography — the bust's
pain distributed by balance sheet, not just by price fall.

## What this does to Hypothesis 01

The per-window instability (±0.5 CCAA, ≈0 provincial) now has a name:
2007–11 prices moved with credit volumes (1.2M→0.4M mortgages), 2011–15
with depopulation, 2021–25 with household formation against tight supply.
The absorption ratio is never the whole model — credit belongs in any
multivariate attempt, and this dataset now carries it (counts + tickets at
both grains, rates nationally).

## Distress: launches and foreclosure filings (CGPJ)

Added 2026-10-08. The CGPJ provincial crisis series gives quarterly
launches practiced by first-instance courts (exhaustive since 2013,
split mortgage / LAU-rent / other) plus mortgage enforcement filings
since 2007 (`desahucios_provincia`, 3,850 rows, 50 provinces — no
Ceuta/Melilla rows). A launch is any property handover ordered, dwelling
or not: a distress indicator, not a tenant-eviction count. National
launches fell to 1,383 in 2020Q2 (moratorium) and stood at 24,540 in
2025; Cádiz closed 2024Q4 with 141 launches (30 mortgage, 103 rent,
8 other). Service-common figures are excluded by construction. One upstream
off-by-one cell exists (Almería 2022Q4 total vs causes); verify pins it
instead of forcing a silent fix.

## Limits

- Mortgage *counts* ≠ credit *conditions*: LTV, effort rates (cuota/renta)
  and approvals aren't in HPT Tempus tables — BdE distributional data is the
  queued upgrade.
- Ticket medio mixes composition (cheaper areas, smaller flats) with leverage;
  deflate by €/m² before leverage claims.
- Rates are national-only: no CCAA mortgage-price sensitivity is testable.
