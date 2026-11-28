"""Catalan mediation, seasonal and deposit-balance figures as an audited artifact.

docs/occupancy_barcelona_mediation.md and docs/occupancy_catalonia_deposit_balances.md
quote about sixty numbers from four pinned Generalitat workbooks and three
Idescat registration exports. Until now those numbers lived as frozen
constants in the doc-audit allowlist: the snippets reproduced them, but
nothing recomputed them, so a publisher reissue would silently leave the
notes quoting a superseded vintage.

This script recomputes them from `data/raw` and writes
artifacts/occupancy_catalonia.json, so `make audit` fails when a note and
the pinned bytes disagree.

What it does **not** claim:

- The mediation counts are recorded programme activity, not coverage of all
  assisted rentals (the municipal workbooks exclude cessions managed by the
  Catalan Housing Agency in these years) and not a count of available homes.
- Rented-during-the-year and active-at-year-end are different measures; the
  difference is not a verified exit count, because the files do not link
  entries, terminations and renewals at dwelling level.
- Deposit entries and cancellations are registry flows. Their difference is
  not a stock of active leases, and nothing here links a mediated contract to
  a deposit filing, so no ratio of the two is a market share.
- Registration counts are used only as a scale denominator per thousand
  filings.

Use --check to verify the artifact matches the pinned inputs byte-for-byte.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

ARTIFACT = ROOT / "artifacts" / "occupancy_catalonia.json"

MEDIATION_FLOW_MUN = RAW / "cat_incasol_mediacio_municipis.xlsx"
MEDIATION_FLOW_CAT = RAW / "cat_incasol_mediacio_catalunya.xlsx"
MEDIATION_ACTIVE_MUN = RAW / "cat_incasol_mediacio_vigents_municipis.xlsx"
MEDIATION_ACTIVE_CAT = RAW / "cat_incasol_mediacio_vigents_catalunya.xlsx"
SEASONAL_MUN = RAW / "cat_incasol_temporada_mun.xlsx"
SEASONAL_CAT = RAW / "cat_incasol_temporada_catalunya.xlsx"
SALDOS_MUN = RAW / "cat_incasol_saldos_municipis.xlsx"
SALDOS_HT = RAW / "cat_incasol_saldos_habitual_temporada.xlsx"
IDESCAT = {year: RAW / f"idescat_lloguers_registre_{year}.ssv" for year in (2017, 2024, 2025)}

CITY = "08019"
DEMARCATION_PREFIX = "08"
YEARS = tuple(range(2017, 2026))
QUARTERS = ("1T", "2T", "3T", "4T")


def values(path: Path, sheet: str) -> list[tuple]:
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        return list(book[sheet].values)
    finally:
        book.close()


def mediation_series(municipal: Path, sheet: str, aggregate: Path, aggregate_sheet: str):
    """Municipal sums checked against the published Catalonia/demarcation rows."""
    m = values(municipal, sheet)
    a = values(aggregate, aggregate_sheet)
    (header,) = [r for r in m if r[:2] == ("Codi", "Municipi")]
    (region_header,) = [r for r in a if r[:4] == (None, 2025, 2024, 2023)]
    (start,) = [i for i, r in enumerate(a) if r[0] == "Demarcacions territorials"]
    demarcation = a[start + 1]
    assert demarcation[0] == "Barcelona"
    (catalonia,) = [r for r in a if r[0] == "Catalunya"]
    towns = [r for r in m if isinstance(r[0], str) and len(r[0]) == 5 and r[0].isdigit()]
    assert len({r[0] for r in towns}) == len(towns)
    (city,) = [r for r in towns if r[0] == CITY]
    out = {
        "barcelona_city": {},
        "rest_demarcation": {},
        "rest_catalonia": {},
        "barcelona_demarcation": {},
        "catalonia": {},
    }
    totals = {}
    for year in YEARS:
        i = next(i for i, value in enumerate(header) if str(value) == str(year))
        j = next(i for i, value in enumerate(region_header) if str(value).split()[0] == str(year))
        region = sum(r[i] for r in towns)
        assert region == catalonia[j], (year, region, catalonia[j])
        assert sum(r[i] for r in towns if r[0].startswith(DEMARCATION_PREFIX)) == demarcation[j]
        out["barcelona_city"][str(year)] = city[i]
        out["barcelona_demarcation"][str(year)] = demarcation[j]
        out["rest_demarcation"][str(year)] = demarcation[j] - city[i]
        out["catalonia"][str(year)] = region
        out["rest_catalonia"][str(year)] = region - city[i]
        totals[year] = [
            sum(r[i] for r in towns if r[0] == CITY),
            sum(r[i] for r in towns if r[0] != CITY),
        ]
    out["city_share_pct"] = {
        str(y): round(100.0 * out["barcelona_city"][str(y)] / out["catalonia"][str(y)], 1)
        for y in YEARS
    }
    out["municipalities"] = switch_decomposition(towns, header, (2024, 2025))
    out["_totals"] = totals
    return out, {r[0] for r in towns}


def switch_decomposition(towns, header, years):
    """Split the change into places positive in both years and switchers."""
    first, last = years[0], years[-1]
    i_first = next(i for i, value in enumerate(header) if str(value) == str(first))
    i_last = next(i for i, value in enumerate(header) if str(value) == str(last))
    both, switched = 0, 0
    for row in towns:
        a, b = row[i_first], row[i_last]
        if a > 0 and b > 0:
            both += b - a
        elif a != b:
            switched += b - a
    return {
        "positive_first": sum(1 for r in towns if r[i_first] > 0),
        "positive_last": sum(1 for r in towns if r[i_last] > 0),
        "change_both_positive": both,
        "change_switchers": switched,
        "net_change": both + switched,
    }


def seasonal_by_year(codes: set[str], years: tuple[int, ...]) -> dict:
    """Municipal seasonal deposits, checked against the territorial workbook."""
    territorial = values(SEASONAL_CAT, "Full1")
    (region_row,) = [r for r in territorial if r[0] == "Catalunya"]
    out = {"barcelona_city": {}, "catalonia": {}}
    for year in years:
        block = territorial[3].index(year)
        quarter_rows = values(SEASONAL_MUN, str(year))
        rows = [r for r in quarter_rows if r[0] in codes]
        assert {r[0] for r in rows} == codes
        assert all(r[3] == sum(r[4:8]) for r in rows)
        total = sum(r[3] for r in rows)
        assert total == sum(region_row[block : block + 4])
        out["barcelona_city"][str(year)] = next(r[3] for r in rows if r[0] == CITY)
        out["catalonia"][str(year)] = total
    out["combined_barcelona"] = {
        str(y): out["barcelona_city"][str(y)] + habitual_deposits_idescat(y) for y in years
    }
    return out


def habitual_deposits_idescat(year: int) -> int:
    with IDESCAT[year].open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream, delimiter=";"))
    (city_row,) = [r for r in rows if r and r[0].strip() == "Barcelona"]
    return int(city_row[1])


def deposit_denominators() -> dict:
    """Idescat registration counts for the three compared years."""
    out = {}
    for year in (2017, 2024, 2025):
        with IDESCAT[year].open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream, delimiter=";"))
        assert [f"Catalunya. {year}"] in rows
        (city_row,) = [r for r in rows if r and r[0].strip() == "Barcelona"]
        (region_row,) = [r for r in rows if r and r[0].strip() == "Catalunya"]
        out[str(year)] = {"barcelona_city": int(city_row[1]), "catalonia": int(region_row[1])}
    return out


def quarterly_totals(path: Path, areas: dict[str, int]) -> dict:
    """Every quarter of every area as {area: {year: {quarter: (altes, baixes, saldo)}}}."""
    rows = values(path, "dades")
    out = {area: {} for area in areas}
    for row in rows[5:]:
        if type(row[0]) is int:
            year = row[0]
        if row[1] not in QUARTERS:
            continue
        for area, column in areas.items():
            entries, cancellations, balance = row[column : column + 3]
            assert entries - cancellations == balance
            cell = (entries, cancellations, balance)
            existing = out[area].setdefault(str(year), {}).setdefault(row[1], cell)
            assert existing == cell
    return out


def add(cells: dict, area: str, periods: list[tuple[int, str]]) -> tuple[int, int, int]:
    picked = [cells[area][str(year)][quarter] for year, quarter in periods]
    return tuple(map(sum, zip(*picked, strict=True)))


def triple(values_: tuple[int, int, int]) -> dict:
    return {"entries": values_[0], "cancellations": values_[1], "balance": values_[2]}


def build() -> dict:
    flow, codes = mediation_series(
        MEDIATION_FLOW_MUN, "Mediacio_mun", MEDIATION_FLOW_CAT, "Mediacio_CAT"
    )
    active, active_codes = mediation_series(
        MEDIATION_ACTIVE_MUN, "Vigents_MUN", MEDIATION_ACTIVE_CAT, "Vigents_CAT"
    )
    assert codes == active_codes

    # The note's two window verdicts, asserted here rather than left to prose:
    # the city's share of active contracts rose every year, and 2025 is the
    # smallest total in the common window for both measures. The flow share is
    # deliberately *not* asserted to rise: it dips in 2018-2020 and 2024.
    active_shares = [active["city_share_pct"][str(year)] for year in YEARS]
    active_pairs = list(zip(active_shares, active_shares[1:], strict=False))
    assert all(later > earlier for earlier, later in active_pairs)
    for series in (flow, active):
        totals = [series["catalonia"][str(year)] for year in YEARS]
        assert totals[-1] == min(totals)
    flow_shares = [flow["city_share_pct"][str(year)] for year in YEARS]
    flow_pairs = list(zip(flow_shares, flow_shares[1:], strict=False))
    assert not all(later > earlier for earlier, later in flow_pairs)

    seasonal = seasonal_by_year(codes, (2024, 2025))
    denominators = deposit_denominators()
    seasonal["denominators"] = denominators

    latest = {
        "city_flow_2024": flow["barcelona_city"]["2024"],
        "city_flow_2025": flow["barcelona_city"]["2025"],
        "city_active_2024": active["barcelona_city"]["2024"],
        "city_active_2025": active["barcelona_city"]["2025"],
        "city_active_change": active["barcelona_city"]["2025"] - active["barcelona_city"]["2024"],
        "rest_active_change": active["rest_demarcation"]["2025"]
        - active["rest_demarcation"]["2024"],
        "demarcation_flow_2024": flow["barcelona_demarcation"]["2024"],
        "demarcation_flow_2025": flow["barcelona_demarcation"]["2025"],
        "catalonia_flow_2024": flow["catalonia"]["2024"],
        "catalonia_flow_2025": flow["catalonia"]["2025"],
        "catalonia_active_2024": active["catalonia"]["2024"],
        "catalonia_active_2025": active["catalonia"]["2025"],
        "city_active_first": active["barcelona_city"]["2017"],
        "city_active_last": active["barcelona_city"]["2025"],
        "rest_active_first": active["rest_catalonia"]["2017"],
        "rest_active_last": active["rest_catalonia"]["2025"],
        "city_share_first_pct": active["city_share_pct"]["2017"],
        "city_share_last_pct": active["city_share_pct"]["2025"],
    }
    for series in (flow, active):
        series.pop("_totals")

    scale = {}
    combined = seasonal["combined_barcelona"]
    for year in (2017, 2024, 2025):
        city_flow = flow["barcelona_city"][str(year)]
        region_flow = flow["catalonia"][str(year)]
        row = {
            "city_filings": denominators[str(year)]["barcelona_city"],
            "catalonia_filings": denominators[str(year)]["catalonia"],
            "city_per_1000": round(
                1000.0 * city_flow / denominators[str(year)]["barcelona_city"], 2
            ),
            "catalonia_per_1000": round(
                1000.0 * region_flow / denominators[str(year)]["catalonia"], 2
            ),
        }
        if year in (2024, 2025):
            row["city_combined_filings"] = combined[str(year)]
            row["catalonia_combined_filings"] = (
                denominators[str(year)]["catalonia"] + seasonal["catalonia"][str(year)]
            )
            row["city_combined_per_1000"] = round(1000.0 * city_flow / combined[str(year)], 2)
            row["catalonia_combined_per_1000"] = round(
                1000.0 * region_flow / row["catalonia_combined_filings"], 2
            )
        scale[str(year)] = row

    city_balances = quarterly_totals(SALDOS_MUN, {"barcelona_city": 2, "catalonia": 18})
    region_balances = quarterly_totals(SALDOS_HT, {"habitual": 2, "seasonal": 6, "total": 10})
    for year in (2024, 2025):
        periods = [(year, quarter) for quarter in QUARTERS]
        assert add(city_balances, "catalonia", periods) == add(region_balances, "habitual", periods)
    assert add(city_balances, "catalonia", [(2026, "1T"), (2026, "2T")]) == add(
        region_balances, "habitual", [(2026, "1T"), (2026, "2T")]
    )

    def block(periods):
        habitual = add(region_balances, "habitual", periods)
        seasonal_ = add(region_balances, "seasonal", periods)
        total = add(region_balances, "total", periods)
        assert tuple(a + b for a, b in zip(habitual, seasonal_, strict=True)) == total
        return {
            "barcelona_habitual": triple(add(city_balances, "barcelona_city", periods)),
            "catalonia_habitual": triple(habitual),
            "catalonia_seasonal": triple(seasonal_),
            "catalonia_combined": triple(total),
        }

    annual = {str(y): block([(y, q) for q in QUARTERS]) for y in (2024, 2025)}
    halves = {str(y): block([(y, "1T"), (y, "2T")]) for y in (2025, 2026)}
    last_three = [(2025, "4T"), (2026, "1T"), (2026, "2T")]
    prior_three = [(2024, "4T"), (2025, "1T"), (2025, "2T")]
    negatives = sorted(
        f"{year} {quarter}"
        for year, quarters in region_balances["seasonal"].items()
        for quarter, cell in quarters.items()
        if cell[2] < 0
    )
    assert negatives == ["2025 4T", "2026 1T", "2026 2T"], negatives

    before = annual["2024"]["barcelona_habitual"]
    after = annual["2025"]["barcelona_habitual"]
    return {
        "source_workbooks": {
            "mediation_flow_municipal": MEDIATION_FLOW_MUN.name,
            "mediation_flow_catalonia": MEDIATION_FLOW_CAT.name,
            "mediation_active_municipal": MEDIATION_ACTIVE_MUN.name,
            "mediation_active_catalonia": MEDIATION_ACTIVE_CAT.name,
            "seasonal_municipal": SEASONAL_MUN.name,
            "seasonal_catalonia": SEASONAL_CAT.name,
            "balances_municipal": SALDOS_MUN.name,
            "balances_habitual_seasonal": SALDOS_HT.name,
            "registration_exports": [IDESCAT[year].name for year in (2017, 2024, 2025)],
        },
        "years": list(YEARS),
        "mediation_flow": flow,
        "mediation_active": active,
        "latest_year": latest,
        "scale_per_1000_filings": scale,
        "seasonal_deposits": seasonal,
        "balances": {
            "annual": annual,
            "first_half": halves,
            "three_quarters": {
                "2024Q4_2025Q2": block(prior_three),
                "2025Q4_2026Q2": block(last_three),
            },
            "seasonal_quarters": {
                f"{year} {quarter}": triple(region_balances["seasonal"][str(year)][quarter])
                for year, quarter in last_three
            },
            "city_habitual_change": {
                "balance_change": after["balance"] - before["balance"],
                "entries_change": after["entries"] - before["entries"],
                "cancellations_change": after["cancellations"] - before["cancellations"],
            },
        },
        "window_verdicts": {
            "city_share_rose_every_year": True,
            "lowest_flow_year": int(min(YEARS, key=lambda year: flow["catalonia"][str(year)])),
            "lowest_active_year": int(min(YEARS, key=lambda year: active["catalonia"][str(year)])),
            "flow_share_is_monotonic": False,
        },
        "seasonal_negative_quarters": negatives,
        "_meta": ols.model_meta(
            __file__,
            [
                str(path.relative_to(ROOT))
                for path in (
                    MEDIATION_FLOW_MUN,
                    MEDIATION_FLOW_CAT,
                    MEDIATION_ACTIVE_MUN,
                    MEDIATION_ACTIVE_CAT,
                    SEASONAL_MUN,
                    SEASONAL_CAT,
                    SALDOS_MUN,
                    SALDOS_HT,
                    *IDESCAT.values(),
                )
            ],
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify artifact matches inputs")
    args = parser.parse_args()

    data = build()
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_text() != payload:
            raise SystemExit(
                "Stale artifacts/occupancy_catalonia.json; re-run occupancy_catalonia.py"
            )
        print("occupancy_catalonia: verified")
        return
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload)

    latest = data["latest_year"]
    scale = data["scale_per_1000_filings"]
    balances = data["balances"]
    print(
        f"mediation active: city {latest['city_active_first']} → {latest['city_active_last']} "
        f"(share {latest['city_share_first_pct']}% → {latest['city_share_last_pct']}%), "
        f"rest {latest['rest_active_first']} → {latest['rest_active_last']}"
    )
    print(
        f"scale 2025: city {scale['2025']['city_per_1000']} per 1,000 filings, "
        f"Catalonia {scale['2025']['catalonia_per_1000']}"
    )
    print(
        f"city habitual balance {balances['annual']['2024']['barcelona_habitual']['balance']} → "
        f"{balances['annual']['2025']['barcelona_habitual']['balance']}"
    )
    print(f"negative seasonal quarters: {data['seasonal_negative_quarters']}")


if __name__ == "__main__":
    main()
