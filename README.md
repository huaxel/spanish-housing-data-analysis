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
- [Panel: absorption with demand controls](docs/explorations/panel_adjusted.md) — adjusted description (CCAA + year FE, clustered SEs); attenuation is the finding
- [Quarterly credit timing](docs/explorations/panel_quarterly.md) — mortgages lead appraisal prices by 3 quarters; supply unobservable at this frequency
- [Identification memo](docs/explorations/identification.md) — what a causal extension would take (scoping only: migration shift-share first, Saiz GIS second)
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
make gates   # lint -> fetch -> build -> verify -> audit -> test
```

Then, for the Evidence dev dashboard (Node/npm required):

```bash
make evidence-install
make evidence-dev
# open http://localhost:3000/ — Nacional, CCAA, comparisons, municipios
```

Starting dev automatically exports the existing DuckDB marts into Evidence's
browser-queryable data. After rebuilding the marts, restart dev to refresh it.
`/comparar/` compares two communities (or the national benchmark) over a shared,
inclusive year range. Inverted year selections are ordered automatically;
missing observations stay missing.
`/municipios/` drills into Madrid (valor tasado + population, 2005–2025)
and Barcelona (sale, rent, burdens, 2007–2024) with multi-municipality
selectors; the two metros use different sources and are read separately.
`make evidence-build` produces a static site in `evidence/build/`.
See [reproducible setup](docs/reproducibility.md#evidence-explorer) for details.

The lightweight static alternative remains available via `make dashboard`
at port 8091 (binds to all interfaces).

`data/` artefacts are git-ignored and pinned by `data/input_manifest.json`
(SHA-256). Never edit `data/raw` by hand — re-run `make fetch`.

## Components

| Component | Current role |
| --- | --- |
| INE IPV (quality-adjusted index, base 2025) | Price *trend* by CCAA, 2007–; no provincial grain |
| MIVAU Estimación del Parque de Viviendas | Dwelling *counts* by provincia, 2001–2025, principal/no-principal |
| INE Padrón → ECP | Population to 2021 (provincia) / 2025 (CCAA); hogares 2021+; seam quantified |
| MIVAU valor tasado | Appraised €/m² *levels* (prov + CCAA), complement to IPV trend |
| INE ECV renta | Mean net household income (CCAA) → affordability in years of income |
| INE Hipotecas + Transmisiones | Mortgage volumes/tickets + transaction liquidity (credit cycle) |
| INE Turísticas (VTE) | Registered tourist dwellings, Dec snapshots from 2020 |
| ECP edad/tamaño + Censo 2011 | 20–34 cohort, 1-person households; 2011 vacancy/vintage splits |
| Municipios (Madrid + Barcelona) | Valor tasado + padrón (Mad); sale/rent/burdens via DIBA (BCN) |
| INE IPC general (base 2021) | Monthly CPI, CCAA + Nacional → `ipc_anual`; deflator for real-terms levels |
| Evidence marts | `mart_ccaa_anual`, `mart_provincia_anual` + `dim_territorio` + `muni_*` |

Annual pre-2021 households (ECH) and the Censo 2021 anchor check are queued
sources — see [project plan](docs/project_plan.md). Missing cells stay missing.
All municipal €/m² are nominal unless stated; Madrid in 2025 euros: capital
−7.5%, Fuenlabrada −28.4%, Getafe −30.3%, Parla −38.1% real (2007–25).

## License

Code license TBD — ask before reusing. Data © their publishers (INE,
MIVAU, Diputació de Barcelona, datos.comunidad.madrid); see
[Sources](docs/sources.md) for terms and attribution.
