"""Offline synthetic contracts for the benchmark-only ECV prototype."""

from __future__ import annotations

import copy
import csv
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "ecv_benchmarks", Path(__file__).parents[1] / "scripts/assess_ecv_benchmarks.py"
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.mark.parametrize(
    ("cost", "income", "allowance", "expected"),
    [
        (0, -1, 0, False),
        (1, 0, 0, True),
        (1, -1, 0, True),
        (1, 30, 0, False),
        (1, 29, 0, True),
        (1, 0, 12, False),
        (10, 1000, 100, False),
    ],
)
def test_official_burden_edges(cost, income, allowance, expected):
    assert module.burden(cost, income, allowance) is expected


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_rejected(value):
    with pytest.raises(ValueError):
        module.number(str(value))
    with pytest.raises(ValueError):
        module.burden(value, 100, 0)


def tables():
    result = {"d": [], "h": [], "r": []}
    for hid, members, income, cost in [
        (1, 2, "0", "100"),
        (2, 1, "10000", "0"),
        (3, 1, "20000", ""),
    ]:
        result["d"].append(
            {"DB010": "2025", "DB020": "ES", "DB030": str(hid), "DB090": "2", "DB090_F": "1"}
        )
        result["h"].append(
            {
                "HB010": "2025",
                "HB020": "ES",
                "HB030": str(hid),
                "HX040": str(members),
                "HY020": income,
                "HY020_F": "51",
                "HY070G": "0",
                "HY070G_F": "55",
                "HH070": cost,
                "HH070_F": "-1" if not cost else "1",
                "HH021": "3",
                "HH021_F": "1",
            }
        )
        for ordinal in range(1, members + 1):
            result["r"].append(
                {
                    "RB010": "2025",
                    "RB020": "ES",
                    "RB030": str(hid * 100 + ordinal),
                    "RB050": "3",
                    "RB050_F": "1",
                    "RB081": "-1" if ordinal == 2 else "30",
                    "RB081_F": "1",
                    "RB090": "1",
                    "RB090_F": "1",
                }
            )
    return result


def test_population_weighting_missingness_newborns_and_imputation():
    report = module.calculate(tables(), 2025)
    total = next(
        r for r in report["cells"] if r["breakdown"] == "age" and r["group_code"] == "TOTAL"
    )
    assert total["rate_pct"] == pytest.approx(200 / 3)
    assert total["sample_persons"] == 3
    assert total["person_weight"] == 9
    assert report["counts"]["persons"] == 4
    assert report["counts"]["missing_cost_persons"] == 1
    assert report["counts"]["missing_cost_households"] == 1
    assert report["counts"]["newborn_reference_ages_mapped_to_zero"] == 1
    assert report["counts"]["known_cost_nonpositive_net_income_persons"] == 2
    assert report["publication_ready"] is False
    assert report["quintile_methodology_status"].startswith("unresolved;")
    assert all(r["breakdown"] != "triple_cross" for r in report["cells"])
    assert "RB030" not in json.dumps(report)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "orphan",
        "members",
        "country",
        "weight",
        "weight_flag",
        "income_flag",
        "age_flag",
    ],
)
def test_structural_failures(mutation):
    data = tables()
    if mutation == "duplicate":
        data["r"].append(copy.deepcopy(data["r"][0]))
    elif mutation == "orphan":
        data["r"][0]["RB030"] = "9901"
    elif mutation == "members":
        data["h"][0]["HX040"] = "1"
    elif mutation == "country":
        data["h"][0]["HB020"] = "FR"
    elif mutation == "weight":
        data["r"][0]["RB050"] = "0"
    elif mutation == "weight_flag":
        data["d"][0]["DB090_F"] = "-1"
    elif mutation == "income_flag":
        data["h"][0]["HY020_F"] = "1"
    else:
        data["r"][0]["RB081_F"] = "-1"
    with pytest.raises(ValueError):
        module.calculate(data, 2025)


def test_candidate_housing_quantiles_and_national_poverty_reference_are_separate():
    base = tables()
    data = {kind: [] for kind in "dhr"}
    # Under this diagnostic candidate, a high-weight cost-missing household
    # affects the national poverty median but not the housing-QPB population.
    # This tests the implementation, not which QPB convention Eurostat intended.
    for hid, income in enumerate([10, 20, 30, 40, 50, 1000], start=1):
        for kind, prefix in [("d", "DB"), ("h", "HB"), ("r", "RB")]:
            row = copy.deepcopy(base[kind][0])
            row[prefix + "030"] = str(hid * 100 + 1 if kind == "r" else hid)
            if kind == "h":
                row.update(HX040="1", HY020=str(income), HH070="1" if hid == 1 else "0")
                if hid == 6:
                    row.update(HH070="", HH070_F="-1")
            elif kind == "r":
                row.update(RB050="5" if hid == 6 else "1")
            data[kind].append(row)
    report = module.calculate(data, 2025)
    cells = {(r["breakdown"], r["group_code"]): r for r in report["cells"]}
    assert cells["income", "QU1"]["sample_persons"] == 1
    assert cells["income", "QU1"]["rate_pct"] == 100
    # National median uses the missing-cost person's income: all five eligible
    # people are below its poverty threshold. Recomputing after exclusion fails.
    assert cells["age_poverty", "TOTAL:B_60"]["sample_persons"] == 5
    assert report["counts"]["poverty_reference_persons"] == 6
    assert report["counts"]["housing_quintile_reference_persons"] == 5


def test_missing_sex_cannot_enter_housing_classification():
    data = tables()
    data["r"][0]["RB090_F"] = "-1"
    with pytest.raises(ValueError, match="sex"):
        module.calculate(data, 2025)


def test_quantiles_and_age_conventions():
    assert module.weighted_cut([(0, 3), (10, 1)], 0.5) == 0
    assert module.weighted_cut([(0, 1), (10, 1)], 0.5) == 5
    assert module.age_groups(-1) == ["TOTAL"]
    assert module.age_groups(18) == ["TOTAL", "Y18-24", "Y18-64"]
    assert module.age_groups(65) == ["TOTAL", "Y_GE65"]
    with pytest.raises(ValueError):
        module.age_groups(-2)
    with pytest.raises(ValueError):
        module.weighted_cut([(0, 0)], 0.5)


def test_mismatch_and_missing_benchmarks_never_certify_publication():
    report = {
        "publication_ready": False,
        "cells": [{"breakdown": "income", "group_code": "QU1", "rate_pct": 27.751189}],
    }
    benchmark = {"breakdown": "income", "group_code": "QU1", "rate_pct": 27.7, "status": "b"}
    output = module.compare(report, [benchmark])
    assert not output["all_benchmarks_match_rounding"]
    assert output["comparisons"][0]["published_status"] == "b"
    assert not output["publication_ready"]
    benchmark["rate_pct"] = 27.8
    assert module.compare(report, [benchmark])["all_benchmarks_match_rounding"]
    assert not report["publication_ready"]
    benchmark["rate_pct"] = None
    assert not module.compare(report, [benchmark])["all_benchmarks_match_rounding"]
    assert not module.compare(report, [])["all_benchmarks_match_rounding"]


def archive(tmp_path, unknown_column=False):
    path = tmp_path / "archive.zip"
    data = tables()
    layouts = io.BytesIO()
    with zipfile.ZipFile(layouts, "w") as z:
        for kind in "dhr":
            z.writestr(
                f"dr_ECV_SM_T{kind}_2025.json",
                json.dumps({"layout": [{"name": name} for name in data[kind][0]]}),
            )
    with zipfile.ZipFile(path, "w") as outer:
        outer.writestr("disreg_ecv25.zip", layouts.getvalue())
        for kind in "dhr":
            fields = list(data[kind][0])
            if kind == "h":
                fields += sorted(module.H_MODULE_COLUMNS)
            if unknown_column and kind == "r":
                fields += ["UNKNOWN"]
            text = io.StringIO()
            writer = csv.DictWriter(text, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data[kind])
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, "w") as inner:
                inner.writestr(f"CSV/esudb25{kind}.csv", text.getvalue())
            outer.writestr(f"ECV_T{kind}_2025.zip", payload.getvalue())
    return path


def test_release_schema_and_explicit_module_extension(tmp_path):
    loaded = module.load_archive(archive(tmp_path), 2025)
    assert module.calculate(loaded, 2025)["counts"]["persons"] == 4
    with pytest.raises(ValueError, match="base layout"):
        module.load_archive(archive(tmp_path, unknown_column=True), 2025)
    with pytest.raises(ValueError, match="year"):
        module.load_archive(tmp_path / "archive.zip", 2024)


def test_cli_numeric_failure_is_nonzero(tmp_path, monkeypatch, capsys):
    import duckdb

    source = archive(tmp_path)
    database = tmp_path / "benchmarks.duckdb"
    with duckdb.connect(str(database)) as con:
        con.execute(
            "CREATE TABLE overburden (breakdown VARCHAR, group_code VARCHAR, "
            "rate_pct DOUBLE, status VARCHAR, survey_year INTEGER)"
        )
        con.execute(
            "CREATE TABLE overburden_age_poverty (age_code VARCHAR, "
            "poverty_code VARCHAR, rate_pct DOUBLE, status VARCHAR, survey_year INTEGER)"
        )
        groups = {
            "age": module.AGES,
            "income": ["TOTAL", *(f"QU{i}" for i in range(1, 6))],
            "tenure": ["TOTAL", *sorted(set(module.TENURES.values()))],
        }
        con.executemany(
            "INSERT INTO overburden VALUES (?, ?, ?, ?, ?)",
            [(kind, code, 1.0, "", 2025) for kind, codes in groups.items() for code in codes],
        )
        con.executemany(
            "INSERT INTO overburden_age_poverty VALUES (?, ?, ?, ?, ?)",
            [(age, poverty, 1.0, "", 2025) for age in module.AGES for poverty in ["A_60", "B_60"]],
        )
    monkeypatch.setattr(
        "sys.argv", ["prototype", "--archive", str(source), "--benchmarks", str(database)]
    )
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 1
    report = json.loads(capsys.readouterr().out)
    assert len(report["comparisons"]) == 26
    assert not report["all_benchmarks_match_rounding"]
    assert not report["publication_ready"]
    assert set(report["input_sha256"]) == {"archive", "benchmarks"}
    assert len(report["prototype_sha256"]) == 64
    success = {
        "publication_ready": False,
        "cells": [
            {
                "breakdown": row["breakdown"],
                "group_code": row["group_code"],
                "rate_pct": row["published_rate_pct"],
            }
            for row in report["comparisons"]
        ],
    }
    monkeypatch.setattr(module, "calculate", lambda tables, year: success)
    with pytest.raises(SystemExit) as passing:
        module.main()
    assert passing.value.code == 0
    numeric_pass = json.loads(capsys.readouterr().out)
    assert numeric_pass["all_benchmarks_match_rounding"]
    assert not numeric_pass["publication_ready"]


def test_duplicate_archive_members_rejected(tmp_path):
    path = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("a", "one")
        with pytest.warns(UserWarning):
            z.writestr("a", "two")
    with zipfile.ZipFile(path) as z, pytest.raises(ValueError, match="Duplicate"):
        module.member(z, "a")
