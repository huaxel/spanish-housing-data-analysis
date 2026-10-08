# Barcelona: the burdened metropolis and its stretched corona

> Pre-2013 municipal prices: closed 2026-10-06. IDESCAT Anuari is
> comarca-grain (nothing over valor tasado) and the 2000–12 TECNIGRAMA
> series is survey offer-prices for big cities only — methodologically
> incompatible with DIBA transactions. DIBA from 2013 stands; revisit
> only for registry-based municipal history.

From `muni_bcn` (Diputació de Barcelona open data + Padrón: sale €/m²
2013–, rents 2005–, registered vacant/tourist, rent/mortgage burdens
2015–2022, population). Burden indicators are DIBA-computed averages
(rent or new-mortgage cost vs gross income) — brutal levels, read the
fine print in sources before quoting beyond averages.

## City vs corona, 2013→2024

| municipio | sale €/m² | rent €/mes | pop |
| --- | --- | --- | --- |
| Barcelona | 2,719 → 4,482 (+65%) | 682 → 1,147 (+68%) | 1.61M → 1.70M |
| L'Hospitalet de Llobregat | 1,825 → 2,703 (+48%) | 516 → 837 (+62%) | 254k → 280k |
| Badalona | 1,787 → 2,672 (+50%) | 541 → 883 (+63%) | 220k → 227k |
| Santa Coloma de Gramenet | 1,768 → 2,310 (+31%) | 481 → 702 (+46%) | 120k → 121k |

All €/m² above are nominal. Deflated by Cataluña CPI (79.0→97.6, base
2021; `ipc_anual`), 2013→24 real gains: Barcelona **+33.4%**, Hospitalet
+19.9%, Badalona +21.0%, Sant Adrià +13.7%, Santa Coloma +5.7%. The
contrast with Madrid is the point: Madrid's recovery was nominal-only
(capital −7.5% real), Barcelona's was real everywhere — a demand recovery
against tight stock, not a nominal illusion over stagnation.

## Burdens 2022: the market prices out its workers

Average rent took **51% of gross income in Barcelona** (51–58% in Badalona,
Santa Coloma, Cornellà) and a new mortgage **63.6%** (71.9% in Sant Adrià,
62.1% in Cornellà). The corona is *more* mortgage-stretched than the city:
cheaper flats, much lower incomes. Santa Coloma (5 tourist flats, 2022) and
Sant Adrià carry no tourist distortion at all — pure income-vs-price gaps.

## Tourist geography is hyper-local

Barcelona city holds 10,271 tourist flats (2024, growing +8% since 2022 —
unlike Balears' decline); Santa Coloma holds 28. The VTE provincial share
(6%) hid a 10k-to-28 split inside one metro area. Tourist pressure is a
district story wearing provincial clothes — the municipal cut is the first
grain that shows it.

## Update: where building happened 2012–24 (M12/M13)

Starts → completions, 2012–24 cumulative: Barcelona city 19,086 → 16,721;
Badalona 6,570 → 5,271; Viladecans 2,358 → 1,050; Sant Joan Despí
1,730 → 1,241; **Santa Coloma 514 → 419 — forty homes a year for 120,000
people**. Demarcation total: 105,696 starts, 84,164 completions in thirteen
years. The city built infill at ~1,500 starts/year against +90k population
2013–24; Santa Coloma built essentially nothing while its rent burden hit
54.6%. Supply geography mirrors the burden map — construction didn't go
where the workers are.

## Update: the 2011 vacant overhang (`censo2011_bcn`)

Vacant share of dwellings, 2011: Barcelona **10.9%** · Sant Adrià 10.6% ·
Badalona 9.6% · Cornellà 7.3% · Santa Coloma 4.9%. Barcelona city alone held
~88k vacant flats (scale: more than all of Santa Coloma's stock). The metro
entered the recovery sitting on a larger vacant overhang than Madrid's south
— then absorbed it through a decade of migration *and* converted part of it:
the city's tourist flats grew 2022–24 while Balears' shrank. Vacancy →
absorption + tourist conversion, not new construction (19k starts in 13
years), is the arithmetic of Barcelona's tightening.

## Barrios: filed-contract rents (INCASÒL deposits)

Added 2026-10-08. The Generalitat's housing statistics service publishes 8
XLSX workbooks exploiting INCASÒL rental deposits: contract counts, mean
contractual rent (€/month), mean rent per m² and mean area. The annual mart
(`barrios_bcn_lloguer_anual`, 2,184 rows) carries the city + 10 districts
for 2000–2025 and 73 barris for 2013–2025; the quarterly mart
(`barrios_bcn_lloguer_trimestral`, 4,984 rows) carries districts from 2000
and adds the 73 barris from 2014, with the 2026 sheet holding only the
published quarters. Areas with fewer than 6 registered contracts are
unpublished (null, never zero). These are filed contracts, not asking
prices, and not directly comparable with Madrid's registrar-declared sale
prices or Sevilla's IPRA windows. In 2024 the city filed 32,903 contracts
at 16.13 €/m²; in 2025 la Barceloneta reached 22.70 €/m², the highest
barrio cell that year.

## Barris: preus de compravenda registrats (Registradors)

Added 2026-10-08. Quarterly workbooks from Colegio de Registradores
records: transactions split new-free / new-protected / used, mean area,
mean total price and mean price per built m² (`barrios_bcn_compraventes`,
2,520 rows). City + 10 districts + 73 barris for 2018–2019 and 2021–2026
(the 2017 series had not started; the 2020 file URL returns not-found,
a publication gap, not a market gap). Prices are unpublished below 3 contracts and appear as zero
in the workbooks: stored as null, never zero. The city total includes
records that could not be geolocated, so it does not equal the sum of its
parts. In 2024Q4 the city registered 4,368 transactions at 4,622.43 €/m².
Two 2025 barrio renames are canonicalized (B11 Poble Sec, B12 Marina del
Prat Vermell). The 2026 sheets add max/min €/m² columns, kept as-is.

## Yields 2024: periphery pays, prime costs (descriptive)

Joining INCASÒL new-contract rents to Registradores sale prices on the 73
barris (71 with both 2024 cells) gives gross yields centered at 4.51%
(median): la Trinitat Nova 7.71% at the top, la Marina del Prat Vermell
2.02% at the bottom. Rents and prices correlate at 0.754 — the gradient is
level-driven (cheap sale prices, not high rents). Two thin cells (under 15
transactions) are flagged, not dropped. Flow rents overstate sitting-tenant
reality in a rising market; read as a cross-sectional sorting, not a return
promise.

## Limits

- Sale prices = Secretaria d'Habitatge (registrars), 2013–; rents = Incasòl
  deposits (census-like). Different populations, same direction.
- Burdens are DIBA's 2015–2022 ratios of averages — distributional reality
  (new contracts, young renters) is worse; don't soften with the mean.
- Registered vacant (Barcelona 1,350) undercounts true vacancy by an order
  of magnitude — registry, not census.
- Padrón municipal runs to 2025; sale prices to 2024; burdens to 2022 —
  the table shows each at its latest, never forward-filled.
