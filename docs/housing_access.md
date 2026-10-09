# Housing access: stock, availability, and household burden

Implemented 2026-10-08 in [`evidence/pages/acceso.md`](../evidence/pages/acceso.md).
This is a descriptive chapter using existing marts plus a separately pinned
[national EU-SILC burden layer](housing_overburden.md) and a separate
[own ECV age × poverty × tenure layer](ecv_joint_scope.md), not a new causal
estimator or a local/full age × income × tenure affordability dataset. Numbers in its tables
are queried from the marts and sidecars rather than copied into narrative text.

## Research questions

- Where is access tightening relative to household growth?
- Who bears the cost? National EU-SILC person rates add separate income,
  tenure and age breakdowns plus a direct age-by-poverty cross. Own ECV estimates
  add a national age × poverty × tenure cross, not income quintiles; local
  household burdens remain unknown.
- How much stock is usable, suitably located, and available? Occupancy
  classifications cannot answer this on their own.

Madrid, Barcelona, and the Valencian coast are illustrative cases, not a
representative sample of markets. Regional incomes, provincial stock and
municipal vacancy must not be silently combined into a local burden metric.

## Claim register

Last implementation verification: 2026-10-08. This date records the chapter's
initial checks, not automatic certification of later data refreshes. Run the
SQL contract tests and validate the queries against rebuilt marts on refresh.

| Claim or question | Query / artifact | Grain and vintage | Uncertainty / caveat | Permitted interpretation |
| --- | --- | --- | --- | --- |
| Total stock is not available supply | `stock_acceso`; `mart_provincia_anual` | Selected provinces, 2021 and 2025 | Modelled stock; non-primary mixes secondary and vacant; use classifications do not identify listings | Compare occupancy composition, not a mobilizable reserve |
| Vacancy differs within markets | `vacancia_acceso`; `vacancy_municipal` export from `censo2021_intensidad` | Selected municipalities, 2021 | Electricity-based classification; no habitability, legal status, willingness to rent or current availability | Historical spatial contrast, not a vacancy trend |
| Regional purchase-price/income reference | `compra_acceso`; `mart_ccaa_anual` | CCAA, price and income year 2024 | Appraisals and mean net income; reference dwelling size; no financing costs | Ratio of averages, not first-time buyer affordability |
| Market-cost burden can be high | `cargas_acceso`; `muni_bcn` DIBA indicators | Selected Barcelona municipalities, 2022 | Ratios of mean costs to mean gross income; not individual household observations | Market-effort comparison within this source and year |
| Stock and household growth can diverge | `cambios_acceso`, `cambios_foco`; `mart_provincia_anual` | Provincial endpoints, 2021–2025 and 2022–2025 | Net modelled stock and measured household changes, not completions and gross formations; changing window duration | Compare growth rates separately; no usable-home deficit estimate |
| Is the aggregate gap driven by weighting or one province? | `sensibilidad_acceso`, derived from `cambios_acceso` | All eligible provinces, excluding combined Ceuta/Melilla | Complete-endpoint sample count shown; equal-province mean differs from aggregate-of-counts estimand | Arithmetic sensitivity, not confidence bounds or regression robustness |
| Tourism's price effect is not established | `artifacts/panel_tourist.json`; `explorations/panel_tourist.py`; [panel note](explorations/panel_tourist.md) | Barcelona municipal panel | Endogenous licensing, limited within variation, incomplete activity coverage; insignificant estimates do not bound relevant effects | No detected association in this design, not proof of negligible effects |
| National distributional burden is now observable | `sobrecarga_ingresos`, `sobrecarga_tenencia`, `sobrecarga_edad`; `access.overburden` | Spain, latest survey year displayed | Person rates, separate marginals; not local household rates, no sampling intervals in these extracts | Group-specific national burden, without joint age/income/tenure inference |
| Published age × poverty burden is observable | `sobrecarga_edad_pobreza`; `access.overburden_age_poverty` | Spain, same latest survey year | Conditional person rates, all tenures; poverty status is not income quintile; no intervals | Direct partial national cross, not reconstructed intersections or renter/local evidence |
| National space strain is now observable | `hacinamiento_quintil`, `hacinamiento_tenencia`, `hacinamiento_urbano`; `access.overcrowding` | Spain, latest survey year displayed | Person rates, separate marginals; tenure cut carries no published national total; no intervals | Group-specific overcrowding, not a causal or local crowding claim |
| Under-occupation is now observable | `infraocupacion_edad`, `infraocupacion_tenencia`; `access.underoccupation` | Spain, latest survey year displayed | Person rates, separate marginals; under-occupied is not available; no intervals | Quantifies slack in room use, not a mobilizable reserve |
| Median burden complements the overburden rate | `carga_mediana_edad`, `carga_mediana_urbano`; `access.burden_median` | Spain, latest survey year displayed | Median of the burden distribution, not a rate above a threshold; no intervals | Center of the cost distribution, not a substitute for the threshold rate |
| Own national age × poverty × tenure burden is estimable | `ecv_cruce_seleccionado`; `ecv.joint_burden` | ECV survey and income years displayed separately | Complete-case person weighting, shared household classification and co-residents; project sample/coverage suppression; all overlapping own marginal rates withheld | Conditional descriptive rates in mutually exclusive groups, no quintiles, design intervals, causal or local claims |
| Full age × income-quintile × tenure/local burden remains unknown | No local age × income × tenure burden artifact | No comparable cross-market series assembled | Published marginals and the own poverty cross cannot recover income-quintile or local distributions | Explicit data gap, not a finding about young low-income renters in a city |

## Arithmetic sensitivity contract

`cambios_acceso` matches exact endpoints by province key. It retains only
positive, non-null stock and household levels at both endpoints. Zero or
negative *growth* is valid; there is no division by growth. Missing endpoints
are excluded, not interpolated; the summary exposes the resulting sample
size for each window.

The growth gap is stock percentage change minus household percentage
change. It is not a count of missing homes. `sensibilidad_acceso` reports:

- The equally weighted mean provincial gap.
- The gap between growth of summed stock and growth of summed households.
  Each growth has its own initial-level weights; this is not a common
  population-weighted mean of provincial gaps.
- Minimum and maximum aggregate gaps after removing each province in turn.
  These are influence diagnostics, not statistical confidence intervals.

The windows test endpoint sensitivity, not equal-duration growth or causal
identification. Neither removes model revisions or source-definition seams.
No price regression has been re-estimated for this chapter.

## Remaining data gaps

The national published burden panels and the separately documented 2025 ECV
age × poverty × tenure analysis are now implemented; see
[the ECV benchmark and scope note](ecv_joint_burden.md) and
[the joint-cell scope](ecv_joint_scope.md). They do not establish municipal
or provincial distributional burden: ECV publishes municipality-size groups,
not individual municipality estimates, and its public microdata do not
identify municipality. INE's Household Income Distribution Atlas supplies
local income, while Urban Indicators supplies rent expenditure for selected
cities, but combining area averages would not recover the ECV rate (person
share above 40% of household disposable income after total housing costs).
That would be a distinct rent-to-income proxy, not observed burden. On proxy
feasibility: the rent side already exists in the marts (SERPAVI municipal
medians, 2011–2024; see the SERPAVI probe), while the income side (ADRH
municipal net income per household and per person, 2015–2023 series with CSV
downloads) is not yet pulled. The year overlap is 2015–2023. A ratio of
median contract rent to mean household income would be mechanically feasible
but carries hard incompatibilities: SERPAVI medians describe new and rolling
tax-deposit contracts, not the sitting-tenant stock, and are suppressed in
small municipalities; ADRH means cover all households, not renters; and the
numerator excludes utilities and other housing costs. No integration until
the proxy semantics are explicitly accepted; never label it an overburden
rate. No local burden integration is otherwise justified without an
independently validated compatible source and household denominator; do not
infer local rates from national or regional marginals. Sources: [INE ECV FAQ](https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736176807&idp=1254735976608&menu=faq),
[ADRH](https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736177088&idp=1254735976608&menu=resultados),
[Urban Indicators](https://www.ine.es/dyngs/INEbase/en/operacion.htm?c=Estadistica_C&cid=1254736176957&idp=1254735976608&menu=ultiDatos).

For first-time buyers, the [purchase scenario calculator](purchase_scenarios.md)
now shows cash deposit, transaction-cost assumptions and debt service under
editable inputs. It is hypothetical, not observed borrower outcomes. The
Banco de España's [2026 Financial Stability Report](https://www.bde.es/f/webbe/Secciones/Publicaciones/InformesBoletinesRevistas/InformesEstabilidadFinancera/26/FSR_2026_1_Box4_1.pdf)
now provides national evidence on mortgage-financed first-time buyers and
financial-capacity constraints, while its Annual Report 2025 describes recent
buyers by age and household income. These are published analyses, not a
reusable local borrower microdata series; INE mortgage counts also do not
identify first-time buyers. Local first-time-buyer income, savings and lending
conditions therefore remain unmeasured in this project. Do not treat the
calculator inputs as observed outcomes.

Evidence check 2026-10-09: three further sources were assessed for reusable
buyer-side evidence. The [ECV 2025 housing-access module](https://www.ine.es/dynt3/inebase/es/index.htm?padre=13548)
(published tables plus free anonymized microdata) is the only directly
reusable source for access barriers — national and regional grain, not
municipal. The [EFF household-finance microdata](https://www.bde.es/wbe/en/estadisticas/anuncios/los-ficheros-de-microdatos-de-la-eff2022-estan-ya-disponibles-para-uso-cientifico-a-traves-de-su-web.html)
(scientific use, registration-gated) supports wealth and savings analysis but
is national-only and needs multiple-imputation handling, so it does not fit
this pipeline. The [PROP registry microdata](https://www.bde.es/wbe/es/punto-informacion/contenidos/servicios/belab/contenido/microdatos-disponibles/microdatos-de-la-estadistica-registral-inmobiliaria-prop.html)
(municipal transactions and mortgages) requires BELab researcher
accreditation and secure-environment access, so it is out of reach here.
Verdict (implemented 2026-10-09): ECV 2025 module tables pulled via
`fetch_ecv_access.py` — twenty-five JAXI tables at national grain with
demographic, tenure, quintile, urbanisation and municipality-size cuts,
plus a single regional table (blocked-search block by CCAA); no municipal
estimates. Single-year module (survey 2025), same sidecar treatment as the
Eurostat conditions pull: `access_moves`, `access_blocked` and
`access_youth` tables in `housing_access.duckdb` (under two thousand
cells, a handful of suppressed cells kept null), headline-identity and
reason-sum checks, cross-table headline agreement, page sections on
/acceso/ with contract tests. The ECV joint proof was rebuilt after the
sidecar write (all joint cells unchanged). EFF parked; PROP out of scope.

For vacancy, seek habitability, legal status, location relative to employment,
and evidence of entry into rental/owner-occupation. Retain census-definition
breaks and never subtract tourism as if occupancy categories were disjoint.
The [Sevilla rental-flow assessment](sevilla_rental_flows.md) checks the AVRA
deposit-register route: no municipal export was verified, and public deposit
collection for new contracts has a legal break from 2026-01-24. Legacy
receipts/refunds, cash balances and tenancy turnover cannot identify currently
available homes or a fall in rental supply. A privacy-preserving aggregate
request is drafted, not submitted.

A focused source check found no national table that cross-classifies the
census vacant-dwelling stock by habitability. INE's 2021 ECEPOV publishes
building condition and accessibility for main dwellings, with municipality
detail limited to provincial capitals and selected larger municipalities; it
cannot describe the vacant units themselves. A broader INE building-condition
table has wider municipal coverage but is from the 2011 census. These are
useful context, not a current vacant-home habitability measure, so neither is
integrated. Sources: [2021 condition table](https://www.ine.es/jaxi/Tabla.htm?tpx=56906),
[2021 accessibility table](https://www.ine.es/jaxi/Tabla.htm?L=0&tpx=56908),
[2011 municipal building-condition table](https://datos.gob.es/es/catalogo/ea0042823-edificios-destinados-principal-o-exclusivamente-a-viviendas-y-n-de-inmuebles-por-municipios-con-mas-de-2-000-habitantes-estado-del-edificio-y-ano-de-construccion-agregado-identificador-api-t20-e244-edificios-p04-l0-2mun45-px1).

For estimator robustness, separately pre-specify geography, leave-one-out
influence, weighting, alternative windows, price measurement, and intervals
for economically meaningful effects. The arithmetic panel above does not
substitute for those checks.

## Implementation and verification record

Interpretation corrections dated 2026-10-08 also update the synthesis,
README and linked tourism/Madrid–Valencia/Barcelona notes: insignificant
estimates no longer establish small effects, census vacancy no longer
establishes later absorption, and averages do not identify worker exclusion.
No existing estimator code, central marts or estimator artifacts were changed.

Verification ran lint, data verification, narrative and artifact audits,
freshness checks, the full offline test suite, real-mart execution of all
chapter queries, and an isolated strict Evidence build. Independent
read-only review findings were corrected. The build exposed missing exports
for existing Sevilla rental, purchase and asking-price tables; these were
restored, and a page-to-source contract test prevents recurrence.

The running dev service was left untouched. Existing sources were not
re-fetched, central marts were not rebuilt, and expensive estimator
regeneration was not repeated: their inputs and code were unchanged and
freshness checks passed. The new Eurostat inputs were fetched and pinned;
sidecar offline rebuilding and exact verification were tested. The central
mart hash remained unchanged. An independent read-only review of the
sidecar ingestion and presentation found no important issues. The isolated
strict build also passed after adding the distribution panels.
The built chapter has not been published or deployed. The
[INE ECV microdata assessment](ecv_joint_burden.md) verifies a public, linkable
national source for full age × income × tenure analysis. The national poverty-only cross is now implemented in a separate sidecar,
with matching relevant published benchmarks, complete coordinate coverage,
null suppression and aggregate source/mode provenance. Quintile ranking remains
unresolved and excluded; the inspected public files do not supply the original sampling-design
fields for confidence intervals. Municipal distributional burden collection
remains a separate gap.

### Own ECV implementation checks — 2026-10-09

`build_ecv_joint.py --offline` rebuilds only the pinned separate ECV sidecar;
`--check` verifies exact parquet/database derivation and source/method/code proof.
The claim register above distinguishes own estimates from published Eurostat
cells. Initial independent implementation review identified reversible
suppression via overlapping own margins and incomplete flag provenance; both
were corrected. Own marginal rates are now withheld, coverage remains visible,
and the proof contains full validated flag counts by sample unit. The unchanged
predeclared sample/coverage gates still apply to all disjoint published leaves.
Offline tests, lint, verification and audits, isolated strict build, and hydrated
selector checks (rates/nulls/status, coverage and imputation) pass; original
Eurostat panels also pass their regression smoke. Independent follow-up review confirmed flag provenance and the disjoint-rate
fix, and identified residual logical inference through shared households. The
UI and contract now explicitly state that even own aggregates may imply a hidden
outcome; withholding margins removes subtraction equations, not all inference.
No automated reconstruction is provided and confidentiality is not claimed.
No central-mart rebuild, estimator rerun, commit, push or deployment occurred.

### Market-rent comparison view — 2026-10-09

`ecv_comparacion_renta` now displays the complete disjoint age-by-poverty grid
for `RENT_MKT` side by side, including minors and older people. It projects
existing reviewed sidecar cells; it does not calculate new rates, sum totals,
rank groups, drop hidden rows, select a preferred age contrast or interpolate.
Survey/income years, sample-valid persons/represented households, weighted cost
loss, state and hiding reasons accompany the rates. Full target/valid weighted
denominators and imputation descriptors remain in the individual-cell selector.
The page explains the mechanical income link and shared-household dependence;
this is not an age effect, significance test, emancipation outcome or local rate.

Offline SQL contracts test market-rent/disjoint membership, absence of outcome
filtering and preservation of null versus genuine zero. The browser regression
checks every comparison cell against the sidecar, then all selector combinations,
coverage and imputation. Offline gates, isolated strict build/route metadata,
live comparison/selector checks and original Eurostat-panel checks passed.
All core and burden sidecar byte hashes were unchanged. No new independent review
was requested for this presentation-only projection; calculation methods retain
the prior independent review. No source refresh, statistical rebuild, estimator
rerun, dev-service restart, commit, push or deployment occurred for this change.
