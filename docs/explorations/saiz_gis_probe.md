# Saiz GIS probe: the supply-side instrument is reachable after all

Verdict: **design B is feasible and cheap.** The identification memo
called it "NOT in reach — needs a GIS build … Weeks, not days … the
single biggest data investment on this list." The probe refutes that on
the data and tooling axes.

Measured, this session, on this machine:

| | |
| --- | --- |
| Source | Copernicus DEM GLO-30 on AWS Open Data (public, no auth) |
| Tiles | 103 on disk of 112 candidates (9 are all-ocean 1° cells, 404 as expected) |
| Volume | **2.6 GB** |
| Compute | **~2 minutes** wall clock, 16-thread prefetch, 52 provincias |
| New dependencies | none committed — `rasterio` + `numpy` via `uv run --with` |
| Code | `scripts/probe_saiz_gis.py` (one file, ~280 lines) |
| Output | `explorations/saiz_probe_results.json` |

The memo's "weeks" estimate was about *building a pipeline*. The probe
shows the pipeline is one script. The remaining work is not data
engineering — it is the exclusion argument (below), which was always the
real cost.

## What the measure is

Following Saiz (2010, QJE 125(3)): undevelopable = steep slope **or**
water, where steep means slope above **15% grade**, i.e.
`arctan(0.15) = 8.53°`.

Note the threshold. The repo's own memo (`identification.md` §B) says
"slope", and the natural misreading is 15 *degrees*. That is 1.76×
steeper and would badly understate the constraint. 15% grade is the
correct figure and is cross-checked against the paper text.

## Four traps that had to be got right

Each of these silently produces a wrong answer that still looks
plausible. All four are now handled in the probe and recorded here so the
production version cannot regress them.

1. **15% grade, not 15 degrees.** Factor 1.76 on the threshold.
2. **EPSG:4326 longitude spacing.** The DEM is in geographic degrees. A
   constant 30 m spacing for the gradient is wrong: at 40°N a cell is
   30.7 m north-south but only 23.5 m east-west. Ignoring `cos(lat)`
   understated the >15% share by ~24% in *relative* terms (Madrid-inland
   tile: 0.0871 → 0.1085). The probe corrects analytically per row, which
   avoids resampling the raster at all.
3. **GLO-30 is a DSM, not a DTM.** It includes buildings and canopy, so
   at native 30 m a single building edge can clear 15%. Saiz worked at
   90 m on a bare-earth USGS DEM. Resolution sensitivity, measured:

   | tile | 30 m | 90 m | 180 m |
   | --- | --- | --- | --- |
   | rolling Extremadura | 0.290 | 0.248 | 0.192 |
   | Pyrenees | 0.880 | 0.876 | 0.853 |

   Ranking is robust (the Extremadura/Pyrenees gap is ~3.5×), the level
   is not. The probe block-averages to 90 m to match Saiz, and the level
   must stay pinned to that choice.
4. **Grain mismatch in the boundary source.** GISCO NUTS-3 (1:1M, 2021,
   public) returns **59** Spanish units, not 52 — the Canaries arrive as 7
   units and Baleares as 3. The probe merges them
   (`Fuerteventura+Gran Canaria+Lanzarote+La Graciosa → Las Palmas`,
   `El Hierro+La Gomera+La Palma+Tenerife → Santa Cruz de Tenerife`,
   `Mallorca+Menorca+Eivissa y Formentera → Illes Balears`) and recovers
   exactly **52**. Any use of GISCO without this crosswalk silently
   splits four provincias.

Also note what is *not* a problem: the Spanish IGN download centre
(`centrodedescargas.cnig.es`) is indeed unreachable from here, which is
probably what the memo generalised from. But IGN was never required —
Copernicus serves the same job, publicly and 30× faster.

## Results — the geography checks out

Full 52-provincia series in `explorations/saiz_probe_results.json`.
Ranked share of undevelopable land:

| rank | least constrained | | rank | most constrained | |
| --- | --- | --- | --- | --- | --- |
| 1 | Valladolid | 0.07 | 52 | Gipuzkoa | 0.92 |
| 2 | Salamanca | 0.14 | 51 | Asturias | 0.88 |
| 3 | Segovia | 0.16 | 50 | Bizkaia | 0.84 |
| 4 | Toledo | 0.16 | 49 | Cantabria | 0.80 |
| 5 | Zamora | 0.18 | 48 | Ceuta | 0.79 |

The ranking is a face-validity test the probe was designed to pass, and
it passes on geography the project does not control:

- Bottom is the **Meseta** — Valladolid, Salamanca, Segovia, Zamora,
  Palencia, Badajoz, Ciudad Real: the flat Castilian plateau and
  Extremadura. Exactly the provinces Spain's own housing literature
  treats as land-abundant.
- Top is the **Cantabrian cornice plus the islands** — Gipuzkoa,
  Asturias, Bizkaia, Cantabria, Santa Cruz de Tenerife, Málaga: the
  steepest and most coastal terrain in the country. Málaga at 0.66 and
  Barcelona at 0.64 are the coastal-metro cases the instrument exists to
  separate from flat inland provinces.
- The spread is 0.07 → 0.92, a 12× range. That is ample variation for a
  supply-shift instrument; a measure that returned every province near
  0.3 would be useless even if computed correctly.

## Deviations from Saiz (deliberate, and they matter)

1. **Unit.** Saiz measures within 10/50 km rings of metro centroids. This
   measures provincias. Consequences run in both directions: province
   grain is the only grain the project's panel can use, but it dilutes
   the metro-level constraint that actually drives supply (a province
   averages its constrained mountains with its buildable valleys).
2. **Ocean is excluded from both numerator and denominator.** NUTS-3
   polygons are clipped to the coastline, so unlike Saiz's rings, sea
   area is not counted against coastal provinces. Water shares here are
   therefore *inland only* — mostly under 2% (Madrid 0.008, Alicante
   0.014, Ceuta 0.060). This is arguably the more defensible definition
   for a land-availability instrument, but it is a real departure and
   makes Spanish numbers not directly comparable to Saiz's US figures.
3. **DEM and water source differ** (Copernicus GLO-30 + bundled WBM
   layer, vs USGS DEM + NLCD land cover).
4. **Slope is max-to-4-orthogonal-neighbours**, matching Saiz's own
   "maximum slope with respect to the adjacent quadrants" in spirit, not
   his exact GIS routine.

## What still stands between this and a usable instrument

The probe answers the feasibility question. It does not produce an
instrument, and the difference is deliberate:

1. **The exclusion argument is still unexamined.** The instrument's
   claim is that terrain affects prices only through supply. Spanish
   counterexamples are obvious and specific — coastal tourism and
   amenities correlate with terrain, and the whole point of using
   developable-land share is that steep coastal provinces are also
   high-amenity provinces. This is a serious thread and belongs in the
   same independent read the migration IV is waiting on; it must not be
   waved through because the numbers look nice.
2. **Pipeline discipline.** The memo flagged that "rasters don't fit the
   manifest-pin pattern without thought." The probe sidesteps this by
   caching to `/tmp` and committing only the reduced JSON. A real
   `fetch` step has to decide: pin 103 tiles (2.6 GB) by hash as a
   second manifest class, or pin the tile list + source version and treat
   the rasters as reproducible-but-not-committed, like `data/` itself.
   The latter matches how this repo already treats `data/`.
3. **Determinism.** `block_mean` depends on `mean` over float32; the
   reduction should be asserted stable, and the province series should
   get audit claims the way `iv_results.json` did.
4. **A resolution/threshold sensitivity table** should ship with the
   series, since both are analyst choices (see trap 3).

## Recommendation

Un-strike design B in `docs/explorations/identification.md`: the data
and tooling blockers were overstated. Re-rank the sequence on *real*
effort, which is now dominated by the exclusion argument rather than by
data acquisition. Do **not** merge the series as an instrument before the
independent read; the plausible amenity-tourism confound is exactly the
kind of thing that read exists to catch.
