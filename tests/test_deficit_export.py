"""Presentation export contracts, using synthetic complete provincial grids."""

import copy
import json
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_deficit as ed  # noqa: E402


@pytest.fixture
def inputs():
    monthly = [
        {
            "cpro": f"{p:02d}",
            "anyo": y,
            "mes": m,
            "tipo": regime,
            "estado": "Terminadas",
            "viviendas": 1,
        }
        for p in range(1, 53)
        for y in range(2021, 2026)
        for m in range(1, 13)
        for regime in ("Libre", "Protegida")
    ]
    stocks = [
        {"cpro": code, "anyo": year, "viviendas_total": value}
        for code in sorted(ed.PROVINCES)
        # Deliberately different levels at Jan-labelled years to catch an off-by-one.
        for year, value in [(2020, 1000), (2021, 1900), (2024, 1100), (2025, 1200)]
    ]
    payload = {"windows": {}}
    for key, (first, last) in ed.WINDOWS.items():
        provinces = {}
        for code in sorted(ed.PROVINCES):
            finished = 24 * (last - first + 1) * (2 if code == "51+52" else 1)
            provinces["Province " + code] = {
                "cpro": code,
                "creation": 150,
                "terminadas": finished,
                "deficit_v2": 150 - finished,
            }
        payload["windows"][key] = {
            "provinces": provinces,
            "national": {"deficit_v2": sum(p["deficit_v2"] for p in provinces.values())},
        }
    return payload, stocks, monthly


def rows(inputs):
    return ed.build_rows(*inputs)


def row(inputs, code="01", window="2021-2024"):
    return next(r for r in rows(inputs) if r["cpro"] == code and r["window_key"] == window)


def reduce_artifact(inputs, code, delta):
    payload = inputs[0]
    for window in payload["windows"].values():
        entry = window["provinces"]["Province " + code]
        entry["terminadas"] -= delta
        entry["deficit_v2"] += delta
        window["national"]["deficit_v2"] += delta


def test_december_stock_and_january_household_boundaries(inputs):
    r = row(inputs)
    assert (r["stock_start_year"], r["stock_end_year"]) == (2020, 2024)
    assert (r["household_start_year"], r["household_end_year"]) == (2021, 2025)
    assert r["stock_change"] == 100  # never stock(2025)-stock(2021)
    assert r["household_change"] == 150
    assert r["gap_stock"] == 50
    r = row(inputs, window="2021-2025")
    assert r["stock_change"] == 200 and r["household_end_year"] == 2026
    assert r["gap_stock"] == -50  # negative is not clamped


def test_complete_counts_and_ceuta_melilla_do_not_duplicate(inputs):
    assert len(rows(inputs)) == 104
    r = row(inputs)
    assert r["completion_cells_expected"] == r["completion_cells_observed"] == 96
    assert r["completions_observed"] == 96
    assert r["gap_completions"] == r["gap_completions_upper"] == 54
    pair = row(inputs, "51+52")
    assert pair["completion_cells_expected"] == 192
    assert pair["completions_observed"] == 192
    national = row(inputs, "NACIONAL")
    assert national["completion_cells_expected"] == 52 * 96
    assert national["completions_observed"] == 52 * 96
    assert national["household_change"] == 51 * 150


@pytest.mark.parametrize("absent_record", [False, True])
def test_missing_cell_is_not_zero_or_exact_gap(inputs, absent_record):
    if absent_record:
        inputs[2].pop(0)
    else:
        inputs[2][0]["viviendas"] = None
    reduce_artifact(inputs, "01", 1)
    r = row(inputs)
    assert r["completion_cells_missing"] == 1
    assert r["completions_observed"] == 95
    assert r["gap_completions"] is None
    assert r["gap_completions_upper"] == 55
    national = row(inputs, "NACIONAL")
    assert national["gap_completions"] is None
    assert national["completion_cells_missing"] == 1
    assert national["gap_completions_upper"] is not None


def test_true_zero_is_observed_and_all_missing_is_unknown(inputs):
    inputs[2][0]["viviendas"] = 0
    reduce_artifact(inputs, "01", 1)
    assert row(inputs)["completion_cells_missing"] == 0
    assert row(inputs)["gap_completions"] == 55
    for r in inputs[2]:
        if r["cpro"] == "02":
            r["viviendas"] = None
    for w in inputs[0]["windows"].values():
        entry = w["provinces"]["Province 02"]
        delta = entry["terminadas"]
        entry["terminadas"] = 0
        entry["deficit_v2"] += delta
        w["national"]["deficit_v2"] += delta
    r = row(inputs, "02")
    assert r["completions_observed"] is None
    assert r["gap_completions_upper"] is None
    assert row(inputs, "NACIONAL")["completions_observed"] is None


def test_missing_stock_endpoint_propagates_to_national_not_sample_dropping(inputs):
    inputs[1][:] = [r for r in inputs[1] if (r["cpro"], r["anyo"]) != ("01", 2020)]
    assert row(inputs)["stock_change"] is None
    national = row(inputs, "NACIONAL")
    assert national["stock_change"] is None and national["gap_stock"] is None
    assert national["household_change"] == 51 * 150


def test_zero_stock_endpoint_and_negative_household_change_are_valid(inputs):
    for r in inputs[1]:
        if r["cpro"] == "01" and r["anyo"] == 2020:
            r["viviendas_total"] = 0
    for w in inputs[0]["windows"].values():
        entry = w["provinces"]["Province 01"]
        entry["creation"] = -10
        entry["deficit_v2"] -= 160
        w["national"]["deficit_v2"] -= 160
    r = row(inputs)
    assert r["stock_change"] == 1100
    assert r["gap_stock"] == -1110
    assert r["gap_completions"] == -106


def test_duplicate_completion_and_stock_keys_fail(inputs):
    bad = copy.deepcopy(inputs)
    bad[2].append(bad[2][0])
    with pytest.raises(ValueError, match="Duplicate completion"):
        rows(bad)
    bad = copy.deepcopy(inputs)
    bad[1].append(bad[1][0])
    with pytest.raises(ValueError, match="Duplicate stock"):
        rows(bad)


@pytest.mark.parametrize("value", [-1, True, 1.5])
def test_invalid_completion_count_fails(inputs, value):
    inputs[2][0]["viviendas"] = value
    with pytest.raises(ValueError):
        rows(inputs)


def test_wrong_state_and_outside_window_never_enter_totals(inputs):
    inputs[2].append({**inputs[2][0], "estado": "Iniciadas", "viviendas": 99999})
    inputs[2].append({**inputs[2][0], "anyo": 2020, "viviendas": 99999})
    assert row(inputs)["completions_observed"] == 96


def test_artifact_coverage_and_arithmetic_drift_fail(inputs):
    bad = copy.deepcopy(inputs)
    bad[0]["windows"]["2021-2024"]["provinces"].pop("Province 01")
    with pytest.raises(ValueError, match="coverage"):
        rows(bad)
    bad = copy.deepcopy(inputs)
    bad[0]["windows"]["2021-2024"]["provinces"]["Province 01"]["terminadas"] = 999
    with pytest.raises(ValueError, match="disagree"):
        rows(bad)
    bad = copy.deepcopy(inputs)
    bad[0]["windows"]["2021-2024"]["national"]["deficit_v2"] += 1
    with pytest.raises(ValueError, match="national"):
        rows(bad)


def test_source_export_rejects_stale_artifact_before_reading_data(tmp_path, monkeypatch):
    artifact = tmp_path / "artifact.json"
    artifact.write_text(json.dumps({"_meta": {"old": "proof"}}))
    monkeypatch.setattr(ed, "ARTIFACT", artifact)
    monkeypatch.setattr(ed.ols, "model_meta", lambda *args: {"current": "proof"})
    with pytest.raises(ValueError, match="Stale"):
        ed.source_rows()


def test_atomic_export_and_readonly_check_detect_mutation(inputs, tmp_path, monkeypatch):
    table = pa.Table.from_pylist(rows(inputs), schema=ed.SCHEMA)
    database = tmp_path / "deficit.duckdb"
    metadata = {"fixture": "proof"}
    monkeypatch.setattr(ed, "DATABASE", database)
    monkeypatch.setattr(ed, "source_rows", lambda: (table, metadata))
    monkeypatch.setattr(sys, "argv", ["export_deficit.py"])
    ed.main()
    before = database.read_bytes()
    monkeypatch.setattr(sys, "argv", ["export_deficit.py", "--check"])
    ed.main()
    assert database.read_bytes() == before
    with pytest.raises(ValueError, match="stale or changed"):
        ed.verify(table, {"fixture": "changed proof"})
    with duckdb.connect(str(database)) as con:
        con.execute("update comparisons set gap_stock=123 where cpro='01'")
    with pytest.raises(ValueError, match="stale or changed"):
        ed.verify(table, metadata)


def test_changed_proof_and_missing_sidecar_fail(inputs, tmp_path, monkeypatch):
    table = pa.Table.from_pylist(rows(inputs), schema=ed.SCHEMA)
    monkeypatch.setattr(ed, "DATABASE", tmp_path / "missing.duckdb")
    with pytest.raises(ValueError, match="Missing"):
        ed.verify(table, {})
