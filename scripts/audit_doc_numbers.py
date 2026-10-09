"""Cross-check narrative-doc numbers against audited claim expectations.

The audit pins artifact values, but nothing checked the docs themselves:
synthesis.md quoted pre-fix panel numbers (and README pre-correction
tourist figures) while the audit stayed green. This script inverts the
check: every result-like number in the covered docs must match some
audited claim (expected +/- tol) or an explicit allowlist entry.

Covered docs are the narrative surface (synthesis + README), where
cross-cutting edits drift from script-local fixes. Historical-record
files (review_brief, and struck-through vintage sections) are excluded
by design — they intentionally quote superseded numbers. Add explorer
docs to COVERED_DOCS only with a built allowlist.

Run: make audit-docs (also runs as part of `make audit`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import audit_claims  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

COVERED_DOCS = [
    "docs/synthesis.md",
    "docs/housing_access.md",
    "docs/housing_overburden.md",
    "docs/ecv_joint_scope.md",
    "docs/purchase_scenarios.md",
    "docs/uncertainty.md",
    "docs/cadastre_stock.md",
    "README.md",
    # Estimator docs (recomputed every analysis run — highest drift risk).
    "docs/explorations/panel_adjusted.md",
    "docs/explorations/panel_tourist.md",
    "docs/explorations/panel_saiz.md",
    "docs/explorations/panel_saiz_municipal.md",
    "docs/explorations/saiz_gis_probe.md",
    "docs/explorations/ratio_ccaa.md",
    "docs/explorations/serpavi.md",
    "docs/explorations/tourist_rents.md",
    "docs/explorations/panel_provincial.md",
    "docs/explorations/panel_quarterly.md",
    "docs/explorations/absorption_hypothesis.md",
    "docs/explorations/iv_migration.md",
    # Descriptive docs (mart-derived; change only on rebuild — bulk-verified
    # display tables plus pinned verdict cells).
    "docs/explorations/boom_bust_vs_tightening.md",
    "docs/explorations/credit_cycle.md",
    "docs/explorations/affordability.md",
    "docs/explorations/young_squeeze.md",
    "docs/explorations/madrid_municipios.md",
    "docs/explorations/barcelona_municipios.md",
    "docs/explorations/valencia_municipios.md",
    "docs/explorations/sevilla_municipios.md",
    "docs/explorations/municipios_nacional.md",
    "docs/explorations/barrios_madrid.md",
    "docs/explorations/barrios_sevilla.md",
    "docs/explorations/madrid_vs_valencia.md",
    "docs/explorations/censo_anual_probe.md",
    "docs/explorations/serpavi_probe.md",
    "docs/explorations/identification.md",
    "docs/explorations/cadastre_eras.md",
    "docs/explorations/cadastre_age_rent.md",
    "docs/explorations/cadastre_era_rehab.md",
    "docs/explorations/cadastre_era_quality.md",
    "docs/explorations/cadastre_era_surface.md",
    "docs/explorations/cadastre_vacancy_alignment.md",
    "docs/explorations/cadastre_household_alignment.md",
    "docs/explorations/cadastre_capitals.md",
    "docs/explorations/provincial_coverage.md",
    "docs/explorations/cadastre_province.md",
    "docs/explorations/cadastre_malaga_barrios.md",
    "docs/explorations/cadastre_granada_distritos.md",
    "docs/explorations/capital_geometries.md",
    "docs/explorations/censo_vintage.md",
    "docs/explorations/credit_probe.md",
    "docs/explorations/construction_probe.md",
    "docs/explorations/valor_referencia_probe.md",
    "docs/occupancy_availability.md",
    "docs/explorations/deficit_vivienda.md",
]

# Numbers that are structural, not results: doc/page counts, ports, sizes,
# parameters, census anchors quoted for provenance rather than as findings.
# Each entry: (value, reason). Years 1990-2030 are skipped globally.
ALLOW = {
    "docs/uncertainty.md": [
        (1.96, "normal critical value in existing panel_tourist interval construction"),
        (95.0, "nominal confidence level of normal approximation, not an empirical finding"),
        (2.0, "prespecified candidate grid endpoint (symmetric +/− 2.0 pp), not a result"),
        (0.1, "prespecified candidate grid step, not a result"),
        (41.0, "prespecified candidate count (41 points), not a result"),
        (1999.0, "bootstrap repetitions shared with the published zero-null routine"),
        (0.05, "nominal alpha level of the candidate acceptance mask"),
    ],
    "docs/housing_overburden.md": [
        (40.0, "Eurostat housing-cost overburden threshold, official indicator definition"),
        (60.0, "Eurostat at-risk-of-poverty threshold relative to national median income"),
    ],
    "docs/ecv_joint_scope.md": [
        (0.60, "Official poverty factor, independently defined national income reference"),
        (90.0, "Six age by three poverty by five tenure coordinates, tested complete grid"),
        (50.0, "Predeclared project minimum valid sample persons, not official reliability"),
        (30.0, "Predeclared project minimum represented households; also age boundary"),
        (5.0, "Predeclared project maximum weighted cost loss percent"),
        (18.0, "Person age category boundary"),
        (24.0, "Person age category boundary"),
        (25.0, "Person age category boundary"),
        (29.0, "Person age category boundary"),
        (64.0, "Person age category boundary"),
        (65.0, "Person age category boundary"),
        (1.0, "Newborn reference age -1 maps to zero, official age convention"),
    ],
    "docs/synthesis.md": [
        (1971.0, "construction-era boundary label"),
        (18083692.0, "2011 census household anchor (provenance, not a finding)"),
        (310.0, "municipios with tourist data (coverage count)"),
        (90.0, "affordability reference dwelling size (assumption, methods 2)"),
        (30.0, "'30 pinned sources' doc count"),
        (20.0, "'20 mart tables' (verified: 20 tables in marts.duckdb)"),
        (24.0, "'24 explorations' doc count"),
        (13.0, "'13 years' Santa Coloma starts window"),
        (514.0, "Santa Coloma starts 2012-24 (printed at verify; coverage fact)"),
        (10000.0, "'10k tourist flats' rounded coverage count"),
        (28.0, "'28 in Santa Coloma' coverage count"),
        (18.0, "'in 18y' window length"),
        (1000.0, "per-1000 unit label (viv/1000, dwellings/1000)"),
        (59531.0, "INE table identifier (electricity vacancy)"),
        (2.11, "principales-as-households proxy tolerance (build-time validation)"),
        (650.0, "rounded interior-range low end (pinned exact: Galicia 652.85)"),
        (770.0, "rounded interior-range high end (pinned exact: CyL 770.67)"),
        (0.34, "quoted inside dated correction notes as superseded pre-repair vintage"),
        (1.04, "quoted inside dated correction notes as superseded pre-repair vintage"),
    ],
    "README.md": [
        (90.0, "affordability reference dwelling size (assumption)"),
        (2555.0, "SERPAVI municipio coverage (also a claim; kept as count)"),
        (52.0, "52-provincia coverage count"),
        (2.6, "GIS probe data size (ancillary)"),
        (3.11, "Python version requirement"),
        (30.0, "gate runtime estimates (author-measured, not results)"),
        (26.0, "26 fetch endpoints in the fetch target"),
        (60.0, "gate runtime estimates (author-measured, not results)"),
        (8091.0, "preview dashboard port"),
        (56945.0, "INE table identifier (blocked provincial ECP)"),
        (1000.0, "per-1000 unit label"),
    ],
    "docs/occupancy_availability.md": [
        (452670.0, "MIVAU unsold-new dwellings 2025-12-31, external source fact"),
        (455280.0, "MIVAU unsold-new dwellings 2024-12-31, external source fact"),
        (25443.0, "Catalan vacant-dwelling register 2024-12-31, external source fact"),
        (3237.0, "Valencian register dwellings 2023, external source fact"),
        (1281.0, "Valencian register dwellings 2025, external source fact"),
        (1181.0, "Valencian register dwellings 2026, external source fact"),
        (635919.0, "AEAT IRPF unoccupied Valencian dwellings 2024, external source fact"),
        (150.0, "San Sebastian IBI vacancy surcharge rate, external source fact"),
        (1363.0, "suppressed census sections (persons only), verified file count"),
        (69.0, "RMDVP table-01 months pulled 2020-12..2026-08, verified file count"),
        (543.0, "RMDVP latest-month listed municipalities, verified file count"),
        (785.0, "Andalusian municipalities (official count), coverage denominator"),
    ],
    "docs/explorations/panel_quarterly.md": [
        (999.0, "bootstrap reps parameter"),
        (0.483, "fit R2 diagnostic, printed at runtime"),
        (0.368, "table SE, inference carried by pinned b/wild-p"),
        (0.303, "table SE, inference carried by pinned b/wild-p"),
        (0.049, "table SE, inference carried by pinned b/wild-p"),
        (0.036, "table SE, inference carried by pinned b/wild-p"),
        (0.035, "table SE, inference carried by pinned b/wild-p"),
        (0.039, "table SE, inference carried by pinned b/wild-p"),
        (0.045, "table SE, inference carried by pinned b/wild-p"),
        (0.034, "table SE, inference carried by pinned b/wild-p"),
        (0.032, "table SE, inference carried by pinned b/wild-p"),
        (2.05, "t-statistic derived from pinned b/se"),
        (3.0, "lag-window descriptor (3-6 quarters)"),
        (6.0, "lag-window descriptor (3-6 quarters)"),
        (108.0, "unpublished valor cells (coverage count)"),
    ],
    "docs/explorations/panel_saiz.md": [
        (7.57, "descriptive mean building rate, verified against panel sample"),
        (24.0, "high-constraint group province count"),
        (0.34, "superseded cumulative-vintage reading, marked as rejected"),
        (5.77, "descriptive SD of the above"),
        (26.0, "low-constraint group province count"),
        (0.497, "superseded first-run diagnostic, marked as rejected"),
        (0.093, "superseded first-run SE, marked as rejected"),
        (5.3, "superseded first-run t, marked as rejected"),
        (0.32, "superseded vintage split tau, marked as rejected"),
        (0.41, "superseded vintage split tau, marked as rejected"),
        (0.165, "table SE, inference carried by pinned coef"),
        (0.075, "table SE, inference carried by pinned coef"),
        (0.1, "table SE, inference carried by pinned coef"),
        (0.11, "table SE, inference carried by pinned coef"),
        (0.263, "table SE, inference carried by pinned interaction"),
        (0.096, "table SE, inference carried by pinned OLS tau"),
        (0.042, "table SE, inference carried by pinned OLS tau"),
        (0.163, "table SE, inference carried by pinned interaction"),
    ],
    "docs/explorations/panel_tourist.md": [
        (253.0, "rent-grain municipio coverage"),
        (130.0, "sale-grain municipio coverage"),
        (0.31, "table SE, inference carried by pinned b/wild-p"),
        (0.23, "table SE, inference carried by pinned b/wild-p"),
        (0.04, "fit R2 diagnostic, printed at runtime"),
        (0.05, "fit R2 diagnostic, printed at runtime"),
        (0.03, "fit R2 diagnostic, printed at runtime"),
    ],
    "docs/explorations/panel_saiz_municipal.md": [
        (-0.9, "table t-statistic, inference carried by pinned coef"),
        (-1.0, "table t-statistic, inference carried by pinned coef"),
        (-2.04, "table t-statistic, inference carried by pinned coef"),
        (-2.25, "table t-statistic, inference carried by pinned coef"),
        (0.026, "table SE, inference carried by pinned coef"),
        (0.028, "table SE, inference carried by pinned coef"),
        (0.02, "table SE, inference carried by pinned coef"),
        (0.059, "table SE, inference carried by pinned coef"),
        (0.068, "table SE, inference carried by pinned coef"),
        (0.0397, "Madrid-leg table SE, inference carried by pinned coef"),
        (0.0448, "Madrid-leg table SE, inference carried by pinned coef"),
        (-0.23, "full-range scaling of pinned premise coef, ~15% of pinned mean"),
        (99.4, "GIS join coverage pct, probe validation"),
        (90.0, "DEM grid resolution in metres (method parameter)"),
        (8254.0, "INE municipio code (identifier)"),
        (179.0, "LAU municipio coverage count"),
        (7979.0, "computed land area km2 (coverage fact)"),
        (8025.0, "LAU land area km2 (coverage fact)"),
        (6.7, "worst area error pct (join validation)"),
        (59531.0, "INE table identifier (electricity vacancy)"),
        (3139.0, "municipio coverage count"),
        (7.0, "steep-village count (coverage fact)"),
        (7000.0, "Cercedilla population (coverage fact)"),
    ],
    "docs/explorations/panel_adjusted.md": [
        (-0.25, "CI endpoint of pinned coef"),
        (-0.22, "CI endpoint of pinned coef"),
        (1.47, "table SE, inference carried by pinned b/wild-p"),
        (6.27, "CI endpoint of pinned coef"),
        (95.0, "CI confidence level header"),
        (2999.0, "bootstrap reps parameter"),
        (0.91, "fit R2 diagnostic, printed at runtime"),
        (2.02, "table SE, inference carried by pinned b/wild-p"),
        (37.0, "dropped-rows share (coverage fact)"),
        (112.0, "dropped-rows count (coverage fact)"),
        (306.0, "total-rows count (coverage fact)"),
        (1.7, "table SE, inference carried by pinned b/wild-p"),
        (30.0, "cluster-comfort threshold (method discussion)"),
        (0.043, "table SE, inference carried by pinned b/wild-p"),
        (0.033, "table SE, inference carried by pinned b/wild-p"),
        (0.057, "table SE, inference carried by pinned b/wild-p"),
        (0.055, "table SE, inference carried by pinned b/wild-p"),
        (0.016, "table SE, inference carried by pinned b/wild-p"),
        (0.059, "table SE, inference carried by pinned b/wild-p"),
        (0.058, "table SE, inference carried by pinned b/wild-p"),
        (0.053, "table SE, inference carried by pinned b/wild-p"),
        (0.028, "table SE, inference carried by pinned b/wild-p"),
        (0.041, "table SE, inference carried by pinned b/wild-p"),
    ],
    "docs/explorations/ratio_ccaa.md": [
        (-1.62, "t-statistic derived from pinned r/n"),
        (60.0, "rounded overstock-group low end (pinned exacts nearby)"),
        (650.0, "rounded level descriptor (pinned exact: Extremadura 671.3)"),
        (-37.4, "illustrative 2021-25 change, verified against gated JSON"),
        (-24.4, "illustrative 2021-25 change, verified against gated JSON"),
        (-17.5, "illustrative 2021-25 change, verified against gated JSON"),
        (-16.4, "illustrative 2021-25 change, verified against gated JSON"),
        (-15.9, "illustrative 2021-25 change, verified against gated JSON"),
        (-14.5, "illustrative 2021-25 change, verified against gated JSON"),
        (-11.8, "illustrative 2021-25 change, verified against gated JSON"),
        (441.0, "illustrative 2021 level, verified against gated JSON"),
        (429.0, "illustrative 2025 level, verified against gated JSON"),
        (506.0, "illustrative 2021 level, verified against gated JSON"),
        (490.0, "illustrative 2025 level, verified against gated JSON"),
        (59531.0, "INE table identifier (electricity vacancy)"),
        (3139.0, "municipio coverage count"),
    ],
    "docs/explorations/panel_provincial.md": [
        (999.0, "bootstrap reps parameter"),
        (-2.98, "t-statistic derived from pinned b/se"),
        (49.0, "spec cluster count (design coverage)"),
        (46.0, "spec cluster count (design coverage)"),
        (24.0, "series length in years (design coverage)"),
    ],
    "docs/explorations/absorption_hypothesis.md": [
        (0.51, "display window from gated output, verified 2026-10-07"),
        (0.36, "display window from gated output, verified 2026-10-07"),
        (0.04, "display CI endpoint from gated output, verified 2026-10-07"),
        (0.8, "display CI endpoint from gated output, verified 2026-10-07"),
        (0.08, "display CI endpoint from gated output, verified 2026-10-07"),
        (0.58, "display CI endpoint from gated output, verified 2026-10-07"),
        (47.0, "display sample count from gated output, verified 2026-10-07"),
        (-0.26, "display window from gated output, verified 2026-10-07"),
        (-0.88, "display CI endpoint from gated output, verified 2026-10-07"),
        (0.7, "display CI endpoint from gated output, verified 2026-10-07"),
        (6.0, "display sample count from gated output, verified 2026-10-07"),
        (-0.54, "display window from gated output, verified 2026-10-07"),
        (-0.87, "display CI endpoint from gated output, verified 2026-10-07"),
        (0.14, "display CI endpoint from gated output, verified 2026-10-07"),
        (10.0, "display sample count from gated output, verified 2026-10-07"),
        (-0.46, "display window from gated output, verified 2026-10-07"),
        (-0.74, "display CI endpoint from gated output, verified 2026-10-07"),
        (-0.05, "display CI endpoint from gated output, verified 2026-10-07"),
        (22.0, "display sample count from gated output, verified 2026-10-07"),
        (-0.22, "display window from gated output, verified 2026-10-07"),
        (-0.13, "display CI endpoint from gated output, verified 2026-10-07"),
        (-0.63, "display CI endpoint from gated output, verified 2026-10-07"),
        (0.46, "display CI endpoint from gated output, verified 2026-10-07"),
        (34.0, "display sample count from gated output, verified 2026-10-07"),
        (-0.52, "display CI endpoint from gated output, verified 2026-10-07"),
        (0.13, "display CI endpoint from gated output, verified 2026-10-07"),
        (16.0, "display sample count from gated output, verified 2026-10-07"),
        (-0.12, "display window from gated output, verified 2026-10-07"),
        (0.4, "display CI endpoint from gated output, verified 2026-10-07"),
        (44.0, "display sample count from gated output, verified 2026-10-07"),
        (-0.64, "display CI endpoint from gated output, verified 2026-10-07"),
        (-0.6, "display CI endpoint from gated output, verified 2026-10-07"),
        (-0.24, "display CI endpoint from gated output, verified 2026-10-07"),
        (-0.58, "display CI endpoint from gated output, verified 2026-10-07"),
        (-0.51, "display CI endpoint from gated output, verified 2026-10-07"),
        (-0.16, "display CI endpoint from gated output, verified 2026-10-07"),
        (57.0, "display sample count from gated output, verified 2026-10-07"),
        (153.0, "display sample count from gated output, verified 2026-10-07"),
        (95.0, "CI confidence level header"),
        (-0.06, "superseded pre-2021-window pooled value, marked as historical"),
        (109.0, "superseded pre-2021-window sample size, marked as historical"),
        (-5.0, "illustrative price-fall range endpoint"),
        (-9.0, "illustrative price-fall range endpoint"),
        (-22.0, "illustrative price-fall range endpoint"),
        (-27.0, "illustrative price-fall range endpoint"),
    ],
    "docs/explorations/iv_migration.md": [
        (48.0, "drop-metro spec cluster count (design coverage)"),
        (50.0, "spec cluster count (design coverage)"),
        (0.34, "superseded pre-repair vintage, historical record"),
        (0.48, "superseded pre-repair vintage, historical record"),
        (58.0, "superseded pre-repair first stage, historical record"),
        (1.04, "superseded pre-repair trends spec, historical record"),
        (0.67, "superseded pre-two-way-fix vintage, historical record"),
        (0.22, "superseded pre-repair recovery F, historical record"),
        (0.13, "superseded pre-repair recovery F variant, historical record"),
        (95.0, "CI confidence level header"),
        (2.35, "read-record AR bound, historical record"),
        (150.0, "read-record multiplier illustration, historical record"),
        (99.4, "read-record attenuation arithmetic, historical record"),
        (4.04, "read-record F critical value, historical record"),
        (0.1, "read-record AR bound, historical record"),
        (0.95, "read-record AR bound, historical record"),
        (0.09, "read-record AR bound, historical record"),
        (7.0, "foreign-stock growth multiple (design context)"),
        (52.0, "province-code reference (Ceuta/Melilla 51/52)"),
        (149.0, "F-stat df notation (verified: not a result)"),
        (299.0, "wild-bootstrap reps parameter"),
        (29.0, "wild-bootstrap grid points parameter"),
        (49.0, "F-statistic denominator df"),
    ],
    "docs/explorations/boom_bust_vs_tightening.md": [
        (-46.0, "rounded fall-range endpoint"),
        (69.3, "display spine cell, bulk-verified 2026-10-07"),
        (1641.0, "display spine cell, bulk-verified 2026-10-07"),
        (562.7, "display spine cell, bulk-verified 2026-10-07"),
        (73.3, "display spine cell, bulk-verified 2026-10-07"),
        (23.0, "rounded bust-fall range low end"),
        (46.0, "rounded bust-fall range high end"),
        (-45.5, "display fall pct, bulk-verified 2026-10-07"),
        (-29.2, "display fall pct, bulk-verified 2026-10-07"),
        (49.0, "display per-capita gain, bulk-verified 2026-10-07"),
        (-42.0, "rounded fall range low end"),
        (1147.0, "display eur rise, bulk-verified 2026-10-07"),
        (1009.0, "display eur rise, bulk-verified 2026-10-07"),
        (76.0, "display eur rise, bulk-verified 2026-10-07"),
        (29.4, "display vintage share, bulk-verified 2026-10-07"),
        (42.0, "display vintage share, bulk-verified 2026-10-07"),
        (1590000.0, "display window count, bulk-verified 2026-10-07"),
        (1930000.0, "display window count, bulk-verified 2026-10-07"),
        (-12.3, "display window delta, bulk-verified 2026-10-07"),
        (1740000.0, "display window count, bulk-verified 2026-10-07"),
        (1900000.0, "display window count, bulk-verified 2026-10-07"),
        (1000.0, "per-1000 unit label"),
        (39.0, "display vintage share, bulk-verified 2026-10-07"),
        (33.0, "display vintage share, bulk-verified 2026-10-07"),
        (29.0, "display vintage share, bulk-verified 2026-10-07"),
    ],
    "docs/explorations/credit_cycle.md": [
        (76316.0, "INE table identifier (HPT)"),
        (76317.0, "INE table identifier (HPT)"),
        (76315.0, "INE table identifier (rates)"),
        (313000.0, "display table cell, bulk-verified 2026-10-07"),
        (640000.0, "display table cell, bulk-verified 2026-10-07"),
        (42.0, "display share, bulk-verified 2026-10-07"),
        (46.0, "display share, bulk-verified 2026-10-07"),
        (79.0, "display used-share, bulk-verified 2026-10-07"),
        (149000.0, "display table cell, bulk-verified 2026-10-07"),
        (100000.0, "display table cell, bulk-verified 2026-10-07"),
        (361000.0, "display table cell, bulk-verified 2026-10-07"),
        (126000.0, "display table cell, bulk-verified 2026-10-07"),
        (2.5, "display rate, bulk-verified 2026-10-07"),
        (145000.0, "display table cell, bulk-verified 2026-10-07"),
        (426000.0, "display table cell, bulk-verified 2026-10-07"),
        (3.3, "display rate, bulk-verified 2026-10-07"),
        (28.4, "display share, bulk-verified 2026-10-07"),
        (32.9, "mortgaged-household share 2011, arithmetic from pinned counts"),
        (34.1, "display share, bulk-verified 2026-10-07"),
        (34.8, "display share, bulk-verified 2026-10-07"),
        (36.7, "display share, bulk-verified 2026-10-07"),
        (88.7, "display table cell, bulk-verified 2026-10-07"),
        (69.3, "display table cell, bulk-verified 2026-10-07"),
        (-46.0, "display fall pct, bulk-verified 2026-10-07"),
        (-42.0, "display fall pct, bulk-verified 2026-10-07"),
        (-32.0, "display fall pct, bulk-verified 2026-10-07"),
        (2013.0, "CGPJ launch series start year"),
        (2007.0, "CGPJ foreclosure series start year"),
        (2020.0, "moratorium quarter year"),
        (2.0, "2020Q2 quarter label"),
        (30.0, "Cadiz mortgage launches 2024Q4, pinned by additivity"),
        (103.0, "Cadiz rent launches 2024Q4, pinned by additivity"),
        (8.0, "Cadiz other launches 2024Q4, pinned by additivity"),
        (50.0, "CGPJ province coverage (no Ceuta/Melilla rows)"),
        (3850.0, "launch mart rows, pinned in claims"),
        (2024.0, "Cadiz anchor year"),
        (4.0, "2024Q4 quarter label"),
        (95.6, "Girona launch rate, pinned in claims"),
        (13.1, "Jaen launch rate, pinned in claims"),
        (42.4, "national launch rate, pinned in claims"),
        (0.28, "launch-rent pearson, pinned in claims"),
        (0.359, "launch-rent spearman, pinned in claims"),
    ],
    "docs/explorations/affordability.md": [
        (2071.0, "display table cell, bulk-verified 2026-10-07"),
        (30045.0, "display table cell, bulk-verified 2026-10-07"),
        (6.2, "display table cell, bulk-verified 2026-10-07"),
        (26154.0, "display table cell, bulk-verified 2026-10-07"),
        (1641.0, "display table cell, bulk-verified 2026-10-07"),
        (30690.0, "display table cell, bulk-verified 2026-10-07"),
        (4.81, "display table cell, bulk-verified 2026-10-07"),
        (1914.0, "display table cell, bulk-verified 2026-10-07"),
        (38994.0, "display table cell, bulk-verified 2026-10-07"),
        (4.42, "display table cell, bulk-verified 2026-10-07"),
        (6.58, "display extreme, bulk-verified 2026-10-07"),
        (6.21, "display extreme, bulk-verified 2026-10-07"),
        (5.15, "display table cell, bulk-verified 2026-10-07"),
        (90.0, "affordability reference dwelling size (assumption)"),
        (47000.0, "display income level, bulk-verified 2026-10-07"),
        (3686.0, "display price level, bulk-verified 2026-10-07"),
    ],
    "docs/explorations/young_squeeze.md": [
        (85.0, "age-band label (85-99 singles)"),
        (99.0, "age-band label (85-99 singles)"),
        (-15.0, "display window pct, bulk-verified 2026-10-07"),
        (-41.0, "display window pct, bulk-verified 2026-10-07"),
        (-2.5, "display window pct, bulk-verified 2026-10-07"),
        (-1.9, "display window pct, bulk-verified 2026-10-07"),
        (19.1, "display share, bulk-verified 2026-10-07"),
        (12.6, "display share, bulk-verified 2026-10-07"),
        (8.4, "display shift pct, bulk-verified 2026-10-07"),
        (10.1, "display shift pct, bulk-verified 2026-10-07"),
        (1.4, "display shift pct, bulk-verified 2026-10-07"),
        (-0.3, "display shift pct, bulk-verified 2026-10-07"),
        (28.2, "display share, bulk-verified 2026-10-07"),
        (35.3, "display share, bulk-verified 2026-10-07"),
        (34.1, "display share, bulk-verified 2026-10-07"),
        (165000.0, "display puzzle count, bulk-verified 2026-10-07"),
        (22000.0, "display puzzle count, bulk-verified 2026-10-07"),
        (160000.0, "display puzzle count, bulk-verified 2026-10-07"),
        (162000.0, "display puzzle count, bulk-verified 2026-10-07"),
        (171000.0, "display puzzle count, bulk-verified 2026-10-07"),
        (37000.0, "display puzzle count, bulk-verified 2026-10-07"),
        (4000.0, "display puzzle count, bulk-verified 2026-10-07"),
        (33000.0, "display puzzle count, bulk-verified 2026-10-07"),
        (8000.0, "display puzzle count, bulk-verified 2026-10-07"),
    ],
    "docs/explorations/madrid_vs_valencia.md": [
        (46.0, "rounded province descriptor (pinned exact: Castellon 46.7)"),
        (48000.0, "display share input, verified 2026-10-07 (Valencia tourist 2025)"),
        (1120000.0, "display share input, verified 2026-10-07 (Valencia non-primary 2025)"),
        (29000.0, "display tourist level, verified 2026-10-07 (Balears 2020)"),
        (37.0, "display share, bulk-verified 2026-10-07 (Gandia secundaria)"),
        (1.13, "display ratio, bulk-verified 2026-10-07 (Madrid viv/hogar 2025)"),
        (614.0, "display ratio, bulk-verified 2026-10-07 (Valencia 2025)"),
    ],
    "docs/explorations/serpavi.md": [
        (71.0, "source file size in MB (coverage fact)"),
        (716889.0, "mart row count (coverage fact)"),
        (7331.0, "municipio coverage count"),
        (80.0, "typical contract size assumption (methods)"),
        (200.0, "historical misquote and coverage threshold (see reason)"),
        (3.9, "superseded quartile, marked as corrected"),
    ],
    "docs/explorations/censo_anual_probe.md": [
        (56945.0, "INE table identifier (blocked provincial ECP)"),
        (56940.0, "INE table identifier (ECP population)"),
        (68519.0, "INE table identifier (censo anual range start)"),
        (68526.0, "INE table identifier (censo anual range end)"),
        (68521.0, "INE table identifier (static CSV source)"),
        (52.0, "province coverage count"),
        (47400798.0, "probe input value (CSV side of seam check)"),
        (2470000.0, "source row count (coverage fact)"),
        (208.0, "source file size in MB (coverage fact)"),
        (1071.0, "pre-extension mart row count (coverage fact)"),
        (1275.0, "post-extension mart row count (coverage fact)"),
        (0.033, "probe seam pct, arithmetic from pinned mart side and CSV input"),
    ],
    "docs/explorations/serpavi_probe.md": [
        (37000000.0, "rental observations count (coverage fact)"),
        (403.0, "HTTP status code (access note)"),
        (200.0, "HTTP status code (access note)"),
        (8894.0, "municipio coverage count"),
        (52.0, "province coverage count"),
        (25.0, "CCAA coverage count"),
        (10543.0, "distrito coverage count"),
        (7332.0, "district-mart municipio count"),
        (10511.0, "published district rows incl. fully-suppressed"),
        (36294.0, "seccion coverage count"),
        (280.0, "column count (coverage fact)"),
        (75.0, "percentile measure label"),
        (1722.0, "municipio coverage count (2011)"),
        (85.0, "typical contract size assumption"),
        (1160.0, "validation illustration, arithmetic from stated rent and size"),
        (1147.0, "validation illustration, DIBA 2024 rent (verified pattern)"),
        (1700.0, "municipio coverage count (backfill)"),
    ],
    "docs/explorations/identification.md": [
        (24322.0, "INE table identifier (EM flows)"),
        (137.0, "nacionalidad coverage count"),
        (131000.0, "memo illustration from script output, reviewed 2026-10-07"),
        (104000.0, "memo illustration from script output, reviewed 2026-10-07"),
        (91000.0, "memo illustration from script output, reviewed 2026-10-07"),
        (205000.0, "memo illustration from script output, reviewed 2026-10-07"),
        (51000.0, "memo illustration from script output, reviewed 2026-10-07"),
        (348.0, "memo illustration from script output, reviewed 2026-10-07"),
        (175.0, "memo illustration from script output, reviewed 2026-10-07"),
        (52.0, "province coverage count"),
        (8.53, "method threshold constant (documented derivation)"),
        (90.0, "DEM grid resolution in metres (method parameter)"),
        (103.0, "tile count (coverage fact)"),
        (180.0, "resolution variant label (method parameter)"),
    ],
    "docs/explorations/cadastre_eras.md": [
        (107.0, "SIM barrios with housing-bearing records, not a result"),
        (57723.0, "cadastre BU records with housing properties, not a result"),
        (58723.0, "total cadastre BU records before filter, coverage fact"),
        (323736.0, "dated housing properties, not a result"),
        (323737.0, "total declared housing properties, coverage fact"),
        (1951.0, "era boundary, not a result"),
        (1970.0, "era boundary, not a result"),
        (1971.0, "era boundary, not a result"),
        (1991.0, "era boundary, not a result"),
        (2010.0, "era boundary, not a result"),
        (1950.0, "era boundary, not a result"),
        (2011.0, "era boundary, not a result"),
        (1943.0, "La Barzola median year"),
        (58.9, "La Barzola pre-1951 share"),
        (1945.0, "Ciudad Jardin median year"),
        (66.5, "Ciudad Jardin and El Prado pre-1951 share"),
        (6.8, "global pre-1951 era share, verified in audit"),
        (28.8, "global 1951-1970 era share, verified in audit"),
        (37.7, "global 1971-1990 era share, verified in audit"),
        (22.1, "global 1991-2010 era share, verified in audit"),
        (4.7, "global 2011+ era share, verified in audit"),
        (1000.0, "excluded non-housing records, coverage fact"),
        (3500.0, "excluded properties, coverage fact"),
    ],
    "docs/explorations/cadastre_age_rent.md": [
        (102.0, "IPRA-2022 non-null barrio coverage count, not a result"),
        (5061.0, "Valdezorras cadastral barrio code"),
        (33.0, "oldest/newest tercile barrio count"),
        (35.0, "middle tercile barrio count"),
        (7.47, "oldest tercile median rent, display context (mean pinned in claims)"),
        (7.4, "middle tercile median rent, display context (mean pinned in claims)"),
        (6.69, "newest tercile median rent, display context (mean pinned in claims)"),
        (6.77, "La Barzola extreme display value, verified in artifact"),
        (7.64, "Ciudad Jardin extreme display value, verified in artifact"),
        (6.83, "Amate extreme display value, verified in artifact"),
        (6.1, "Bellavista extreme display value, verified in artifact"),
        (4.17, "Elcano-Bermejales extreme display value, verified in artifact"),
        (4.96, "Colores, Entreparques extreme display value, verified in artifact"),
        (1929.0, "Heliopolis median construction year"),
        (1943.0, "La Barzola median construction year"),
        (1945.0, "Ciudad Jardin median construction year"),
        (1951.0, "era boundary and El Tardon-El Carmen median year"),
        (1957.0, "Amate median construction year"),
        (1970.0, "era boundary"),
        (1971.0, "era boundary and tercile range endpoint"),
        (1978.0, "tercile range endpoint median year"),
    ],
    "docs/explorations/cadastre_era_rehab.md": [
        (108.0, "SIM barrio row coverage, not a result"),
        (5061.0, "Valdezorras cadastral barrio code"),
        (33.0, "oldest/newest tercile barrio count"),
        (35.0, "middle tercile barrio count"),
        (53.0, "middle tercile median rehab, display context (mean pinned in claims)"),
        (14.0, "newest tercile median rehab, display context (mean pinned in claims)"),
        (1943.0, "tercile range endpoint and La Barzola median year"),
        (1971.0, "tercile range endpoint and era boundary"),
        (1978.0, "tercile range endpoint"),
        (99.0, "SIM rehab level label (99-100% band)"),
        (100.0, "SIM rehab level label (99-100% band)"),
    ],
    "docs/explorations/cadastre_era_quality.md": [
        (30.0, "null-barrio count for unifamiliar coverage, not a result"),
        (3.2, "observed calidad_colectiva range low endpoint"),
        (99.0, "SIM rehab band label (99-100%)"),
        (100.0, "SIM rehab band label (99-100%)"),
        (3.56, "San Bernardo extreme display value, verified in artifact"),
        (3.59, "Tabladilla extreme display value, verified in artifact"),
        (3.69, "La Buhaira extreme display value, verified in artifact"),
        (3.75, "El Porvenir extreme display value, verified in artifact"),
        (6.99, "Las Letanias extreme display value, verified in artifact"),
        (6.98, "El Carmen extreme display value, verified in artifact"),
        (6.93, "San Pablo extreme display value, verified in artifact"),
        (1943.0, "La Barzola median construction year"),
        (1950.0, "El Prado median construction year"),
        (1963.0, "El Carmen and San Pablo median construction year"),
        (1966.0, "Poligono Norte median construction year"),
        (1972.0, "Las Letanias median construction year"),
        (1979.0, "La Buhaira median construction year"),
        (1980.0, "El Porvenir median construction year"),
        (1981.0, "Tabladilla median construction year"),
    ],
    "docs/explorations/cadastre_era_surface.md": [
        (1951.0, "era boundary label"),
        (1971.0, "era boundary label"),
        (50321.0, "records with floor and properties, coverage fact"),
        (81757.0, "largest record gross floor, coverage fact"),
        (82000.0, "rounded top-of-range descriptor (82k)"),
        (219.0, "Pre-1951 median floor display, verified in artifact"),
        (200.0, "1951-1970 median floor display, verified in artifact"),
        (263.0, "1971-1990 median floor display, verified in artifact"),
        (224.0, "1991-2010 median floor display, verified in artifact"),
        (12702.0, "Q1 record count, coverage"),
        (12481.0, "Q2 record count, coverage"),
        (12569.0, "Q3 record count, coverage"),
        (12568.0, "Q4 record count, coverage"),
        (12811.0, "Q1 properties, coverage"),
        (13613.0, "Q2 properties, coverage"),
        (41472.0, "Q3 properties, coverage"),
        (259340.0, "Q4 properties, coverage"),
        (1965.0, "Q1 median year, display context"),
        (1972.0, "Q2 median year, display context"),
        (1964.0, "Q3 median year, display context"),
        (1978.0, "Q4 median year, display context"),
        (1951.0, "era boundary"),
        (1971.0, "era boundary"),
        (20.6, "Q1 pre-1951 share, matrix cell"),
        (21.5, "Q2 pre-1951 share, matrix cell"),
        (19.3, "Q3 pre-1951 share, matrix cell"),
        (3.2, "Q4 pre-1951 share, matrix cell"),
        (0.7, "Q1 2011+ share, matrix cell"),
        (1.7, "Q2/Q3 2011+ share, matrix cell"),
        (5.6, "Q4 2011+ share, matrix cell"),
    ],
    "docs/explorations/cadastre_vacancy_alignment.md": [
        (41091.0, "Sevilla municipality census code"),
        (3139.0, "municipality count on the vacancia page, coverage fact"),
        (156.0, "city total gap in dwelling units, coverage fact"),
        (3500.0, "properties outside SIM barrio geometry, coverage fact"),
        (1007.0, "San Gil barrio code (lacks SIM deshabitadas value)"),
        (2023.0, "La Barzola barrio code (lacks SIM deshabitadas value)"),
        (2034.0, "Santa Justa barrio code (lacks SIM deshabitadas value)"),
        (5054.0, "Bami barrio code (lacks SIM deshabitadas value)"),
        (5058.0, "El Prado barrio code (lacks SIM deshabitadas value)"),
        (10101.0, "Barriada de Pineda barrio code (lacks SIM deshabitadas value)"),
        (10104.0, "Heliopolis barrio code (lacks SIM deshabitadas value)"),
        (5061.0, "Valdezorras cadastral barrio code"),
        (23.45, "max SIM-own unoccupied rate, display context (mean pinned)"),
        (22.49, "max cadastre-referenced unoccupied rate, display context"),
        (0.31, "min unoccupied rate under both denominators"),
        (0.665, "min barrio denominator ratio, display context (median pinned)"),
        (1.257, "max barrio denominator ratio, display context (median pinned)"),
    ],
    "docs/explorations/cadastre_household_alignment.md": [
        (5061.0, "Valdezorras cadastral barrio code"),
        (59543.0, "INE municipal households table code"),
        (60500.0, "rounded property surplus descriptor (exact 60534 from pinned totals)"),
        (700.0, "small-barrio property threshold, coverage context"),
        (0.6203, "Alfalfa extreme display value, verified in artifact"),
        (0.6564, "El Plantinar extreme display value, verified in artifact"),
        (0.6736, "Bami extreme display value, verified in artifact"),
        (0.6821, "San Bartolome extreme display value, verified in artifact"),
        (1.0626, "Aeropuerto extreme display value, verified in artifact"),
        (1.0506, "El Prado extreme display value, verified in artifact"),
        (1.0305, "La Barzola extreme display value, verified in artifact"),
        (1.0247, "La Corza extreme display value, verified in artifact"),
    ],
    "docs/explorations/cadastre_capitals.md": [
        (1951.0, "era boundary label"),
        (1971.0, "era boundary label"),
        (50321.0, "Sevilla benchmark record count, coverage fact"),
        (35.0, "rounded peak-band low endpoint"),
        (42.0, "rounded peak-band high endpoint"),
        (109582.0, "total capital BU records parsed, coverage fact"),
        (91232.0, "housing-bearing capital records, coverage fact"),
        (33.6, "Malaga archive size in MB, coverage fact"),
        (14.2, "Granada archive size in MB, coverage fact"),
        (25.2, "Cordoba archive size in MB, coverage fact"),
        (0.0, "Malaga/Sevilla missing-year share, coverage fact"),
        (0.02, "Granada missing-year share, coverage fact"),
        (0.1, "Cordoba missing-year share, coverage fact"),
        (29900.0, "Malaga CAT municipality code"),
        (29067.0, "Malaga INE municipality code"),
        (18900.0, "Granada CAT municipality code"),
        (18087.0, "Granada INE municipality code"),
        (14900.0, "Cordoba CAT municipality code"),
        (14021.0, "Cordoba INE municipality code"),
        (41900.0, "Sevilla CAT municipality code"),
        (41091.0, "Sevilla INE municipality code"),
        (4.1, "Malaga/Cordoba pre-1951 share, matrix cell"),
        (6.5, "Granada pre-1951 share, matrix cell"),
        (6.7, "Sevilla pre-1951 share, pinned in era-doc claims"),
        (22.6, "Malaga 1951-1970 share, matrix cell"),
        (24.5, "Granada 1951-1970 share, matrix cell"),
        (26.6, "Cordoba 1951-1970 share, matrix cell"),
        (28.6, "Malaga 1991-2010 and Sevilla 1951-1970 shares, matrix cells"),
        (23.0, "Granada 1991-2010 share, matrix cell"),
        (27.8, "Cordoba 1991-2010 share, matrix cell"),
        (22.1, "Sevilla 1991-2010 share, matrix cell"),
        (5.2, "Malaga 2011+ share, matrix cell"),
        (3.9, "Granada 2011+ share, matrix cell"),
        (4.7, "Sevilla 2011+ share, pinned in era-doc claims"),
        (34.6, "Cordoba post-1990 combined share, derived descriptor"),
        (227.0, "median floor range low endpoint, display context"),
        (256.0, "median floor range high endpoint, display context"),
    ],
    "docs/explorations/provincial_coverage.md": [
        (267.0, "rounded total MB descriptor (exact bytes pinned in claims)"),
        (266.9, "rounded total MB descriptor (exact bytes pinned in claims)"),
        (13.3, "Sevilla share of provincial bytes, computed descriptor"),
        (1.5, "rounded median archive MB, coverage fact"),
        (190.0, "rounded minimum archive kB descriptor"),
        (35.4, "Sevilla archive MB display (exact bytes pinned in claims)"),
        (14.9, "Dos Hermanas archive MB display (exact bytes pinned)"),
        (11.0, "Alcala archive MB display, verified in artifact"),
        (8.6, "Carmona archive MB display, verified in artifact"),
        (7.1, "Utrera archive MB display, verified in artifact"),
        (6.8, "Los Palacios archive MB display, verified in artifact"),
        (5.4, "La Rinconada archive MB display, verified in artifact"),
        (5.0, "Coria del Rio archive MB display, verified in artifact"),
        (4.9, "Ecija/Mairena del Aljarafe archive MB display, verified in artifact"),
        (4.8, "Moron/Lebrija archive MB display, verified in artifact"),
        (4.5, "Mairena del Alcor archive MB display, verified in artifact"),
        (4.4, "Arahal/Marchena archive MB display, verified in artifact"),
        (1650.0, "records-per-MB rate estimate from the Sevilla pilot"),
        (440000.0, "rough province record-count estimate, explicitly approximate"),
        (25.0, "parse-time estimate low end, explicitly approximate"),
        (35.0, "parse-time estimate high end, explicitly approximate"),
        (73.0, "rounded combined capitals archive MB descriptor"),
        (30.0, "rounded parse-time descriptor, explicitly approximate"),
        (41900.0, "Sevilla CAT municipality code"),
        (41038.0, "Dos Hermanas CAT municipality code"),
        (41004.0, "Alcala de Guadaira CAT municipality code"),
        (41024.0, "Carmona CAT municipality code"),
        (41095.0, "Utrera CAT municipality code"),
        (41069.0, "Los Palacios CAT municipality code"),
        (41081.0, "La Rinconada CAT municipality code"),
        (41034.0, "Coria del Rio CAT municipality code"),
        (41039.0, "Ecija CAT municipality code"),
        (41059.0, "Mairena del Aljarafe CAT municipality code"),
        (41065.0, "Moron de la Frontera CAT municipality code"),
        (41053.0, "Lebrija CAT municipality code"),
        (41058.0, "Mairena del Alcor CAT municipality code"),
        (41011.0, "Arahal CAT municipality code"),
        (41060.0, "Marchena CAT municipality code"),
    ],
    "docs/explorations/cadastre_province.md": [
        (25829.0, "UTM zone 29N EPSG code, CRS provenance label"),
        (1951.0, "era boundary label"),
        (1971.0, "era boundary label"),
        (28.6, "Sevilla 1951-1970 share, comparison column (province share pinned)"),
        (22.1, "Sevilla 1991-2010 share, comparison column (province share pinned)"),
        (512758.0, "parsed BU records incl. non-residential, coverage fact"),
        (2.39, "El Madrono display value, verified in artifact"),
        (2.15, "El Ronquillo display value, verified in artifact"),
        (42.0, "25829-zone municipality count, verified in artifact"),
    ],
    "docs/explorations/capital_geometries.md": [
        (4.0, "CC BY-SA license version, external source fact"),
        (419.0, "Malaga official barrio polygon count, external source fact"),
        (1.8, "Malaga barrio GeoJSON size in MB, external source fact"),
        (8.0, "Granada municipal district count, external source fact"),
        (101.0, "Granada AA.VV. zone count, external source fact"),
        (38.8, "Cordoba distritos GeoJSON size in kB, external source fact"),
        (25830.0, "cadastre pilot CRS code, method context"),
        (4326.0, "alternative CRS code offered by the Malaga portal"),
    ],
    "docs/explorations/cadastre_malaga_barrios.md": [
        (1951.0, "era boundary label"),
        (1971.0, "era boundary label"),
        (28.6, "municipal 1991-2010 share, comparison column (barrio share pinned)"),
        (419.0, "official Malaga barrio count, external source fact"),
        (51455.0, "Malaga BU records parsed, coverage fact"),
        (51411.0, "exactly matched Malaga records, coverage fact"),
        (27.0, "cross-boundary Malaga records, coverage fact"),
        (14.0, "outside-polygon Malaga records, coverage fact"),
        (3.0, "partly-outside Malaga records, coverage fact"),
        (196.0, "excluded-record properties, coverage fact"),
        (0.1, "max era-share drift from excluded records, display context"),
        (1900.0, "Finca La Concepcion median year, display context"),
        (1925.0, "Olias median year, display context"),
        (1936.0, "diseminado median year, display context"),
        (2023.0, "Torre del Rio median year, display context"),
        (2024.0, "Pizarrillo median year, display context"),
        (2025.0, "new-sector median year, display context"),
        (100.0, "single-era barrio share label"),
    ],
    "docs/explorations/cadastre_granada_distritos.md": [
        (1632.0, "EPSG transformation code, method provenance"),
        (1951.0, "era boundary label"),
        (1971.0, "era boundary label"),
        (0.02, "missing-date share, coverage fact"),
        (0.0, "Norte pre-1951 share label"),
        (20274.0, "exactly matched Granada records, coverage fact"),
        (20277.0, "Granada BU records parsed, coverage fact"),
        (1960.0, "Albayzin median year (pinned in claims), display context"),
        (1970.0, "Centro median year, display context"),
        (1974.0, "Ronda/Zaidin median year, display context"),
        (1976.0, "Norte median year, display context"),
        (1981.0, "Chana median year, display context"),
        (1984.0, "Beiro/Genil median year, display context"),
        (5218.0, "Albayzin properties, display context"),
        (15624.0, "Centro properties, display context"),
        (29121.0, "Ronda properties, display context"),
        (22735.0, "Zaidin properties, display context"),
        (12187.0, "Norte properties, display context"),
        (13637.0, "Chana properties, display context"),
        (26532.0, "Beiro properties, display context"),
        (15763.0, "Genil properties, display context"),
        (2.8, "Ronda/Beiro pre-1951 shares, display context"),
        (0.5, "Zaidin/Chana pre-1951 shares, display context"),
        (4.3, "Norte 2011+ share, display context"),
        (2.3, "Chana 2011+ share, display context"),
        (5.4, "Beiro 2011+ share, display context"),
        (2.1, "Genil 2011+ share, display context"),
        (1.8, "Genil pre-1951 share, display context"),
        (2.0, "Centro 2011+ share, display context"),
        (4.1, "Ronda 2011+ share, display context"),
        (1.2, "Albayzin 2011+ share, display context"),
    ],
    "docs/explorations/censo_vintage.md": [
        (2.8, "post-bust 2011-2020 additions share of total stock"),
        (85.0, "descriptive threshold for primary absorption in urban centers"),
    ],
    "docs/explorations/credit_probe.md": [
        (37.0, "historical caja count (literature fact)"),
        (1989.0, "liberalization year (historical fact)"),
    ],
    "docs/explorations/construction_probe.md": [
        (200.0, "HTTP status code (access note)"),
        (30293.0, "INE table identifier (construction production)"),
    ],
    "docs/explorations/valencia_municipios.md": [
        (2903.0, "INE DPOP table id (structural)"),
        (266.0, "municipio coverage count"),
        (159.0, "municipios with 2024 rent (coverage fact)"),
        (798000.0, "display table cell, spot-verified 2026-10-07"),
        (81000.0, "display table cell, spot-verified 2026-10-07"),
        (91000.0, "display table cell, spot-verified 2026-10-07"),
        (79000.0, "display table cell, spot-verified 2026-10-07"),
        (83000.0, "display table cell, spot-verified 2026-10-07"),
        (66000.0, "display table cell, spot-verified 2026-10-07"),
        (73000.0, "display table cell, spot-verified 2026-10-07"),
        (49.0, "display table pct, spot-verified 2026-10-07"),
        (59.0, "display table pct, spot-verified 2026-10-07"),
        (33.0, "display table pct, spot-verified 2026-10-07"),
    ],
    "docs/explorations/sevilla_municipios.md": [
        (2895.0, "INE DPOP table id (structural)"),
        (106.0, "municipio coverage count"),
        (57.0, "municipios with 2024 rent (coverage fact)"),
        (91.0, "municipios with 2011 vacancy (coverage fact)"),
        (703000.0, "display table cell, spot-verified 2026-10-07"),
        (689000.0, "display table cell, spot-verified 2026-10-07"),
        (127000.0, "display table cell, spot-verified 2026-10-07"),
        (143000.0, "display table cell, spot-verified 2026-10-07"),
        (73000.0, "display table cell, spot-verified 2026-10-07"),
        (77000.0, "display table cell, spot-verified 2026-10-07"),
        (42000.0, "display table cell, spot-verified 2026-10-07"),
        (48000.0, "display table cell, spot-verified 2026-10-07"),
        (31.0, "display table pct, spot-verified 2026-10-07"),
        (27.0, "display table pct, spot-verified 2026-10-07"),
        (22.0, "display table pct, spot-verified 2026-10-07"),
        (28.0, "display table pct, spot-verified 2026-10-07"),
    ],
    "docs/explorations/municipios_nacional.md": [
        (52.0, "DPOP municipal tables (structural)"),
        (2270.0, "rows with 2011 vacancy (coverage fact)"),
    ],
    "docs/explorations/barrios_madrid.md": [
        (504020100060.0, "Banco de datos series identifier"),
        (153.0, "barrio coverage count"),
        (8721.0, "fetched rows (coverage fact)"),
        (3546.0, "suppressed nulls (coverage fact)"),
        (15.0, "bank publication threshold (cases)"),
        (7.4, "display ratio, spot-verified 2026-10-07"),
        (96.0, "source-reported coverage range lower bound"),
        (98.0, "source-reported coverage range upper bound"),
        (46.0, "barrio number in barrio label, structural name"),
        (121.0, "barrio number in barrio label, structural name"),
        (172.0, "barrio number in barrio label, structural name"),
    ],
    "docs/explorations/barrios_sevilla.md": [
        (179.0, "SIM IPRA ArcGIS feature-layer identifier"),
        (171.0, "SIM purchase ArcGIS feature-layer identifier"),
        (108.0, "barrio coverage count, pinned in claims"),
        (756.0, "barrio-year rows, pinned in claims"),
        (37.0, "unpublished cells, pinned in claims"),
        (99.0, "2016 non-null coverage, pinned by dataset"),
        (105.0, "upper annual non-null coverage, dataset fact"),
        (102.0, "2022 non-null coverage, pinned by dataset"),
        (10.83, "2022 highest published IPRA, pinned in claims"),
        (3.30, "2022 lowest published IPRA, pinned in claims"),
        (7.52, "Alfalfa 2016 IPRA, verified against mart"),
        (6.80, "Alfalfa 2022 IPRA, pinned in claims"),
        (77.0, "purchase indicator non-null coverage, pinned in claims"),
        (31.0, "missing unifamiliar purchase values, pinned in claims"),
        (796.0, "lowest collective purchase indicator, pinned in claims"),
        (2585.0, "highest collective purchase indicator, pinned in claims"),
        (26.0, "SIM population ArcGIS layer identifier"),
        (30.0, "SIM households ArcGIS layer identifier"),
        (2.0, "SIM typology ArcGIS layer identifier"),
        (4.0, "SIM joined barrio ArcGIS layer identifier"),
        (101.0, "SIM rehabilitation ArcGIS layer identifier"),
        (133.0, "SIM housing-use ArcGIS layer identifier"),
        (109.0, "SIM accessibility district-layer identifier"),
        (2008.0, "SIM tourist-listing snapshot year"),
        (2015.0, "explicit SIM demographic-series start year"),
        (2021.0, "explicit SIM demographic-series end and tourist snapshot year"),
        (2022.0, "SIM tourist-listing snapshot year"),
        (1.0, "SIM construction-quality scale lower bound"),
        (9.0, "SIM construction-quality scale upper bound"),
    ],
    "docs/explorations/valor_referencia_probe.md": [
        (25.0, "publication day-of-month (administrative fact)"),
        (8131.0, "municipio coverage count"),
        (113.0, "PDF page count (coverage fact)"),
        (1.9, "PDF size in MB (coverage fact)"),
        (210.0, "thousands fragment of example value (see 5210)"),
        (5210.0, "format example value (documentation, not a result)"),
        (37.8, "format example value (documentation, not a result)"),
    ],
    "docs/explorations/madrid_municipios.md": [
        (3845.0, "display table cell, spot-verified 2026-10-07 (Madrid row fully checked)"),
        (2432.0, "display table cell, spot-verified 2026-10-07 (Madrid row fully checked)"),
        (3631.0, "display table cell, spot-verified 2026-10-07"),
        (2412.0, "display table cell, spot-verified 2026-10-07"),
        (32.0, "display table pct, spot-verified 2026-10-07"),
        (3644.0, "display table cell, spot-verified 2026-10-07"),
        (2370.0, "display table cell, spot-verified 2026-10-07"),
        (4437.0, "display table cell, spot-verified 2026-10-07"),
        (22.0, "display table pct, spot-verified 2026-10-07"),
        (3520.0, "display table cell, spot-verified 2026-10-07"),
        (2529.0, "display table cell, spot-verified 2026-10-07"),
        (4327.0, "display table cell, spot-verified 2026-10-07"),
        (23.0, "display table pct, spot-verified 2026-10-07"),
        (2872.0, "display table cell, spot-verified 2026-10-07"),
        (1542.0, "display table cell, spot-verified 2026-10-07"),
        (2812.0, "display table cell, spot-verified 2026-10-07"),
        (-2.0, "display table pct, spot-verified 2026-10-07"),
        (3018.0, "display table cell, spot-verified 2026-10-07"),
        (1523.0, "display table cell, spot-verified 2026-10-07"),
        (2869.0, "display table cell, spot-verified 2026-10-07"),
        (-5.0, "display table pct, spot-verified 2026-10-07"),
        (2696.0, "display table cell, spot-verified 2026-10-07"),
        (1326.0, "display table cell, spot-verified 2026-10-07"),
        (2644.0, "display table cell, spot-verified 2026-10-07"),
        (2801.0, "display table cell, spot-verified 2026-10-07"),
        (1391.0, "display table cell, spot-verified 2026-10-07"),
        (2514.0, "display table cell, spot-verified 2026-10-07"),
        (-10.0, "display table pct, spot-verified 2026-10-07"),
        (2552.0, "display table cell, spot-verified 2026-10-07"),
        (1354.0, "display table cell, spot-verified 2026-10-07"),
        (2566.0, "display table cell, spot-verified 2026-10-07"),
        (2448.0, "display table cell, spot-verified 2026-10-07"),
        (1323.0, "display table cell, spot-verified 2026-10-07"),
        (2097.0, "display table cell, spot-verified 2026-10-07"),
        (55.0, "rounded bust-fall range high end"),
        (71.2, "Madrid CPI 2007 deflator reference, verified 2026-10-07"),
        (2881.0, "DPOP table identifier"),
        (62.0, "display pop growth pct, bulk-verified 2026-10-07"),
        (8.3, "display vacancy share, bulk-verified 2026-10-07"),
        (7.3, "display vacancy share, bulk-verified 2026-10-07"),
        (7.0, "display vacancy share, bulk-verified 2026-10-07"),
        (1.9, "display vacancy share, bulk-verified 2026-10-07"),
        (57000.0, "display secundaria count, bulk-verified 2026-10-07"),
    ],
    "docs/explorations/barcelona_municipios.md": [
        (2719.0, "display table cell, spot-verified 2026-10-07 (Badalona row fully checked)"),
        (682.0, "display table cell, spot-verified 2026-10-07"),
        (1147.0, "display table cell, spot-verified 2026-10-07"),
        (1610000.0, "display table cell, spot-verified 2026-10-07"),
        (1700000.0, "display table cell, spot-verified 2026-10-07"),
        (1825.0, "display table cell, spot-verified 2026-10-07"),
        (2703.0, "display table cell, spot-verified 2026-10-07"),
        (48.0, "display table pct, spot-verified 2026-10-07"),
        (516.0, "display table cell, spot-verified 2026-10-07"),
        (837.0, "display table cell, spot-verified 2026-10-07"),
        (62.0, "display table pct, spot-verified 2026-10-07"),
        (254000.0, "display table cell, spot-verified 2026-10-07"),
        (280000.0, "display table cell, spot-verified 2026-10-07"),
        (1787.0, "display table cell, spot-verified 2026-10-07"),
        (2672.0, "display table cell, spot-verified 2026-10-07"),
        (541.0, "display table cell, spot-verified 2026-10-07"),
        (883.0, "display table cell, spot-verified 2026-10-07"),
        (220000.0, "display table cell, spot-verified 2026-10-07"),
        (227000.0, "display table cell, spot-verified 2026-10-07"),
        (1768.0, "display table cell, spot-verified 2026-10-07"),
        (2310.0, "display table cell, spot-verified 2026-10-07"),
        (481.0, "display table cell, spot-verified 2026-10-07"),
        (702.0, "display table cell, spot-verified 2026-10-07"),
        (46.0, "display table pct, spot-verified 2026-10-07"),
        (120000.0, "display table cell, spot-verified 2026-10-07"),
        (121000.0, "display table cell, spot-verified 2026-10-07"),
        (79.0, "Cataluña CPI 2013 deflator reference, verified 2026-10-07"),
        (97.6, "Cataluña CPI 2024 deflator reference, verified 2026-10-07"),
        (58.0, "display burden band, bulk-verified 2026-10-07"),
        (62.1, "display burden, bulk-verified 2026-10-07"),
        (10271.0, "display tourist count, bulk-verified 2026-10-07"),
        (10000.0, "rounded metro split descriptor"),
        (19086.0, "display starts total, bulk-verified 2026-10-07"),
        (16721.0, "display completions total, bulk-verified 2026-10-07"),
        (6570.0, "display starts flow, bulk-verified 2026-10-07"),
        (5271.0, "display completions flow, bulk-verified 2026-10-07"),
        (2358.0, "display starts flow, bulk-verified 2026-10-07"),
        (1050.0, "display completions flow, bulk-verified 2026-10-07"),
        (1730.0, "display starts flow, bulk-verified 2026-10-07"),
        (1241.0, "display completions flow, bulk-verified 2026-10-07"),
        (514.0, "display starts flow, printed at verify"),
        (419.0, "display completions flow, bulk-verified 2026-10-07"),
        (105696.0, "display starts total, bulk-verified 2026-10-07"),
        (84164.0, "display completions total, bulk-verified 2026-10-07"),
        (1500.0, "rounded infill rate descriptor"),
        (90000.0, "rounded population growth descriptor"),
        (54.6, "display burden, bulk-verified 2026-10-07"),
        (7.3, "display vacancy share, bulk-verified 2026-10-07"),
        (1350.0, "registered vacant coverage count"),
        (8.0, "INCASÒL workbook count (structural)"),
        (73.0, "barri coverage count, pinned in claims"),
        (10.0, "district coverage count (structural)"),
        (6.0, "contract suppression threshold (documented)"),
        (2000.0, "INCASÒL district series start year"),
        (2013.0, "INCASÒL barri annual start year"),
        (2014.0, "INCASÒL barri quarterly start year"),
        (2025.0, "INCASÒL latest annual year"),
        (2026.0, "INCASÒL partial quarterly year"),
        (3.0, "Registradores price suppression threshold (documented)"),
        (2018.0, "compravendes series start year"),
        (2019.0, "compravendes full year"),
        (2017.0, "compravendes pre-series year"),
        (2020.0, "compravendes publication-gap year"),
        (2021.0, "compravendes post-gap resume year"),
        (2024.0, "compravendes anchor year"),
        (15.0, "yield thin-cell transaction threshold"),
        (2023.0, "yield peak year"),
    ],
    "docs/explorations/saiz_gis_probe.md": [
        (99.4, "probe headline validation, arithmetic from pinned anchor"),
        (8110.0, "external published area (reference value)"),
        (10604.0, "external published area (reference value)"),
        (1980.0, "external published area (reference value)"),
        (49.0, "table rank (display order)"),
        (48.0, "table rank (display order)"),
        (103.0, "tile count (coverage fact)"),
        (112.0, "tile candidate count (coverage fact)"),
        (404.0, "all-ocean cell count (coverage fact)"),
        (2.6, "probe data size in GB (coverage fact)"),
        (52.0, "province coverage count"),
        (280.0, "script line count (coverage fact)"),
        (125.0, "cited journal volume (reference)"),
        (1.76, "threshold factor (documented derivation)"),
        (4326.0, "EPSG code (method parameter)"),
        (92.0, "grid cell size in metres (method detail)"),
        (71.0, "grid cell size in metres (method detail)"),
        (24.0, "relative error pct (method finding)"),
        (90.0, "DEM grid resolution in metres (method parameter)"),
        (625064.0, "naive cell-count area km2 (method illustration)"),
        (505990.0, "actual area km2 (reference)"),
        (30.0, "resolution variant label (method parameter)"),
        (180.0, "resolution variant label (method parameter)"),
        (59.0, "boundary-set unit count (coverage fact)"),
        (7.0, "Canaries split count (coverage fact)"),
        (15.0, "grade threshold pct (method parameter)"),
    ],
}


def claim_expectations() -> list[tuple[float, float]]:
    """All (expected, tol) pairs the audit checks. Single source of truth.

    Parsed from audit_claims.py with ast (robust to formatting): every
    tuple literal ending in two numbers is a claim, regardless of arity
    (mart 5-tuples, path 4-tuples, computed-got 4-tuples). Freshness
    entries have no numbers and are excluded by construction. The count
    guard below fails loudly if a new tuple shape appears.
    """
    import ast

    src = (ROOT / "scripts" / "audit_claims.py").read_text()
    tree = ast.parse(src)
    out: list[tuple[float, float]] = []

    def number(e: ast.expr) -> float | None:
        if isinstance(e, ast.Constant) and isinstance(e.value, (int, float)):
            return float(e.value)
        if (
            isinstance(e, ast.UnaryOp)
            and isinstance(e.op, (ast.USub, ast.UAdd))
            and isinstance(e.operand, ast.Constant)
            and isinstance(e.operand.value, (int, float))
        ):
            return -float(e.operand.value) if isinstance(e.op, ast.USub) else float(e.operand.value)
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Tuple) or len(node.elts) < 4:
            continue
        vals = [number(e) for e in node.elts[-2:]]
        if all(v is not None for v in vals):
            out.append((vals[0], vals[1]))
    # The saiz_gis_probe land-area anchor is an ad-hoc check (+ 1 in the
    # audit total), not a tuple: pin it here, failing if it ever leaves.
    assert "503189.7" in src, "land anchor literal moved; update this pin"
    out.append((503189.7, 2.0))
    return out


def audit_total() -> int:
    """Recompute the audit's own printed claim total.

    Mirrors main(): the initial assignment plus every `total +=`, EXCLUDING
    `len(MODEL_FRESHNESS)` — that line runs after the "claims hold" print,
    so the printed total covers value claims only.
    """
    src = (ROOT / "scripts" / "audit_claims.py").read_text()
    scope = {
        "CLAIMS": audit_claims.CLAIMS,
        "IV_CLAIMS": audit_claims.IV_CLAIMS,
        "PROBE_CLAIMS": audit_claims.PROBE_CLAIMS,
        "SENSITIVITY_CLAIMS": audit_claims.SENSITIVITY_CLAIMS,
        "PANEL_SAIZ_CLAIMS": audit_claims.PANEL_SAIZ_CLAIMS,
        "PANEL_SAIZ_MUNI_CLAIMS": audit_claims.PANEL_SAIZ_MUNI_CLAIMS,
    }
    total = 0
    seen_lists: set[str] = set()
    for line in src.splitlines():
        sline = line.strip()
        if not sline.startswith("total"):
            continue
        for n in re.findall(r"total \+= (\d+)", sline):
            total += int(n)
        for name in re.findall(r"len\((\w+)\)", sline):
            if name == "MODEL_FRESHNESS" or name in seen_lists:
                continue
            seen_lists.add(name)
            total += len(scope[name])
        if "+=" not in sline:
            for n in re.findall(r"(?<![\w.])\d+(?![\w.])", sline.split("=", 1)[1]):
                if f"len({n})" not in sline:
                    total += int(n)
    return total


def doc_numbers(text: str) -> list[tuple[float, float, str]]:
    """Extract (value, rounding-slack, context-line) triples from markdown.

    Normalizes unicode signs, splits ranges/arrows into endpoints, drops
    code spans/urls, list markers, age-band labels (20-34), and two-digit
    year fragments (2021-25 keeps 2021). Slack is half the token's last
    decimal place (scaled by k/M) so honest doc rounding passes while
    real drift still fails.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.S)  # fenced code
    text = re.sub(r"`[^`]*`", " ", text)  # inline code (ports, commands)
    text = re.sub(r"https?://\S+", " ", text)  # urls
    # Non-result identifiers: ISO dates, project jargon, regressor labels,
    # decade labels (2000s), integer year-counts (18y -- decimal 6.2y is a
    # real value and is kept by stripping only the y).
    text = re.sub(r"\b(19|20)\d{2}-\d{2}(-\d{2})?\b", " ", text)
    text = re.sub(r"\b((19|20)\d{2})/(\d{2})\b", r"\1 ", text)
    text = re.sub(r"\bmilestone-\d+\b", " ", text)
    text = re.sub(r"\bL\d+\b", " ", text)
    text = re.sub(r"\b(19|20)\d0s\b", " ", text)
    text = re.sub(r"\b(\d+\.\d+)y\b", r"\1 ", text)
    text = re.sub(r"\b(\d+)y\b", " ", text)
    text = re.sub(r"F\((\d+),(\d+)\)", r"F(\1 \2)", text)
    out = []
    for line in text.splitlines():
        line = re.sub(r"^\s*\d+\.\s+", "", line)  # ordered-list markers
        # age-band labels and 2-digit year fragments are not results
        line = re.sub(r"\b20\s*[-–]\s*34\b", " ", line)
        line = re.sub(r"\b(19|20)\d{2}\s*[-–→]\s*\d{2}\b", lambda m: m.group(0)[:4] + " ", line)
        norm = (
            line.replace("−", "-")
            .replace("–", " ")
            .replace("—", " ")
            .replace("→", " ")
            .replace("×", " ")
            .replace("~", " ")
            .replace("±", " ")
            .replace("…", " ")
            .replace("†", " ")
            .replace("²", " ")
        )
        # split digit-digit ranges on leftover hyphens: 2001-2025 -> pair
        norm = re.sub(r"(\d)-(\d)", r"\1 \2", norm)
        # thousands separators first (1,147), then Spanish decimals (37,8)
        norm = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", norm)
        norm = re.sub(r"(\d),(\d{1,2})(?!\d)", r"\1.\2", norm)
        for m in re.finditer(r"[-+]?\d[\d,]*\.?\d*\s*[kM%]?(?![A-Za-z])", norm):
            tok = m.group(0).strip()
            if re.fullmatch(r"[-+]?\d", tok):
                continue  # bare single digit: labels and fragments, not results
            # skip tokens glued to a preceding letter: SHA-256, pre-2021,
            # post-2021 (identifiers, not measurements)
            if m.start() > 0 and norm[m.start() - 1].isalpha():
                continue
            mult = 1.0
            if tok and tok[-1] in "kM%":
                if tok[-1] == "k":
                    mult = 1e3
                elif tok[-1] == "M":
                    mult = 1e6
                tok = tok[:-1].strip()
            try:
                digits = tok.replace(",", "")
                val = float(digits) * mult
            except ValueError:
                continue
            # half the last decimal place, scaled by k/M
            slack = 0.5 * 10 ** (-len(digits.split(".")[1])) * mult if "." in digits else 0.5 * mult
            out.append((val, slack, line.strip()[:120]))
    return out


def main() -> int:
    claims = claim_expectations()
    want = audit_total()
    if len(claims) != want:
        print(
            f"FAIL: extracted {len(claims)} claim expectations but the audit "
            f"prints {want} — a new claim tuple shape appeared; "
            "teach claim_expectations() the new shape"
        )
        return 1
    print(f"claim expectations extracted: {len(claims)} (matches audit value claims)")
    failures = 0
    for rel in COVERED_DOCS:
        text = (ROOT / rel).read_text()
        allowed = [(v, why) for v, why in ALLOW.get(rel, [])]
        unmatched = []
        for val, slack, ctx in doc_numbers(text):
            if val == int(val) and 1990 <= val <= 2030:
                continue  # calendar years are not results
            if any(abs(val - e) <= t + slack for e, t in claims):
                continue
            if any(abs(val - v) <= 1e-9 for v, _ in allowed):
                continue
            unmatched.append((val, ctx))
        if unmatched:
            print(f"[FAIL] {rel}: {len(unmatched)} numbers match no claim/allowlist entry")
            for val, ctx in unmatched:
                print(f"    {val:g} :: {ctx}")
            failures += len(unmatched)
        else:
            print(f"[OK] {rel}: all numbers match claims or allowlist")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
