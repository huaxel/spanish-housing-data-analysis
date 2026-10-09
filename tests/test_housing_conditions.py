"""Offline Eurostat housing-conditions parser and sidecar contracts."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_housing_conditions as cond  # noqa: E402


def fixture(code="ilc_lvho05q", reverse=False):
    _, _, dim, groups = cond.DATASETS[code]
    dimensions = {
        "freq": ["A"],
        "unit": ["PC"],
        dim: list(groups),
        "geo": ["ES"],
        "time": ["2024", "2025"],
    }
    if code in cond.THREE_WAY:
        dimensions["sex"] = ["T", "F"]
        dimensions["rskpovth"] = ["TOTAL", "B_60"]
    if reverse:
        dimensions = dict(reversed(list(dimensions.items())))
    return {
        "id": list(dimensions),
        "size": [len(v) for v in dimensions.values()],
        "dimension": {
            k: {
                "category": {
                    "index": {code: i for i, code in enumerate(v)},
                    "label": {code: code for code in v},
                }
            }
            for k, v in dimensions.items()
        },
        "value": {"0": 0.0, "1": 27.7},
        "status": {"0": "b"},
        "updated": "2026-09-17",
    }


@pytest.mark.parametrize("code", cond.DATASETS)
def test_parser_keeps_null_cells_true_zero_and_flags(code):
    rows = cond.parse(fixture(code), code)
    _, _, _, groups = cond.DATASETS[code]
    assert len(rows) == len(groups) * 2
    assert any(row["rate_pct"] == 0 and row["status"] == "b" for row in rows)
    assert any(row["rate_pct"] is None for row in rows)
    assert all(row["geo"] == "ES" for row in rows)
    assert all(row["survey_year"] in (2024, 2025) for row in rows)
    assert all(row["table"] == cond.DATASETS[code][0] for row in rows)


def test_dimension_order_not_assumed():
    payload = fixture(reverse=True)
    payload["value"] = {"0": 12, "6": 8}
    rows = cond.parse(payload, "ilc_lvho05q")
    totals = {row["survey_year"]: row["rate_pct"] for row in rows if row["group_code"] == "TOTAL"}
    assert totals == {2024: 12, 2025: 8}


def test_dense_and_sparse_cell_containers_agree():
    payload = fixture()
    dense = copy.deepcopy(payload)
    dense["value"] = [0, 27.7] + [None] * 10
    dense["status"] = ["b"] + [None] * 11
    for dim in dense["dimension"].values():
        dim["category"]["index"] = list(dim["category"]["index"])
    assert cond.parse(dense, "ilc_lvho05q") == cond.parse(payload, "ilc_lvho05q")


@pytest.mark.parametrize("bad", [-1, 101, float("nan"), True, "27.7"])
def test_invalid_rate_fails(bad):
    payload = fixture()
    payload["value"]["0"] = bad
    with pytest.raises(ValueError):
        cond.parse(payload, "ilc_lvho05q")


def test_wrong_geography_fails():
    payload = fixture()
    payload["dimension"]["geo"]["category"]["index"] = {"FR": 0}
    with pytest.raises(ValueError, match="geo"):
        cond.parse(payload, "ilc_lvho05q")


def test_schema_drift_fails():
    payload = fixture()
    payload["id"][0] = "unexpected"
    with pytest.raises(ValueError, match="dimensions"):
        cond.parse(payload, "ilc_lvho05q")


def test_no_observed_values_fails():
    payload = fixture()
    payload["value"] = {}
    with pytest.raises(ValueError, match="no observed"):
        cond.parse(payload, "ilc_lvho05q")


def test_three_way_selects_total_sex_and_poverty_only():
    payload = fixture("ilc_lvho05a")
    payload["value"]["2"] = 99  # female cell: never part of selected total-sex data
    rows = cond.parse(payload, "ilc_lvho05a")
    assert not any(row["rate_pct"] == 99 for row in rows)


def test_missing_group_fails():
    payload = fixture("ilc_lvho50c")
    del payload["dimension"]["tenure"]["category"]["index"]["RENT"]
    payload["dimension"]["tenure"]["category"]["label"].pop("RENT")
    payload["size"][2] = 2
    with pytest.raises(ValueError, match="missing required groups"):
        cond.parse(payload, "ilc_lvho50c")


def test_total_disagreement_fails():
    rows = [
        {
            "dataset": "ilc_lvho05a",
            "table": "overcrowding",
            "group_code": "TOTAL",
            "survey_year": 2025,
            "rate_pct": 7.2,
        },
        {
            "dataset": "ilc_lvho05q",
            "table": "overcrowding",
            "group_code": "TOTAL",
            "survey_year": 2025,
            "rate_pct": 8.2,
        },
    ]
    with pytest.raises(ValueError, match="disagree"):
        cond.validate_totals(rows)
    rows[1]["rate_pct"] = 7.2
    cond.validate_totals(rows)


def test_single_total_source_fails():
    rows = [
        {
            "dataset": "ilc_lvho05a",
            "table": "overcrowding",
            "group_code": "TOTAL",
            "survey_year": 2025,
            "rate_pct": 7.2,
        },
    ]
    with pytest.raises(ValueError, match="Single TOTAL source"):
        cond.validate_totals(rows)


def test_median_tables_excluded_from_totals():
    rows = [
        {
            "dataset": "ilc_lvho08a",
            "table": "burden_median",
            "group_code": "TOTAL",
            "survey_year": 2025,
            "rate_pct": 12.0,
        },
        {
            "dataset": "ilc_lvho08b",
            "table": "burden_median",
            "group_code": "DEG1",
            "survey_year": 2025,
            "rate_pct": 99.0,
        },
    ]
    cond.validate_totals(rows)  # no TOTAL pair to compare: must not raise
