# National housing-cost overburden: marginals and direct age-poverty cells

Added 2026-10-08 to the [housing-access chapter](housing_access.md) and
[`evidence/pages/acceso.md`](../evidence/pages/acceso.md).

## Sources and definition

Eurostat's annual Spain extracts, unit percentage:

- [`ilc_lvho07b`](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07b/default/table): income quintile, including published total.
- [`ilc_lvho07c`](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07c/default/table): tenure status, including published total.
- [`ilc_lvho07a`](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07a/default/table): age, with total sex and total poverty status selected.

The [official definition](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:Housing_cost_overburden_rate)
is the percentage of **persons living in households** whose total housing
costs, net of housing allowances, exceed **40% of disposable income**, also
net of housing allowances. Costs include utilities, maintenance and mortgage
interest, but not mortgage principal repayment. This is not the share of
households and is not comparable to DIBA's ratios of average market costs to
average gross income.

The [EU-SILC metadata](https://ec.europa.eu/eurostat/cache/metadata/en/ilc_sieusilc.htm)
sets the reference period to survey year; income generally concerns the
previous calendar year. We retain `survey_year`, rather than shifting the
whole rate to an income year. Persons in collective households or
institutions are generally outside the target population.

Income quintiles classify equivalent disposable household income. Age is
the age of the person, not the household reference person. Young people
living with parents are included; low measured burden does not demonstrate
access to independent housing. The selected age categories overlap and must
not be added. Tenure rates include existing occupiers, not just new renters
or first-time buyers.

The original panels are separate **national marginal breakdowns**. They cannot identify
local conditions in Madrid, Barcelona or coastal Valencia, nor the burden
of young low-income renters jointly. Survey uncertainty remains: these API
extracts contain quality flags, not sampling confidence intervals. We do not
claim statistical significance of subgroup differences.

## Reproduction and freshness

```bash
uv run python scripts/fetch_housing_overburden.py
# Rebuild derived files without a network request, verifying input pins first:
uv run python scripts/fetch_housing_overburden.py --offline
uv run python scripts/verify_housing_overburden.py
```

The fetch is part of `make fetch`; the exact-derivation verification is part
of `make verify`. Raw JSON-stat responses, the derived raw parquet and the
sidecar database are SHA-pinned in the input manifest, like other inputs.
The dedicated `data/processed/housing_access.duckdb` contains `overburden`;
Evidence's `access` connection reads it separately from the central marts.
No existing estimator reads this database, so adding the source does not
invalidate unrelated estimator artifacts.

Companion tables (2026-10-09, `scripts/fetch_housing_conditions.py`):
`overcrowding` (published overcrowding rate by age, tenure, urbanisation
and income quintile), `underoccupation` (under-occupation share by age,
tenure and urbanisation) and `burden_median` (median of the housing-cost
burden distribution by age and urbanisation) — same Spain annual person
rates/medians, same JSON-stat validation, verified by
`scripts/verify_housing_conditions.py` (also in `make verify`). Break
flags appear in mid-2000s and early-2010s cuts of the new tables and are
retained, not smoothed.

The parser validates dimensions and category indexing, selects Spain,
annual percentage units, total sex and total poverty status for age, and
retains every selected group/year cell. Unpublished cells remain null; true
zero remains zero. Quality flags are retained, including `b` for a break in
series. The current Spain extract flags a break in 2008 in the age/income
series; this does not certify that every other year is free of methodological
change.

The page shows the latest survey year with any published observation, with
no subgroup backfill. The full history remains in the sidecar. National total
rates across the separate tables must agree within published rounding;
verification compares parquet and database cells exactly with the current
parser applied to pinned raw inputs, detecting stale derivations after code
changes. No subgroup rates are averaged into a total.

## Claim register extension

| Claim / question | Query and evidence | Permitted interpretation |
| --- | --- | --- |
| Burden varies by income group | `sobrecarga_ingresos`; `ilc_lvho07b` | Person-weighted national rates by equivalent-income quintile, not a local household burden rate |
| Burden varies by tenure | `sobrecarga_tenencia`; `ilc_lvho07c` | National rates among persons in each tenure group; not prospective financing requirements |
| Burden varies by age | `sobrecarga_edad`; `ilc_lvho07a`, total sex/poverty status | Age of person including co-resident young adults, not successful emancipation or joint age/income/tenure effects |
| Latest observation and quality | `periodo_sobrecarga`, `sobrecarga_acceso` | Survey vintage explicitly displayed; flags and missing subgroup observations retained |

Last source/implementation verification: 2026-10-08. Empirical rates are
queried from pinned data, not restated as hardcoded prose in this note.


## Direct national age-by-poverty cross

The already pinned full `ilc_lvho07a` response also publishes age × poverty
status × sex cells. We now retain a separate `overburden_age_poverty` table and
`housing_overburden_age_poverty.parquet`, selecting total sex and the published
`A_60` / `B_60` categories. The original marginal rows and their definitions
are unchanged; no new API response or inferred intersection is required.

The [official at-risk-of-poverty definition](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:At-risk-of-poverty_rate)
uses a threshold of 60% of national median equivalised disposable income after
social transfers. This is not an income quintile or an absolute poverty measure.
The displayed overburden rate is conditional on each age/poverty group: its
person denominator is that group, not the national population. It does not give
the national population share simultaneously poor and overburdened.

All tenures are included. The partial cross cannot identify young low-income
renters, or replace local age × income × tenure distributions. Co-resident
children/adults are included; age is not household-reference-person age. Income
appears in both the poverty classification and cost/income burden ratio, so a
group difference is not an independent causal contrast or a monetary-cost gap.
The same latest marginal survey year is selected, with no subgroup backfill;
missing cells and quality flags survive. Overlapping age groups are not summed
or averaged. No sampling intervals or significance claims are added.

Offline rebuild and verification above now also reproduce and compare the
joint parquet and database rows exactly. Synthetic contracts verify coordinate
order, dense/sparse forms, sex filtering, separate poverty groups, rate bounds,
missing cells/true zeros/flags and no reconstruction from marginal rates.

Joint-panel checks: `uv run python -m pytest tests/test_housing_burden_joint.py -q`
and `bash scripts/smoke_burden_joint.sh <BASE_URL>`. The browser smoke compares
hydrated direct-cross coordinates, survey years, rates, missingness and flags
with the verified sidecar, alongside the three original marginal panels.
An isolated strict build is used while the existing dev service owns its
template; a running dev instance may need its normal source refresh to discover
the new table export. No central mart or estimator is modified.

## Full joint microdata route: source assessment

The [INE ECV microdata assessment](ecv_joint_burden.md), inspected 2026-10-09,
verifies a public national person–household linkage with age, income, tenure,
costs and weights. It does not add a rate to this sidecar or replace the directly
published age/poverty cells. Exact indicator conventions and same-vintage
benchmark replication remain prerequisites. The inspected public release lacks
the original sampling-design fields needed for design-correct intervals; it
also cannot identify municipal markets.

The separate [own ECV poverty × age × tenure implementation](ecv_joint_scope.md)
now supplements these published panels. Its rates are complete-case descriptive
estimates, not API cells; overlapping own totals have no published rate and
small/low-coverage leaves are null with reasons. Original published Eurostat
parquet and database values are unchanged.
