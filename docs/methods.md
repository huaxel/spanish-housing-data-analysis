# Methods and interpretation

## 1. What each number means

- **IPV (INE, base 2025):** a quality-adjusted Laspeyres-chained *index* of
  free-market transaction prices (notarial data, hedonic + stratification).
  It measures price *trend*, not price *level*: IPV 80 vs 60 says prices rose
  ~33% between those years, nothing about €/m². New/segunda-mano splits are
  published. Grain: national + CCAA (+ Ceuta/Melilla separately). **There is
  no provincial IPV** — any "provincial price" would be a fabrication.
  Base identity guard: Nacional/General/2025 == 100.0, checked at build.
- **Parque (MIVAU):** estimated dwelling *counts* by provincia and year,
  split principal / no-principal. Method: Census 2001/2011/2021 anchors plus
  yearly modelled flows (finished homes in, withdrawals out). Inter-census
  years are estimates, rebased at each census — treat census seams (2001,
  2011, 2021) as revision points, not organic jumps. Counts sum across
  provinces legitimately (unlike indices or medians).
- **Padrón (INE DPOP, 1996–2021) → ECP (INE, 2022–):** registered population
  to 2021, resident population (Estadística Continua de Población, Tempus3
  56940, CCAA grain) from 2022. Same reference point (1 January), different
  methodology. The 2021 overlap is quantified at build (ECP-vs-Padrón: max
  +0.89% Balears, most CCAA <0.2%) and stored in `coverage.json` — a benign
  seam, not a silent splice. Column `pop_source` tags every row.
  Provincial ECP (table 56945) is unreachable via the public API (volume
  block + empty series/filter endpoints, probed 2026-10-06), so the
  **provincia mart ends 2021** while CCAA/national run to 2025.
- **Hogares (INE ECP, 2021–):** households in family dwellings, CCAA (60131)
  and provincia (60133), 1-January. Enables `viv_por_hogar` — dwellings per
  household, the closest observable to shortage (a region can have ample
  dwellings per capita yet few per household when second/vacant homes dominate).
  NULL before 2021; household-size breakdown queued.
- **Renta (INE ECV, Tempus3 9949, CCAA):** mean net household income.
  TIMING: ECV survey year Y reports calendar-year Y−1 incomes — the build
  stores `renta_anyo = encuesta_anyo − 1` and joins on income year (table
  49146 verified byte-identical content, not fetched). Enables
  `afford_90m2_years = eur_m2_libre × 90 / renta` (CCAA mart only — no
  provincial incomes in Tempus). Means-on-means: blind to inequality.
- **Turísticas (INE VTE, 39364/46141 CCAA+provincia):** registered tourist
  dwellings, monthly registry snapshots from 2020 — December (or latest
  month) kept, never averaged. Uniprovincial CCAA appear as duplicate
  CCAA+provincia series (verified value-identical, first kept with a guard).
  Marts carry `viv_turisticas` + `share_turistica_no_princ` (2020–). Finding:
  4–6% of non-primary stock in most CCAA (Balears/Canarias higher), falling
  2021→25 — tourist flats are not the composition crisis.
- **Hipotecas (INE HPT, 76316/76317 CCAA+provincia, 76315 rates):** monthly
  mortgages constituted on dwellings (número + importe, thousands of EUR)
  and national average rates (total/fijo/variable). Marts carry annual
  `hip_viv_num` + `hip_ticket_miles` (complete 12-month years only; NULL
  before 2003) and a `tipos_hipoteca_nacional` table. CCAA/provincia grain
  for volumes; rates national-only. Layout swap between tables handled
  structurally (territory↔measure positions differ).
- **Edades (ECP 56940 single-year detail, CCAA):** `scripts/parse_edad.py`
  aggregates to 0–19/20–34/35–49/50–64/65+ at 1-January. Overlap guards
  verified arithmetically: single years 85–99 and both centenarian series
  live inside the grouped `85 y más años` (bands must sum to the published
  total within 2e-4; early back-series years carry integer-rounding noise).
  The mart carries `pob_20_34`/`share_20_34` — the household-formation ages.
- **Valor tasado (MIVAU, 1995–):** appraisal-based mean €/m² (Libre/Protegida),
  stratified by urban area/age/type and weighted by cadastral stock. This is
  the price *level* complement to IPV's *trend* — and it exists at provincial
  grain (48 provinces direct; Madrid/Murcia/Navarra/Asturias filled from
  their identical CCAA aggregate and flagged). Caveats: appraisals, not
  transactions (mortgage-selection bias); NOT quality-adjusted, so composition
  shifts leak into the series; 844 unpublished quarter-cells kept missing.
  Validation: Nacional Libre YoY changes correlate **0.95** with IPV YoY
  (18 years) — two independent methodologies telling the same trend story.
- **Census dwellings (2001/2011):** independent anchors for the stock series.
  The 2021 anchor is embedded in the parque rebase; pinning the 2021 census
  table is queued as a cross-check, not a blocker.

## 2. Derived ratios (the actual subject)

- `viv_por_1000_hab = viviendas_total / poblacion * 1000` — dwellings per
  capita; the core supply-vs-people lens.
- `share_no_principal` — second homes + vacant; high values change what
  "shortage" means (stock exists but is not primary housing).
- Dwellings-per-*household* (queued): dwellings can exceed households while
  households still face shortage (second homes, vacant, mismatch). Needs ECH.

## 3. Join rules enforced in code

- Counts sum; indices never sum/average across territories — CCAA IPV is read
  from INE rows.
- Ceuta+Melilla: stock is one MIVAU aggregate; Padrón rows are summed to
  match; IPV rows are kept separate (no aggregate fabricated) and therefore
  absent from `mart_ccaa_anual`.
- Missing cells stay NULL with a coverage report (`data/processed/coverage.json`).
  `make verify` fails on null keys/counts, not on documented NULL IPV.
- Additive guard: principal + no-principal == total for every parque cell,
  checked at build.

## 4. Reading the charts honestly

Spain 2007–2013 shows the pattern that motivates this project: IPV Nacional
fell ~36% while dwellings per 1,000 inhabitants *rose* (stock outlived demand
and kept being finished). After ~2014, prices recovered while per-capita
stock plateaued — and since 2021 the screw turned further: dwellings per
1,000 inhabitants *fell* (565→552) while dwellings per household fell
1.44→1.39, as household formation outpaced construction. These are
descriptive co-movements. Composition (what got built, where), credit
conditions, and household formation all confound any causal reading —
this project does not attempt one.
