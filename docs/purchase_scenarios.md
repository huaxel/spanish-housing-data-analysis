# Purchase scenarios: cash access and debt service

Implemented 2026-10-08 in [`evidence/pages/compra.md`](../evidence/pages/compra.md),
linked from the housing-access chapter. This is a hypothetical budgeting
calculator, not a new empirical estimate, lending rule or causal model.
No additional data source or estimator rerun is required. A separate regional
reference table uses existing MIVAU appraisal levels and ECV income averages
for the same economic year. These values neither set controls nor enter
the buyer calculations; a contract test confirms that reference data changes
do not affect scenario output.

## Model contract

All inputs come from bounded numeric sliders: purchase price, share of price
financed, term, nominal annual interest rate, upfront acquisition costs as
a share of price, annual net household income, cash savings available for
the purchase and other monthly debt payments. Defaults are arbitrary
illustrative assumptions, not typical Spanish buyers or bank requirements.

- Loan principal is purchase price multiplied by the financed share.
- The unfinanced part of the price is the deposit.
- Upfront acquisition costs are an assumed share of price and are not financed.
- Required cash is deposit plus upfront costs.
- Cash shortfall and savings remaining are the positive parts of their
  respective differences; neither indicates underwriting approval.
- Monthly income is annual net income divided by the number of months in a year.
- Monthly repayments use the standard fixed-payment annuity formula:
  principal times monthly rate divided by the difference between unity and
  the discounted annuity factor. With no interest, principal is divided by
  the number of payments. With no loan, the mortgage payment is zero.
- Interest over the whole loan is all mortgage payments minus principal,
  without early rounding, early repayment or rate changes.
- The debt-service share includes the mortgage payment and other monthly
  debt payments, divided by monthly net income.

The financed share uses purchase price, not a separately observed appraisal.
Lower appraisals, underwriting criteria, guarantees and special loan products
can change actual financing availability. The cost slider is not a tax
engine: taxes and fees vary with territory, property and buyer eligibility.
No emergency reserve is imposed; users should enter only savings they want
to allocate to the purchase.

## Sensitivity, not a variable-rate reset simulation

The selected nominal rate is compared with increases of one and two
percentage points, holding initial principal and full term fixed. Each row
is a distinct hypothetical fixed-rate loan from origination. It does not
reprice the outstanding balance of an existing variable-rate loan.

The nominal annual rate is divided into monthly rates; it is not an
annual effective rate or APR/TAE. Fees, insurance and linked products are
not embedded in that rate. Repayments are monthly; the model does not capture
other payment schedules or cash-flow timing around extra salary payments.

## Interpretation limits

Cash access and monthly repayment feasibility are separate constraints.
The page does not infer how many households could buy, whether a bank would
approve a mortgage, or whether buying is preferable to renting. No numerical
approval or affordability threshold is assumed.

Remaining income after debt payments still has to cover utilities, building
charges, insurance, maintenance and living costs. It is not disposable savings.
Inflation, changing wages, house prices, tax relief, resale, early repayment
and emergency reserves are not modelled.

The scenario's mortgage payments include principal and interest but omit
other housing expenses. EU-SILC overburden includes utilities and interest
and excludes mortgage principal repayments. These are different metrics;
the calculator must not be used to reconstruct Eurostat burden rates or
compare local buyer scenarios with national population shares.

## Verification

`tests/test_evidence_purchase.py` executes the actual page SQL with synthetic
inputs, without publisher data or Node. Tests compare annuity repayments with
an independently derived discount-factor sum; check cash and interest
identities, zero interest, no borrowing, maximal borrowing, valid boundary
values, monotonic rate sensitivity, other debt and missing/invalid inputs.
Links, source contracts, page metadata and the isolated strict frontend build
are checked separately. `scripts/smoke_purchase.sh` (also `make evidence-smoke-purchase`) validates
that numeric controls recalculate displayed cash and payments rather than
just compiling. Run it against an isolated preview URL to avoid changing
the running dev service. The browser contract catches missing query bundles
and uses scalar Slider inputs; Dropdown-style `.value` is not the Slider
interpolation contract.

No hardcoded narrative result is added: all amounts on the page are derived
from the current scenario, and the complete assumptions are visible in its
controls. The calculator is not automatically published or deployed.

Independent read-only review initially could not run: both reviewer launch
attempts failed because their new terminal panes were not available shells.
Those workers were stopped with transcripts retained. A later same-day
review on the recovered launcher examined the page, this note, arithmetic
tests and browser assertions and found no important issues. That review was
static only; tests and actual browser checks were run by the implementing
agent separately.
