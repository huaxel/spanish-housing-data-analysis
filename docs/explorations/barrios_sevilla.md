# Sevilla por barrios: IPRA de alquiler basado en fianzas

> Added 2026-10-07. Public EMVISESA/Ayuntamiento SIM ArcGIS layer 179
> (`X/FeatureServer/179`): 108 barrios × IPRA years 2016–2022, 756
> barrio-year rows; 37 cells null. Purchase indicator layer 171
> (`VHS/FeatureServer/171`): 108 barrio rows, `PRO_COL_UNT` populated for
> all, `PRO_UNI_UNT` for 77. Both services were last edited 2023-02-12.
> The purchase layer has no period field and its reference period and
> calculation method are unspecified; treat as an undated SIM snapshot,
> not an annual or directly comparable transaction-price series.

IPRA is **monthly rent €/m² of built area** estimated from AVRA rental-deposit
(fianza) records, not offer prices. Each annual label is a rolling
three-year window; the 2022 update uses 2019–2021 contracts, not only
2022 contracts. It is a mean reference indicator; not interchangeable
with the national SERPAVI median, whose surface/series definitions differ. The SIM documents its
method in [EMVISESA's IPRA materials](https://www.emvisesa.org/wp-content/uploads/2019/12/191219-BASES-REGULADOREAS-PROGRAMA-ALQ-ASE-E-INDICE-DE-PRECIOS-REV06.pdf)
and its [IPRA update](https://www.emvisesa.org/aprobacion-definitiva-de-la-actualizacion-del-ipra/).

## 2022 window: El Carmen 10.83, Valdezorras 3.30 €/m²/month

Among the 102 barrios with a 2022 value, El Carmen is highest (10.83)
and Valdezorras lowest (3.30). 2016 coverage is 99 barrios; availability
varies by year (99–105 valid cells), so null is no published cell, not zero.
Alfalfa moves from 7.52 (2016 window) to 6.80 (2022 window); these are
rolling-window reference levels, not a clean annual growth series.

## Boundary

The purchase layer defines `PRO COL UNT` and `PRO UNI UNT` as unit purchase
prices for collective and unifamiliar housing (€/m² built). It supplies no
underlying observations, counts, or reference period, so we do not infer an
year, transaction cohort, or statistical estimator. In the public layer,
collective-housing values range from 796 €/m² (Torreblanca) to 2,585 €/m²
(Museo); unifamiliar values are missing for 31 barrios. Keep this separate
from the more clearly documented IPRA rent series and from Madrid's
registrar-declared sale-price data. Do not present the SIM purchase snapshot
as current or as an annual transaction series without better methodology.

## Context SIM por barrio: demografía, vivienda y turismo

Added 2026-10-07 from public EMVISESA/Ayuntamiento SIM ArcGIS layers.
Población residente (FeatureServer/26) and households (FeatureServer/30)
provide 108 barrio series for 2015–2021. The vivienda familiar typology
layer (service `ñññ`, layer 2) reports collective/unifamiliar counts and
shares. The joined barrio layer (`TTT`, layer 4) additionally supplies
average age, construction quality (SIM scale 1–9), and built area for each
typology; these variables have no reference year in the fields. Estimated
rehabilitation need comes from `rrr`, layer 101. Housing use/vacancy comes
from `VIVVAC`, layer 133. The last two layers also lack a field identifying
the reference year; last edit timestamps are not treated as data vintage.

`TTT`, layer 4, provides active tourist-purpose dwellings observed on
portals at four snapshots: 2008, February 2021, August 2021, and February
2022, plus registered dwelling/place totals without an explicit date.
SIM's help text describes counts as active portal listings and the pressure
measure as the proportion relative to family dwellings. Missing percentages
are retained; in particular, many barrio-period pressure cells are absent.
These are a short set of snapshots, not a continuous annual trend.

The context tables join on SIM's exact `IDG` barrio key; they do not join
across province-wide municipal sources. A barrio-level accessibility layer
is not published in the app: the public accessibility service (`FeatureServer/109`)
is district-grain, so no barrio interpolation or allocation is made.
For those reasons, the explorer charts population/household series separately
and presents the undated housing and tourist snapshots in separate tables;
none are presented as current price or causal evidence.

## District/zone offer prices, 2024 (separate from transaction data)

The Ayuntamiento's [2025 Statistical Yearbook, table 7.3.9](https://www.sevilla.org/servicios/servicio-de-estadistica/datos-estadisticos/anuarios/anuario-estadistico-de-la-ciudad-de-sevilla-2025/indice/capitulo-vii-mercado-del-suelo)
publishes monthly second-hand home **offer prices** in €/m² from Fotocasa
and Idealista. The [official XLS](https://www.sevilla.org/servicios/servicio-de-estadistica/datos-estadisticos/anuarios/anuario-estadistico-de-la-ciudad-de-sevilla-2025/tablas/capitulo-7/7.3/7-3-9.xls)
was retrieved from the FEMAS mirror after the Ayuntamiento host timed out.
The workbook contains 11 Fotocasa district labels and 17 distinct Idealista
zone labels. They are preserved as separate portal geographies, not joined
to each other or to SIM barrio codes. The resulting `sevilla_oferta_zona`
mart has 336 monthly rows. This measures advertised prices, not closed
transactions; the workbook gives no offer counts or sample sizes.
