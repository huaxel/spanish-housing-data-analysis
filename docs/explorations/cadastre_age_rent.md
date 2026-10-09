# Age–rent gradient: cadastre era profiles vs IPRA rent per Sevilla barrio

Added 2026-10-09. Descriptive cross-section joining the property-weighted
construction-era profile ([cadastre eras](cadastre_eras.md)) with the IPRA
2022 rent level per barrio. Artifact: `artifacts/cadastre_age_rent.json`
(exploration: `explorations/cadastre_age_rent.py`).

## Method

Per barrio, the era profile uses the same record-date proxy as the era
exploration: each BU record's earliest component construction year
(`year_start`) is assigned to every declared housing property
(`dwelling_properties`). The rent side is the IPRA 2022 update
(EUR/m²/month, contract window 2019–2021) from `marts.barrios_sevilla`.
Every barrio weighs equally. No causal claim, no significance testing,
no adjustment for income or centrality.

Coverage: 107 barrios have an era profile and 102 have a non-null IPRA
2022 value; **101 barrios join**. Six era-profile barrios lack a 2022 IPRA
value (El Prado-Parque María Luisa, El Gordillo, La Bachillera, Los
Carteros, La Corza, Barriada de Pineda); Valdezorras (05061) has a 2022
rent but no housing-bearing dated records in the cadastre extract.

## Findings

**Overall gradient is weakly negative and not monotone.**

| Measure | Value |
|---|---|
| Spearman, median construction year vs IPRA 2022 (n=101) | −0.159 |
| Pearson, same pair | −0.138 |

The Spearman value coincides with the record-date sensitivity published on
the [stock page](../../evidence/pages/stock.md) (property-weighted median year), which
is a consistency check, not an independent estimate.

**Era-share correlations reveal the non-monotonicity** the single median
hides. Spearman of each era's property share vs IPRA 2022:

| Era share | Spearman vs rent |
|---|---|
| Pre-1951 | +0.228 |
| 1951–1970 | +0.318 |
| 1971–1990 | −0.137 |
| 1991–2010 | −0.123 |
| 2011+ | −0.005 |

Barrios dominated by mid-century (1951–1970) and pre-1951 stock have
*higher* rents on average — the expensive historic core and Ensanche-type
neighborhoods are old. The 1971–2010 expansion-era shares correlate mildly
negatively, and the 2011+ share is essentially unrelated (few barrios have
meaningful post-2011 stock). Newer is not more expensive in this
cross-section.

**Terciles of median construction year** (mean IPRA 2022, EUR/m²/month):

| Group | n | Median-year range | Mean rent | Median rent |
|---|---|---|---|---|
| Oldest third | 33 | 1929–1971 | 7.22 | 7.47 |
| Middle third | 35 | 1971–1978 | 7.36 | 7.40 |
| Newest third | 33 | 1978–2002 | 6.87 | 6.69 |

The middle tercile, not the oldest, has the highest mean rent — again
consistent with a non-monotone age–rent profile.

**Extremes:**

| Oldest barrios | Median year | IPRA 2022 |  | Newest barrios | Median year | IPRA 2022 |
|---|---|---|---|---|---|---|
| Heliópolis | 1929 | 3.67 |  | Palmete | 2002 | 3.64 |
| La Barzola | 1943 | 6.77 |  | Bellavista | 1999 | 6.10 |
| Ciudad Jardín | 1945 | 7.64 |  | Elcano-Bermejales | 1999 | 4.17 |
| El Tardón-El Carmen | 1951 | 8.56 |  | Colores, Entreparques | 1997 | 4.96 |
| Amate | 1957 | 6.83 |  | San Bernardo | 1994 | 7.56 |

Both extremes contain cheap and expensive barrios: Heliópolis (oldest,
rent 3.67) and Palmete (newest, 3.64) are equally cheap, while El
Tardón-El Carmen (old, 8.56) and San Bernardo (comparatively new, 7.56)
are both expensive. Construction age alone does not order rents.

## Limitations

- The age measure is a **record-date proxy** (earliest component year per
  BU record, weighted by declared housing properties), not observed
  dwelling age; see the [era profile limitations](cadastre_eras.md).
- IPRA is a registered-contract index for 2019–2021 contracts, published
  2022 — a different vintage from the cadastre snapshot, and it prices
  only dwellings that actually transacted, not the whole stock.
- Rent levels reflect location quality, renovation state and selection
  into the rental market; nothing here separates those channels from age.
- Cross-sectional description at barrio level; no significance testing,
  no causal claim, and no adjustment for income, centrality or size mix.

## Relation to existing work

The [stock page](../../evidence/pages/stock.md) already publishes the median-year vs
rent scatter, its Spearman, district-centered rank correlation and
district-omission sensitivity. This exploration adds the era-share
decomposition, which shows why the single-median gradient is weak: old
stock splits between the expensive historic core and cheap suburban
developments like Heliópolis.
