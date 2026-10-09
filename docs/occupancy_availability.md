# Occupancy and availability evidence: source hunt

Assessed 2026-10-09. Research-only: no fetch scripts, no manifest pins, no
`data/raw` additions. The synthesis gap is matched-date, matched-geography
stock, households and rent **with occupancy/availability evidence** — this
note surveys what public sources could fill it, with a verdict per
candidate. Already-covered ground is not re-hunted: AVRA deposit flows
([rental-flows note](sevilla_rental_flows.md), no reusable export, 2026
legal break), census electricity vacancy and SIM `deshabitadas`
([vacancy alignment](explorations/cadastre_vacancy_alignment.md)),
properties-per-household ratios
([household alignment](explorations/cadastre_household_alignment.md)),
SERPAVI contract rents and tourist-dwelling counts (in the marts).

## Conclusion

No public source counts effectively available homes (willingness plus legal
access plus market listing). The closest recurring occupancy-composition
sources are tax-administrative (AEAT use split) and the census itself at
section grain; the closest genuine availability count is unsold new stock
(narrow: new segment only). Demand-side waiting lists exist (Andalucía) but
are PDF-only. Portal listings are commercial-only. Everything else is a
large-holder or fiscal instrument, not a statistical series.

## Shortlist

| # | Candidate | Verdict | Grain / vintage | Next step if approved |
| --- | --- | --- | --- | --- |
| 1 | AEAT viviendas declaradas en IRPF, use split | Strongest recurring occupancy composition | CCAA + provincia (+ municipal rentals); annual tax year, 2024 latest | Integration design |
| 2 | Censo 2021 inframunicipal dwellings/persons/households | Section-grain occupancy from one aligned source; 2021 vintage aging | Sección censal, 2021-01-01 | Verify-and-pull design |
| 3 | MIVAU stock de vivienda nueva sin vender | Genuine availability, new segment only | CCAA + provincia, annual to 2025-12-31 | Park (PDF-only, no tabular endpoint; assessed 2026-10-09) |
| 4 | RMDVP municipal demandante counts (Andalucía) | Demand-side waiting-list proxy; monthly .xls twins | Municipal, 2020-12.. monthly | Pulled 2026-10-09 (table 01 → `rmdvp_inscripciones`) |
| 5 | Catalan / Valencian vacant-dwelling registers | Large-holder vacancy signals, compliance scope | Regional, 2024–2026 | Context only |
| 6 | IBI vacancy surcharges | Fiscal instruments, not data | Municipal ordinances, heterogeneous | No integration |
| 7 | Idealista/data listings | Commercial-only; wrappers are ToS risk | Down to sección, weekly | Park |

## 1. AEAT use split: habitual, rented, at owners' disposal

The [AEAT Estadística de viviendas declaradas en el IRPF](https://sede.agenciatributaria.gob.es/Sede/estadisticas/estadisticas-impuesto/estadistica-viviendas-declaradas-irpf.html)
classifies every declared residential dwelling by use over the tax year:
habitual, rented at any point, or at the owners' disposal (generally a
second home, possibly an empty dwelling with no use). Geography is CCAA
plus provincia, with municipal detail for rentals and postal-code detail
for large rental markets; the 2024 edition is the latest verified. The
series incorporates the dwelling module published inside the IRPF
statistics since 2019, crossed with Catastro for location and surfaces.

Status 2026-10-09: integrated in `scripts/fetch_aeat_viviendas.py` (both
published vintages pinned; Total rows excluded per the pinned publisher gap).
Wired into the marts as `aeat_viviendas_uso` with headline audit pins; no
estimator reads it yet.

Why this is the strongest candidate: annual cadence, official methodology
([FAQ](https://sede.agenciatributaria.gob.es/Sede/estadisticas/estadisticas-impuesto/estadistica-viviendas-declaradas-irpf/metodologia/preguntas-frecuentes.html)),
matched reference year across stock/use/rent variables, and finer grain
than anything else recurring. Limits, all disqualifying for availability
but not for occupancy composition: only natural persons in the common
fiscal territory (no País Vasco or Navarra foral regimes); "at disposal"
entangles second homes with truly vacant dwellings and no public source
separates them recurrently; tax-concept use is not physical occupancy;
rented-vs-disposition priority differs from SERPAVI's (habitual first
here, rental first there — do not mix the two splits).

## 2. Census at section grain: one aligned source

Status 2026-10-09: integrated in `scripts/fetch_censo_secciones.py` and
wired into the marts as `censo2021_secciones` (34,970 usable sections,
1,363 suppressed carry persons only) with occupancy ratios; 2021 vintage
quarantined, cartography join keys verified not vendored.

The [Censo 2021 query system](https://www.ine.es/dynt3/inebase/index.htm?capsel=9817&padre=8952)
publishes dwellings, persons and households down to inframunicipal scope
(distritos y secciones censales), with [section indicator files](https://www.ine.es/uc/Kpj8DYAg)
in XLSX/CSV plus digitised section cartography. Persons-per-dwelling and
households-per-dwelling at sección grain come from one aligned source at
one reference date — no cross-publisher join, no vintage mismatch. Limits:
2021 vintage aging with no intercensal update; census dwellings are not
cadastral properties and persons are not households, so the ratios are
occupancy composition, never availability; microdata is a 10% sample with
suppressed small-municipality geography.

## 3. Unsold new stock: narrow but genuine availability

[MIVAU's stock de vivienda nueva](https://www.mivau.gob.es/el-ministerio/observatorios-y-estadisticas/estadisticas/stock-vivienda-nueva)
estimates unsold new dwellings annually at CCAA plus provincia grain; the
[2025 report](https://www.mivau.gob.es/recursos_mfom/comodin/recursos/stock_2025.pdf)
puts 452,670 unsold new dwellings at 31 December 2025 (455,280 a year
earlier). This is the only official series that counts dwellings for sale
and unsold — genuine availability, not a proxy. Limits: new segment only
(about one sixtieth of the dwelling stock); provincial grain, no municipal
detail; an estimation methodology (completions minus sales), not a listing
count; unsold does not mean affordable, habitable on arrival, or located
where demand is.

Series-pull assessment (2026-10-09): parked. The statistics page links
only report PDFs (recent vintages plus a revised-series note) with no
Excel, CSV or ODS endpoint; direct report downloads are bot-walled, so
there is no reproducible fetch path, and the repo stack has no PDF-table
tooling. A provincial annual series would mean hand-transcribing PDF
tables year by year — grey-zone extraction under the same rule that
parked the Valor de Referencia probe. Watch for a machine-readable
series or request one before any integration. Data quirk for that day:
several provinces and autonomous communities read zero in the latest
table under a methodology note, so zeros must be treated as
not-measured-or-suppressed, not as true zeros, before any use.

## 4. Protected-housing waiting lists: demand side, now pulled

The Junta de Andalucía publishes [monthly RMDVP statistics](https://www.juntadeandalucia.es/organismos/viviendajuventudyordenaciondelterritorio/areas/vivienda-rehabilitacion/vivienda-protegida/paginas/rmdv-estadistica-mensual.html);
the March 2025 municipal inscription PDF was verified live.
Registered protected-housing demand by municipality is the only
municipal-grain demand-side count found — it measures the queue for
regulated housing, a complement to supply-side vacancy, not a substitute.
Limits: Andalucía only; registered demand is not total demand (eligibility
and self-registration filter it).

Watch outcome (2026-10-09): the watch resolved POSITIVE — every monthly
table carries a machine-readable `.xls` twin in static archive-page HTML
(URL eras: `export/drupaljda` for older months, `sites/default/files`
for recent ones), running 2020-12 (single month) then full monthly from
2021-01. Table 01 (solicitudes y estado de inscripciones) is now pulled
by `scripts/fetch_rmdvp.py` into the `rmdvp_inscripciones` mart table:
69 monthly files, municipio grain with province subtotals and a
reconciling Andalucía total, strict layout/month/identity/aggregation
asserts per file. It is an end-of-month stock of registered demand with
inscripción states (total, activas, canceladas por adjudicación,
caducadas y otros). Baseline 2020-12: 518 listed municipalities with
257,208 solicitudes, 203,128 inscripciones (64,471 activas) — all four
audit-pinned; only the immutable first month is pinned because the
series grows with each publication. Coverage grows from 518 to 543
listed municipalities of 785 Andalusian municipalities: absent
municipalities have no recorded solicitudes and are never zero-filled.
Tables 02-08 (régimen, sexo, edad, IPREM, composición) remain unpulled
PDF-adjacent demographic breakdowns, same `.xls`-twin pattern if needed.

## 5. Regional vacant-dwelling registers: large holders, compliance scope

Catalonia's [register of empty and irregularly occupied dwellings](https://tramits.gencat.cat/es/tramits/tramits-temes/20184_Registre_Habitatges_Buits)
(foreclosure-sourced large-holder stock, running since 2015) stood at
25,443 dwellings at 31 December 2024, press-reported from Agència figures
with demarcación and top-municipality detail; a new large-holder register
for tense zones was announced in February 2025 with no published output
yet. The Valencian [register](https://habitatge.gva.es/es/registres-en-materia-habitatge)
(holders of ten or more dwellings, two years vacant) fell from 3,237
dwellings in 2023 to 1,281 in 2025 and 1,181 in 2026 while the AEAT IRPF
statistic counted 635,919 unoccupied Valencian dwellings across all
holders in 2024 — the collapse reads as self-reporting compliance, not a
market change. Limits: large-holder scope by construction; self-reported;
heterogeneous legal definitions across regions; press-mediated totals
rather than statistical tables. Context for large-holder vacancy only.

## 6. IBI surcharges: instruments, not data

The 2026 ordinance compilation at [guiafiscal.es](https://guiafiscal.es/downloads/estudio-recargo-ibi-vivienda-vacia-2026.csv)
(secondary) shows the full heterogeneity: San Sebastián applies 150% to any
dwelling with nobody registered; Soria, Pontevedra and others use
registration-plus-consumption tests; most capitals restrict the surcharge
to large holders (four or more, sometimes ten or more dwellings) with two
years of unjustified vacancy. These ordinances create vacancy-detection
machinery (Pontevedra even compiles a vacancy census for application) but
publish no statistical output. No integration: tax instruments with
jurisdiction-specific definitions are not comparable dwelling counts.

## 7. Portal listings: commercial-only

[Idealista/data](https://www.idealista.com/data/) sells comparables APIs,
zone metrics down to sección censal, and bespoke market reports over
millions of tracked properties on a weekly cadence — exactly the
asking-stock signal missing elsewhere. But there is no free research
series, only commercial products and marketing summaries; third-party
scraping wrappers carry ToS risk and sampling opaqueness (deduplication
does not make paginated results a snapshot). Parked: no commercial
dependency and no grey-zone extraction in this pipeline.

## What remains unfillable

- Effective availability has no public count: willingness, legal access
  and market listing are jointly unobserved. Unsold-new covers the new
  segment; asking-listings are commercial; registers cover large holders.
- Second homes and true vacancy are entangled in every recurring source
  (AEAT "at disposal", MIVAU/census non-principal, consumption bands).
  Only the one-off 2020 consumption snapshot ever separated them, by
  assumption-laden bands.
- Small-holder vacancy has no recurring measurement at all; the registers
  exclude small holders by design and the census snapshot does not repeat.
- Water-consumption vacancy beyond the 2020 census snapshot was not
  surveyed (utility publications unchecked).

## Bounded next implementation (conditional, not started)

1. AEAT integration design: fetch module for the use-split tables, foral
   exclusion handling, use-priority semantics vs SERPAVI, annual cadence.
2. Section-grain census pull design: indicator files plus cartography join
   keys, ratio definitions, 2021-vintage quarantine.
3. MIVAU unsold-new provincial series: assessed 2026-10-09, parked
   (PDF-only, no tabular endpoint, bot-walled downloads).
4. RMDVP watch: resolved positive 2026-10-09, table 01 pulled.
