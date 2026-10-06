# Hypothesis 01: does construction-per-new-person predict price growth?

Tested by `explorations/test_absorption_hypothesis.py`
(raw output: `artifacts/hypothesis_01.json`). For each territory × window:
X = new dwellings per additional inhabitant, Y = % price change
(IPV general at CCAA grain; valor-tasado €/m² at provincia grain).
Windows with shrinking population are excluded from the ratio (undefined)
and counted. Pearson + Spearman per window and pooled.

## Result: moderate support at CCAA grain, not a huge predictor

| Window | CCAA (IPV) | Provincia (€/m²) |
| --- | --- | --- |
| 2007–2011 | +0.51 (17/17) [0.04, 0.80] | +0.36 (47/51) [0.08, 0.58] |
| 2011–2015 | — (<3 growing) | −0.26 (6/51) [−0.88, 0.70] |
| 2015–2019 | −0.54 (10/17) [−0.87, 0.14] | −0.46 (22/51) [−0.74, −0.05] |
| 2019–2021 | −0.13 (13/17) [−0.63, 0.46] | −0.22 (34/51) [−0.52, 0.13] |
| 2021–2025 | −0.12 (16/17) [−0.58, 0.40] | — (pop ends 2021) |
| **Pooled rank** | **−0.41 (n=57) [−0.60, −0.16]** | **−0.06 (n=109) [−0.25, 0.13]** |

(Spearman with naive Fisher-z 95% CIs; Pearson similar. Positive = more
building per person went with *bigger price rises* in that window.
With n=17 CCAA the window CIs are wide by construction — only the pooled
CCAA band clears zero, and it pools repeat observations of the same 17
territories across windows with no clustering, so treat it as a floor on
uncertainty, not a standard error.)

## Reading

- The hypothesis points the right way about half the time. The pooled CCAA
  −0.41 is real but modest, and it vanishes at provincial grain (−0.06)
  and in the most recent window (−0.12): 2021–25 absorption ran 0.10–0.65
  dwellings per new person almost everywhere while IPV rose 28–43%
  almost everywhere — everyone was tight, so tightness doesn't discriminate.
- The 2007–2011 *positive* sign is instructive, not supportive: high ratios
  there mean tiny population growth under big construction (Galicia 4.1,
  Asturias 4.4), and those markets fell least (−5 to −9%), while Madrid and
  Cataluña (ratio 0.3–0.4, population still growing into the crash) fell
  most (−22 to −27%). The denominator is demand itself.
- 2011–2015 is the dog that didn't bark: only 1–2 CCAA grew at all, so the
  ratio test is undefined for the whole depopulation window — a reminder the
  metric only exists when people arrive. Stronger: this test *cannot observe
  the bust*, the one regime where overhang-lowers-prices is most testable.
  Excluding shrinking-population windows conditions the sample on demand
  itself, so the design selects away its best shot at the theory.

## Verdict

"Dwellings built per extra person" is a **useful descriptor of regimes**
(bust overhang vs post-2021 shortfall) but **not a huge predictor of price
increases**: pooled rank −0.4 at best, ≈0 at provincial grain, and mute in
exactly the window you'd trade on. The confounder is structural — population
change (the denominator) is demand, credit, and jobs, not just mouths to
house. Price moves need those covariates before any predictive claim.
Next: household age-structure (already in raw ECP JSON) and incomes.
