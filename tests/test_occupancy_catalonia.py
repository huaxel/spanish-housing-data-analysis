"""Accounting identities in the Catalan occupancy artifact.

These run against the pinned workbooks in data/raw, so they also fail when a
publisher reissue breaks the sheets' internal sums — the same bytes the notes
quote.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "explorations"))
import occupancy_catalonia as occ  # noqa: E402

INPUTS = [
    occ.MEDIATION_FLOW_MUN,
    occ.MEDIATION_FLOW_CAT,
    occ.MEDIATION_ACTIVE_MUN,
    occ.MEDIATION_ACTIVE_CAT,
    occ.SEASONAL_MUN,
    occ.SEASONAL_CAT,
    occ.SALDOS_MUN,
    occ.SALDOS_HT,
    *occ.IDESCAT.values(),
]


@pytest.fixture(scope="module")
def data():
    """Built artifact.

    CI runs `make test` without the git-ignored publisher files, so the
    workbook-level checks skip there; `make verify` (local, after fetch) runs the
    same build via the artifact --check. The pure-helper tests below always run.
    """
    missing = [str(path.relative_to(ROOT)) for path in INPUTS if not path.exists()]
    if missing:
        pytest.skip(f"pinned raw inputs absent: {missing[0]} (run make fetch)")
    return occ.build()


def test_switch_decomposition_splits_continuers_from_switchers():
    header = ["Codi", "Municipi", 2024, 2025]
    towns = [
        ("08001", "A", 10, 4),  # positive both years
        ("08002", "B", 0, 7),  # switcher: enters
        ("08003", "C", 5, 0),  # switcher: exits
        ("08004", "D", 3, 3),  # positive both, no change
        ("08005", "E", 0, 0),  # never positive
    ]
    out = occ.switch_decomposition(towns, header, (2024, 2025))
    assert out == {
        "positive_first": 3,
        "positive_last": 3,
        "change_both_positive": -6,
        "change_switchers": 2,
        "net_change": -4,
    }
    assert out["change_both_positive"] + out["change_switchers"] == out["net_change"]


def test_add_and_triple_sum_the_selected_quarters_only():
    cells = {"a": {"2024": {"1T": (10, 5, 5), "2T": (1, 2, -1), "3T": (0, 0, 0), "4T": (3, 1, 2)}}}
    assert occ.add(cells, "a", [(2024, "1T"), (2024, "2T")]) == (11, 7, 4)
    assert occ.add(cells, "a", [(2024, "4T")]) == (3, 1, 2)
    assert occ.triple((11, 7, 4)) == {"entries": 11, "cancellations": 7, "balance": 4}


def test_every_input_is_pinned_in_the_manifest(data):
    manifest = json.loads((ROOT / "data/input_manifest.json").read_text())
    for path, digest in data["_meta"]["data_sha"].items():
        assert manifest["sha256"][path] == digest, path


def test_artifact_is_the_committed_shape(data):
    assert data["years"][0] == 2017 and data["years"][-1] == 2025
    meta = data["_meta"]
    assert {"script_sha", "ols_sha", "data_sha"} <= set(meta)
    # 8 workbooks + the 3 Idescat registration exports.
    assert len(meta["data_sha"]) == 11
    for series in ("mediation_flow", "mediation_active"):
        for area in ("barcelona_city", "rest_demarcation", "rest_catalonia", "catalonia"):
            assert len(data[series][area]) == len(data["years"])


@pytest.mark.parametrize("series", ["mediation_flow", "mediation_active"])
def test_area_splits_add_up(data, series):
    block = data[series]
    for year in data["years"]:
        key = str(year)
        city = block["barcelona_city"][key]
        assert block["rest_demarcation"][key] + city == block["barcelona_demarcation"][key]
        assert block["rest_catalonia"][key] + city == block["catalonia"][key]


@pytest.mark.parametrize("series", ["mediation_flow", "mediation_active"])
def test_municipal_decomposition_covers_the_regional_change(data, series):
    municipalities = data[series]["municipalities"]
    total = data[series]["catalonia"]
    assert municipalities["net_change"] == total["2025"] - total["2024"]
    assert (
        municipalities["change_both_positive"] + municipalities["change_switchers"]
        == municipalities["net_change"]
    )
    assert municipalities["positive_first"] > 0


def test_city_share_is_computed_from_the_two_levels(data):
    for series in ("mediation_flow", "mediation_active"):
        block = data[series]
        for year in data["years"]:
            key = str(year)
            expected = round(100.0 * block["barcelona_city"][key] / block["catalonia"][key], 1)
            assert block["city_share_pct"][key] == expected


@pytest.mark.parametrize("window", ["annual", "first_half", "three_quarters"])
def test_balance_blocks_subtract_and_add(data, window):
    for label, block in data["balances"][window].items():
        for area, cell in block.items():
            assert cell["entries"] - cell["cancellations"] == cell["balance"], (label, area)
        habitual = block["catalonia_habitual"]
        seasonal = block["catalonia_seasonal"]
        combined = block["catalonia_combined"]
        for field in ("entries", "cancellations", "balance"):
            assert habitual[field] + seasonal[field] == combined[field]


def test_seasonal_negative_quarters_are_exactly_the_last_three(data):
    quarters = data["balances"]["seasonal_quarters"]
    assert data["seasonal_negative_quarters"] == ["2025 4T", "2026 1T", "2026 2T"]
    assert all(quarters[label]["balance"] < 0 for label in data["seasonal_negative_quarters"])
    assert list(quarters) == data["seasonal_negative_quarters"]
    # The three-quarter block is the sum of exactly those quarters.
    summed = sum(cell["entries"] for cell in quarters.values())
    block = data["balances"]["three_quarters"]["2025Q4_2026Q2"]["catalonia_seasonal"]
    assert summed == block["entries"]


def test_scale_ratios_are_the_two_counts(data):
    for year, row in data["scale_per_1000_filings"].items():
        flow = data["mediation_flow"]
        city_flow, region_flow = flow["barcelona_city"][year], flow["catalonia"][year]
        assert row["city_per_1000"] == round(1000.0 * city_flow / row["city_filings"], 2)
        assert row["catalonia_per_1000"] == round(
            1000.0 * region_flow / row["catalonia_filings"], 2
        )
        if "city_combined_per_1000" in row:
            assert row["city_combined_per_1000"] == round(
                1000.0 * city_flow / row["city_combined_filings"], 2
            )
            assert row["city_combined_filings"] > row["city_filings"]


def test_idescat_denominators_are_the_register_habitual_entries(data):
    """The Idescat export and the balance workbook publish the same habitual count."""
    annual = data["balances"]["annual"]
    for year in ("2024", "2025"):
        register = annual[year]["barcelona_habitual"]["entries"]
        idescat = data["seasonal_deposits"]["denominators"][year]["barcelona_city"]
        assert idescat == register, (year, idescat, register)


def test_city_share_of_active_contracts_rises_every_year(data):
    """The note's "rose every year" reading applies to the active portfolio."""
    shares = [data["mediation_active"]["city_share_pct"][str(year)] for year in data["years"]]
    assert all(later > earlier for earlier, later in zip(shares, shares[1:], strict=False))
    assert data["window_verdicts"]["city_share_rose_every_year"] is True


def test_flow_share_is_not_monotonic_so_the_reading_stays_with_active_contracts(data):
    shares = [data["mediation_flow"]["city_share_pct"][str(year)] for year in data["years"]]
    assert not all(later > earlier for earlier, later in zip(shares, shares[1:], strict=False))
    assert data["window_verdicts"]["flow_share_is_monotonic"] is False


def test_2025_is_the_smallest_total_in_the_window_for_both_measures(data):
    for series in ("mediation_flow", "mediation_active"):
        totals = [data[series]["catalonia"][str(year)] for year in data["years"]]
        assert totals[-1] == min(totals)
    assert data["window_verdicts"]["lowest_flow_year"] == 2025
    assert data["window_verdicts"]["lowest_active_year"] == 2025
