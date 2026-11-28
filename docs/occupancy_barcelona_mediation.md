# Barcelona: mediated rental activity and active contracts can move in different directions

The Generalitat’s [social-rental mediation statistics](https://habitatge.gencat.cat/ca/dades/indicadors_estadistiques/estadistiques-de-la-politica-dhabitatge-/habitatge-de-lloguer-amb-mediacio-social/)
publish **dwellings rented during the year** through the network and
**dwellings with an active rental contract at year-end**. They are two different
measures, not alternate estimates of the same total. This check uses both
municipal workbooks and distinguishes Barcelona city from the demarcation.

| Area | Rented during 2024 | Rented during 2025 | Active at end of 2024 | Active at end of 2025 |
| --- | ---: | ---: | ---: | ---: |
| Barcelona city | 202 | 176 | 1,246 | 1,301 |
| Rest of Barcelona demarcation | 488 | 375 | 4,028 | 3,912 |
| Whole Barcelona demarcation | 690 | 551 | 5,274 | 5,213 |

**The city added 55 active contracts while the rest of the demarcation lost
116**, despite fewer homes rented during the year in both areas. The city’s
active contracts include agreements from earlier years. These tables do not
link entries, terminations and renewals at dwelling level, so the annual
rented count minus the stock change is not a verified exit count.

The municipal workbooks exclude cessions managed by the Catalan Housing Agency
in these years. This is not a count of all assisted rentals, all privately
available homes or formerly vacant homes. The [Bizigune case](occupancy_euskadi_bizigune.md)
uses owner agreements, a managed portfolio and tenant leases; do not rank the
programs as if those measures were the same as the Catalan ones.

## Across Catalonia: activity fell, but more municipalities recorded it

| Measure | Catalonia total, 2024 → 2025 | Municipalities with a positive count, 2024 → 2025 |
| --- | ---: | ---: |
| Dwellings rented through the network during the year | 1,133 → 910 | 150 → 158 |
| Dwellings with an active year-end contract | 7,790 → 7,704 | 294 → 298 |

The biggest change came from municipalities that recorded rentals in both
years: they counted **229 fewer** rentals. Municipalities switching between
zero and a positive count contributed **6 more** on net. The two components
sum to the Catalonia-wide decline of **223**. The same pattern appears in
active year-end contracts: **94 fewer** in places with contracts in both
snapshots, partly offset by **8 more** from places switching between zero
and positive. A positive count measures observed activity, not whether a
municipality opened a program or offered a new service.

## Barcelona's share rose well before 2025

From 2017, the first year in both municipal workbooks, to 2025, Barcelona's
active year-end contracts rose from **760 to 1,301**. In the rest of Catalonia,
they fell from **7,687 to 6,403**. Barcelona's share of the regional total rose
every year, from **9.0% to 16.9%**. Across Catalonia, 2025 had the lowest count
of both annual mediated rentals and active year-end contracts in this common
window. That does not make it an all-time low across other programs or older
records using different definitions.

The territorial workbooks print alternative comarca groupings for some
historical years. The reproduction selects the first published column for each
year and verifies the municipal-code sums against the demarcation and Catalonia
figures, not the comarca tables.

## Scale alongside registered rental activity

For every thousand habitual rental contracts registered with INCASÒL, there were about
**5.72** homes rented through the mediation network in Barcelona in 2025,
compared with **8.42** across Catalonia. These ratios compare two annual
counts at the same geographic level. They are **not market shares**: we have
not linked the mediated homes to individual registered deposits, and homes
rented and contracts registered are different units of observation.

| Year | Barcelona city registrations | Mediated homes per thousand registrations | Catalonia registrations | Mediated homes per thousand registrations |
| --- | ---: | ---: | ---: | ---: |
| 2017 | 49,953 | 3.56 | 156,936 | 9.02 |
| 2024 | 32,903 | 6.14 | 118,626 | 9.55 |
| 2025 | 30,789 | 5.72 | 108,057 | 8.42 |

Barcelona mediated almost the same number of homes in 2017 and 2025
(**178** and **176**); the higher ratio in 2025 reflects fewer deposit
registrations, not more homes rented through mediation. The denominator
comes from [Idescat's INCASÒL contract series](https://www.idescat.cat/indicadors/?id=aec&n=15708&t=202500),
which counts contracts with a deposit registered in the reference period.
Do not divide the year-end active portfolio by these annual registrations. The
[deposit-balance check](occupancy_catalonia_deposit_balances.md) separately
examines new registrations minus cancellations.

## Including seasonal registrations

Barcelona’s registrations in the two published categories together fell
from **41,309 to 39,584** between 2024 and 2025. Seasonal registrations rose
from **8,406 to 8,795**, partly offsetting the decline in habitual
registrations. Across Catalonia, seasonal registrations instead fell from
**13,517 to 13,152**. These counts are deposits by reported contract type;
they do not track a home switching from one type to the other.

| Area | Mediated homes per thousand habitual + seasonal registrations, 2024 | 2025 |
| --- | ---: | ---: |
| Barcelona city | 4.89 | 4.45 |
| Catalonia | 8.57 | 7.51 |

The ratio still fell in both places from 2024 to 2025. This is a broader
scale check, not a market share or a count of distinct homes. The Generalitat
publishes the [seasonal series](https://habitatge.gencat.cat/ca/dades/indicadors_estadistiques/estadistiques_de_construccio_i_mercat_immobiliari/mercat_de_lloguer/lloguer-de-temporada/)
from 2023, so the earlier comparison remains habitual-only.

## Reproduce from the official workbooks

Download `mediacio_mun.xlsx`, `MediacioVigents_mun.xlsx`, `Mediacio_CAT.xlsx`,
and `MediacioVigents_CAT.xlsx` under the two sections on the Generalitat page.
Use the municipality code for Barcelona, not a name query across geographies.
For the scale comparison, save the Idescat semicolon downloads as `2017.ssv`,
`2024.ssv` and `2025.ssv` using the [2017](https://www.idescat.cat/indicadors/?id=aec&n=15708&t=201700&f=ssv),
[2024](https://www.idescat.cat/indicadors/?id=aec&n=15708&t=202400&f=ssv), and
[2025](https://www.idescat.cat/indicadors/?id=aec&n=15708&t=202500&f=ssv) links.
For the seasonal check, also copy the pinned `data/raw/cat_incasol_temporada_mun.xlsx`
and download the territorial `lloguer_temporada.xlsx` from the seasonal page.
From a directory containing these downloads, with `openpyxl` available:

```python
import csv
from pathlib import Path

from openpyxl import load_workbook


def values(file, sheet):
    workbook = load_workbook(file, read_only=True, data_only=True)
    try:
        return list(workbook[sheet].values)
    finally:
        workbook.close()


codes = None
for municipal, ms, aggregate, ags in [
    ("mediacio_mun", "Mediacio_mun", "Mediacio_CAT", "Mediacio_CAT"),
    ("MediacioVigents_mun", "Vigents_MUN", "MediacioVigents_CAT", "Vigents_CAT"),
]:
    m = values(municipal + ".xlsx", ms)
    a = values(aggregate + ".xlsx", ags)
    (header,) = [r for r in m if r[:2] == ("Codi", "Municipi")]
    (region_header,) = [r for r in a if r[:4] == (None, 2025, 2024, 2023)]
    (start,) = [i for i, r in enumerate(a) if r[0] == "Demarcacions territorials"]
    demarcation = a[start + 1]
    assert demarcation[0] == "Barcelona"
    (catalonia,) = [r for r in a if r[0] == "Catalunya"]
    towns = [r for r in m if isinstance(r[0], str) and len(r[0]) == 5 and r[0].isdigit()]
    observed_codes = {r[0] for r in towns}
    assert len(observed_codes) == len(towns)
    assert codes is None or codes == observed_codes
    codes = observed_codes
    (city,) = [r for r in towns if r[0] == "08019"]
    history = []
    for year in range(2017, 2026):
        i = next(i for i, value in enumerate(header) if str(value) == str(year))
        j = next(i for i, value in enumerate(region_header) if str(value).split()[0] == str(year))
        assert sum(r[i] for r in towns) == catalonia[j]
        assert sum(r[i] for r in towns if r[0].startswith("08")) == demarcation[j]
        history.append((year, city[i], catalonia[j]))
        print(municipal, year, city[i], demarcation[j] - city[i], demarcation[j])
    if ms == "Mediacio_mun":
        for year, city_flow, region_flow in history:
            if year not in (2017, 2024, 2025):
                continue
            path = Path(f"{year}.ssv")
            with path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.reader(stream, delimiter=";"))
            assert [f"Catalunya. {year}"] in rows
            seasonal = {}
            if year in (2024, 2025):
                quarters = values("cat_incasol_temporada_mun.xlsx", str(year))
                assert quarters[4][3:8] == ("Total", "I", "II", "III", "IV")
                season_rows = [r for r in quarters if r[0] in codes]
                assert len(season_rows) == len(codes) and {r[0] for r in season_rows} == codes
                assert all(r[3] == sum(r[4:8]) for r in season_rows)
                city_season = next(r[3] for r in season_rows if r[0] == "08019")
                region_season = sum(r[3] for r in season_rows)
                territorial = values("lloguer_temporada.xlsx", "Full1")
                k = territorial[3].index(year)
                (region_row,) = [r for r in territorial if r[0] == "Catalunya"]
                assert region_season == sum(region_row[k : k + 4])
                seasonal = {"Barcelona": city_season, "Catalunya": region_season}
            for area, flow in [("Barcelona", city_flow), ("Catalunya", region_flow)]:
                (row,) = [r for r in rows if r and r[0] == area]
                deposits = int(row[1])
                print(year, area, deposits, round(1000 * flow / deposits, 2))
                if area in seasonal:
                    combined = deposits + seasonal[area]
                    print(year, area, seasonal[area], combined, round(1000 * flow / combined, 2))
    assert history[-1][2] == min(total for _, _, total in history)
    print("Window endpoints (year, city, rest of Catalonia, city share):")
    for year, town, total in (history[0], history[-1]):
        print(year, town, total - town, round(100 * town / total, 1))
    if ms == "Vigents_MUN":
        assert all(
            b_city * a_total > a_city * b_total
            for (_, a_city, a_total), (_, b_city, b_total) in zip(
                history[:-1], history[1:], strict=True
            )
        )

    i, j = (header.index(str(year)) for year in (2024, 2025))
    endpoints = [(r[i], r[j]) for r in towns]
    assert all(type(v) is int and v >= 0 for pair in endpoints for v in pair)
    both = sum(b - a for a, b in endpoints if a > 0 and b > 0)
    switches = sum(b - a for a, b in endpoints if (a > 0) != (b > 0))
    assert both + switches == sum(b - a for a, b in endpoints)
    print("Catalonia totals:", sum(a for a, _ in endpoints), sum(b for _, b in endpoints))
    print(
        "Municipalities above zero:",
        sum(a > 0 for a, _ in endpoints),
        sum(b > 0 for _, b in endpoints),
    )
    print("Change in places positive both years / switches:", both, switches)
```

The territorial totals reconcile with their own workbooks. This check does not
add the new data to the national mart.
