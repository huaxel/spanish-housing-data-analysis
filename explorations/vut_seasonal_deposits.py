"""Registered tourist dwellings in Catalonia, set against the seasonal deposit flow.

The deposit-balance note shows the regional seasonal balance turning negative in
2025-2026 while the habitual balance narrowed. The tempting explanation is that
seasonal tenancies became tourist lets, so this script puts the tourist register
(INE's experimental VTE estimates, operation 410) beside those balances for the
same region and window.

What it shows: Catalonia's registered tourist-dwelling stock moves with the
season — August peaks, February and November troughs — between 45,709 and
63,199 across the window, and stood at 51,305 in May 2026, well below its 2020
peak. There is no rise in the tourist register that would offset the seasonal
deposit fall.

What it cannot say:

- The two registers count different legal categories (``vivienda de uso
  turístico`` vs ``lloguer de temporada``); no home is linked across them, so
  this is a co-movement comparison, not a reclassification measure.
- The tourist series is a platform-based *estimate* of listings, revised with
  each snapshot, not a licence count.
- Seasonal deposits are a flow of registrations, not the stock of seasonal
  tenancies.

Outputs: artifacts/vut_seasonal_deposits.json with an `_meta` freshness key.
Use --check to verify the artifact matches its inputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

VUT_PARQUET = RAW / "parquet" / "vut_municipal.parquet"
DEPOSITS = ROOT / "artifacts" / "occupancy_catalonia.json"
ARTIFACT = ROOT / "artifacts" / "vut_seasonal_deposits.json"
REGION = "09 Cataluña"
MEASURE = "viviendas_turisticas"


def tourist_stock() -> dict[str, int]:
    """Catalonia's estimated tourist dwellings per published period."""
    rows = pq.read_table(VUT_PARQUET).to_pylist()
    cells = {
        (row["anyo"], row["periodo"]): row["valor"]
        for row in rows
        if row["nivel"] == "agregado" and row["territorio"] == REGION and row["medida"] == MEASURE
    }
    assert cells, "no Catalonia tourist-dwelling rows found"
    assert all(value == int(value) for value in cells.values())
    return {f"{year}-{period:02d}": int(value) for (year, period), value in sorted(cells.items())}


def build() -> dict:
    stock = tourist_stock()
    periods = sorted(stock)
    assert periods[0] == "2020-08", periods[0]
    peak_period = max(stock, key=lambda period: stock[period])
    trough_period = min(stock, key=lambda period: stock[period])
    latest = periods[-1]

    # A seasonal band, not a trend: the series both rises and falls repeatedly,
    # its maximum is the first snapshot, and the latest value is below the same
    # month a year earlier. August is usually the peak of its own year, but 2022
    # is not an August peak, so seasonality is described rather than asserted.
    series = [stock[period] for period in periods]
    steps = [later - earlier for earlier, later in zip(series, series[1:], strict=False)]
    assert sum(1 for step in steps if step > 0) >= 3
    assert sum(1 for step in steps if step < 0) >= 3
    assert peak_period == "2020-08", peak_period
    assert stock[latest] < stock[peak_period]
    same_month_prior = f"{int(latest[:4]) - 1}{latest[4:]}"
    assert same_month_prior in stock, same_month_prior
    assert stock[latest] < stock[same_month_prior]
    august_by_year = {period[:4]: stock[period] for period in periods if period.endswith("-08")}
    february_by_year = {period[:4]: stock[period] for period in periods if period.endswith("-02")}
    paired = [
        august_by_year[y] > february_by_year[y] for y in august_by_year if y in february_by_year
    ]
    assert sum(paired) == 3 and len(paired) == 4, paired

    quarterly = json.loads(DEPOSITS.read_text())["balances"]["seasonal_quarters"]
    seasonal_balance = {
        period.replace("T", "").replace(" ", "-"): cell["balance"]
        for period, cell in quarterly.items()
    }
    negative = sorted(period for period, value in seasonal_balance.items() if value < 0)
    assert negative, "expected negative seasonal balances in the latest quarters"

    return {
        "sources": {
            "tourist_stock": str(VUT_PARQUET.relative_to(ROOT)),
            "seasonal_deposits": str(DEPOSITS.relative_to(ROOT)),
        },
        "grain": {
            "tourist_stock": "INE VTE estimate of tourist dwellings, Cataluña, by snapshot",
            "seasonal_deposits": "INCASÒL seasonal rental-deposit balance, Cataluña, by quarter",
            "unit": "dwellings (stock) against deposit registrations (flow)",
        },
        "tourist_stock": stock,
        "seasonal_balance": seasonal_balance,
        "verdicts": {
            "peak_period": peak_period,
            "peak_value": stock[peak_period],
            "trough_period": trough_period,
            "trough_value": stock[trough_period],
            "latest_period": latest,
            "latest_value": stock[latest],
            "same_month_prior_period": same_month_prior,
            "same_month_prior_value": stock[same_month_prior],
            "august_above_february_years": sum(paired),
            "paired_years": len(paired),
            "negative_seasonal_quarters": negative,
            "tourist_stock_offsets_seasonal_fall": False,
        },
        "_meta": ols.model_meta(
            __file__,
            [
                str(VUT_PARQUET.relative_to(ROOT)),
                str(DEPOSITS.relative_to(ROOT)),
            ],
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
        print(f"{ARTIFACT.name}: tourist stock and seasonal balances match their inputs")
        return
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(expected)
    print(f"wrote {ARTIFACT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
