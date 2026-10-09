"""Offline Eurostat JSON-stat parser and sidecar contracts."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_housing_overburden as burden  # noqa: E402


def fixture(code="ilc_lvho07b", reverse=False):
    _, dim, groups = burden.DATASETS[code]
    dimensions = {
        "freq": ["A"],
        "unit": ["PC"],
        dim: list(groups),
        "geo": ["ES"],
        "time": ["2024", "2025"],
    }
    if code == "ilc_lvho07a":
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


@pytest.mark.parametrize("code", burden.DATASETS)
def test_parser_keeps_null_cells_true_zero_and_flags(code):
    rows = burden.parse(fixture(code), code)
    groups = burden.DATASETS[code][2]
    assert len(rows) == len(groups) * 2
    assert any(row["rate_pct"] == 0 and row["status"] == "b" for row in rows)
    assert any(row["rate_pct"] is None for row in rows)
    assert all(row["geo"] == "ES" for row in rows)
    assert all(row["survey_year"] in (2024, 2025) for row in rows)


def test_dimension_order_not_assumed():
    payload = fixture(reverse=True)
    payload["value"] = {"0": 12, "6": 8}
    rows = burden.parse(payload, "ilc_lvho07b")
    totals = {row["survey_year"]: row["rate_pct"] for row in rows if row["group_code"] == "TOTAL"}
    assert totals == {2024: 12, 2025: 8}


def test_dense_and_sparse_cell_containers_agree():
    payload = fixture()
    dense = copy.deepcopy(payload)
    dense["value"] = [0, 27.7] + [None] * 10
    dense["status"] = ["b"] + [None] * 11
    for dim in dense["dimension"].values():
        dim["category"]["index"] = list(dim["category"]["index"])
    assert burden.parse(dense, "ilc_lvho07b") == burden.parse(payload, "ilc_lvho07b")


@pytest.mark.parametrize("bad", [-1, 101, float("nan"), True, "27.7"])
def test_invalid_rate_fails(bad):
    payload = fixture()
    payload["value"]["0"] = bad
    with pytest.raises(ValueError):
        burden.parse(payload, "ilc_lvho07b")


def test_wrong_geography_fails():
    payload = fixture()
    payload["dimension"]["geo"]["category"]["index"] = {"FR": 0}
    with pytest.raises(ValueError, match="geo"):
        burden.parse(payload, "ilc_lvho07b")


def test_schema_drift_fails():
    payload = fixture()
    payload["id"][0] = "unexpected"
    with pytest.raises(ValueError, match="dimensions"):
        burden.parse(payload, "ilc_lvho07b")


def test_no_observed_values_fails():
    payload = fixture()
    payload["value"] = {}
    with pytest.raises(ValueError, match="no observed"):
        burden.parse(payload, "ilc_lvho07b")


def test_age_selects_total_sex_and_poverty_population_only():
    payload = fixture("ilc_lvho07a")
    payload["value"]["2"] = 99  # female cell: never part of selected total-sex data
    rows = burden.parse(payload, "ilc_lvho07a")
    assert not any(row["rate_pct"] == 99 for row in rows)


def test_total_disagreement_fails_but_groups_not_averaged():
    rows = [
        {"group_code": "TOTAL", "survey_year": 2025, "rate_pct": 7.2},
        {"group_code": "TOTAL", "survey_year": 2025, "rate_pct": 8.2},
        {"group_code": "QU1", "survey_year": 2025, "rate_pct": 27.7},
    ]
    with pytest.raises(ValueError, match="disagree"):
        burden.validate_totals(rows)
    rows[1]["rate_pct"] = 7.2
    burden.validate_totals(rows)
