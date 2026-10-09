# Cadastre construction-era profile: property-weighted era shares by Sevilla barrio

Added 2026-10-09. Property-weighted distribution of earliest construction years
from the cadastre BU records (INSPIRE Buildings), by SIM barrio.

## Method

Each building record's earliest component construction year (`year_start`) is
assigned to every declared housing property (`dwelling_properties`) in that
record. This is a **record-date proxy weighted by housing-property counts**,
not a measured distribution of individual dwelling construction ages. A BU
record can group several constructions with different dates; the oldest
component determines the record's year. Mixed-use buildings with non-residential
components are included — residential-only floor-area fractions are unavailable.

Records without `dwelling_properties` or with a non-positive count are
excluded (1,000 of 58,723 BU records, representing 3,500 properties). These
are non-housing-bearing parcels.

Era boundaries:
- **Pre-1951**: 6.8% of dated properties
- **1951–1970**: 28.8%
- **1971–1990**: 37.7% (peak era)
- **1991–2010**: 22.1%
- **2011+**: 4.7%

323,736 of 323,737 declared housing properties have a valid `year_start`;
the missing share is 0.00%.

## Key findings

**Oldest median construction eras:**
| Barrio | District | Median year | Pre-1951 share |
|---|---|---|---|
| Heliópolis | Bellavista-La Palmera | 1929 | 75.0% |
| La Barzola | Macarena | 1943 | 58.9% |
| Ciudad Jardín | Nervión | 1945 | 66.5% |
| El Prado-Parque María Luisa | Sur | 1950 | 66.5% |
| El Tardón-El Carmen | Triana | 1951 | — |

**Newest median construction eras:**
| Barrio | District | Median year | 2011+ share |
|---|---|---|---|
| Palmete | Cerro-Amate | 2002 | 3.6% |
| Bellavista | Bellavista-La Palmera | 1999 | 21.0% |
| Elcano-Bermejales | Bellavista-La Palmera | 1999 | 0.4% |
| Colores, Entreparques | Este | 1997 | 24.1% |
| Los Carteros | Norte | 1996 | 4.9% |

107 of 108 SIM barrios have housing-bearing records with valid dates.
Valdezorras is excluded (no positive `dwelling_properties` count in the
cadastre extract).

## Limitations

- The `year_start` is the **earliest** construction date among the grouped
  components of a parcel. It is not the construction year of each dwelling.
- A parcel's dominant use may be non-residential; its earliest date and
  declared property count include mixed uses.
- The `dwelling_properties` count is cadastral property units, not census
  dwellings or households.
- The era shares are weighted by property counts, not building records:
  a large apartment block weighs more than a single-family home.
- Date placeholders and invalid/missing values are excluded; they do not
  gain fabricated era assignments. The missing share is negligible (0.00%).
- The cadastre snapshot has a single reference date; no trend or construction
  rate is inferred.
- This profile describes declared stock, not available housing or occupied
  homes. Cross-reference with SIM occupancy/vacancy indicators and the
  cadastre geometry/area analysis on the stock page.

## Source and verification

Source: INSPIRE Buildings municipal feed (DGC), Sevilla municipality code
41900. Buildings table and barrio geometry from the cadastre pilot
([docs/cadastre_stock.md](../cadastre_stock.md), built via
`scripts/fetch_cadastre_stock.py`). Exploration script:
`explorations/cadastre_eras.py`. Artifact: `artifacts/cadastre_eras.json`.

```bash
uv run python explorations/cadastre_eras.py
```
