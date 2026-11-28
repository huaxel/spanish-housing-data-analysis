# Tourist dwellings and rents: levels versus changes

Municipalities with more tourist dwellings relative to their housing stock tend
to have higher rents. In the same municipalities, however, increases in the
tourist share line up much less closely with increases in rents.

## A code-matched comparison

Join INE VTE and SERPAVI on their official municipality codes, never on names.
Tourist exposure is INE's published tourist-dwelling share of census dwellings.
Rent is SERPAVI's annual median in €/m²/month for collective housing, derived
from tax records; it is not a constant-quality price index. Use August at both
ends of each change window to avoid comparing different tourist snapshot months.
The rent series is annual, not an August quote. Keep published zeros in VTE and
exclude missing observations rather than treating them as zeros.

| Comparison | Paired municipalities | Spearman rank correlation | 2024 levels on exactly the same municipalities |
| --- | ---: | ---: | ---: |
| 2024 levels | 2,555 | +0.206 | +0.206 |
| 2022–2024 changes | 2,340 | +0.050 | +0.224 |
| 2020–2024 changes | 2,122 | +0.007 | +0.241 |

The change comparisons rank the percentage-point change in the tourist share
against the percentage change in the rent median, averaging ranks when values
tie. The gap between levels and changes is not just a change of sample: the
level relationship is still positive on each change sample. The longer window
starts in a pandemic year; the shorter window does not use that baseline.

## Does the rent measure change the result?

The [IPVA rent price index](ipva_rent_index.md) lets us repeat the comparison
with a different measure of rent growth. Two things change if we simply swap
series: IPVA covers fewer municipalities, and it measures a different quantity.
In the table, first read across the two SERPAVI columns to see what changes
when restricting the sample. Then compare SERPAVI with IPVA on the common
towns. The last column compares the two rent series with each other.

| Window | Common towns | SERPAVI, full sample | SERPAVI, common towns | IPVA, common towns | SERPAVI vs IPVA rent growth, common towns |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022–2024 | 703 | +0.050 | +0.120 | +0.104 | +0.694 |
| 2020–2024 | 701 | +0.007 | +0.068 | +0.032 | +0.747 |

For both windows, restricting SERPAVI to the towns with IPVA increases its
correlation with tourist-share growth. Switching the rent measure on those
same towns changes it less. The two rent series broadly agree on **which towns
had faster rent growth**, but neither ordering closely follows the change in
the tourist-dwelling share. These are Spearman correlations, not rent effects per additional
tourist dwelling.

All municipalities with a published municipal IPVA index at both endpoints
also have SERPAVI rents and August tourist shares at both endpoints in these
windows. They account for **76.98%** (2022–2024) and **76.96%** (2020–2024)
of the published August 2024 tourist stock. The sample reflects IPVA's
larger-municipality coverage in common fiscal territory, not every municipality
in Spain. IPVA covers both collective and single-family housing and shares tax
data with SERPAVI; this is not independent confirmation. We compare changes
in the index, never its level with a rent in euros.

## Does the census denominator matter?

Both change windows cross a measurement break: [INE’s share table](https://www.ine.es/jaxiT3/Tabla.htm?t=39366) uses the
2021 census from 2023 onward. A difference between two published shares can
therefore reflect a change in the housing denominator, not just a change in
tourist dwellings.

We recalculate the exposure as **the change in INE’s estimated August tourist
count per hundred dwellings counted in the 2021 census**. The housing denominator
is fixed for each town, including when looking back to 2020; it is not a claim
about how many dwellings existed in that earlier year. Use only named municipal
`Viviendas totales` from [census table 59531](https://www.ine.es/jaxi/files/tpx/csv_bd/59531.csv),
never a provincial remainder. All towns in the two common rent samples have
a denominator. For each row below, both exposure measures and both rent outcomes
are ranked on exactly the same municipalities.

| Window | Municipalities | n | SERPAVI: published share | SERPAVI: fixed base | IPVA: published share | IPVA: fixed base |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2022–2024 | All matched | 703 | +0.120 | +0.167 | +0.104 | +0.133 |
| 2020–2024 | All matched | 701 | +0.068 | +0.113 | +0.032 | +0.069 |
| 2022–2024 | Outside Andalucía | 551 | +0.088 | +0.145 | +0.041 | +0.076 |
| 2020–2024 | Outside Andalucía | 549 | +0.045 | +0.091 | +0.017 | +0.055 |

On these matched towns, the fixed-base correlations are higher in each
comparison, but still weak. We have not tested whether the differences extend
beyond these samples. This is not an exact reconstruction: the published shares
are rounded, and census table 59531 need not reproduce INE’s VTE denominator
in every town. We cannot attribute the entire difference to the change of
census. As an endpoint check, the recalculated August 2024 share is
within half the last published decimal place in **694 of 703** towns in the
shorter window.

The Andalucía cut addresses a **separate change in the numerator**. [INE’s count
table](https://www.ine.es/jaxiT3/Tabla.htm?t=39363) says the August and November
2024 estimates were revised to include Andalusian VUT-type licences. Removing
Andalucía shows whether the descriptive pattern persists elsewhere; it does
not estimate the size of that revision or imply unchanged platform coverage.

## Did earlier tourist-stock growth line up with later rent growth?

Not consistently. For the **same 703 municipalities** and the **same 2023–2024
rent change**, gains in tourist homes per hundred dwellings in 2020–2021 have a
small negative rank correlation with later rent growth. Using tourist gains
in 2021–2022 instead gives a small positive correlation under both rent measures.

| Earlier change in August tourist count, per hundred 2021 dwellings | Later change in annual rent | SERPAVI (Spearman) | IPVA (Spearman) |
| --- | --- | ---: | ---: |
| 2020–2021 | 2022–2023 | −0.045 | −0.072 |
| 2020–2021 | 2023–2024 | −0.104 | −0.098 |
| 2021–2022 | 2023–2024 | +0.075 | +0.072 |

These are **all** pairs of one-year changes in 2020–2024 in which the last
tourist snapshot precedes the first rent calendar year. For example, the first
row ends its tourist comparison in August 2021; its rent comparison uses 2022
and 2023, not 2021 and 2022. All towns with both rent series throughout
2022–2024 also have all three required August counts and a named census base.
A reported zero counts; a missing value does not. No tourist count after 2022
enters the calculation, so the 2024 Andalucía revision cannot drive these rows.

The timing rule avoids comparing changes that share a calendar year. It does
not remove differences in local housing demand or the disruption to tourism
during the pandemic. August 2021 is the end of one tourist window and the start
of the next, so an error in that count enters the two changes with opposite
signs. The rows reuse towns and periods: the signs describe these samples, not
a statistical test that the relationship changed or a test of forecast accuracy.

### What if the shared August 2021 count is left out?

Take the net change from August 2020 to August 2022, keeping the same 703
municipalities and the 2021 housing denominator. An error in the August 2021
count does not enter this net change. The rank correlation with 2023–2024
rent growth is **−0.023** for SERPAVI and **−0.004** for IPVA.

| Net change in tourist-home count | Municipalities | Median SERPAVI rent growth | Median IPVA rent growth |
| --- | ---: | ---: | ---: |
| Fell | 320 | +5.21% | +3.27% |
| Unchanged | 44 | +5.10% | +3.17% |
| Rose | 339 | +5.43% | +3.37% |

These are medians of municipal growth rates, not changes in a pooled rent
measure. The typical stock change was small: **−0.053** and **+0.073**
tourist dwellings per hundred census dwellings in towns where counts fell
and rose, respectively. Offsetting changes can also leave a small net
change. This check does not show that the August 2021 count was wrong or that
large sustained increases in tourist stock have no effect on rents.

## Coverage and limits

The 2024 level sample covers **31.42%** of the municipalities but **95.29%** of
INE's estimated August tourist dwellings. All 2,555 SERPAVI municipalities for
that measure have a published August tourist share. Without the IPVA restriction,
the 2022–2024 and 2020–2024 SERPAVI change samples cover **94.19%** and **92.97%**
of the August 2024 tourist stock, respectively. These
are stock coverage figures, not sampling weights: each paired municipality
contributes one observation.

This is an unadjusted descriptive comparison. The same places can have higher
rents and more tourist listings for other reasons; tourist shares can move with
measured stock or revisions to denominators; and rental contract composition
can change. A near-zero rank correlation in changes neither rules out local
effects nor estimates what regulation would do. In particular, May 2026 tourist
stock is not paired with a 2026 rent series here: SERPAVI ends in 2024.

## Reproduce

```sh
uv run python explorations/vut_rent_overlap.py
uv run python explorations/vut_rent_overlap.py --check
uv run pytest -q tests/test_vut_rent_overlap.py  # includes raw-source timing check with pinned data
```

Reads the municipality-coded `data/raw/parquet/vut_municipal.parquet` and
`data/raw/parquet/ipva_municipal.parquet`, plus `serpavi_municipal`,
`censo2021_intensidad` and the province-to-region mapping in
`data/processed/marts.duckdb`. The sample counts, coverage and rank
correlations are in `artifacts/vut_rent_overlap.json`.
