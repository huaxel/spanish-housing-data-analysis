# How closely do IPVA and SERPAVI agree on municipal rent growth?

Among **701 municipalities** observed in both 2019 and 2024, the median increase
was **11.62%** in INE’s rent price index (IPVA) and **22.09%** in MIVAU’s
SERPAVI rent per square metre. Municipalities with larger increases by one
measure generally also had larger increases by the other (Spearman **0.758**).
That agreement in ordering does not establish agreement on the size of a rise.

| Window | Paired municipalities | Median IPVA change | Median SERPAVI change | Pearson | Spearman | Median paired gap (IPVA − SERPAVI) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2013→2023 | 697 | +15.82% | +32.51% | +0.634 | +0.679 | −16.54 pp |
| 2019→2023 | 702 | +8.03% | +16.15% | +0.690 | +0.703 | −8.02 pp |
| 2019→2024 | 701 | +11.62% | +22.09% | +0.753 | +0.758 | −10.64 pp |

The gap is calculated **within each municipality before taking the median**;
it need not equal the difference of the two displayed medians. Each municipality
counts once; these are not national rent growth rates.

## Do the measures pick the same faster-rising town within a province?

Yes, more often than not. In 2019→2024, IPVA and SERPAVI picked the same town
in **8,046 of 10,786** within-province pairs (**74.60%**). That compares with
**79.35%** of **230,379** pairs drawn from different provinces, using exactly
the same **695 municipalities**. Neither measure tied on any pair in this
window. The two measures agree on local ordering more often than not, even
without comparing municipalities across provincial boundaries.

| Window | Same province | Different provinces | Equal weight per province (within) | Equal weight per province pair (between) |
| --- | ---: | ---: | ---: | ---: |
| 2013→2023 | 66.50% | 75.66% | 66.32% | 74.68% |
| 2019→2023 | 73.53% | 76.84% | 71.82% | 78.81% |
| 2019→2024 | 74.60% | 79.35% | 74.87% | 81.40% |

For each window, group the matched towns by the province prefix of the INE
code. Exclude a town from **both** comparisons if no other town in its
province is matched. In 2019→2024 this leaves 695 of the 701 matched towns.
Compare the percentage changes for every unordered pair; omit a pair from the
rate if either measure ties. The same- and different-province rates give each
comparable pair one vote, so provinces with more observed towns contribute more
pairs. The last two columns average rates across provinces and unordered pairs
of provinces, respectively. In 2019→2024, **42 provinces** contribute local
comparisons. Even a narrow difference in growth counts as an ordering; these
are descriptive rates, not measures of economic significance or accuracy. Many
pairs share a town and are not independent trials.

## What is being compared?

- [INE’s IPVA](https://www.ine.es/dyngs/Prensa/IPVA2024.htm) is a chained
  price index for rented primary residences in common fiscal territory (it
  excludes País Vasco and Navarra). The municipal table covers municipalities
  above 10,000 inhabitants; smaller places are grouped. We use the overall
  municipal index, not an index restricted to apartments.
- The SERPAVI measure is the annual median rent in €/m²/month for collective
  housing (`ALQM2_LV_M_VC`). [AEAT describes its tax and cadastral inputs](https://sede.agenciatributaria.gob.es/Sede/estadisticas/estadisticas-impuesto/estadistica-viviendas-declaradas-irpf/metodologia/preguntas-frecuentes.html).
  IPVA also uses AEAT records: these are **different statistics with overlapping
  source data**, not independent observations of the market. An index level
  cannot be compared directly with a euro rent.
- [INE table 59060](https://www.ine.es/jaxiT3/Tabla.htm?t=59060) supplies
  five-digit municipality codes in its JAXI CSV. All **718** codes with a
  published index somewhere in 2011–2024 occur in the SERPAVI measure in at
  least one year. The table above requires both series at *both endpoints*;
  missing data are not filled. The national and provincial remainder rows
  never enter the join. Equal percentage changes receive average ranks.

## Why might the amounts diverge?

Over 2013→2023 the median paired gap ranges from **−9.50 pp** in the quartile
with the smallest SERPAVI increases to **−24.98 pp** in the quartile with the
largest. Because the gap subtracts the same SERPAVI change used for sorting,
this pattern alone cannot diagnose composition bias. Coverage, changes in the
mix of rented dwellings, and the index construction can all matter. Neither
series tells us which factor explains how much.

**Correction (2026-11-27):** The previous comparison joined place names. Some
names mapped to the same rental series, and a provincial remainder could map
to a city. Its coverage denominator also counted aggregate labels as municipalities.
The table above replaces that comparison, retains both historical windows and
adds the 2024 endpoint. The rank calculation now averages ties; on the old
samples that fix alone did not change either reported correlation at three decimals.

## Reproduce

```sh
uv run python scripts/fetch_ipva.py          # first download; --offline uses the pinned CSV
uv run python explorations/ipva_rent_index.py
uv run python scripts/fetch_ipva.py --check
uv run python explorations/ipva_rent_index.py --check
```

Inputs: `data/raw/ipva_municipal_59060.csv` and the `serpavi_municipal` table
in `data/processed/marts.duckdb`. Output: `artifacts/ipva_rent_index.json`.
