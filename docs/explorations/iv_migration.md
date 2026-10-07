# IV: migration exposure → prices (NEGATIVE RESULT — independent read rejected it)

Merged into `docs/synthesis.md` in `1616d9f`/`82aa409` (user-directed),
then **removed from the synthesis on 2026-10-07** after the milestone-5
independent read returned REMOVE (read record below + [`docs/review_brief.md`](../review_brief.md)).
Per the pre-committed protocol this note is kept as a documented negative
result: the numbers stay pinned in `explorations/iv_results.json` (still
freshness- and transcription-checked by `make audit`), but nothing here is
quotable as a causal finding.

Computed by `explorations/iv_migration.py` (`artifacts/iv_migration.json`,
git-ignored). Provincia panel 2002–2021 (n=1,000, G=50 clusters).
Endogenous: foreign net inflow per 1,000 inhabitants (padrón stock
differences). Instrument: shift-share predicted inflow (1998 origin
levels × leave-one-out national growth). Outcome: valor-tasado Libre
YoY % (no provincial IPV exists). Province + year FE; CR1V SEs.

## Results (repaired 2026-10-07: annual-flow instrument — provisional, new read pending)

| | base | + province trends | drop Madrid/Barcelona |
| --- | --- | --- | --- |
| OLS | +0.002 (0.058) | −0.023 (0.079) | −0.009 (0.061) |
| 2SLS | +0.08 (0.09) | +0.20 (0.11) | +0.08 (0.09) |
| first-stage F | 44.5 | 44.2 | 40.7 |
| AR set | [−0.20, 0.40] | [−0.15, 0.65] | [−0.20, 0.40] |
| n / clusters | 1000 / 50 | 1000 / 50 | 960 / 48 |

| | bust 2002–13 | recovery 2014–21 |
| --- | --- | --- |
| 2SLS | +0.46 (0.20), F 34.4, AR [−0.10, 1.40] | −0.06 (0.03), F 30.9, AR [−0.20, 0.05] |

The repair changes the story, not just the digits: with a flow instrument
the first stage exists in *both* halves (F ≈ 31–45 everywhere — the old
"bust-only instrument" was an artifact of the cumulative construction),
and **no spec has an AR region excluding zero**. The old +0.48 bust headline
is now +0.46 with AR [−0.10, 1.40] (covers zero); the recovery half is an
identified near-null (−0.06, AR [−0.20, 0.05]). The trends spec (+0.20) now
sits close to the base (+0.08) instead of tripling it — the violent
sensitivity the first read flagged was partly the levels/flows artifact.
The exclusion threat (bubble geography) is NOT discharged by this repair
and goes to the new reader. Superseded numbers (cumulative-instrument
vintage: pooled +0.34, bust +0.48/F 58, recovery unidentified, trends
+1.04) are preserved in git history and the read record below — do not
quote them; quote this table only as *provisional pending the new read*.

(Corrected 2026-10-06 after an external-model review caught an incorrect
two-way within transform: year dummies are now province-demeaned alongside
y, exposure, and the instrument. The pooled estimate halved, 0.67 → 0.34;
the trends spec previously ran a singular design — G trends plus year FE
contain the common time trend twice — and solved only on rounding noise.
It now carries G−1 trends, is identified, and diverges from the base
instead of confirming it.)

(Coefficient (clustered SE, sandwich with transposed right bread — corrected 2026-10-06 after independent review caught the missing .T). AR = Anderson-Rubin acceptance region over a grid (F<10 cutoff, uncalibrated — NOT a calibrated 95% set; see review finding).)

Reading below is the REJECTED-vintage reading (cumulative instrument,
2026-10-06 correction) — kept for the record, superseded by the repaired
table above. Original text: 1pp faster
foreign-inflow growth raises appraised prices ~0.3–0.5pp that year among
bust-era instrument compliers — against an OLS association of ~zero, so
the gap reads as full attenuation of a noisy exposure measure, LATE
compliers in tight markets, or residual exclusion failure (unadjudicated).
The estimate is NOT stable across the trends spec (+1.04, AR [0.40,
2.35]): differential trends are a live threat, not a discharged one. The
top-2 drop is close to the base (+0.29, LOO working as designed). First
stage is strong in the bust era (F ≥ 20); the base AR region is bounded
but covers zero ([−0.20, 0.80]), so even the pooled sign is not
AR-robust. The recovery half (2014–21) has no first stage (F = 0.22) and
its AR region is the full search grid — unidentified, reported for
completeness.

## Why 2SLS >> OLS (three readings — REJECTED vintage, kept for the record)

Struck through 2026-10-07: under the repaired instrument pooled 2SLS is
+0.08 vs OLS +0.002 (statistically indistinguishable), so there is no
large multiplier left to explain. Original text follows unmodified:

1. **Measurement attenuation (plausible hypothesis, not established):** exposure = Δstock/pop mixes
   inflows with outflows, deaths, and naturalizations (naturalized
   citizens vanish from the Extranjero count). Classical noise in the
   endogenous regressor attenuates OLS; the instrument, built from 1998
   levels × national waves, is immune to that noise.
2. **LATE:** compliers are settlement-geography markets (big cities,
   coasts, agricultural belts) where housing supply is tightest — bigger
   effects there are economically coherent, not a bias.
3. **Residual exclusion failure (the threat):** 1998 shares correlate with
   persistent demand trends not absorbed by province FE (levels) + year FE
   (national). The trends spec directly attacks this and the estimate
   *rises* — but trends are linear and the truth may not be.

## Limits (binding — read before quoting)

- Appraisal, not transaction prices (mortgage-selection + smoothing).
- 2021 census tipo-split divergence reminds us registers and reality
  differ at the margin; stocks inherit it.
- Single instrument, single endogenous variable: no overidentification
  test exists. Exclusion is argued, not tested.
- 2002–2021 window only (flows + tasado overlap); 2022+ refill wave
  untested, COVID year inside the sample.

## Split-sample (repaired 2026-10-07: both halves identified — provisional)

| | bust 2002–13 | recovery 2014–21 |
| --- | --- | --- |
| OLS | +0.03 (0.11) | +0.02 (0.03) |
| 2SLS | +0.46 (0.20) | −0.06 (0.03) |
| first-stage F | 34.4 | 30.9 |
| AR set | [−0.10, 1.40] (covers zero) | [−0.20, 0.05] (covers zero) |

The old "bust-only instrument" (F = 58 vs 0.22) was an artifact of the
cumulative construction: with a flow instrument both halves are identified
(F ≈ 31–34) and neither AR region excludes zero. The bust point estimate
stays positive (+0.46) but is no longer AR-robust; the recovery half is a
near-null (−0.06). Superseded vintage numbers above are struck through by
this section — see git history and the read record if you need them.

## Read plan

1. Independent reader gets: this note + identification.md + ols.py/bartik.py
   tests + artifacts JSON. Questions for them: exclusion plausibility,
   trends-spec adequacy, LATE vs attenuation adjudication — **now written out
   in `docs/review_brief.md` §Section 2; not yet run.**
2. ~~On approval: fold ONE paragraph + the base-spec table into synthesis~~
   DONE (`1616d9f`) ahead of step 1, with audit claims for tau/AR bounds and
   the split-sample first stages; linked from synthesis, branch merged.
3. On rejection of exclusion: keep the estimate unmerged as a negative
   result and say so in the memo. Remedy is removal from synthesis, not
   softer wording.

## Read record

- Merged without an independent read (process gap, disclosed in the brief).
- Milestone-5 independent read ran 2026-10-07 (agnostic external model,
  read-only, briefed with the corrected +0.34-base numbers — not the stale
  +0.67 values quoted in `docs/review_brief.md` §Section 2). Verdict:
  **REMOVE to a documented negative result.** Exclusion FAIL: 1998
  settlement geography (Mediterranean arc, agro belts, Madrid) coincides
  with the Cajas-credit/construction-bubble footprint, and the trends spec
  triples tau (+0.34 → +1.04) instead of corroborating it. Attenuation
  cannot explain 2SLS ~150× OLS (would need >99.4% noise in Padrón stock
  differences). Mechanism finding: the instrument as built is a *cumulative*
  predicted level since 1998 (`bartik_predict.py`: growth computed 1998→t)
  behind annual-flow language, instrumenting an *annual* inflow rate — the
  first stage rides a non-stationary stock trajectory through the within
  transform, consistent with the violent trends-spec sensitivity. Strongest
  reason it is wrong: the first stage exists only 2002–13 (F = 58 vs 0.22
  after), i.e. exactly the bubble/bust window the instrument's geography
  already marks. Remedy applied same day: causal section removed from
  `docs/synthesis.md` (pointer left), numbers preserved here and in
  `explorations/iv_results.json`.

## Round-2 read (2026-10-07): REJECT AGAIN — inference itself is unsettled

Second independent read (external model, repaired numbers) verdict: REJECT
AGAIN — the repaired results may not be claimed as an "identified null"
either. Three findings, each independently verified or dispositioned:

1. **Stale companion docs (confirmed, fixed same day).** `panel_saiz.md`
   still narrated the rejected-vintage split (+0.32/+0.41, "both reproduce
   +0.34") against JSON holding +0.05/+0.137; the "Why 2SLS >> OLS" section
   here was unmarked; audit labels still said "synthesis". All fixed:
   Saiz note now reads flat-at-zero, vintage sections struck, audit IV
   claims relabeled `iv_note`.
2. **Calibrated AR cuts the other way (confirmed by replication).** The
   repo's F<10 cutoff is a documented placeholder. Re-running the bust AR
   set through the repo's own `ols.ar_ci` with F(1,49) ≈ 4.04 gives
   **[0.10, 0.95] — excludes zero** (reader reported [0.09, 0.95]; the
   0.01 gap is grid resolution). But F(1,G−1) quantiles are themselves
   optimistic with G=50 (`ols.ar_ci` docstring), and the wild-bootstrap
   calibration the code calls for does not exist yet. Status: the bust
   "null" rests on a placeholder cutoff and the "positive" on an
   optimistic one — **neither is established**. If this design is ever
   revived, the prerequisite is wild-bootstrap-calibrated AR, not another
   cutoff argument.
3. **Normalization dispute (recorded, not adjudicated).** The reader calls
   the YoY-rate construction (ΔN/N_{t−1}) a dimensional error and wants
   first-differenced cumulative levels (ΔN/N_1998, Card-flow form). The
   YoY-rate form is the canonical Bartik growth-rate construction; the two
   differ in implicit origin weighting over time (Spain's foreign stock grew
   ~7×, so the choice matters arithmetically). Adjudication would need the
   both-normalizations comparison, which no one has run. Either way it does
   not touch finding (a) from round 1 — bubble-geography exclusion failure
   stands under both normalizations.

Coverage footnote (both vintages): Ceuta y Melilla never enter (no
origin-level 1998 base for 51/52 aggregation in `bartik_predict.py`, no
`51+52` stock key in the estimator) — n=1000 is 50 provinces × 20 years.
Exclusion-untested, appraisal outcome, single instrument: unchanged.
Design stays out of the synthesis in both directions — no causal claim and
no null claim — until calibrated inference plus a new read says otherwise.

## Wild-bootstrap AR calibration (2026-10-07): bust signal is robust, still unidentified

Built `ols.wild_ar_ci` (null-imposed wild cluster bootstrap of the AR Wald;
unit-tested for coverage + determinism) and ran it on the bust spec
(`explorations/wild_ar_bust.py`, 29-pt grid, 299 reps, seed-pinned →
`artifacts/wild_ar_bust.json`, freshness- and transcription-checked by
`make audit`). Three answers side by side for bust tau (+0.46):

- placeholder F<10: AR [−0.10, 1.40] (covers zero);
- F(1,49) ≈ 4.04: AR [0.10, 0.95] (excludes zero);
- **wild bootstrap: AR [0.25, 1.00]** (excludes zero; per-grid critical
  values 3.7–7.9, i.e. between the two shortcuts).

The inference question round 2 left open is now answered: the bust-era
association is AR-robust under bootstrap calibration (caveats: 299 reps of
Monte Carlo noise; coarse 0.25 grid). This does **not** revive the causal
claim — exclusion (bubble geography) is untouched by calibration, and a
robust-but-unidentified association stays out of the synthesis. It does
retire the "identified null" reading of the repair: the repaired bust
result is a robust positive association in search of an instrument, not a
null. Recovery half (−0.06, uncalibrated AR covering zero) was not
recalibrated — nothing there to rescue either way.
