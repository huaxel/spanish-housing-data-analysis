# Spanish housing: prices vs built stock vs people

**Core question:** how has the evolution of Spanish housing prices related to
the amount of housing stock built and to population / household growth —
nationally and by CCAA/provincia, 2001–2025?

The required deliverable is an Evidence-based explorer (DuckDB + Parquet),
a reproducible pipeline, and an evidence-backed account of coverage and
limitations. Causal estimation and price forecasting are extensions, not v1.

## Start here

- [Project plan](docs/project_plan.md)
- [Methods and interpretation](docs/methods.md)
- [Sources](docs/sources.md)
- [Reproducible setup](docs/reproducibility.md)
- [Data dictionary](docs/data_dictionary.md)
- [Exploration 01: boom-bust vs tightening](docs/explorations/boom_bust_vs_tightening.md)
- [Hypothesis 01: absorption ratio vs prices](docs/explorations/absorption_hypothesis.md) — verdict: descriptor, not a huge predictor
- [Affordability: years of income for 90 m²](docs/explorations/affordability.md)
- [Young-adult squeeze: collapse, refill, two household surges](docs/explorations/young_squeeze.md)
- [Credit cycle: the bust's other half](docs/explorations/credit_cycle.md)
- [Madrid vs Valencia: scarcity vs composition](docs/explorations/madrid_vs_valencia.md)
- [Synthesis: the answer in one place](docs/synthesis.md)
- [Madrid capital vs corona: the south never recovered](docs/explorations/madrid_municipios.md)
- [Barcelona: burdened metropolis, stretched corona](docs/explorations/barcelona_municipios.md)

## Setup and verification

Python 3.11+, `uv`, and `make` are required. Node/npm only for the Evidence app.

```bash
uv sync --group dev
make gates   # fetch -> build -> verify -> test
```

Then, for the explorer:

```bash
make evidence-install
make evidence-dev   # open the printed localhost URL
```

`data/` artefacts are git-ignored and pinned by `data/input_manifest.json`
(SHA-256). Never edit `data/raw` by hand — re-run `make fetch`.

## Components

| Component | Current role |
| --- | --- |
| INE IPV (quality-adjusted index, base 2025) | Price *trend* by CCAA, 2007–; no provincial grain |
| MIVAU Estimación del Parque de Viviendas | Dwelling *counts* by provincia, 2001–2025, principal/no-principal |
| INE Padrón → ECP | Population to 2021 (provincia) / 2025 (CCAA); hogares 2021+; seam quantified |
| Evidence marts | `mart_ccaa_anual`, `mart_provincia_anual` + `dim_territorio` |

Price *levels* (€/m², MIVAU valor tasado), post-2021 population (Cifras de
Población), and annual households (ECH) are queued sources — see
[project plan](docs/project_plan.md). Missing cells stay missing.
