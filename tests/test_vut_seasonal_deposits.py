"""The tourist register must not be read as offsetting the seasonal fall.

The deposit note uses Catalonia's registered tourist dwellings to rule out one
explanation of the falling seasonal balance: that seasonal tenancies became
tourist lets. These tests hold the facts that claim rests on — a seasonal band
with no rise, the latest value below its own year-earlier value — and keep the
two registers from being equated.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "explorations"))
import vut_seasonal_deposits as vut  # noqa: E402

ARTIFACT = ROOT / "artifacts/vut_seasonal_deposits.json"


@pytest.fixture(scope="module")
def data():
    if not (vut.VUT_PARQUET.exists() and ARTIFACT.exists()):
        pytest.skip(f"{ARTIFACT.name} absent; run make analysis")
    return json.loads(ARTIFACT.read_text())


def test_the_series_is_a_band_not_a_trend(data):
    stock = data["tourist_stock"]
    periods = sorted(stock)
    steps = [stock[b] - stock[a] for a, b in zip(periods, periods[1:], strict=False)]
    assert any(step > 0 for step in steps) and any(step < 0 for step in steps)
    assert periods[0] == data["verdicts"]["peak_period"]
    assert stock[periods[-1]] < stock[periods[0]]


def test_the_latest_value_is_below_the_same_month_a_year_earlier(data):
    verdicts = data["verdicts"]
    stock = data["tourist_stock"]
    assert verdicts["same_month_prior_value"] == stock[verdicts["same_month_prior_period"]]
    assert verdicts["latest_value"] == stock[verdicts["latest_period"]]
    assert verdicts["latest_value"] < verdicts["same_month_prior_value"]


def test_the_verdict_refuses_the_offset_reading(data):
    assert data["verdicts"]["tourist_stock_offsets_seasonal_fall"] is False
    prose = " ".join((ROOT / "docs/occupancy_catalonia_deposit_balances.md").read_text().split())
    assert "no rise in the tourist register that would offset" in prose
    assert "co-movement comparison" in prose
    assert "different legal categories" in prose


def test_negative_seasonal_quarters_are_read_from_the_deposit_artifact(data):
    negative = data["verdicts"]["negative_seasonal_quarters"]
    balances = data["seasonal_balance"]
    assert negative == sorted(period for period, value in balances.items() if value < 0)
    assert negative
