"""The contract-stock/deposit-flow contrast must stay a stock-versus-flow read.

The note uses SERPAVI's declared contract counts to rule out one reading of
the falling deposit flow: that Barcelona's rented stock shrank. These tests
hold the arithmetic of that claim and the shape that makes it safe — one
stock series that rises every year, one flow series that falls after its
peak, and no derived ratio presented as turnover.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "explorations"))
import serpavi_deposit_contrast as contrast  # noqa: E402

ARTIFACT = ROOT / "artifacts" / "serpavi_deposit_contrast.json"


@pytest.fixture(scope="module")
def data():
    if not (contrast.MARTS.exists() and ARTIFACT.exists()):
        pytest.skip(f"{ARTIFACT.name} absent; run make analysis")
    return json.loads(ARTIFACT.read_text())


def test_contract_totals_are_collective_plus_single_family(data):
    for year, cell in data["barcelona_city"]["serpavi_contracts"].items():
        assert cell["total"] == cell["collective"] + cell["single_family"], year


def test_the_stock_rises_every_year_and_the_flow_does_not(data):
    stock = [
        data["barcelona_city"]["serpavi_contracts"][str(year)]["total"]
        for year in range(2011, 2025)
    ]
    assert all(later > earlier for earlier, later in zip(stock, stock[1:], strict=False))
    entries = data["barcelona_city"]["incasol_entries"]
    peak = data["verdicts"]["deposit_entries_peak_year"]
    after = [value for year, value in sorted(entries.items()) if int(year) >= peak]
    assert after == sorted(after, reverse=True)


def test_the_verdict_numbers_come_from_the_series(data):
    verdicts = data["verdicts"]
    stock = data["barcelona_city"]["serpavi_contracts"]
    overlap = str(verdicts["serpavi_overlap_year"])
    assert verdicts["contracts_in_overlap_year"] == stock[overlap]["total"]
    assert verdicts["contracts_2011"] == stock["2011"]["total"]
    assert verdicts["contracts_last"] == stock["2024"]["total"]
    assert (
        verdicts["deposit_entries_in_overlap_year"]
        == (data["barcelona_city"]["incasol_entries"][overlap])
    )
    expected_growth = round(100.0 * (stock["2024"]["total"] / stock["2011"]["total"] - 1), 1)
    assert verdicts["contracts_growth_pct_2011_2024"] == expected_growth


def test_the_overlap_year_is_chosen_from_the_data_not_assumed(data):
    overlap = str(data["verdicts"]["serpavi_overlap_year"])
    assert overlap in data["barcelona_city"]["serpavi_contracts"]
    assert overlap in data["barcelona_city"]["incasol_entries"]
    assert overlap == max(data["overlap_years"])


def test_no_turnover_or_share_is_derived_from_the_two_series(data):
    """The note must not publish a ratio the data cannot identify."""
    text = (ROOT / "docs/occupancy_catalonia_deposit_balances.md").read_text()
    for forbidden in ("turnover rate of", "compliance rate of", "market share of"):
        assert forbidden not in text
    assert "not a turnover, compliance or" in text


def test_reconciliation_subtracts_the_two_series(data):
    for year, cell in data["reconciliation"].items():
        assert cell["balance_minus_change"] == (
            cell["deposit_balance"] - cell["declared_stock_change"]
        ), year


def test_the_reconciliation_is_reported_as_a_failure_to_reconcile(data):
    reconciliation = data["reconciliation"]
    verdicts = data["verdicts"]
    assert verdicts["reconciliation_sign_conflicts"] == [2020]
    closest = verdicts["reconciliation_closest_year"]
    assert verdicts["reconciliation_closest_gap"] == abs(
        reconciliation[str(closest)]["balance_minus_change"]
    )
    gaps = {year: abs(cell["balance_minus_change"]) for year, cell in reconciliation.items()}
    assert max(gaps, key=gaps.get) == str(verdicts["reconciliation_widest_year"])
    assert min(gaps, key=gaps.get) == str(closest)


def test_the_note_states_the_gap_rather_than_equating_the_two_series():
    text = (ROOT / "docs/occupancy_catalonia_deposit_balances.md").read_text()
    assert "net balance is not the annual change in rented stock" in text
    assert "registry activity" in text


def test_the_municipal_spread_agrees_with_its_own_selection_rule(data):
    spread = data["municipal_spread"]
    selection = spread["selection"]
    assert selection["min_contracts_last_year"] == 1000
    assert selection["years"] == [2015, 2024]
    assert spread["n_municipios"] == spread["rising"], "every selected municipality rose"
    assert 0 < spread["monotone"] <= spread["n_municipios"]
    assert spread["min_growth_pct"] > 0
    assert spread["median_growth_pct"] >= spread["min_growth_pct"]
    assert len(spread["largest"]) == 10
    stocks = [row["last"] for row in spread["largest"]]
    assert stocks == sorted(stocks, reverse=True), "largest list must be ordered by 2024 stock"


def test_the_largest_growth_figures_match_their_endpoints(data):
    for row in data["municipal_spread"]["largest"]:
        assert row["growth_pct"] == round(100.0 * (row["last"] / row["first"] - 1), 1)


def test_the_note_keeps_the_two_cautions_about_the_spread():
    prose = " ".join((ROOT / "docs/occupancy_catalonia_deposit_balances.md").read_text().split())
    assert "better declaration compliance raises the count" in prose
    assert "single-family-dominated stocks" in prose
