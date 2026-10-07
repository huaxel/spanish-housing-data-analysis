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

## Results

| | base | + province trends | drop Madrid/Barcelona |
| --- | --- | --- | --- |
| OLS | +0.002 (0.058) | −0.023 (0.079) | −0.009 (0.061) |
| 2SLS | **+0.34 (0.13)** | **+1.04 (0.27)** | **+0.29 (0.13)** |
| first-stage F | 27.3 | 52.8 | 20.3 |
| AR set | [−0.20, 0.80] | [0.40, 2.35] | [−0.45, 0.75] |
| n / clusters | 1000 / 50 | 1000 / 50 | 960 / 48 |

(Corrected 2026-10-06 after an external-model review caught an incorrect
two-way within transform: year dummies are now province-demeaned alongside
y, exposure, and the instrument. The pooled estimate halved, 0.67 → 0.34;
the trends spec previously ran a singular design — G trends plus year FE
contain the common time trend twice — and solved only on rounding noise.
It now carries G−1 trends, is identified, and diverges from the base
instead of confirming it.)

(Coefficient (clustered SE, sandwich with transposed right bread — corrected 2026-10-06 after independent review caught the missing .T). AR = Anderson-Rubin acceptance region over a grid (F<10 cutoff, uncalibrated — NOT a calibrated 95% set; see review finding).)

Reading (corrected 2026-10-06 after independent review): 1pp faster
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

## Why 2SLS >> OLS (three readings, not one)

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

## Split-sample: the instrument is a bust-era instrument (branch)

| | bust 2002–13 | recovery 2014–21 |
| --- | --- | --- |
| OLS | +0.03 (0.11) | +0.02 (0.03) |
| 2SLS | +0.48 (0.15) | +3.25 (6.28) — uninformative |
| first-stage F | 57.7 | **0.22** |
| AR set | [0.05, 1.05] | full grid (no information) |

The pooled +0.34 is bust-driven: 1998 settlement geography predicts
2002–13 inflows (F = 58) but nothing about 2014–21 flows (F = 0.22).
Post-crisis migration decoupled from historical networks — new origins
(Venezuela, Honduras), dispersal, ECP-era patterns. Consequence: the
recovery half of the story (S3's inflow surge) remains descriptive;
only the bust-half effect is identified. If merged, the synthesis
paragraph needs this qualifier, not just the pooled number.

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
