# IV: migration exposure → prices (MERGED — independent read still owed)

Merged into `docs/synthesis.md` in `1616d9f`/`82aa409` (user-directed).
Read plan step 1 — an independent reader on exclusion and LATE vs
attenuation — has **not** run; the questions are carried in
[`docs/review_brief.md`](../review_brief.md) §Section 2, folded into the
milestone-5 read. Until that returns, treat this estimate as provisional
and the split-sample caveat below as binding on any quotation.

Computed by `explorations/iv_migration.py` (`artifacts/iv_migration.json`,
git-ignored). Provincia panel 2002–2021 (n=1,000, G=50 clusters).
Endogenous: foreign net inflow per 1,000 inhabitants (padrón stock
differences). Instrument: shift-share predicted inflow (1998 origin
levels × leave-one-out national growth). Outcome: valor-tasado Libre
YoY % (no provincial IPV exists). Province + year FE; CR1V SEs.

## Results

| | base | + province trends | drop Madrid/Barcelona |
| --- | --- | --- | --- |
| OLS | +0.145 (0.057) | +0.152 (0.061) | +0.129 (0.059) |
| 2SLS | **+0.67 (0.11)** | **+0.76 (0.12)** | **+0.65 (0.12)** |
| first-stage F | 47.7 | 56.3 | 35.5 |
| AR set | [0.35, 1.00] | [0.40, 1.15] | [0.25, 1.05] |
| n / clusters | 1000 / 50 | 1000 / 50 | 960 / 48 |

(Coefficient (clustered SE). AR = Anderson-Rubin 95% set over a grid.)

Reading: 1pp faster foreign-inflow growth raises appraised prices ~0.7pp
that year — 4–5× the OLS association, stable across province trends
(differential-trends exclusion threat: rejected) and top-2 dominance
(LOO working as designed). First stage is strong everywhere (F ≥ 35);
AR sets are bounded, informative, and exclude both zero and OLS.

## Why 2SLS >> OLS (three readings, not one)

1. **Measurement attenuation (most likely):** exposure = Δstock/pop mixes
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
| 2SLS | +0.84 (0.15) | +2.29 (4.84) — uninformative |
| first-stage F | 88.4 | **0.13** |
| AR set | [0.45, 1.40] | full grid (no information) |

The pooled +0.67 is bust-driven: 1998 settlement geography predicts
2002–13 inflows (F = 88) but nothing about 2014–21 flows (F = 0.13).
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
- Milestone-5 read pending; reviewer identity + verdict to be appended to
  `docs/review_brief.md` when it runs.
