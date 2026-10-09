# Censo 2021: housing stock by construction vintage and occupancy status

Added 2026-10-09. Analysis of the Censo de Población y Viviendas 2021 (INE,
reference date 1 January 2021) dwelling stock by construction era band and
occupancy status (vivienda principal vs no principal) across all 52 provinces.

## Method and scope

Source: INE Censo de Población y Viviendas 2021, table `59521` (provincial
viviendas by tipo and construcción). Stored in `data/raw/parquet/censo2021_viviendas.parquet`
and loaded into `marts.duckdb` as `censo2021_viviendas`.

Total dwellings count across 52 provinces:
- **Total dwellings:** 26,623,708
- **Principal dwellings:** 18,536,616 (69.6%)
- **Non-principal dwellings (secondary and vacant):** 8,087,092 (30.4%)

Exploration script: `explorations/censo_vintage.py`. Artifact: `artifacts/censo_vintage.json`.

```bash
uv run python explorations/censo_vintage.py
```

## 1. Decade-over-decade additions: boom vs post-bust collapse

Comparing construction volume in the boom decade vs the following decade:
- **2001–2010 additions (Boom):** 5,240,772 dwellings (19.7% of total stock).
- **2011–2020 additions (Post-bust):** 734,659 dwellings (2.8% of total stock).
- Additions collapsed by a factor of **7.13** between the two decades.

## 2. Provincial absorption of boom-era (2001–2010) construction

Utilization of housing built during the 2001–2010 boom diverges sharply between
vacation/second-home belts and primary urban employment markets:

**Second-home belt (highest non-principal share of boom stock):**
- **Ávila:** 52.0% non-principal
- **Castellón:** 49.2% non-principal
- **Alicante:** 44.1% non-principal

**Metropolitan markets (lowest non-principal share / primary absorption):**
- **Bizkaia:** 10.7% non-principal
- **Barcelona:** 13.8% non-principal
- **Madrid:** 14.7% non-principal

In Madrid, Barcelona, and Bizkaia, over 85% of boom-era construction became permanent
primary residences, whereas in coastal and interior leisure provinces around half
of boom construction remains secondary or vacant.

## 3. Total provincial stock non-principal extremes

Across the entire provincial housing stock regardless of construction era:
- **Highest non-principal share:** Ávila at 59.4%
- **Lowest non-principal share:** Madrid at 13.9%

## Caveats and limitations

- **Census reference date:** 1 January 2021. Does not reflect post-2021 migration or construction.
- **Non-principal definition:** Combines secondary dwellings (holiday, weekend) and vacant stock.
- **Purely descriptive:** These distributions describe physical stock and census occupancy; they do not identify causal supply effects.
