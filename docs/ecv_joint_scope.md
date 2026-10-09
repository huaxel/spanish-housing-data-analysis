# Reviewed ECV joint-analysis implementation contract

Status: predeclared 2026-10-09, before calculating or inspecting joint outcomes.
Native Codex independently reviewed the benchmark method and proposed contract
read-only. The bounded implementation and UI integration are now present, with offline,
strict-build and browser checks. Initial implementation review corrections
withhold overlapping own rates and retain aggregate full flag provenance;
follow-up review confirmed the fixes and identified residual shared-household
inference, now explicitly retained as a limitation of presentation gates. This is not public-deployment approval.

## First phase: national age × poverty × tenure, not quintiles

Use the public anonymised transversal ECV 2025 D/H/R release described in
[the source and benchmark assessment](ecv_joint_burden.md). Output own descriptive
person-weighted estimates, clearly distinguished from directly published
Eurostat rates. No municipality, province, regional extrapolation, prospective
housing-access outcome, causal effect or statistical-significance claim.

The first phase deliberately excludes income quintiles. Independent review
found that the available historical QPB specification does not unambiguously
settle the ranking population; the benchmark-matching cost-eligible convention
remains a diagnostic candidate, not a confirmed official algorithm.

Define a complete coordinate grid:

- Age: total, under 18, 18–24, 25–29, 30–64, and 65 or over. Non-total cohorts
  are mutually exclusive; age is `RB081` at income-year end, with newborn `-1`
  mapped to zero. It is not household-head or interview age.
- Poverty: total, below the national relative-poverty threshold, at or above it.
  Threshold is the national person-weighted median equivalised disposable
  household income after transfers multiplied by **0.60**, matching the
  [official relative-poverty definition](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:At-risk-of-poverty_rate).
  Use the full income-valid reference population, not an age, tenure or
  cost-valid subset. Poverty status is not a quintile or absolute deprivation.
- Tenure: total, ownership with mortgage, ownership without mortgage, market
  rent, reduced-price/rent-free use. Map from the release's `HH021` categories.

The grid contains 90 aggregate cells. Total categories overlap their components;
never sum totals plus components. Persons have a person age but shared household
income, costs, poverty and tenure. Young co-residents are not necessarily paying
rent themselves or seeking independent housing.

## Eligibility, weights and coverage

Reuse one validated normalisation/poverty implementation for benchmark and joint
calculations rather than independently duplicating the financial definitions.
Validate the year/country, official CSV/layout contracts, keys and household
member counts, weights, ages, sex, tenure, gross/net and source/imputation flags.
Unknown conventions or incomplete classification inputs stop the build; do not
silently change this release-specific target population.

For each target coordinate, count all classified persons before cost exclusion,
then persons and distinct represented households with valid costs. Calculate
burden using the ordered official financial edge rules already tested in the
prototype. Missing costs never become zero. Use `RB050` person weights, not
household weights; household counts are sample/coverage descriptors, not the
rate denominator. Income/allowances retain their prior-income-year reference;
monthly interview-year costs are annualised, not an observed annual cash ledger.

Weighted missing-cost loss is excluded person weight divided by total classified
person weight in that coordinate. Display both eligible and target denominators,
unweighted valid persons and distinct represented households, coverage/loss and
quality/suppression reasons. Flags describing imputation/source must survive;
other flag categories do not certify wholly observed household income components.

## Predeclared presentation gates

Suppress a point rate if **any** of these project conditions holds:

- fewer than 50 valid sample persons;
- fewer than 30 distinct represented households with valid costs;
- weighted-person missing-cost loss greater than 5% in the target cell.

No target persons: `empty`, rate null. Target persons but no valid costs:
`no_valid_cost`, rate null. A suppressed rate is null with all applicable reasons,
not a true zero. A genuine zero is permitted only when eligibility and every
presentation gate pass. Show coverage even when the rate is hidden.

These are conservative **project presentation rules**, not Eurostat reliability
thresholds, design-correct confidence statements or confidentiality guarantees.
Do not export burden-weight numerators, individual economic rows or anonymous
identifiers into Evidence; do not offer UI reconstruction of suppressed rates.
Own overlapping marginal rates are withheld, regardless of sample size; only
mutually exclusive non-total age × poverty × tenure leaves can carry a rate.
All coordinates retain coverage and reasons. This additional conservative rule
was adopted after implementation review detected reversible primary suppression;
it does not relax the predeclared sample/coverage gates. Public external marginals
and the underlying open release still prevent a confidentiality guarantee.
Even own disjoint-age aggregates can imply a hidden outcome through shared
households, particularly an all-zero or all-burdened outcome with shared full
household coverage. Withholding marginal rates removes direct overlapping-total
subtraction equations, not every possible logical inference from own output.
The UI does not automate reconstruction; these are direct-presentation gates,
not a claim that suppressed outcomes are mathematically uninferable.
The proof retains full validated source/mode flag counts by sample unit; these
are aggregate provenance, not household income-component completeness claims. No Kish-weight-only interval, independent
person interval or household-cluster-only interval substitutes for missing
original survey design information.

## Provenance and integration gates

1. Pin the official release bytes and current register definitions before a
   production build. Retain attribution and methodology/revision dates. Read only
   necessary columns internally; execute no bundled statistical programs.
2. Keep a separate sidecar/export. Preserve original Eurostat marginal and direct
   age/poverty tables, explorer values, central marts and estimator inputs.
3. Verify selected age, tenure and age/poverty benchmark cells at original
   publisher rounding, without making ambiguous quintile assumptions a condition
   for poverty-only implementation. Agreement does not certify unpublished joint
   cells or undisclosed missing-value recalibration.
4. Keep primary method limitations explicit: complete-case person weighting is
   descriptive; unavailable stratum corrections/PSUs cannot be recreated. No
   design-correct intervals or significance claims.
5. Test financial boundaries, linking, national poverty reference, coordinate
   conservation, missing/zero/empty states, imputation, suppression boundaries
   and multiple reasons. Verify exact aggregate derivation and source pins;
   changing an input or an exported cell must fail checks.
6. Query all page coordinates against the sidecar, run offline project gates,
   isolated strict build and hydrated browser checks. Confirm original panels
   remain unchanged and no suppressed rate leaks through charts/tooltips/exports.
7. Obtain independent read-only implementation review and fix important findings
   before reporting completion. Current review approves the bounded scope, not
   future code or empirical conclusions. No commit, push or deployment is implied.

## Final implementation verification — 2026-10-09

Offline lint/test/verify/audit, exact sidecar/proof checks, isolated strict
Evidence build and all route metadata checks passed. Hydrated browser checks
covered every coordinate's selections, displayed rate/null/status, sample and
weighted coverage, imputation counts and caveats; original Eurostat panels passed
unchanged. Independent native Codex follow-up confirmed flag provenance and the
narrowed presentation-only claims, with no further defect reported. The reviewer
did not independently rerun the gates. No central-mart rebuild, estimator rerun,
commit, push or deployment occurred; the original dev service was preserved.

Live dev verification — 2026-10-09: refreshed generated Evidence source exports
with `npm run sources`, without restarting the existing service. Both the full
ECV selector regression and original Eurostat-panel regression passed against
`http://127.0.0.1:3000`. Central marts, published-burden sidecar and own ECV
sidecar byte hashes remained unchanged; no statistical data rebuild occurred.
