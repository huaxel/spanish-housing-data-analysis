# Does land constraint shape the migration → price gradient?

Verdict: **a null with precision.** The terrain series from
`saiz_gis_probe.md` does not deliver a clean confirmation of Saiz's
supply-elasticity mechanism on this panel. Three diagnostics, in
increasing order of how much they can bear:

| # | question | result |
| --- | --- | --- |
| 1 | Premise: do constrained provinces build less? | −0.05 (0.17) per 0.1 constraint — **null** |
| 2 | Exclusion threat: does terrain predict prices directly? | −0.05 (0.08) per 0.1 — **null** |
| 3 | Mechanism: is τ larger where land is scarce? | high 0.74 (0.15) vs low 0.64 (0.18) — right direction, **not distinguishable** |

Code: `explorations/panel_saiz.py`; numbers pinned in
`explorations/panel_saiz_results.json` and audited by `make audit`.
Exploratory. Nothing here merges into synthesis.

## 1. The premise is untested, not refuted

If terrain constrains construction, provinces with a high
undevelopable-land share should add less stock per capita. Estimated
cross-sectionally (constraint + year FE, SEs clustered by provincia, the
constraint being time-invariant and so absorbed by province FE):

**−0.054 dwellings per 1,000 inhabitants per 0.1 constraint (SE 0.165).**
Mean building is 7.57 per 1,000 per year (SD 5.77), so the point estimate
is ~1% of the mean and indistinguishable from zero.

The honest reading is *untested*, not refuted. Constrained provinces are
precisely the coastal/urban high-demand ones (Málaga 0.66, Barcelona 0.64,
Gipuzkoa 0.93), so demand and terrain push stock in opposite directions and
a raw cross-section cannot separate them. This diagnostic shows only that
naive Saiz-style cross-sectional validation does not work on Spanish
provincia data.

## 2. No visible direct terrain → price channel

A valid instrument for design B must affect prices *only* through supply.
Testing the crudest version — does constraint predict price changes
directly, with year FE? — gives **−0.052 per 0.1 constraint (SE 0.075)**,
i.e. nothing.

This is mildly reassuring but weak evidence, and it should not be
over-read. It rules out a *large unconditional* terrain→price association.
It cannot separate "terrain affects prices through supply" (the channel of
interest) from "amenity and terrain happen to be uncorrelated at provincia
grain", where the municipality-level amenity effect is averaged away.

## 3. The mechanism is directionally right and statistically invisible

Splitting the design-A IV at the median constraint (0.445):

| | low constraint | high constraint |
| --- | --- | --- |
| 2SLS τ | +0.64 (0.18) | +0.74 (0.15) |
| first-stage F | 40.3 | 22.8 |
| AR 95% set | [0.25, 1.30] | [0.10, 1.30] |
| clusters | 26 | 24 |
| OLS τ | +0.07 (0.10) | +0.25 (0.04) |

Both subsamples reproduce the headline (+0.67): the causal estimate is
**not** an artifact of pooling provinces with very different terrain. The
high-constraint point estimate is larger, which is the direction Saiz
predicts, but the AR sets overlap almost exactly and the descriptive
interaction is +0.29 (0.26) with wild-cluster p = 0.33.

Conclusion: migration raises prices by a similar amount in land-scarce and
land-abundant provinces. That is a real (if modest) result — it says the
migration→price channel is not primarily a supply-scarcity amplifier in
this panel. Note the contrast with the OLS column: attenuation is much
larger in low-constraint provinces (+0.07) than high (+0.25), so whatever
2SLS is correcting for differs across terrain groups.

## A bug worth recording

The first run reported +0.497 (SE 0.093, t = 5.3) for diagnostics 1 and 2 —
a strong *positive* terrain→price association, the opposite of the raw
means. It was wrong, and the raw means are what exposed it. Cause: the
cross-sectional helper dropped the first year dummy **and** had no
intercept, leaving the earliest year with no constant term, so those rows
were fitted through the origin and dominated the slope.

After adding the intercept the coefficient is −0.05 with t = −0.7. The
lesson generalises and is worth keeping: the province-demeaned specs in
`iv_migration.py` legitimately drop one year dummy because demeaning
supplies an implicit intercept; copying that pattern into a
non-demeaned cross-sectional spec silently changes the model. The explicit
constant is now in the code with a comment saying why.

## What this does and does not license

- Does **not** license building design B as an instrument on the strength
  of these results. The premise is untested and the mechanism is a null.
- Does **not** contradict Saiz. Nothing here measures a supply elasticity;
  it tests whether terrain moderates the migration→price response at
  provincia grain, and that is a much coarser object than a metro-level
  elasticity.
- **Does** strengthen the design-A headline: τ survives splitting the
  sample by a variable the design never used, which is a genuine (if
  weaker than a true overidentification test) robustness check.
- **Does** add a second reason — alongside the amenity confound in
  `docs/review_brief.md` — to treat design B as lower priority than the
  identification memo's re-ranking implies.

## Next step if this thread continues

The honest upgrade is municipal, not provincial. Saiz's own object is
metro-level, and the amenity/terrain confound lives at the coast where
municipal rents and sale prices already exist in this repo (DIBA + VTE,
used by `panel_tourist.py`). A provincia is an average of mountains and
valleys, and averaging may be exactly what erases the mechanism.
