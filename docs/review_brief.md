# Independent review brief (milestone 5)

Status: **CLOSED — the read ran 2026-10-06 and was adjudicated in-repo; two
round-2 addenda follow.** (This status line alone is amended 2026-10-07 per
repo review: it had stale-said "OPEN — reviewer not yet run" long after the
Review record below was complete. The rest of this file is the unmodified
record of what was briefed.) This file is the package. It covers the
project-wide methods/limitations read (plan milestone 5) **and** the causal IV
read that `docs/explorations/iv_migration.md` §Read plan step 1 asked for,
because both are outstanding and the IV merge skipped its own gate.

## How to use this brief

Hand it to a reviewer who did not build the analysis. They need: the repo at
`HEAD`, ~1–2 hours, and no write access. The reviewer's job is to attack the
analysis, not to improve the code.

**Ground rules for the reviewer**

- Read-only. Do not edit code, docs, or data. Report; do not fix.
- Every objection cites a file and line/table. No vibes.
- Distinguish "wrong" from "under-disclosed". Both are findings, but the second
  is usually cheaper to fix.
- A finding that the project already discloses by name is not a discovery —
  say instead whether the disclosure is *adequate*.
- If a claim cannot be checked from the repo alone, say what is missing.

**Verdict requested** (one per section, plus overall):

`SOUND` / `SOUND-WITH-CAVEATS (list)` / `OVERCLAIMED (list)` / `UNSUPPORTED (list)`

## What is being reviewed

| Path | Role |
| --- | --- |
| `docs/methods.md` | What each number means, join rules, honest-reading section |
| `docs/synthesis.md` | The narrative claims (three regimes + causal extension) |
| `docs/explorations/identification.md` | Design menu and its own ranking |
| `docs/explorations/iv_migration.md` | The one causal estimate, its limits |
| `docs/reproducibility.md` | Gate definitions and clean-rebuild record |
| `docs/sources.md`, `docs/data_dictionary.md` | Provenance and column semantics |
| `src/spanish_housing/`, `scripts/` | Estimation + build code |
| `explorations/*.py`, `*.md` | 24 explorations: boom-bust vs tightening, credit cycle, absorption, panel (adjusted/quarterly), affordability, young-squeeze, Madrid/Barcelona municipios, tourist panel + SERPAVI extension, terrain (Saiz probe, provincial/municipal nulls, Madrid leg), ratio decomposition + vacancy, IV migration, data probes (censo anual, SERPAVI, valor referencia, construction) |

**New-data additions since the brief was written (2026-10-06), all in scope:**

- `docs/explorations/censo_anual_probe.md` — provincia mart extended 2001→2025 via Censo Anual de Población (static CSV 68521; closes the 56945 API block).
- `docs/explorations/serpavi.md` + `docs/explorations/serpavi_probe.md` — municipal rents nationwide (MIVAU fianzas, 2011–2024), DIBA-validated (Pearson 0.825), rent-vs-sale wedge.
- `docs/explorations/ratio_ccaa.md` — viv/1000 decomposition: two-group split (scarcity vs overstock) + electricity-vacancy confirmation (Galicia 28.8% vs Madrid 6.3%).
- `docs/explorations/tourist_rents.md` — tourist→rents null extended to Balears/Canarias via SERPAVI.
- `docs/explorations/valor_referencia_probe.md`, `docs/explorations/construction_probe.md` — parked decisions (PDF-only / app+gap access).

## Reproduce before judging

```bash
uv sync --group dev
make gates      # verify + audit + test + lint
make audit      # 199 headline doc numbers re-queried against marts/models/probe
```

`make audit` is the anti-drift device: every quotable number in the docs is a
declared claim in `scripts/audit_claims.py`, re-queried at gate time. A number
that survives audit is *reproducible*, not *correct* — audit checks the
pipeline, not the inference. **Do not read a green audit as a passed review.**

## Known limitations, already disclosed (judge adequacy, don't rediscover)

- Fictional/deflator boundaries: IPV base changes are never spliced; real-terms
  work uses INE IPC (base 2021) per CCAA/national.
- 2021 census *tipo* split is definitionally incompatible with MIVAU modelled
  stock (up to ~20% on no-principal); totals anchor at ≤0.77%, splits don't.
- Population 2022+ is ECP (CCAA/national) or Censo Anual de Población
  (province grain), not Padrón; both overlaps quantified (ECP-vs-Padrón
  2021 max +0.89% in `coverage.json`; Censo-Anual-vs-Padrón 2021 mean
  0.17%, verified in `censo_anual_probe.md`), never silently spliced.
  Provincial ECP (table 56945) remains API-blocked, but the provincia mart
  runs 2001–2025 on the Censo Anual static CSV — the block no longer caps
  the mart (see `censo_anual_probe.md`).
- `viv/hogar` 2001 is a documented proxy, not a measurement.
- Appraisal prices (valor tasado), not transaction prices.
- The site is already reachable at `vivienda-explorer.juakke.workers.dev`
  **before** this review. Treat workers.dev as an unlisted preview; the custom
  domain is the release act this review gates.

## Section 1 — Descriptive claims and methods

Attack these specifically:

1. **Regime 3 (2021–25)** is the strongest descriptive claim: "0.23–0.90
   dwellings per new household in *every* CCAA". Is the range stated honestly,
   and is the household-formation series (ECP-based) viable for a per-CCAA
   ratio given the 2022+ methodology break?
2. **The long arc** 1.48 → 1.40 → 1.41 → 1.42 → 1.44 → 1.39 mixes a 2001
   proxy with measured years. Does one sentence carry more inferential weight
   than the mixed-provenance series can bear?
3. **"The overhang narrative is backwards"** (regime 1). This is a strong
   rhetorical claim resting on stock rising while prices fell. Is any causal
   direction being smuggled into a co-movement?
4. **Derived ratios**: `viv/1000` and `viv/hogar` are the analytical subject.
   Are the join rules (counts sum, indices never average, Ceuta/Melilla
   handling) sufficient to make cross-territory ratio comparison valid?

5. **New: the two-group viv/1000 decomposition** (`docs/explorations/ratio_ccaa.md`).
   National flatness hides scarcity CCAA (Madrid −29.7, Cataluña −27.6)
   vs overstock (+100…+130 interior). The price cross is −0.385 (n=17,
   insignificant); the vacancy cross +0.523 (n=17, significant). Is the
   split a fair decomposition or a cherry-picked partition? Does the
   electricity-vacancy confirmation (Galicia 28.8% vs Madrid 6.3%,
   2021 snapshot) carry the weight the narrative gives it?
6. **New: provincial population via Censo Anual** (`docs/explorations/censo_anual_probe.md`).
   The provincia mart now runs 2001–2025, splicing padrón (≤2021) to
   census-annual (≥2022). Is the seam handled as carefully as the
   ECP/padrón seam (same order of magnitude, but new)? The 2021
   province-vs-padrón mean |Δ| 0.17% is documented — is the whole
   extended mart's exposure to this seam adequately disclosed?
7. **New: SERPAVI rents** (`docs/explorations/serpavi.md`). Tax-deposit based municipal
   rents, DIBA-validated (Pearson 0.825). The rent-vs-sale wedge
   (Barcelona yield 3.61% vs corona 4.58% median) and the rent-vs-
   vacancy null (Pearson −0.43, Spearman −0.02 — scale artifact vs no
   signal: which is it?) are new analytical claims. Is the tax-file
   selection (new/rolling contracts) disclosed well enough for a
   comparison to DIBA rents (2005–) that used the old panel?

## Section 2 — The causal IV (the part most likely to be overclaimed)

> **Status note (2026-10-07): the +0.67/+0.84 figures below are the
> pre-repair vintage the first read saw. Corrected numbers (pooled +0.34,
> bust +0.46 with first stages 34.4/30.9) live in `iv_migration.md` and
> the addenda. This section is preserved as the record of what was briefed.**

Scope: `docs/explorations/iv_migration.md`, `explorations/iv_migration.py`,
`explorations/iv_results.json`, `src/spanish_housing/ols.py`.

The headline is +0.67 (SE 0.11), provincia panel 2002–2021, two-way FE,
clustered by provincia (G=50); +0.84 in the pre-2013 half, no first stage
after (F=0.13).

Questions the IV note itself names, now owed an answer:

1. **Exclusion plausibility.** The instrument is 1998 origin shares ×
   leave-one-out national waves. What is the most credible channel by which
   1998 settlement geography affects 2002–13 price *changes* other than
   through migration? Is the province-trend spec (which moves tau to 0.76) an
   adequate defence, or does it absorb too much?
2. **LATE vs attenuation.** The note offers OLS attenuation, LATE compliers in
   tight markets, and residual exclusion failure as three readings of
   why 2SLS is 4–5× OLS. Adjudicate: is the 4–5× multiplier better explained
   by a weak-instrument/attenuation account than by a real complier effect?
3. **Split-sample consequence.** The instrument works only pre-2013. Is the
   bust-only identification stated strongly enough in `docs/synthesis.md`, or
   does the pooled +0.67 still carry the headline unfairly?
4. **Single instrument.** No overidentification test exists. Is acknowledging
   this sufficient, or does the claim need to be narrowed further?
5. **Selection of outcome.** Valor tasado is appraisal, not transaction. Does
   mortgage-selection bias plausibly correlate with migration inflows in a way
   that inflates the estimate?

**Carry the reviewer's IV verdict upward**: per `docs/explorations/identification.md`
§Recommended sequence item 4, nothing causal should sit in synthesis until this
read passes. If it fails, the remedy is removal of the causal paragraph from
`docs/synthesis.md` and retention of the IV as a documented negative result —
not a softer wording.

## Process gaps the review should weigh

Disclosed here so the reviewer judges them rather than finding them later:

- The IV was merged into `docs/synthesis.md` (`82aa409`, `1616d9f`) **before**
  its own read plan step 1 ran. The merge was user-directed, but the project's
  stated bar was not met at merge time.
- Milestone 5 has been open since the plan was written while the explorer was
  already deployed to workers.dev.
- Design B (Saiz GIS) was probed this session
  (`docs/explorations/saiz_gis_probe.md`): the memo's "data NOT in reach,
  weeks not days" claim was **wrong** — the full 52-provincia series takes
  ~2 minutes and 2.6 GB from public Copernicus DEM. That probe needs
  reviewing too, and its own exclusion argument (terrain correlates with
  coastal amenity/tourism) is the sharpest open question on the list —
  **now partly answered against it**: `docs/explorations/panel_saiz.md`
  finds a *null* direct terrain→price association, a *null* build-suppression
  premise, and a right-signed but indistinguishable mechanism
  (high-constraint τ 0.74 vs low 0.64). `docs/explorations/panel_saiz_municipal.md`
  reruns the same diagnostics at municipal grain (310 municipios, real
  starts/completions, 0.00-1.00 constraint spread, density control) and
  **still** gets nulls, which closes the "provincial averaging hid it"
  hypothesis. The documented reopen condition ("a second province, price
  levels") was then attempted in Madrid
  (`docs/explorations/panel_saiz_municipal.md` §Madrid leg,
  `explorations/panel_saiz_madrid.py`): the join works (28/28) but priced
  municipios span constraint 0.00–0.25 against the province's 0.00–0.98,
  so the test has no leverage where the question lives, and its one
  significant association (negative price levels, t≈−2) is a
  centrality gradient wearing a terrain proxy (periphery ~1,700 €/m² vs
  flat NW suburbs ~3,200). Review should weigh whether the nulls are
  evidence about the mechanism, about the outcome (price *growth*, not
  levels), or about power — and whether the Madrid leg's failure is a
  data-availability close or a sign the cross-sectional design itself
  cannot separate terrain from centrality.

## Output

Return findings as: file → claim → why it fails → suggested remedy class
(rewrite / narrow / remove / disclose / re-run), ordered by severity. Append the
verdict block and the reviewer's identity + date at the bottom of this file so
the read becomes part of the record.

## Review record (2026-10-06)

Two independent opposite-family reviewers executed this brief via
orchestrated agents (read-only; findings in /tmp, since removed).
All 16 findings were verified against the code, fixed or narrowed in
the repo, and re-gated (199/199 claims, 53 tests) — commits `1e140de`
(Spearman fix), `42682f2` (2SLS/AR/language), `fc47232` (all 16
adjudications), `44eb9b3` (lint).

**Section 1 (descriptive) — reviewer: Codex / GPT-6-Sol medium.**
Verdict: **OVERCLAIMED** (rent–vacancy null; long-arc interpretation;
two-group/only-two-regions framing; boom–bust causal rhetoric). 9
findings: buggy Spearman (confirmed, fixed, re-ran — rent-vacancy
−0.024→−0.507, DIBA-SERPAVI 0.82→0.866); long-arc direction backwards
(rewritten); 13/17 not 2 CCAA falling (corrected); regime-1 rhetoric
narrowed; two-group disclosed as selected tails; regime-3 net-net
terminology; SERPAVI yield sample/quartiles corrected; censo probe
grain fixed + build-time seam guard added; methods base-year wording
fixed. Numbers reproducible; conclusions did not follow.

**Section 2 (causal IV) + terrain — reviewer: Copilot CLI.** Verdict:
**OVERCLAIMED** (IV) / **SOUND-WITH-CAVEATS** (terrain). 7 findings:
AR intervals mislabeled (f_crit=10.0 placeholder — "95%" removed
everywhere); 2SLS bread-transpose omission (fixed + regression test +
re-run; SEs shift 3rd decimal); trends≠rejection, multiplier
unadjudicated, pooled headline, appraisal selection, "independent
nulls" — all narrowed (bust-only +0.84 headline primary; convergent
non-independent diagnostics).

**Milestone-5 gate: satisfied.** Independent read before release —
both verdicts adjudicated in-repo. Remaining release act: custom domain
(user DNS action).

## Addendum (2026-10-06): post-record estimation correction

A subsequent model-level review found an incorrect two-way within
transform in every panel estimator: year dummies entered raw after
unit-demeaning y and X, which biases all coefficients (the Section 2
quotes above — +0.67 pooled, +0.84 bust, trends 0.76 — are the biased
values the reviewers saw). Corrected via a shared `ols.two_way_within`
helper (regression-tested against explicit dummy OLS), the provincial
panel gained its missing province FE plus a genuinely null-imposed
bootstrap, and the old singular province-trends spec (G trends + year FE
contain the common trend twice) now carries G−1 trends. Corrected
headlines: pooled +0.34 (AR [−0.20, 0.80]), bust-only +0.48 (F = 58),
trends spec +1.04 (diverges — sensitivity, not robustness). OLS is now
~zero, so no finite IV/OLS multiplier exists. `make audit` now also fails
when a committed model output predates its estimator code or input data
(`_meta` freshness keys), closing the staleness hole this episode
exposed. This addendum preserves the original brief text as the record of
what was reviewed; the corrected numbers live in
`docs/explorations/iv_migration.md` and `docs/synthesis.md`.

## Addendum (2026-10-07): milestone-5 IV read ran — verdict REMOVE

An independent read-only review (external model, briefed with the corrected
+0.34-base numbers since §Section 2 still quotes the stale +0.67 series)
returned **REMOVE to a documented negative result**:

- Exclusion FAIL — 1998 settlement geography coincides with the
  Cajas-credit/bubble footprint; the trends spec triples tau (+0.34 → +1.04).
- Attenuation cannot explain 2SLS ~150× OLS (needs >99.4% noise).
- New mechanism finding: the instrument is a *cumulative* predicted level
  since 1998 behind annual-flow language (`bartik_predict.py` grows 1998→t),
  instrumenting an *annual* rate — first stage rides a non-stationary stock
  trajectory through the within transform.
- First stage exists only 2002–13 (F = 58 vs 0.22), exactly the bubble/bust
  window the instrument geography already marks.

Remedy applied same day per the pre-committed protocol (removal, not softer
wording): causal section removed from `docs/synthesis.md` (pointer left);
`docs/explorations/iv_migration.md` re-headed as a negative result with the
full read record; numbers preserved in `explorations/iv_results.json` and
still guarded by `make audit`. No causal claim remains in the synthesis;
design B is likewise null, so the causal program is on hold pending a new
design with its own read.

## Addendum (2026-10-07): round-2 read on the repaired instrument — REJECT AGAIN

The annual-flow repair (first-differenced national growth, both estimators
re-run, audit repinned) went to a second independent read. Verdict: REJECT
AGAIN — principally on inference grounds. Independently replicated in-repo:
the repo's placeholder AR cutoff (F<10) covers zero in the bust, but the
calibrated F(1,49) ≈ 4.04 cutoff gives AR [0.10, 0.95], excluding it — while
F(1,G−1) itself is optimistic at G=50 and the wild-bootstrap calibration
`ols.ar_ci` calls for is unbuilt. So neither "identified null" nor
"significant positive" is established; the design is out of the synthesis in
both directions. The read also caught real staleness (Saiz note narrating
rejected-vintage splits, unmarked multiplier section, "synthesis" audit
labels) — all fixed same day — and disputes the YoY-rate normalization
(recorded unadjudicated; canonical Bartik form vs Card-flow form). Ceuta y
Melilla confirmed absent from both vintages (n=1000 = 50×20). Prerequisite
for any revival: wild-bootstrap-calibrated AR plus a third read.

## Addendum (2026-10-07): round-3 read on the wild-AR-calibrated bust result — KEEP OUT

The third independent read ran (read-only reviewer agent, briefed with the
calibrated numbers; no write access). Verdict: **KEEP OUT** — the synthesis
posture (no causal claim, no null claim) is correct. Six findings, all
verified against the code and dispositioned same day:

1. Exclusion language overstated (this note, round-2 finding 3): "stands
   under both normalizations" presented an unrun comparison as
   established; the credit probe supports *unresolved confounding*, not a
demonstrated failure. Disposition: narrowed by dated amendment to
   plausible-under-both, demonstrated-under-neither.
2. Wild-bootstrap AR provisional (`ols.wild_ar_ci`, 299 reps, 0.25 grid):
   method null-imposed and sound, but [0.25, 1.00] are grid summaries
   and the 95th-percentile cutoff is MC-noisy. Disposition: language
   narrowed to "rejects the null on the tested grid under this
   calibration"; seed-stability checked in-repo (two alternate seeds
   reproduce [0.25, 1.00] exactly at identical settings; /tmp only, no
   repo state touched).
3. Normalization comparison is a revival prerequisite: current flow =
   1998 levels x YoY growth (`bartik_predict.py`); proposed =
   first-differenced levels scaled to 1998 stocks — different origin
   weighting, potentially different first stage. Not run; no decision
   value for the current KEEP OUT posture, so deferred, not
   commissioned. Recorded here as an explicit prerequisite.
4. Quarterly rate correction (dr -0.055 to +1.00) leaves exclusion
   untouched: within-year national-cycle co-movement at CCAA grain,
   testing nothing about 1998 settlement geography to 2002-13 prices.
   Checked: no doc cites it as IV corroboration; recorded as context.
5. Audit scope: pins transcription/freshness (now including wild-AR reps
   + seed as claims), not inferential validity — already disclosed
   ("audit checks the pipeline, not the inference"). Section 2's stale
   vintage now carries a status banner; original text preserved.
6. Saiz chain: no drift; consistent with the repaired vintage.

Vintage note: the "F = 58 vs 0.22" figures in the round-2 addendum
above describe the pre-repair cumulative instrument; the repaired
design's first stages are 34.4/30.9 (note split-sample table,
re-runnable code, committed `iv_results.json`). Preserved above as
written; corrected here.

Revival prerequisites (supplanting "calibrated AR plus a third read,"
both now done without reviving the claim): (a) the both-normalizations
comparison under matched specifications and inference; (b) materially
higher bootstrap precision (reps, grid, seed sensitivity) for any revived
set claim; (c) a fourth independent read of the result.

## Addendum (2026-10-09): milestone-5 delta read — SOUND-WITH-CAVEATS

Plan milestone 5 still reads STILL OPEN ("required before sharing beyond
workers.dev") while the explorer is public, so a delta read ran covering
the 51 commits since round 3 (2026-10-07): estimator/inference changes
plus the new descriptive surface. Read-only subagent, offline checks only.

Verdict: Scope A (estimators/inference) SOUND-WITH-CAVEATS, Scope B
(descriptive surface) SOUND, overall SOUND-WITH-CAVEATS. No causal claim
crept back anywhere; KEEP-OUT posture intact and further narrowed in the
delta. New mart tables (AEAT/secciones/RMDVP) have no estimator consumer
(verified by search); quarantines disclosed where numbers appear.

Two documentation-class caveats, both disclosed same day in
`docs/uncertainty.md` (no code change, no re-run required):
degenerate-cluster guard thresholds differ between the panel-bootstrap
and grid-inversion paths (published results non-degenerate, unaffected);
inversion acceptance masks are per-model nominal with no joint coverage
across models. The bootstrap vectorization itself was verified
numerically identical; the candidate-grid inversion methods sound with
prespecification honestly qualified.

Reviewer identity: pi subagent milestone5-review (same-model family,
read-only, no write access), 2026-10-09. Transcript retained in-session;
worker stopped after delivery. This addendum, not a new brief: round-3
record above is unmodified.
