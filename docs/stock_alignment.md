# Same-reference-year stock, households and rent: Sevilla source assessment

## Conclusion

A separate municipal profile for the 2021 reference year is feasible using
primary official sources. It is not a historical reconstruction of the
current cadastral BU layer, not a barrio crosswalk and not an identified supply
effect. Same reference year does not mean every quantity has the same temporal
support: census stock/households are point-in-time counts, annual rent is a
flow-period summary, and electricity use refers to the preceding year.

A separate municipal profile is now implemented at `/stock-2021/`; no new
association or causal estimator is added. The official household CSV and
catalogue are pinned inputs. The original barrio pilot and central models
remain separate. This note records source suitability and remaining limits.

## Verified sources

| Quantity | Primary source and key | Geography / timing | Current repository status |
| --- | --- | --- | --- |
| Census household count | [INE table 59543: Hogares por municipios y tamaño del hogar](https://www.ine.es/jaxi/Tabla.htm?tpx=59543&L=0); select `Total (tamaño del hogar)` | Official municipal code; 1 January 2021; units are households | Pinned CSV/catalogue, validated and integrated in the separate municipal sidecar |
| Census housing total and use context | [INE table 59531](https://www.ine.es/jaxi/Tabla.htm?tpx=59531&L=0); `Viviendas totales` and separately named consumption measures | Census stock reference 1 January 2021; electricity classification based on 2020 consumption | Already retained as `censo2021_intensidad`, raw CSV/parquet and main mart table |
| Annual municipal rent | Retained `serpavi_municipal`, `ALQM2_LV_M_VC`, year 2021 | Municipal code; tax-year rent median in EUR/m²/month for the publisher's collective-housing typology | Already retained; use source codes, not display-label guesses |

The household export is:

<https://www.ine.es/jaxi/files/tpx/csv_bd/59543.csv>

Its inspected tab-separated header is `Total Nacional`, `Municipios`,
`Tamaño del hogar`, `Total`. Municipality labels carry official codes. The
[INE municipal household catalogue](https://www.ine.es/dynt3/inebase/index.htm?capsel=9813&padre=8952)
identifies this as Censo de Población y Viviendas 2021, not the annual population
series or a sample survey of selected large cities.

The [INE household/housing release](https://www.ine.es/prensa/censo_2021_jun.pdf)
confirms the census reference date and explains the electricity period and
construction-based stock definitions. Use the currently pinned table values
for figures: electricity-classification amounts in the original release were
provisional and can differ from subsequently revised downloads.

### Code-based alignment and observed source coverage

Inspection found 106 household-total codes in Sevilla province, each unique;
the retained housing table has 101 individually named municipalities plus a
`Resto de Sevilla` aggregate. The retained annual rent measure has 50
nonmissing municipal codes for the selected year, with no duplicate selected
keys. All those rent codes have named housing and household totals, yielding
50 candidate complete municipal profiles. These are source-availability
checks, not a claim that all municipalities or rental-market types are observed.
Final integration must recompute coverage after value/type/label validation.

For the capital, the official code is `41091`; the main municipal display
label is `Sevilla (ciudad)`, while the raw SERPAVI municipal label is `Sevilla`.
Do not accidentally select a province total also called Sevilla, or interpret
an unsuccessful literal-name query as absent data. Filter by code, province,
year and exact measure, and require a single observation.

The `Resto` row must remain an aggregate. Do not allocate it to missing
municipalities using area, population, household weights or current cadastral
footprints. Missing rent remains missing, not zero. Do not add a measure's
total and its component categories: the household total and size classes,
and electricity-use totals/sub-bands, are overlapping representations.

## What this does not solve

- **No verified historical barrio BU snapshot.** The current municipal INSPIRE
  layer is a contemporary snapshot. Filtering it by construction year would
  still retain current survival, conversions and property splits; it cannot
  reconstruct past declared stock or household availability.
- **No newer barrio IPRA demonstrated.** Direct metadata inspection of the
  retained official `X/FeatureServer/179` still exposes `IPRA_16` through
  `IPRA_22`. The official household layer exposes `HOG_15` through `HOG_21`.
  These checks establish the inspected services' limits, not global proof
  that no other publisher has newer data. The
  [official IPRA update](https://www.emvisesa.org/aprobacion-definitiva-de-la-actualizacion-del-ipra/)
  distinguishes deposit-based paid rent from asking rent; do not replace one
  with the other or treat publication year as a contract-year observation.
- **No effective-availability count.** The electricity measure includes absent
  contracts and very low consumption under the census rule. It does not
  establish habitability, legal access, willingness to offer, asking rent or
  market availability. Consumption in the pandemic year is also distinct
  from current occupation.
- **No census/cadastral unit equivalence.** Census stock can include dwellings
  originally built as such but currently used as offices or other premises.
  Current declared housing-property counts are a different concept. Do not
  subtract the census total from BU counts to infer net building/demolition.
- **No interchangeable household proxy.** Use actual household totals rather
  than relabelling principal homes, population or tax-income families as
  household counts. Census household counts and housing categories are
  separately published variables.
- **No rental-typology equivalence.** The selected SERPAVI collective-housing
  typology is not every rented dwelling. It is not the census concept of
  collective establishments. Stock/household totals have broader coverage.

## Other sources assessed

[IECA's census portal](https://www.juntadeandalucia.es/institutodeestadisticaycartografia/dega/censos-de-poblacion-y-viviendas)
confirms municipal household/housing dissemination. Its BADEA housing and
household pages require JavaScript. The open-data resource labelled CSV points
back to that landing page, not directly to a downloadable data file; the
verified INE CSV avoids assuming the catalogue format is a file endpoint.

[Catastro's statistics guide](https://www.catastro.hacienda.gob.es/es-ES/estadisticas.html)
provides a separate historical-count route: municipal annual urban statistics
refer to the end of the prior year, while census-district annual urban
statistics use a September snapshot. These are cadastral property counts,
not a validated historical barrio geometry/archive. A search hit for
[legacy file layouts](https://www.catastro.hacienda.gob.es/es-ES/estadisticas_5_estructura.html)
describes older formats and is not a validated layout for a modern annual
extract. No current annual extract was integrated in this assessment.

## Bounded next implementation

1. Pin the official household CSV and its catalogue/definition. Validate
   headers, unit/reference year, municipal-code uniqueness, missing values
   and nonnegative integers; retain size categories separately or select the
   published total without summing both representations.
2. Build a separate municipal sidecar using pinned household, housing and
   annual rent inputs. Leave the central marts/estimators and barrio pilot
   unchanged. Verify input/code freshness and exact derived rows.
3. Preserve the household-code universe and explicit stock/rent missingness.
   Mark province/`Resto` aggregates as nonmunicipal; publish inclusion/loss
   counts and exact keys/labels rather than selecting ambiguous rows.
4. Present reference date, annual tax period, electricity period and rental
   typology beside each metric. A stock/household ratio, if exposed, is a
   nominal census ratio including nonprincipal/other-use stock—not usable
   homes per household, unmet demand or housing-market availability.
5. Begin with a descriptive municipal profile, not another regression or a
   growth/causal supply test. Synthetic parsing/join tests, production
   freshness checks, browser validation and independent review precede
   promotion of any new result.


## Implemented reproduction

```sh
uv run python scripts/build_sevilla_2021.py           # fetch/pin household source + build
uv run python scripts/build_sevilla_2021.py --offline # rebuild pinned inputs only
uv run python scripts/build_sevilla_2021.py --check   # exact rows/aggregates + source/code freshness
make verify
uv run python -m pytest tests/test_sevilla_2021.py -q
```

The separate `data/processed/sevilla_2021.duckdb` retains the household-code
universe, null stock/rent joins, per-source status and excluded aggregate rows.
Validation rejects incompatible units/year/schema, malformed or duplicated
household cells, inconsistent source codes, invalid numeric counts and vacancy
counts exceeding stock. Duplicate or mismatched selected stock/rent keys yield
null source quantities with explicit flags. Benign municipal-name differences
use the existing normalizer only to check labels; official codes do the join.
Metadata hashes every input actually read, code, normalization helper and
DuckDB version. Verification recomputes and compares every profile and excluded
aggregate, rather than trusting a row count or stored metadata alone.


The page is `evidence/pages/stock-2021.md`; it reads the separate `alignment`
Evidence source. `bash scripts/smoke_sevilla_2021.sh <BASE_URL>` checks hydrated
coverage, capital identity/values, profile cells, missingness, excluded aggregates
and temporal/interpretation caveats against the verified sidecar. An already
running dev service may need its normal source refresh/restart to discover the
new connection; validation uses an isolated strict build rather than modifying
the service-owned template or stopping the existing service.


## Rental-household denominator follow-up

[The official tenure-source assessment](sevilla_rental_denominator.md) checks
ECEPOV household table 56582 and census dwelling table 59529. The inspected
municipal publications cover four Sevilla cities, not the full household
universe. Survey interview-date estimates and conventional-primary-dwelling
counts are not replacements for census household totals. Census tenure also
uses ECEPOV frequencies for imputation, so the two are not independent checks.
No rental-household coverage ratio is added from these restricted sources.

## Household geography of rent-data coverage

The page also groups the full household municipality universe by validated rent
presence. Municipality shares and household-location shares have separate
units: households include all tenures, not just renters. Published household
sums are accompanied by the number of observed counts. A household share is
suppressed whenever any municipality lacks its count, or the total is zero;
partial published sums are not a complete provincial denominator. Empty groups
have known zero membership, distinct from unknown household counts.
This describes where households live relative to the geography of published
VC medians. It is not contract/tenant coverage, representativeness of rented
homes or a household-weighted provincial rental price. The source and estimator
remain unchanged; no missing rents or Resto housing are allocated.


## Rental-flow follow-up

[The AVRA deposit-register feasibility note](sevilla_rental_flows.md) separates
new agreements from administrative events and occupied/available stock. No
reusable municipal residential-flow export was verified. Public deposit
obligations for new contracts end at the January 2026 legal seam, while older
contract receipts/refunds can continue; this is not a measured supply collapse.
An aggregate request is drafted but has not been submitted or ingested.

## Restricted dwelling-tenure context

The separate sidecar now also reads pinned INE census table 59529 CSV/catalogue
and exposes `tenencia_contexto`: published conventional-primary-dwelling totals
and ownership/rental/other tenure counts for its four Sevilla municipalities.
The exact-code scope, unit/year/schema, numeric grouping, category uniqueness,
label compatibility and complete-count conservation are validated before new
source pins are recorded. The builder's exact-table check covers these rows.
The original household/rent profile and its denominator are unchanged.

`celdas_completas` is publication completeness, not absence of imputation.
Administrative/tax/title evidence and ECEPOV-frequency imputation underlie the
census tenure classification; the panel explicitly disclaims independent
replication, rented-household equivalence, province-wide sample coverage and
currently available supply. ECEPOV household survey table 56582 is not ingested.
