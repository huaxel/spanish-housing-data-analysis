# Sevilla: income controls for the physical-stock exploration

## Source assessment — 2026-10-08

The absence of income from the currently retained SIM context layers is not
an absence of public barrio income data. The official SIM organisation
publishes a separate service:

- [Publisher application](https://experience.arcgis.com/experience/fe78eabad62b4e55a6531cb3e2249f1f/).
- [Service item](https://www.arcgis.com/home/item.html?id=c69d0109b84c4c3a8e59762bc233e8cb),
  owned by `Mario_EMVISESA` in the same organisation as the retained SIM layers.
- [Barrio layer metadata](https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/Cualificaci%C3%B3n_de_hogares_residentes_por_Renta_Neta_declarada/FeatureServer/31?f=pjson).
- [Publisher application configuration](https://www.arcgis.com/sharing/rest/content/items/fe78eabad62b4e55a6531cb3e2249f1f/data?f=pjson).

The service title is **Cualificación de hogares residentes por Renta Neta
declarada**. The application legend, widgets `widget_1389` and `widget_1439`,
defines `ING FAM AA` as **Ingresos familiares declarados ejercicio AA (Renta
media neta €)**. Its population/household introduction identifies the INE
Atlas de distribución de renta de hogares among its sources. Preserve this
publisher definition: these are family/household income indicators, not rental
prices, gross salaries, renter-only income or current income.

The barrio layer contains `ID_DIS`, `ID_BAR`, `DIS`, `BAR`, `IDG`, and
`ING_FAM_15` through `ING_FAM_20`. District and municipal layers are separate;
do not substitute them for barrio observations.

Direct checks of the public barrio query on the assessment date found:

- 108 records and 108 unique numeric `(ID_DIS, ID_BAR)` keys.
- Exactly the same keys and barrio/district labels as retained
  `sevilla_sim_poblacion.json`.
- Complete, positive values for the 2015 and 2017–2020 income fields.
- 20 null values in the 2016 income field; null is not zero.

These initial checks established source suitability. The implementation below
now pins production inputs separately and estimates descriptive adjustments;
no central model or affordability result is changed.

## Why not derive income from the municipal study annex?

The [municipal tensioned-market study](https://www.emvisesa.org/wp-content/uploads/2023/06/ESTUDIOESPECIFICODECLARACIONZONASMERCADOTENSIONADO.pdf)
uses net household income from the INE Atlas and reports census-section
observations. Its rental annex is restricted to the identified tensioned
zones, not a complete income sample. A section can appear against more than
one barrio. Do not average the annex's section means, weight income by rented
property counts, or assume section-to-barrio membership is one-to-one.

The SIM barrio layer avoids inventing that crosswalk. Its public service/item
metadata does not explain the section aggregation weights. Treat values as
publisher-reported barrio summaries; do not claim to have independently
reconstructed household-weighted means or to know within-barrio inequality.

## Bounded next implementation

1. Pin the income query, layer metadata and application definition; validate
   field types, reference years, complete downloads and unique keys. Produce
   a separate explorer input without rebuilding the central marts/models.
2. Require exact barrio/district labels in the rent/stock join. Fail on
   duplicate or conflicting keys, retain missingness and report sample losses.
3. Report 2019 and 2020 adjustments separately, rather than selecting the
   year yielding a preferred association. These years relate to the IPRA
   contract window; neither is income at the cadastral snapshot date.
4. For each stock variable/year, rank stock, rent and income on the same
   complete-case sample. Recalculate unadjusted and district-centered
   baselines on that identical sample. Residualize global stock/rent ranks
   against district indicators and the global income rank, then correlate
   residuals. This is a descriptive partial-rank association, not a causal
   effect or an affordability/burden measure. Return null for insufficient
   residual variation.
5. Test tied ranks, missing/constant income, duplicate keys, same-sample
   baselines and a synthetic income-driven association. Obtain independent
   read-only review before promoting results.

Income adjustment cannot resolve the cadastral/IPRA snapshot mismatch,
residential-stock survival, rental-contract selection, within-district location
or unobserved housing quality. See [physical-stock methods](cadastre_stock.md).

## Implemented reproduction

`scripts/fetch_sevilla_income.py` pins the public query, layer metadata and
application definition in `data/input_manifest.json`. It rejects truncated
queries, changed field types/definition/grain, duplicate or conflicting keys,
invalid labels, and nonpositive/nonfinite values. Null income remains null.
The separate `data/processed/income.duckdb` stores source and script hashes;
verification compares every row with the pinned query, not just metadata.

```sh
uv run python scripts/fetch_sevilla_income.py           # fetch, pin, build
uv run python scripts/fetch_sevilla_income.py --offline # rebuild pinned inputs
uv run python scripts/fetch_sevilla_income.py --check   # exact row/source checks
make stock-rent                                        # refresh descriptive report
make verify                                            # recompute and compare report
uv run python -m pytest tests/test_stock_income.py -q
```

The stock page reports income-join exclusions, same-sample global and
district-centered baselines, and district-plus-income partial-rank
associations for both exercises. A constant intradistrict income rank gives
null for the extra adjustment; insufficient residual variation also gives
null, using a relative squared-residual tolerance against pre-projection
variation to avoid correlations of floating-point noise. Empty samples do
not produce association rows. These are neither confidence intervals nor
significance tests. The report hashes both databases, source payloads, helper
and page/code; the main housing marts and estimators remain unchanged.

### District-omission stress test

The page uses a common estimator query for full and omitted samples. Each
variable/year's districts come from its own income-complete sample. Omitting
a district recomputes average global ranks, district means and income
projection on the remaining barrios; it does not reuse full-sample ranks or
slopes. Results include individual omissions, sample sizes, defined/null
adjustment counts and extrema over defined adjustments only. Empty omissions
remain explicit zero-sample/null rows. These extrema are geographic-composition
sensitivity, not confidence intervals or evidence of a causal mechanism.

The report and browser checks include these panels. Offline tests compare
omissions with standalone reduced-sample refits and an independent partial
correlation identity, including ties, unequal district sizes, year/variable
separation and empty/degenerate adjustments.
