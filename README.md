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
- [Quarterly credit timing](docs/explorations/panel_quarterly.md) — no mortgage lead once year effects are correctly absorbed (the old L3/L5/L6 shape was transform artifact); mortgage-rate changes co-move with appraisal growth within years (2022–24 inflation cycle — descriptive, not causal); supply unobservable at this frequency
- [Identification memo](docs/explorations/identification.md) — what a causal extension would take (scoping only: migration shift-share first, Saiz GIS second)
- [IV: migration exposure → prices](docs/explorations/iv_migration.md) — commissioned design A, **rejected on independent read** (exclusion fails; repaired flow design also rejected on inference grounds); kept as a documented negative result, removed from synthesis
- [Tourist intensity panel](docs/explorations/panel_tourist.md) — municipal null: tourist changes don't track price/rent accelerations (wild-p 0.49–0.96)
- [**Independent review brief**](docs/review_brief.md) — milestone-5 package (scope, reproduction, adversarial questions, disclosed limitations); **review completed; IV design rejected**
- [Saiz GIS probe](docs/explorations/saiz_gis_probe.md) — design B feasibility: full 52-provincia developable-land series, 2.6 GB / ~2 min from public Copernicus DEM; the memo's "data not in reach" was wrong
- [Land constraint vs the migration→price gradient](docs/explorations/panel_saiz.md) — null with precision: premise and direct-price checks null, mechanism right-signed but indistinguishable (high τ 0.41 vs low 0.32)
- [Terrain null survives the grain change](docs/explorations/panel_saiz_municipal.md) — municipal rerun (310 municipios, real starts/completions, 0.00–1.00 constraint spread): still null; Madrid leg can't deliver the replication (priced municipios span 0.00–0.25) and its one association is a centrality gradient in terrain clothing; design B left unbuilt
- [Affordability: years of income for 90 m²](docs/explorations/affordability.md)
- [Young-adult squeeze: collapse, refill, two household surges](docs/explorations/young_squeeze.md)
- [Credit cycle: the bust's other half](docs/explorations/credit_cycle.md)
- [Madrid vs Valencia: scarcity vs composition](docs/explorations/madrid_vs_valencia.md)
- [Housing access: stock is not availability; averages are not household burdens](docs/housing_access.md) — explorer `/acceso/`, separate vintages, arithmetic sensitivity checks and national EU-SILC burden marginals
- [Purchase scenarios: cash access and mortgage debt service](docs/purchase_scenarios.md) — explorer `/compra/`, explicit hypothetical inputs, no observed borrower claims
- [Model uncertainty: effect sizes, approximate ranges and zero-null tests](docs/uncertainty.md) — explorer `/incertidumbre/`, no bootstrap intervals invented
- [Physical-stock pilot: cadastral polygons, dates and areas](docs/cadastre_stock.md) — explorer `/stock/`, Sevilla; parcel-grouped records, explicit spatial coverage and no availability inference
- [Synthesis: the answer in one place](docs/synthesis.md)
- [Madrid capital vs corona: the south never recovered](docs/explorations/madrid_municipios.md)
- [Censo Anual probe](docs/explorations/censo_anual_probe.md)
- [SERPAVI probe](docs/explorations/serpavi_probe.md)
- [SERPAVI rents](docs/explorations/serpavi.md)
- [Tourist rents: municipal and provincial cross-sectional associations](docs/explorations/tourist_rents.md)
- [Provincial absorption panel](docs/explorations/panel_provincial.md) — 50 provinces × 2002–2025 (Censo Anual extension): negative everywhere, wild-robust nowhere — SERPAVI finds a weak BCN municipal cross-sectional association (0.16) and finds a positive provincial level association (Spearman 0.53), confounded with coastal demand — municipal rent-vs-sale wedge: DIBA cross-validated (Pearson 0.825), Barcelona yield 3.6% vs corona 4.6% median; rent-vacancy negative on ranks (−0.507) — municipal rents 2011–2024 nationwide (2,555 municipios at 2024), validated vs DIBA; highest-value data candidate
- [Valor de Referencia probe](docs/explorations/valor_referencia_probe.md) — all-municipio MBR/MBC modules, PDF-only, parked (reopens with design B)
- [Construction probe](docs/explorations/construction_probe.md) — licencias/ECB flows, app/PDF access with coverage gaps, parked
- [viv/1000 flatness is a two-group accident](docs/explorations/ratio_ccaa.md) — national ratio +7.8% hides a split: scarcity CCAA falling (−30 Madrid/Cataluña) vs overstock rising (+100–130 interior); price cross −0.39 (n=17, directional) — provincial population 2021–2025 reachable as static CSV; closes the 56945 block (2025 national = mart exact)
- [Barcelona: burdened metropolis, stretched corona](docs/explorations/barcelona_municipios.md)

## Setup and verification

Python 3.11+, `uv`, and `make` are required. Node/npm only for the Evidence app.

```bash
uv sync --group dev
make gates   # lint -> fetch -> build -> analysis -> verify -> audit -> test
```

`make gates` is slow by design: `analysis` re-runs every pure-Python
bootstrap estimator (~30 min alone; `panel_quarterly` is the worst at
~11 min) and `fetch` hits 26 INE endpoints — expect 30–60 min end to
end. CI runs the offline subset only (`make lint` + `make test`); run
the full gate locally before release.

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
| Padrón extranjeros (1998–2022) | Foreign stocks by provincia → `padron_extranjeros`; Bartik shares base |
| INE EM inmigración (2008–2021) | Foreign/Spanish inflows by provincia → `migra_anual`; demand-side data layer |
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
