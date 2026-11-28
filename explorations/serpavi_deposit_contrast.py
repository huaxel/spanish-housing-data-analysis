"""Contrast Barcelona's tax-based rental contract stock with the deposit flow.

docs/occupancy_catalonia_deposit_balances.md shows the INCASÒL deposit
register's new filings falling from a 2021 peak while its net balance narrowed
towards zero. That note cannot say whether the *rented stock* shrank, because
registry flows are not a stock. SERPAVI gives an independent, tax-based count
of contracts in force per municipality and year (2011–2024), so the two
measures can be set side by side for Barcelona city:

  - INCASÒL: new habitual deposit filings and their net balance (flow, 2019+)
  - SERPAVI: rental contracts declared in the income-tax files (stock, to 2024)

They answer different questions and are not interchangeable: SERPAVI counts
contracts in force at some point in the tax year, INCASÒL counts registrations
and cancellations of deposits. Nothing here links a filing to a contract, so
the ratio of the two is not a turnover rate, a compliance rate or a share of
the market.

What it does support: through the last year both series cover (2024), the
declared contract stock was still rising while new filings fell, so the
falling deposit flow is not by itself evidence that Barcelona's rented stock
shrank.

Only Barcelona city is published as a level: SERPAVI suppresses cells for
small municipalities, so a regional sum would move with coverage as well as
with stock.

Use --check to verify the artifact matches its inputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED  # noqa: E402

ARTIFACT = ROOT / "artifacts" / "serpavi_deposit_contrast.json"
MARTS = PROCESSED / "marts.duckdb"
DEPOSITS = ROOT / "artifacts" / "occupancy_catalonia.json"
CITY = "08019"
COLLECTIVE = "BI_ALVHEPCO_TVC"
SINGLE = "BI_ALVHEPCO_TVU"


def contracts(table: duckdb.DuckDBPyConnection) -> dict[str, dict[str, int]]:
    """Barcelona city contract counts in force, by tax year."""
    rows = table.execute(
        f"""
        SELECT anyo, medida, valor
        FROM serpavi_municipal
        WHERE codigo = '{CITY}' AND medida IN ('{COLLECTIVE}', '{SINGLE}')
        ORDER BY anyo, medida
        """
    ).fetchall()
    out: dict[str, dict[str, int]] = {}
    for anyo, medida, valor in rows:
        assert valor == int(valor), (anyo, medida, valor)
        cell = out.setdefault(str(anyo), {})
        cell["collective" if medida == COLLECTIVE else "single_family"] = int(valor)
    for anyo, cell in out.items():
        assert set(cell) == {"collective", "single_family"}, (anyo, cell)
        cell["total"] = cell["collective"] + cell["single_family"]
    assert sorted(out) == [str(year) for year in range(2011, 2025)], sorted(out)[:3]
    return out


def build() -> dict:
    deposits = json.loads(DEPOSITS.read_text())
    history = deposits["balances"]["history"]
    city_deposits = history["barcelona_habitual"]
    overlap_years = sorted(set(city_deposits) & {str(year) for year in range(2011, 2025)})

    table = duckdb.connect(str(MARTS), read_only=True)
    try:
        stock = contracts(table)
    finally:
        table.close()

    totals = [stock[str(year)]["total"] for year in range(2011, 2025)]
    assert totals == sorted(totals), "SERPAVI contract stock must be non-decreasing"
    assert totals[0] < totals[-1]
    collective = [stock[str(year)]["collective"] for year in range(2011, 2025)]
    assert collective == sorted(collective)

    # A tempting use of these two series is to read the register's net balance
    # as the annual change in rented stock. Recomputing that comparison shows
    # why it is not one: in 2020 the sign differs, and in 2021-22 the balance is
    # several thousand higher than the stock change.
    reconciliation = {}
    for year in overlap_years:
        previous = str(int(year) - 1)
        if previous not in stock:
            continue
        change = stock[year]["total"] - stock[previous]["total"]
        balance = city_deposits[year]["balance"]
        reconciliation[year] = {
            "deposit_balance": balance,
            "declared_stock_change": change,
            "balance_minus_change": balance - change,
        }
    assert sorted(reconciliation) == ["2019", "2020", "2021", "2022", "2023", "2024"], sorted(
        reconciliation
    )
    conflicts = [
        year
        for year, cell in sorted(reconciliation.items())
        if cell["deposit_balance"] * cell["declared_stock_change"] < 0
    ]
    assert conflicts == ["2020"], conflicts
    closest = min(
        reconciliation, key=lambda year: abs(reconciliation[year]["balance_minus_change"])
    )
    widest = max(reconciliation, key=lambda year: abs(reconciliation[year]["balance_minus_change"]))
    assert closest == "2024" and widest == "2020", (closest, widest)
    larger = sum(
        1
        for cell in reconciliation.values()
        if abs(cell["deposit_balance"]) > abs(cell["declared_stock_change"])
    )
    # In every overlap year the register's balance exceeds the stock change in
    # magnitude, so it cannot be used as a scaled estimate of it either.
    assert larger == len(reconciliation), larger

    entries = {year: city_deposits[year]["entries"] for year in overlap_years}
    balances = {year: city_deposits[year]["balance"] for year in overlap_years}
    peak_year = max(entries, key=lambda year: entries[year])
    assert peak_year == "2021", peak_year
    overlap = overlap_years[-1]

    return {
        "sources": {
            "serpavi": "data/processed/marts.duckdb: serpavi_municipal",
            "incasol": DEPOSITS.relative_to(ROOT).as_posix(),
        },
        "grain": {
            "serpavi": "rental contracts declared in the income-tax files, in force, by tax year",
            "incasol": "new/cancelled rental-deposit registrations, by calendar year",
            "unit": "Barcelona city (codigo 08019), habitual rentals only",
        },
        "barcelona_city": {
            "serpavi_contracts": stock,
            "incasol_entries": entries,
            "incasol_balance": balances,
        },
        "overlap_years": overlap_years,
        "reconciliation": reconciliation,
        "verdicts": {
            "serpavi_stock_rose_every_year_2011_2024": True,
            "serpavi_overlap_year": int(overlap),
            "contracts_in_overlap_year": stock[overlap]["total"],
            "deposit_entries_in_overlap_year": entries[overlap],
            "contracts_2011": stock["2011"]["total"],
            "contracts_last": stock[str(max(int(year) for year in stock))]["total"],
            "contracts_growth_pct_2011_2024": round(
                100.0 * (stock["2024"]["total"] / stock["2011"]["total"] - 1), 1
            ),
            "deposit_entries_peak_year": int(peak_year),
            "deposit_entries_peak": entries[peak_year],
            "deposit_entries_fell_every_year_after_peak": True,
            "reconciliation_closest_year": int(closest),
            "reconciliation_closest_gap": reconciliation[closest]["balance_minus_change"],
            "reconciliation_widest_year": int(widest),
            "reconciliation_sign_conflicts": [int(year) for year in conflicts],
        },
        "_meta": ols.model_meta(
            __file__,
            [str(MARTS.relative_to(ROOT)), str(DEPOSITS.relative_to(ROOT))],
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_text() != expected:
            raise SystemExit(f"{ARTIFACT.relative_to(ROOT)} is stale; re-run without --check")
        print(f"{ARTIFACT.name}: contract stock and deposit flow match their inputs")
        return
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(expected)
    print(f"wrote {ARTIFACT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
