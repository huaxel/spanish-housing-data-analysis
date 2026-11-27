# How many tourist dwellings are there, officially?

The public debate about *pisos turísticos* argues about a number the repo never
had a direct measure of. The tourist claim in this project is built on
**intensity panels** — travellers and nights per resident — which measure *flow*.
INE publishes the stock separately: the municipal tourist-dwelling register
(VTE, operation 410, tables 39363/39366).

## The stock, in the current snapshot

| | Value |
| --- | ---: |
| Tourist dwellings (Spain) | **341,001** |
| Beds | **1,714,702** |
| Beds per dwelling | 5.03 |
| Share of census dwellings | **1.28%** |

The register also carries history — irregular reference months from 2020 — and
the national count is **+6.07%** above its first snapshot (2020-M08, 321,496).
Snapshot months move (Feb/Aug before 2024, May/Nov since), so the series is a
sequence of administrative photographs rather than a smooth monthly series.

## It is a local phenomenon, not a national one

INE's own share variable (tourist dwellings over census dwellings, per
municipio) is the honest way to look at this, because it uses INE's denominator
rather than one we invent:

| Municipal share of tourist dwellings | Value |
| --- | ---: |
| Median municipio | **0.61%** |
| 90th percentile | **3.40%** |
| Maximum | **33.33%** |
| Municipios above 5% | **5.34%** |

So the national 1.28% is an average over a very skewed distribution: in half of
the municipalities the register is a rounding error, in the top decile it is a
structural share of the housing stock, and one municipality approaches a third
of it. Concentration at the top is real but not overwhelming — the ten largest
municipal stocks hold **14.99%** of the assigned total, led by Marbella with
6,987 registered dwellings.

## What it cannot do

- **It is a floor, not a census.** The register counts declared tourist
  dwellings under the current definition; unregistered letting is by
  construction absent. Under-registration is the standing critique of every
  such register, and this module does not resolve it.
- **Coverage is partial and reported.** INE ships no municipality code in the
  data payload and **122 labels** in the current snapshot belong to more than
  one territory (a province and its capital, or the same name in two provinces).
  Those are marked `ambiguo` and excluded rather than guessed: the municipal
  rows that do join the repo's dimension carry **84.52%** of the national stock.
- **It says nothing about rents.** Whether tourist dwellings move municipal
  rents is the question of the intensity panel, which finds no intra-municipal
  association. A bigger stock number does not turn that null into an effect, and
  the null does not make the stock small.

## Reproduce

```bash
uv run python scripts/fetch_vut_municipal.py --offline
uv run python explorations/vut_stock.py
```

Pinned inputs: `data/raw/vut_municipal_39363.json`, `data/raw/vut_municipal_39366.json`.
Output artifact: `artifacts/vut_stock.json`; `--check` verifies it against the
pinned parquet and `marts.duckdb`.
