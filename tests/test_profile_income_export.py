"""Standalone income export must not require rent or invent missing values."""

import copy
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_profile_income as ei  # noqa: E402


def source():
    return [
        {
            "codigo": f"{p:02d}001",
            "municipio": "L'Hospitalet" if p == 1 else f"Town {p}",
            "cpro": f"{p:02d}",
            "indicador": "neta_hogar",
            "anyo": y,
            "renta_eur": None if p == 1 else 0 if p == 2 else 30000,
        }
        for p in range(1, 53)
        for y in sorted(ei.YEARS)
    ]


def test_full_projection_keeps_all_null_municipalities_zero_and_original_names():
    rows = source()
    rows.append({**rows[0], "indicador": "bruta_hogar", "renta_eur": 999999})
    projected = ei.project(rows)
    assert len(projected) == 52 * 9
    assert projected[0] == {
        "codigo": "01001",
        "municipio": "L'Hospitalet",
        "cpro": "01",
        "anyo": 2015,
        "renta_neta_hogar": None,
    }
    assert all(r["renta_neta_hogar"] is None for r in projected if r["codigo"] == "01001")
    assert all(r["renta_neta_hogar"] == 0 for r in projected if r["codigo"] == "02001")
    assert not any("ratio" in k or "alquiler" in k for r in projected for k in r)


@pytest.mark.parametrize(
    "field,value",
    [
        ("codigo", "1001"),
        ("codigo", "01999"),
        ("codigo", "00123"),
        ("cpro", "02"),
        ("anyo", True),
        ("anyo", 2024),
        ("anyo", 2023.0),
        ("municipio", ""),
        ("municipio", None),
        ("renta_eur", True),
        ("renta_eur", -1),
        ("renta_eur", 1.5),
    ],
)
def test_invalid_selected_income_cells_fail(field, value):
    rows = source()
    rows[0][field] = value
    with pytest.raises(ValueError):
        ei.project(rows)


def test_duplicate_and_missing_year_records_fail_instead_of_filling():
    rows = source()
    with pytest.raises(ValueError, match="Duplicate"):
        ei.project(rows + [copy.deepcopy(rows[0])])
    with pytest.raises(ValueError, match="missing year"):
        ei.project(rows[1:])
    with pytest.raises(ValueError, match="empty"):
        ei.project([])


def pinned_fixture(tmp_path, monkeypatch):
    input_path = tmp_path / "income.parquet"
    pq.write_table(pa.Table.from_pylist(source()), input_path)
    monkeypatch.setattr(ei, "ROOT", tmp_path)
    monkeypatch.setattr(ei, "INPUT", input_path)
    monkeypatch.setattr(ei.manifest, "load", lambda: {"sha256": {"income.parquet": "pin"}})
    monkeypatch.setattr(ei.manifest, "check", lambda expected: ([], []))
    return input_path


def test_pinned_source_projection_and_proof(tmp_path, monkeypatch):
    pinned_fixture(tmp_path, monkeypatch)
    table, metadata = ei.source_rows()
    assert table.num_rows == 52 * 9
    assert metadata["input_sha"] == "pin"
    assert metadata["export_script_sha"] == ei.ols.sha_file(ei.__file__)


@pytest.mark.parametrize("case", ["unpinned", "changed", "missing"])
def test_unpinned_or_changed_input_is_rejected(tmp_path, monkeypatch, case):
    pinned_fixture(tmp_path, monkeypatch)
    if case == "unpinned":
        monkeypatch.setattr(ei.manifest, "load", lambda: {"sha256": {}})
    else:
        monkeypatch.setattr(
            ei.manifest,
            "check",
            lambda expected: (
                ["income.parquet"] if case == "missing" else [],
                ["income.parquet"] if case == "changed" else [],
            ),
        )
    with pytest.raises(ValueError, match="Unpinned|changed"):
        ei.source_rows()


def test_dropped_province_rejected_even_if_remaining_codes_have_full_years(tmp_path, monkeypatch):
    path = pinned_fixture(tmp_path, monkeypatch)
    pq.write_table(pa.Table.from_pylist([r for r in source() if r["cpro"] != "52"]), path)
    with pytest.raises(ValueError, match="province coverage"):
        ei.source_rows()


def test_export_check_is_readonly_and_detects_row_and_proof_tampering(tmp_path, monkeypatch):
    table = pa.Table.from_pylist(ei.project(source()), schema=ei.SCHEMA)
    metadata = {"input_sha": "pin", "export_script_sha": "exporter"}
    database = tmp_path / "profile_income.duckdb"
    monkeypatch.setattr(ei, "DATABASE", database)
    monkeypatch.setattr(ei, "source_rows", lambda: (table, metadata))
    monkeypatch.setattr(sys, "argv", ["export_profile_income.py"])
    ei.main()
    before = database.read_bytes()
    monkeypatch.setattr(sys, "argv", ["export_profile_income.py", "--check"])
    ei.main()
    assert database.read_bytes() == before
    with pytest.raises(ValueError, match="stale or changed"):
        ei.verify(table, {**metadata, "input_sha": "changed"})
    with duckdb.connect(str(database)) as con:
        con.execute("update municipal set renta_neta_hogar=999 where codigo='01001'")
    with pytest.raises(ValueError, match="stale or changed"):
        ei.verify(table, metadata)


def test_missing_sidecar_has_rebuild_guidance(tmp_path, monkeypatch):
    monkeypatch.setattr(ei, "DATABASE", tmp_path / "missing.duckdb")
    table = pa.Table.from_pylist(ei.project(source()), schema=ei.SCHEMA)
    with pytest.raises(ValueError, match="make profile-income"):
        ei.verify(table, {})


def test_missing_whole_selected_municipality_fails_despite_other_indicators():
    rows = source()
    original = [r for r in rows if r["codigo"] == "01001"]
    # A second municipality retains province 01 coverage after the first loses
    # all nine selected records, while its other indicator remains in source.
    rows.extend({**r, "codigo": "01002"} for r in original)
    rows = [r for r in rows if r["codigo"] != "01001"]
    rows.extend({**r, "indicador": "bruta_hogar"} for r in original)
    with pytest.raises(ValueError, match="missing year"):
        ei.project(rows)
