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

## Madrid leg: the replication that could not be delivered

That next step was attempted (`explorations/panel_saiz_madrid.py`,
`explorations/saiz_municipal_mad.json`, 179 LAU municipios, land total
7,979 km² against LAU's 8,025, worst area error 6.7%). The join works —
28/28 priced municipios match. The replication does not, and it fails
for a reason worth recording:

**Madrid's priced municipios span constraint 0.00–0.25 against the
province's 0.00–0.98.** The steep municipios (Atazar 0.96, Puebla de la
Sierra 0.98, La Hiruela 0.98) are villages with no price series; the 28
with series are the big central-basin ones. So the test has no leverage
where the question lives — exactly the selection problem the Barcelona
price caveat (130 of 310) has, one step worse.

What the test *does* find is instructive as a warning rather than as
evidence. Price **levels** are *negatively* associated with constraint
(−0.081 log points per 0.1, t = −2.04; −0.101 with a density control,
t = −2.25), while growth is null (−0.134, t = −1.00). Taken at face value
that contradicts both the supply-scarcity story (constraint ⇒ dearer) and
the amenity story (mountains ⇒ dearer). Look at the municipios carrying
the slope and neither story is needed: the "constrained" ones are the
periphery (Arganda 1,707 €/m², Aranjuez 1,611, Valdemoro 1,784) while the
dear flat ones are the NW suburbs (Pozuelo 3,214, Madrid city 3,280). The
slope is a **centrality/wealth gradient wearing a terrain proxy** —
within a 0.00–0.25 range, "hillier" mostly means "farther from the
centre".

That is the sharpest lesson of the Madrid leg: at cross-sections,
terrain correlates with everything, and an association can be
significant, wrong-signed, and fully explained by something else — at
28 clusters, with a quarter of the constraint range, and no construction
data. It is not evidence against or for design B; it is evidence for why
design B needs an exclusion argument the data here cannot buy, and it
confirms the recommendation above with a stronger one:

**Final recommendation: leave design B unbuilt. The reopen condition
("second province, price levels") cannot be met — no Spanish province
publishes municipal price series for its steep municipios. If terrain is
ever revisited, it needs a design in which terrain is compared to
*terrain*, not to centrality: matched pairs or within-mountain-range
variation, not cross-sectional slopes.**

## Madrid epilogue: the vacancy table does not reopen the question

The one remaining variant — vacancy by electricity consumption (INE
table 59531, `censo2021_intensidad`), which names 3,139 municipios and
might reach the villages prices miss — was tested
(`explorations/panel_saiz_madrid_vacancy.py`,
`artifacts/madrid_vacancy_terrain.json`) and **closes the door twice**:

1. **0 of the 7 steepest Madrid villages appear in the vacancy table**
   (Hiruela 0.984, Puebla de la Sierra 0.982, Atazar 0.960, Patones
   0.898, Acebeda 0.892, Somosierra 0.888, Horcajuelo 0.852 — all
   rolled into "Resto de Madrid"; only Cercedilla 0.826, ~7k pop, is
   named). The selection problem is structural: the terrain-relevant
   tail aggregates away in *every* administrative series, not just
   prices.
2. On the 135 named Madrid municipios with both terrain (0.00–0.826)
   and vacancy (2.7–38.5%): constraint→vacancy is **positive** (Pearson
   0.375, Spearman 0.557). But the highest-vacancy named ones are rural
   south-east periphery (Carabaña 39%, Valdelaguna 33%, Orusco 33%),
   not mountains. It is the same centrality gradient as the price
   finding, wearing a third proxy: constraint predicts vacancy
   positively *and* prices negatively in the same sample, both fully
   explained by center-versus-periphery. Terrain correlates with
   everything, again — no identification added, verdict unchanged.
