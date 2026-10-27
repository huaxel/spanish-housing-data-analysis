# Municipal profile: scope and query contract

The `/perfil/` explorer brings existing municipal evidence into one selector.
It adds presentation queries and an isolated standalone-income presentation
sidecar, not a new estimator or data fetch. It does not modify the central
marts or any existing sidecar.

## Geography and selection

The page catalogue is the union of five-digit codes in the section-grain
census, SERPAVI and standalone ADRH. `housing.perfil_catalogo` retains the
original census/SERPAVI base. Page SQL adds the ADRH codes without requiring
rental records, using ADRH's latest retained name only where SERPAVI lacks a
name. The identity table shows the municipal-name source. Province labels
come from `housing.perfil_provincias`, keyed by the code prefix, with Ceuta
and Melilla explicitly separate. Codes ending in `999` (Resto aggregates)
are excluded throughout.

A display-name change does not change the join key. Homonyms in different
provinces stay separate, including codes with leading zeros. This is a union
of retained source geographies, not an authoritative current municipality
directory or a boundary crosswalk. Historical, all-null or source-only codes
remain selectable; no reallocations or interpolations are made for mergers,
segregations or boundary changes.

## Indicators

| Indicator | Export / query | Reference and interpretation |
| --- | --- | --- |
| Population | `housing.perfil_censo` | Section census sum at the census reference date; not current Padrón population |
| Dwellings and households | `housing.perfil_censo` | Section census sums only when every section publishes the measure and none is suppressed; not cadastral properties or available homes |
| Electricity vacancy | Existing `housing.vacancy_municipal` | Census classification based on prior-year electricity consumption; missing named municipalities are not allocated shares of Resto |
| Rent median and contract count | `housing.perfil_alquiler` | SERPAVI collective-housing measures `ALQM2_LV_M_VC` and `BI_ALVHEPCO_TVC`; nominal rent per square metre per month and published contract count, separately |
| Mean net household income | `profile_income.municipal` | Complete retained ADRH net household income series, independent of rent availability; all-household mean, not renter income |
| Rent/income proxy | Existing `access.rent_income` | Reviewed same-year monthly rent median divided by annual mean household income, annualized in the existing builder; not an individual burden or overburden rate |

The census exports retain their original census reference year. Market
headline years are dataset-wide maxima with a nonmissing selected measure,
independently for rent, income and proxy. They are not per-municipality maxima.
A missing local value in a headline year remains missing, even if an older
local value exists. Each row displays its own year, unit, source and limit.
No cross-source availability deficit, price prediction or local ECV rate is
computed. Different census products are not forced to reconcile by subtraction.

The rent export preserves code/year keys even when the selected measures are
missing. If a selected measure is duplicated, its value is withheld rather
than averaged. Existing input parsers/builders guarantee their own keys; the
page does not resolve ambiguous source records by names.

## Explicit limits

- Population, dwelling and household context is historical census evidence,
  not a contemporary local stock-demand balance. Summing only published
  sections would silently undercount some municipalities: those stock and
  household totals are instead withheld. Population can remain published
  in otherwise suppressed sections.
- Census stock is not the same unit as cadastral property counts. Neither
  stock nor low electricity consumption establishes habitability, legal
  access, willingness to offer, current listings or affordability.
- Standalone income is independent of the reviewed rent-income cross. The
  proxy and its history still come only from `access.rent_income`; they are
  never widened, recalculated or filled with the standalone income values.
  A missing standalone income cell stays null, with no invented distinction
  between secrecy, source thresholds and other publication gaps.
- ADRH averages describe all households. Its small-municipality diffusion
  rules can substitute broader-area income averages without a row-level
  flag; the profile discloses that existing source behavior and makes no
  new regional substitutions.
- Rents and income remain nominal. The signing-market proxy has the
  limitations documented in [housing access](housing_access.md), including
  missing housing costs and the non-renter-specific income denominator.
- Source-coverage gaps and suppressed values stay null; a published zero
  remains zero. A null is not assigned a suppression cause unless section
  suppression is actually known.
- Calendar rows explicitly retain missing interior years, and charts use
  gaps rather than connecting or filling those years.

## Verification

`tests/test_evidence_profile.py` exercises the actual export and page SQL
against synthetic records: homonyms, apostrophes, leading-zero keys, census
suppression, incomplete sums, duplicate rental measures, missing endpoints,
true zeros, calendar gaps and fixed dataset-wide cuts. The general
page/source and route-metadata contracts cover the new exports and route.
`scripts/smoke_browser.sh` includes profile content and chart hydration.
`make evidence-smoke-profile` additionally changes the selector and compares
all indicator and history cells against read-only real-source queries,
including leading-zero, census-only and suppressed-section cases.
The section-table quarantine allowlist admits only the two historical profile
exports, not current-series or estimator consumers; generated Evidence copies
are excluded from that source-consumer scan.
The independent release checks remain `make lint test verify audit` plus an
isolated strict Evidence build and browser checks. Build/dev entry points export standalone income and verification checks it;
the estimator pipeline is unchanged. Frontend-only verification does not
claim a fresh full-pipeline reproduction. Source definitions remain authoritative in
[sources](sources.md), [dictionary](data_dictionary.md), and
[section-census scope](occupancy_availability.md).

### Initial profile verification — 2026-10-26

Offline lint, the full test suite, data verification and claim/freshness audits
passed. An isolated strict source extraction and Evidence build passed without
restarting the active dev service. Browser checks passed for the default city,
a leading-zero code, a census-only municipality and a municipality with
suppressed census sections; identity, indicator values/nulls/statuses and both
history tables matched the real-source queries. The mobile page had no
horizontal document overflow. Independent read-only review found no blocking
issues; its interactive-selector suggestion was implemented and verified.
The follow-up review accepted the narrow historical census presentation
exception. No source refresh, mart/sidecar write, estimator rerun, commit,
push or deployment was performed for this feature.

## Standalone ADRH income extension

`scripts/export_profile_income.py` projects only `neta_hogar` from the already
pinned `adrh_renta_municipal.parquet`. It requires valid five-digit codes,
matching province prefixes, unique municipality/year keys and the complete
retained year grid for every source municipality. Null income observations
and municipalities with no published values are retained, not dropped; a
published zero remains zero. The input contains the full municipal table,
not district/section observations and not a rental-market selection.

The new `data/processed/profile_income.duckdb` sidecar contains `municipal` and
`export_meta` tables. The proof pins the source-parquet and exporter bytes;
input bytes must match the existing manifest. `--check` verifies every row
and proof field read-only. No input-manifest re-pin, CSV parse, mart write,
existing-sidecar write, rent join or proxy recalculation is performed here.
The normal source parser and its exact-parquet check remain authoritative.

```bash
make profile-income
uv run python scripts/export_profile_income.py --check
make lint test verify audit
make evidence-smoke-profile  # against a built/running matching version
```

Standalone income has its own dataset-wide headline year and calendar-filled
history. It cannot backfill a missing latest local value or alter the proxy's
reference year. The new export tests cover pins, source-grid integrity,
all-null municipalities, true zeros and exact read-only derivation. Profile
SQL/browser regressions additionally cover income without rent or a proxy,
ADRH-only codes and source-specific year gaps. Existing small-municipality
source substitutions are disclosed without claiming to identify affected rows.

### Income-extension verification — 2026-10-26

Offline lint, all tests, data verification and claim/freshness audits passed.
Strict isolated source extraction/build passed, including both the original
Sevilla barrio-income datasource and the new `profile_income` namespace.
Independent review caught the initial datasource-name collision and a
whole-municipality omission gap in validation; both were corrected, covered
by regressions and accepted on follow-up read-only review.

Interactive profile checks matched identity/name provenance, values, nulls,
source-specific dates and all three histories against real queries, including
income without rent/proxy, suppressed latest income and an ADRH-only code.
Mobile document width stayed within the viewport. The combined browser smoke
passed every tested route and map, including the original stock feature;
the deficit interactive regression also passed.

Only the new standalone-income presentation sidecar was generated. No input
refresh, re-pin, central-mart write, existing-sidecar write, proxy/estimator
recalculation, dev-service restart, commit, push or deployment occurred.
The full network-fetch/analysis pipeline was not rerun. Source-level null
causes and small-municipality substitution flags remain unavailable; the
profile does not reconstruct them.


## Matched municipality comparison

`/comparar-municipios/` is a presentation-only comparison of compatible
published measures, not matched housing samples or causally comparable markets.
It reuses the profile catalogue contract (tested for exact SQL equality),
code-keyed sources and suppressed census aggregates. No raw input, mart,
sidecar, estimator or existing rent-income proxy is changed.

The reader chooses two municipal codes, one measure and inclusive years.
Inverted year controls are ordered rather than silently clipping the window.
Supported measures remain distinct: SERPAVI median collective-housing rent
per square metre/month, standalone ADRH mean annual net household income,
and the already-reviewed rent-income proxy. Income without a rental sample
does not fill that sample or extend the proxy. Metadata shows the active
source/unit; proxy level differences are percentage points, not percentage
changes. All currency values are nominal.

For every requested calendar year the query retains both published values,
including genuine zeros. A year is common exactly when both values are
nonnull in that same year for that same selected measure. The chart and its
CSV/JSON show both series only on this common support, with explicit null
calendar rows elsewhere, so missing interior years break lines. The audit
table separately retains individually published values in excluded years.
Coverage reports requested years, each side's observed years, excluded
count and the exact list of common years; first/last common dates alone
would conceal internal holes. No change between substituted endpoints,
interpolation, growth ratio, implicit complete-case average or significance
interval is computed. A displayed A-minus-B difference uses the same year
and measure and is null without common data.

If the same municipality is selected twice, the chart renders one series
and differences are withheld: there is no independent A/B contrast. If
there are no common years, the coverage state says so, chart values remain
null and no historical backfill is performed. Homonyms stay distinct through
codes/provinces and code-bearing chart labels. The catalogue includes
historical and ADRH-only municipalities, not just complete rental cases;
no boundary crosswalk or relocation of Resto aggregates is implied.

Census population/dwellings/households and electrical vacancy are shown in a
separate historical table. Census reference and electricity-consumption years
remain explicit; this table does not change when the annual measure/window
changes and is not fed into the annual comparison. Partial suppressed
census totals stay withheld. These counts do not establish current available
supply, habitability or the homes a locality needs.

Unit tests exercise disjoint supports, interior gaps, valid zeros, metric
isolation, inverted/single-year windows, A/B reversal, identical selections,
name collisions and invariant censal context. Browser checks compare the
reactive controls, coverage, chart-query downloads and historical table
against actual source queries, including empty support and suppressed income.
The evidence panel uses the current resolved comparison query; its listed
source inputs cover the possible selector measures, not an assertion that
every measure uses every file. Definitions and publisher substitutions in
the original profile still apply. This comparison does not control dwelling
composition, household mix, centrality, demand or changes in boundaries.

### Common-year comparison verification — 2026-10-27

Offline lint, all tests, input/data verification and claim/freshness audits
passed, along with an isolated strict Evidence build. Browser checks compared
all visible identity, unit, coverage, annual and census tables with real-source
queries across eight control scenarios. The actual chart CSV/JSON downloads
matched the same-year null masks, units, codes and values. Covered cases
included inverted years, no common rental years, income without rental data,
a suppressed latest income cell, the unchanged proxy intersection, identical
municipalities and an ADRH-only code. Expanded evidence/download controls also
worked at mobile width with no horizontal document overflow. The existing
whole-site browser smoke passed, including the new route. Independent
read-only review found no important findings.

No source was fetched or re-pinned; no mart, sidecar, model or proxy was
rewritten. The active dev service was left running. No commit, push or
deployment was performed for this comparison implementation. Same year and
source remain necessary publication-compatibility checks, not proof of
comparable dwelling/household composition or stable historical boundaries.
