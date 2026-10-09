# INE ECV 2025 microdata: feasibility of joint housing-burden analysis

## Decision

A genuine national age × income × tenure analysis is **technically feasible**
from public anonymised ECV transversal microdata, rather than reconstructed
intersections of published marginal rates. The archive, current layouts,
weights and household/person linkage have been inspected. It has not been
pinned as a production input, and no new burden rate is published yet.

The next implementation must first reproduce same-vintage published indicators,
with documented cost, allowance, income, age and missingness conventions.
Availability of variables does not by itself certify an EU-SILC overburden
calculation. Municipal conditions and survey-design confidence intervals are
not supported by the inspected public release.

## Official resources and inspected release

- [INE ECV results and microdata portal](https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736176807&idp=1254735976608&menu=resultados),
  **Ficheros transversales. Base 2013**, year 2025.
- [Official archive `datos_2025.zip`](https://www.ine.es/ftp/microdatos/ecv/ecv_b2013/datos_2025.zip).
  The inspected download is 76,147,963 bytes. It contains nested D/H/R/P archives
  and `disreg_ecv25.zip`, with release-specific Excel and JSON register designs.
- [Eurostat methodological guidelines, 2025 operation](https://ec.europa.eu/eurostat/documents/d/microdata/methodological-guidelines-2025-operation_updated).
- [Generic INE register PDF](https://www.ine.es/metodologia/t25/dise%C3%B1o_registro_ecv.pdf):
  useful background, but the inspected text includes older reference years and
  fields absent in the current release. It is not the schema authority for 2025.

Read only the CSV and metadata members. Bundled RData, SAS, SPSS and Stata
formats/programs were not loaded or executed. The archive is inspection-only
at `/tmp/ine-ecv-2025.zip`; metadata workbooks are also under `/tmp`.

## Verified structural contracts

The comma-delimited `CSV/esudb25d.csv`, `CSV/esudb25h.csv` and
`CSV/esudb25r.csv` contain:

| Component | Verified role | Inspected record count |
| --- | --- | --- |
| D / basic household | Unique household key, region, household weight | 29,369 |
| H / detailed household | Same unique household universe, income, costs, tenure | 29,369 |
| R / basic person | Unique person key, person weight, person ages | 71,398 |

All D/H household keys agree. All R persons link to a household, and linked
person counts exactly agree with H's `HX040` household member counts. The
checked year/country is `2025`/`ES`. The current R layout explicitly defines
`RB030` as the household identifier followed by a two-digit within-household
ordinal; `RB040` is not present. Use the documented encoding, preserving
survey year and country in keys, not an invented missing-field join.

Both `DB090` household weights and `RB050` person weights are finite and
strictly positive for all inspected records, with completed-weight flags.
Person-weighted burden must use R and `RB050`, including children, rather than
restricting to the detailed-adult P file. A separately declared household rate
would instead use D/H and `DB090`; neither denominator can be relabelled as
the other.

## Field semantics established from current layouts

| Field | Meaning / necessary interpretation |
| --- | --- |
| `HY020` | Total disposable household income in the calendar year before the survey; the layout notes inclusion of private pension-scheme receipts |
| `HH070` | Monthly housing costs: actual rent or mortgage **interest**, plus associated costs such as utilities/community charges; not mortgage principal repayments |
| `HY070G`, `HY070N` | Gross/net housing allowances in the preceding income year; both values are present in this release, with different gross/net-mode flags |
| `HH021` | Tenure category: ownership without/with mortgage, market rent, reduced-price rent, rent-free use; validate against the release's `TH021H` codelist |
| `RB081` | Person age at 31 December of the year before survey |
| `RB082` | Person age at interview; not interchangeable with `RB081` |
| `HX040` | Household member count, structurally reconciled to linked R records |

Eurostat's 2025 guidance distinguishes income-reference-period age from
interview age; its main age definition is the former. Do not approximate it
by survey year minus birth year or silently use household-head age. Respect
newborn/top-coding conventions in the actual release.

The release's Excel detailed income flag table uses two digits: the first
identifies source/imputation and the second gross/net collection mode. Thus
`11`, `21`, `51`, `15` or `55` are not a boolean completed/not-completed test.
Statistically imputed income can be valid and must retain its provenance.
Do not apply the generic older register PDF's flag format to this release.
The JSON codelist contains a placeholder for this compound flag; consult the
Excel detail, not just that placeholder.

There are 106 H records with a missing monthly cost and `HH070_F=-1`; the other
cost records have completed flags. Both allowance fields have no blank values
in the inspected release. Never turn a missing cost into zero, discard all
income flags other than `1`, or assume gross allowances are absent merely
because their flags differ from net allowances.

## Geography and uncertainty limits

Current D exposes `DB040` region and `DB100` degree of urbanisation, not a
municipal/provincial market identifier. A regional result for Andalucía,
Cataluña or Comunidad Valenciana is not a Sevilla/Barcelona/coastal result.
Do not infer location from anonymous household or person identifiers.

Although the older generic PDF mentions `DB060`, neither `DB060` primary
sampling unit nor `DB050` stratum appears in the inspected current D CSV or
layout. The public weights permit descriptive weighted point estimates; they
do not by themselves permit replication of the original complex-sample
variance. Person-level independence, household clustering alone, or a Kish
weight-only effective sample size is not a substitute for the missing design.
Do not publish significance claims or purported design-correct intervals
without a validated design/replicate-weight route.

## Benchmark-first implementation gate

Before showing any triple-cross burden rate:

1. Pin the archive, its current register designs and definitions, and the
   same-vintage published benchmark cells/release dates. Differences between
   public-file and published-series revisions must be reported, not tuned away.
2. Validate archive member bounds, CSV schema, key uniqueness, country/year,
   D/H/R cardinality, person/household counts, weights and categorical flags.
   Export only aggregate outputs; no microdata rows or identifiers in Evidence.
3. Establish the official allowance treatment and cost/income conventions.
   Monthly costs need annualisation; household income and allowances use the
   prior income year. Do not double-subtract interest already in `HH070` or
   add principal repayments. Gross versus net fields require a documented rule.
4. Establish official treatment of zero/negative disposable income, net costs,
   missing costs and missing income. Do not silently exclude non-positive
   incomes or create zero burdens through division/empty-value defaults.
5. Replicate the national total and published tenure, age and age/poverty
   conditional rates, plus income-quintile rates if quintiles are used.
   Require agreement at published rounding precision, with all denominator
   losses and any unresolved differences explicit. No benchmark pass is
   claimed in this source assessment.
6. For poverty/quintile classification, validate the equivalence scale and
   national person-weighted median/quantile conventions, including ties. Do not
   calculate thresholds within the renter/young subset or conflate poverty
   status with an income quintile.
7. Predeclare small-cell presentation rules. Show unweighted persons and
   households, weighted person denominator and missing-data losses; those
   counts are not confidence intervals or proof of representativeness.
8. Keep costs, burden and prospective housing access distinct. Existing
   occupiers include co-resident young people and exclude households that never
   formed. The triple cross cannot identify barriers to emancipation by itself.

## Benchmark prototype: rounded replication, not publication

`scripts/assess_ecv_benchmarks.py` now provides an aggregate-only prototype.
It reads the inspection archive and the verified existing macro sidecar,
validates D/H/R linkage and release schemas, and emits diagnostic marginal
comparisons without person/household identifiers or a triple-cross table.
The H CSV appends a recognised module-column suffix beyond its base JSON
layout; the prototype accepts that explicit extension, not arbitrary extra
columns. It uses the release-specific compound income flags, retaining valid
imputation rather than requiring a boolean income flag.

The [official historical Eurostat indicator algorithm, LC-ILC 39-09 rev.1](https://www.dst.dk/ext/747139308/0/),
housing-cost-overburden section, establishes gross allowance subtraction from
both annualised costs and disposable income. Ordered edge rules put
non-positive net housing costs at zero burden, and positive costs with
non-positive net income at full burden. The prototype tests the strict
threshold boundary and does not drop those non-positive-income persons.
The [Eurostat income/living-conditions working paper](https://ec.europa.eu/eurostat/documents/1012329/1012395/D5.1.3-Working_paper_final_20141204.pdf/c4ed99f5-7cc3-4bf9-a6eb-b1f730299e0e)
provides the modified-OECD scale and weighted-quantile crossing/midpoint rules.
These historical specifications are not silently represented as complete
current-release certification, especially for missing-value weight corrections.

The current release contains newborns with reference age `-1`; the official
age convention maps this to zero, retaining them in population and equivalence
calculations. Other negative ages fail validation. Income classification uses
person-weighted equivalised disposable income before subtracting housing
allowances, not a threshold recalculated within an age/tenure subgroup.

The first prototype matched **25 of 26** selected current-vintage published
cells: the lowest-income quintile narrowly missed. A diagnostic change on
2026-10-09 ranked cost-eligible rather than all income-valid persons for housing
quintiles, without widening the tolerance. **LC-ILC 39-09 rev.1, pages 75–78**
excludes missing housing inputs from the indicator and specifies corrected
weights for QPB. However, its QPB note explicitly excludes missing equivalised
income and does **not unambiguously specify** whether missing housing costs
also determine the ranking population. Independent read-only review caught the
earlier note's overconfident interpretation. This is a benchmark-matching
candidate convention, not a confirmed official-method correction.

Housing quintile cutoffs now use the indicator-eligible population after
housing-cost exclusions. The national poverty threshold still uses the full
income-valid population, as separately specified by the manual. No renter,
young-person or regional subset determines either reference distribution.
All other required inputs are complete or cause a validation failure in this
release-specific prototype; sex completeness is now explicitly checked too.
The national poverty reference is supported separately by the manual; the
housing-quintile reference remains unresolved and must not be used as an
official-methodology claim or production quintile classification.

Under this candidate convention, **all 26 of 26** selected published cells match at their
original rounding precision, with the original tolerance unchanged. The
report records both reference-population counts and descriptions. A synthetic
regression fixture with a high-weight cost-missing person verifies the chosen
candidate's separation of reference populations, not which QPB convention
Eurostat intended. The diagnostic itself exports no joint rates. The separately implemented
[poverty-only age × tenure cross](ecv_joint_scope.md) exports own descriptive
rates only for disjoint groups passing its project gates; income quintiles
remain excluded. It is not a directly published Eurostat cross.

This is rounded benchmark replication, not proof of identical underlying
microdata calculations. The manual allows missing-value weight correction
within strata where applicable, but the inspected public release lacks those
stratum/design fields. The prototype does not invent such weights or claim
that complete-case person weights reproduce an undisclosed correction.
Current-release methodology and revision differences therefore remain visible
limitations, even though the selected numeric replication gate now passes.

Reproduce the diagnostic, after confirming the existing macro input pins:

```bash
uv run python scripts/verify_housing_overburden.py
uv run python scripts/assess_ecv_benchmarks.py \
  --archive /tmp/ine-ecv-2025.zip \
  --benchmarks data/processed/housing_access.duckdb \
  > /tmp/ecv-benchmark-report.json
# Current expected exit: 0, all selected numeric benchmarks match.
# This is not a publication-ready or design-inference certification.
uv run python -m pytest tests/test_ecv_benchmarks.py -q
```

The JSON includes input/prototype hashes, counts, missing-cost losses, source
flags, published quality statuses and explicit comparison outcomes. It keeps
`publication_ready=false`, despite the numeric comparisons passing.
The diagnostic JSON stays outside production artifacts; the archive is not
an input-manifest addition. Offline synthetic tests cover edge rules, newborns,
weights, compound flags/imputation, linkage failures, CSV/module contracts,
quantile cutpoints, distinct reference populations, duplicate archive members,
sex completeness and failed/missing benchmarks. The CLI tests establish both
successful and failed numeric exits without setting publication readiness.
Project lint, offline tests, data verification and audits pass. There is no
UI/build change. Independent native Codex read-only review found the QPB
population ambiguous: numerical agreement and synthetic tests cannot settle
its intended methodology. The definitive claim has been removed; production
quintile analysis stays blocked.

The reviewer considers national age × poverty × tenure descriptive analysis
viable, with the national income-valid poverty reference and cost-valid person
rates. The [predeclared implementation contract](ecv_joint_scope.md) keeps
source pinning, coverage/suppression and uncertainty gates separate from this
benchmark tool. Existing sidecars, central marts, model outputs and explorer
values remain unchanged.
