# Independent review brief (milestone 5)

Status: **OPEN — reviewer not yet run.** This file is the package. It covers the
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
| `docs/sources.md`, `data_dictionary.md` | Provenance and column semantics |
| `src/spanish_housing/`, `scripts/` | Estimation + build code |
| `explorations/*.py`, `*.md` | The four explorations and their writeups |

## Reproduce before judging

```bash
uv sync --group dev
make gates      # verify + audit + test + lint
make audit      # 83 headline doc numbers re-queried against marts/models
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
- Population 2022+ is ECP, not Padrón; overlap quantified in `coverage.json`,
  never silently spliced. Provincial ECP is API-blocked, so provincia marts end
  2021 while CCAA/national run to 2025.
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

## Section 2 — The causal IV (the part most likely to be overclaimed)

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
- Design B (Saiz GIS, `identification.md` §B) has not been started; its
  precondition ("only after A or C shows the machinery works") is now met by
  A. Its exclusion argument has not been independently checked either.

## Output

Return findings as: file → claim → why it fails → suggested remedy class
(rewrite / narrow / remove / disclose / re-run), ordered by severity. Append the
verdict block and the reviewer's identity + date at the bottom of this file so
the read becomes part of the record.
