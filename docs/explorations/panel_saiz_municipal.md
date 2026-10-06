# The terrain null survives the grain change

`panel_saiz.md` ended with a hypothesis it could not test: a provincia
averages mountains with valleys, and **that averaging may be what erased
the mechanism**. This note tests that directly.

Within Barcelona province the terrain measure spans **0.00** (Llagosta,
Badia del Vallès — flat Vallès) to **1.00** (Gisclareny, high Pyrenees).
Median municipal constraint is 0.62. That is the variation the provincial
test threw away, and it does not restore the mechanism.

| diagnostic | coefficient per 0.1 constraint | t |
| --- | --- | --- |
| Premise: housing starts per 1,000 pop | −0.023 (0.026) | −0.90 |
| Premise: completions per 1,000 pop | −0.008 (0.020) | −0.43 |
| Premise, + density control | −0.028 (0.028) | −1.00 |
| Exclusion: price growth (year-on-year %) | −0.009 (0.059) | −0.15 |
| Exclusion, + density control | +0.050 (0.068) | +0.74 |

**Verdict: still null, and now at the right grain.** Every coefficient has
the sign Saiz's logic predicts (constrained ⇒ less building) except the
density-controlled price term, and none is distinguishable from zero. The
provincial null was not an averaging artifact.

## Why this grain is the right test

Three upgrades over `panel_saiz.md`, all of which make the null harder to
explain away:

1. **Grain.** Saiz's own object is finer than a province. Municipal is
   closer to it than provincia, and the within-province spread (0.00–1.00)
   is the variation that could plausibly matter.
2. **Real construction flows.** `muni_bcn` carries actual `starts` and
   `completions` (DIBA), not stock differences. The provincial premise
   test had to infer building from `viviendas_total` changes, which mixes
   construction with demolitions and register revisions.
3. **A demand control.** Population density at municipal grain is a usable
   urbanisation proxy, which the provincial run lacked. Adding it moves
   nothing.

Mean starts are 1.52 per 1,000 inhabitants per year. The point estimate
across the full 0→1 constraint range is ≈ −0.23, about 15% of the mean —
so this is a *null on detection*, not a demonstration of exact zero. The
data cannot resolve a supply-suppression effect of that size.

## Face validity of the municipal measure

This part works well and is worth recording:

- 310 of 310 `muni_bcn` municipalities joined to the 311 LAU units.
- Computed land area totals **7,685 km² against LAU's 7,729 km² (99.4%)**;
  **median per-municipality area error is 0.99%**. (13 small municipalities
  exceed 5%, worst 14% — coarse 1:1M LAU boundaries against a 90 m grid
  matter most where municipalities are tiny.)
- The extremes are geographically obvious: Gisclareny 1.00, Castell de
  l'Areny 0.99, Montseny 0.99, Cercs 0.98 at the top; Llagosta, Badia del
  Vallès, Puigdàlber, Vilassar de Mar at 0.00.

## A name-join case worth keeping

One municipality did not match: **Santa Maria de Corcó**. It was
officially renamed **L'Esquirol** in 2014 — same INE code 08254, but the
name stem genuinely changed, so `muni_key()` cannot see the identity and
the default behaviour is to leave it unmatched. It is declared as an
explicit alias in `explorations/panel_saiz_municipal.py` with the reason.
This is the failure mode `muni_names.py` is designed to make loud, and it
worked: the join silently dropped one municipality and said so.

## Caveats that limit how much this can bear

1. **Price coverage is 130 of 310 municipios** (n = 1,414). DIBA publishes
   sale prices for larger municipalities, so the price test is a
   *selected* sample — precisely the urban ones where terrain variation is
   smallest. The construction test, by contrast, covers all 310.
2. **One province.** This is Barcelona. Terrain variation in Madrid
   province is different in kind, and a second province would be a genuine
   replication rather than a robustness tweak.
3. **Amenity is not measured here.** These tests ask whether terrain
   *predicts* prices; they still cannot separate terrain→supply from
   terrain→amenity. A null on both is most consistent with terrain being
   close to irrelevant for municipal price *growth* in this window, but
   that is a statement about growth, not levels.
4. **Year FE, no municipio FE.** Constraint is time-invariant and is
   absorbed by municipio FE, so these are cross-sectional comparisons.
   This is a real identification limit, not a stylistic choice, and it is
   why the premise test cannot be read as a supply elasticity.

## Consequence for the board

The identification memo was right that design B's data problem was
overstated, and this session showed that — but the mechanism it exists to
exploit does not show up in Spanish price growth at either provincia or
municipal grain, in two different provinces, with real construction data
and a demand control. That is now three independent nulls
(`panel_saiz.md`, this note, and the tourist panel) pointing the same way.

Recommendation: **leave design B unbuilt as an instrument.** Not because
the data are unreachable — they are not — but because the preponderance of
evidence here says the terrain channel is not doing measurable work in
this outcome. If it is revisited, the honest next step is a second
province and price *levels* rather than growth, not more instruments.
