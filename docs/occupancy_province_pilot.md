# When housing stock grows, do more homes become primary residences?

A pilot for the four provinces with the largest positive household–stock gaps
in the [deficit analysis](deficit_2025_methods.md): Madrid, Barcelona, Valencia
and Alicante. These are **provinces**, not the four capital cities, and are not
a representative sample of Spain.

## The stock and primary-residence counts can move apart

| Province | Total stock change, 2023 to 2024 | Primary dwellings change, 2023 to 2024 | Primary dwellings change, 2024 to 2025 | Tax-declared dwellings at owners’ disposal, change from 2023 to 2024 |
| --- | ---: | ---: | ---: | ---: |
| Madrid | +20,608 | +29,457 | +41,660 | +2,224 |
| Barcelona | +10,448 | −9,209 | +14,985 | +994 |
| Valencia | +4,300 | +40,529 | +10,185 | −1,983 |
| Alicante | +6,000 | −7,343 | +30,433 | +1,374 |

The first three numeric columns use December endpoints from the [MIVAU stock
estimate](https://datos.gob.es/es/catalogo/e05233601-estimacion-del-parque-de-viviendas1).
Barcelona and Alicante are clear examples: total stock rose in the year ending
December 2024, but the estimated primary-residence count fell. The rise in
the estimated non-primary count more than offset the fall in the primary
count. In the next year the primary estimate rose in all four
provinces. These are net changes between estimates, not observed conversions of
individual dwellings, and the results do not establish fewer homes on offer.

The last column is a separate series: the count classified *a disposición de
sus titulares* in the [AEAT dwelling-use statistics](https://sede.agenciatributaria.gob.es/Sede/estadisticas/estadisticas-impuesto/estadistica-viviendas-declaradas-irpf.html).
It covers dwellings declared by individuals in the common tax jurisdiction, not
all dwellings. It refers to use during the tax year, not occupancy on December
31. For example, in Madrid the MIVAU non-primary estimate fell while the AEAT
count at owners’ disposal rose. This is not a contradiction: the categories
and populations differ. Neither identifies whether a home at an owner's
disposal is a second home, empty or on the rental market.

## What would count as separate evidence?

- **Primary and non-primary counts:** MIVAU tracks both annually. Its non-primary
  category does not tell us how many were second homes, vacant or available to
  rent. The pilot should not be read as a vacancy trend.
- **Vacancy and sporadic use:** the [INE housing census](https://www.ine.es/dynt3/inebase/index.htm?capsel=9848&padre=8952)
  distinguishes these electricity-use categories at municipal scale in 2021.
  It is a historical snapshot, not a matching annual follow-up. Sporadic use
  is not a direct second-home classification, and classified vacancy is not
  evidence that a home is habitable, affordable or offered to tenants.
- **Market availability:** neither source identifies homes genuinely offered
  year-round. A dated register or listing series with a consistent coverage
  definition could answer a narrower question. The [unsold-new-stock check](occupancy_availability.md#3-unsold-new-stock-a-sales-inventory-estimate-not-available-homes)
  found a public Madrid series, but it estimates unsold stock and may include
  dwellings already rented. It does not resolve the availability question. The
  [Barcelona mediation case](occupancy_barcelona_mediation.md) measures actual
  program activity, but only within that network and with city and province
  reported separately. See the [four-city reporting comparison](occupancy_city_programs.md)
  for what can and cannot be compared with Madrid, Alicante and València.

## Reproduce

From the repository root, using the pinned inputs:

```sh
uv run python - <<'PY'
from pathlib import Path
import duckdb
query = Path('explorations/occupancy_province_pilot.sql').read_text()
duckdb.sql(query).show()
PY
make audit
```

The SQL uses province codes, keeps the 2025 tax cells null, and returns
non-primary changes alongside the figures shown above. The audit checks the
published table against the independently built mart. No new input vintage
was fetched or pinned for the pilot.
