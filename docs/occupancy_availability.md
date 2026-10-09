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
| 7 | Idealista/data listings | Commercial-only; wrappers are ToS risk | Down to sección, weekly | Park (commercial API confirmed 2026-10-09) |
| 8 | Eustat EUV non-principal dwellings (Euskadi) | Only recurring small-holder vacancy cut (owner type × offer status) | Territorio histórico / size bands, biennial | Watch (series PDF-locked; HTML tables lack owner split) |

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
series or request one before any integration. Recheck 2026-10-09: the 2025
edition keeps the same PDF-only format and the statistics page still lists
no tabular endpoint; the only CSV surfaced is a Madrid-only regional series,
which does not fill the national gap — park stands. Data quirk for that day:
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
Tables 02-08 (régimen, sexo, edad, IPREM, composición) assessed
2026-10-09 and parked: all seven are municipal-grain crosstabs with
the same title/filter/footer skeleton as table 01 (header layout
 byte-identical between the oldest and latest table-02 files checked),
so a future pull is mechanical — but their content is composition of
the already-pulled inscription counts (tenure preference, applicant
demographics), descriptive only with no estimator consumer and no open
hunt gap behind them. The documented demand-side gap was the counts
themselves. Revisit if an estimator or narrative needs demand
composition; per-table category specs and the window-start-optional
footer variant are recorded here for that day.

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
years of unjustified vacancy. The [Directorate-General for Cadastre](https://www.catastro.hacienda.gob.es/es-ES/estadisticas_9.html)
also publishes municipal ordinance/rate tables. These record the instrument
adopted, not how many dwellings were actually declared vacant or charged.
Article 34 of Law 12/2023 separately requires annual aggregate publication of
vacant-home and applied-surcharge counts, but does not prescribe a single
central municipal dataset. Bounded portal check (2026-10-09): Sevilla's 2026
ordinance regulates the surcharge, but no annual count of assessed homes was
located; Madrid's reviewed 2026 ordinance does not appear to adopt the
vacancy surcharge, and no Article 34 vacancy return was located there.
Barcelona's reviewed municipal material describes an ordinance surcharge,
but no annual applied-home count surfaced. Zaragoza's 2026 ordinance retains
a conditional surcharge but leaves qualifying conditions to regulation; no
annual count surfaced. Málaga's reviewed 2026 IBI sources show no adopted
vacancy surcharge. Alicante's reviewed ordinance also has no vacancy
surcharge; no Article 34 return surfaced. Press reporting says Palma removed
its surcharge for 2025; no applied-home count surfaced. Bilbao's July 2026
municipal inventory estimates six thousand nine
hundred thirty-five dwellings with indicators of vacancy (four point two
percent of the stock), using padrón, public registers and abnormally low
water use; one thousand five hundred sixty-five are estimated to have been unoccupied
for at least two years. These are indicators/estimates, not formal legal
vacancy declarations or an IBI surcharge count; no annual applied-home total
surfaced. Follow-up: the city has since adopted 2027 fiscal ordinances with
a vacancy surcharge and a near-total bonus for homes entering public-rental
programs, while the declaration ordinance itself is still in process (Pleno
expected in the early months of 2027). Recheck after that Pleno for the
first formal declaration counts; until then this remains an
indicators-only lead, not a reusable legal-status series. One positive city-level signal surfaced
in València: a
municipal announcement
said the surcharge would apply to 41 homes held by six large holders, based
on the regional register dated 31 December 2022. A later press report citing
a municipal response says 26 were actually charged in 2023, while also
quoting an earlier figure of 29; the difference between announced, eligible
and billed counts is unresolved. These are a narrow large-holder
administrative subset, not a full vacant-stock count or an annual Article 34
series. The spot check is not a Spain-wide absence claim. No integration:
ordinance rates and locally declared counts are not comparable
availability measures.

If pursuing the gap, the next reproducible step is a public-information
request to a municipality that operates the surcharge (València is the clearest
lead). Request annual aggregate counts of residential properties formally
identified as vacant, cases assessed the surcharge, and cases actually
liquidated/collected, by fiscal year; ask for the applicable definition,
reference date and coverage, and a zero/not-collected distinction. Request
no owner names, addresses or property-level records. Draft for València
(not submitted):

> Al amparo del derecho de acceso a la información pública, solicito para
> cada ejercicio disponible desde 2023 los datos agregados municipales sobre:
> (a) viviendas habituales y viviendas identificadas formalmente como vacías
> o deshabitadas; (b) inmuebles a los que se inició o resolvió aplicar el
> recargo del IBI por desocupación; y (c) inmuebles efectivamente liquidados
> y recaudación, si se dispone de esos datos. Para cada cifra, indiquen el
> ejercicio de referencia, fecha de corte, definición y cobertura; distingan
> cero de dato no disponible/no publicado. Solicito el fichero o tabla en
> formato reutilizable y excluyo expresamente nombres, direcciones y cualquier
> dato identificativo o registro de inmueble individual.

No request has been submitted. València's official [public-information access procedure](https://sede.valencia.es/sede/registro/procedimiento/AD.IS.50?lang=1)
accepts requests online, including a route without a digital certificate;
filing requires the requester to provide contact and notification details.
Sources: [Law 12/2023, Article 34](https://www.boe.es/buscar/act.php?id=BOE-A-2023-12203&p=20231228&tn=0),
[Sevilla 2026 fiscal ordinance](https://www.sevilla.org/servicios/agencia-tributaria-de-sevilla/ordenanzas-fiscales/ordenanzas_2026/ordenanzas-2026-libro.pdf),
[Madrid 2026 IBI ordinance comments](https://transparencia.madrid.es/UnidadWeb/UGNormativas/Normativa/HUELLANORMATIVA/Fiscales/2026/IBI/Ficheros/MemoriaAlegaciones20251126.pdf),
[Barcelona housing-policy note](https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/141817/1/Quaderns%20habitatge_n%C3%BAm%201_2025.pdf),
[Zaragoza IBI ordinance](https://www.zaragoza.es/sede/servicio/normativa/3444),
[Málaga IBI information](https://gestrisam.malaga.eu/tributos/tributos-destacados/i.b.i./),
[Alicante IBI ordinance](https://www.alicante.es/es/normativa/impuesto-bienes-inmuebles),
[Palma IBI ordinance](https://seuelectronica.palma.es/portal/PALMA/sede/RecursosWeb/DOCUMENTOS/1/1_153224_1.pdf),
[reported Palma removal](https://www.ultimahora.es/noticias/palma/2024/09/16/2242399/psoe-denuncia-cort-elimina-recargo-del-50-por-ciento-del-ibi-viviendas-grandes-tenedores-desocupadas.html),
[Bilbao vacancy-inventory update](https://www.bilbao.eus/cs/Satellite?autoplay=si&c=BIO_Noticia_FA&cid=1279249697409&language=es&pageid=3000075248&pagename=Bilbaonet%2FBIO_Noticia_FA%2FBIO_Noticia),
[Bilbao 2027 fiscal ordinances](https://www.agenciadenoticias.es/2026/09/25/el-ayuntamiento-de-bilbao-aprueba-congelar-las-tasas-de-2027-e-impulsara-la-movilizacion-de-vivienda-vacia/),
[Bilbao ordinance-process announcement](https://www.bilbao.eus/servlet/Satellite/vvmm/es/noticias/bilbao-inicia-la-tramitacion-de-una-ordenanza-para-regular-la-incorporacion-de-la-vivienda-deshabitada-al-mercado-de-alquiler/vm_noticia_fa),
[València surcharge announcement](https://www.valencia.es/es/-/0222-ibi-grandes-propietarios-1),
[reported 2023 billed count](https://elpais.com/espana/comunidad-valenciana/2024-02-05/solo-26-inmuebles-de-grandes-tenedores-pagan-en-valencia-el-recargo-del-ibi-por-permanecer-vacios.html).

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
- Small-holder vacancy has no recurring national measurement at all; the
  registers exclude small holders by design and the census snapshot does
  not repeat. The one regional exception is the Basque EUV survey
  (Euskadi-only, biennial) — see the second hunt round below.
- Water-consumption vacancy beyond the 2020 census snapshot: utility
  publications checked 2026-10-09; no reusable national dwelling-level
  series found. INE's water-supply survey publishes household-use results
  by autonomous community, not municipality, so it cannot fill the
  municipality panel. Sevilla's EMVISESA 2022 update describes use of
  EMASESA domestic-consumption records, but the dwelling-level file was
  not located as a public download. Its existence is a lead for a future
  public-information request, not a reproducible data source today.
  Aggregate billed-water totals cannot identify vacant dwellings.
  Sources: [INE 2024 water survey](https://www.ine.es/dyngs/Prensa/en/ESSA2024.htm),
  [EMVISESA 2022 update](https://www.emvisesa.org/wp-content/uploads/2023/06/ESTUDIOESPECIFICOACTUALIZACIONVIVIENDAVACIA2022.pdf).

## Second hunt round (2026-10-09): small-holder vacancy + asking-stock

Small-holder vacancy: the only genuine recurring measurement found is
Eustat's Encuesta sobre el Uso de la Vivienda (EUV, Euskadi-only,
biennial survey): it classifies non-principal dwellings by owner type
(including private individuals) and market situation (on offer for sale
or rent vs off-market "gestionable" stock). Verdict: watch, not pull.
The machine-readable surface is two single-year cross-section tables
with predictable CSV twins and no owner split; the gap-filling cuts
(owner-type series, gestionable series) live in the PDF reports only.
The Eustat databank node carries no dataset tables for this operation
as of now. Even pulled, Euskadi-only survey data would be a context
sidecar, never a mart join. Revisit when a new edition extends the
downloadable tables. Recheck 2026-10-09: latest edition remains 2023
(reference period 2023, published May 2024); no 2025 edition out yet and
no next-update date announced — watch stays. ECV was confirmed structurally blind (it samples
principal dwellings only). The Basque deshabitada canon register is
procedural (municipality-initiated, no public municipal series found) —
context only, alongside the IBI surcharges.

Asking-stock: park confirmed. Idealista listing microdata sits behind
commercial request-access APIs; Fotocasa publishes survey-based
perception reports (offer/demand participation, "ineffective demand")
as web pages with no tabular series. Both duplicate existing price
signals or measure perceptions, not counts — no integration. Two
context-only notes for future work: Fotocasa's ineffective-demand
framing complements RMDVP registered demand at national survey grain;
CaixaBank's province deficit (household creation minus completions in
several variants) is now implemented as a derived series, not a source
pull — see the [deficit exploration](explorations/deficit_vivienda.md).
Reproduced: finished-dwellings variant from MIVAU VDP005 plus a
tourist-adjusted partial; not reproduced: visados variant and the
foreign-buyer adjustment.

## Bounded next implementation (status 2026-10-09)

1. AEAT integration: DONE 2026-10-09 — `fetch_aeat_viviendas.py` plus
   `aeat_viviendas_uso` mart with audit pins; no estimator reads it.
2. Section-grain census pull: DONE 2026-10-09 — `fetch_censo_secciones.py`
   plus `censo2021_secciones` mart with occupancy ratios and quarantine.
3. MIVAU unsold-new provincial series: assessed 2026-10-09, parked
   (PDF-only, no tabular endpoint, bot-walled downloads).
4. RMDVP watch: resolved positive 2026-10-09, table 01 pulled.
