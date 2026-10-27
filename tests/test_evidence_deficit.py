"""Offline SQL contracts for the deficit explainer controls and coverage."""

import re
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import export_deficit as ed  # noqa: E402

PAGE = ROOT / "evidence/pages/deficit.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.DOTALL))


def query(name, code="NACIONAL", window="2021-2024"):
    sql = QUERIES[name].replace("${inputs.territorio_deficit.value}", code)
    sql = sql.replace("${inputs.ventana_deficit.value}", window)
    if "${seleccion_deficit}" in sql:
        sql = sql.replace(
            "${seleccion_deficit}", "(" + query("seleccion_deficit", code, window) + ")"
        )
    return sql


@pytest.fixture
def database():
    rows = []
    for window, (first, last) in ed.WINDOWS.items():
        for code, name, created, stock, completed, missing in [
            ("01", "First province", -10, 20, 0, 0),
            ("02", "Incomplete province", 100, 50, 60, 1),
            ("NACIONAL", "España (suma provincial)", 90, 70, 60, 1),
        ]:
            rows.append(
                {
                    "window_key": window,
                    "cpro": code,
                    "provincia": name,
                    "flow_start": first,
                    "flow_end": last,
                    "stock_start_year": first - 1,
                    "stock_end_year": last,
                    "household_start_year": first,
                    "household_end_year": last + 1,
                    "household_change": created,
                    "stock_change": stock,
                    "completions_observed": completed,
                    "completion_cells_expected": 96,
                    "completion_cells_observed": 96 - missing,
                    "completion_cells_missing": missing,
                    "gap_stock": created - stock,
                    "gap_completions": None if missing else created - completed,
                    "gap_completions_upper": created - completed,
                }
            )
    con = duckdb.connect()
    con.execute("create schema deficit")
    con.register("fixture", pa.Table.from_pylist(rows, schema=ed.SCHEMA))
    con.execute("create table deficit.comparisons as select * from fixture")
    yield con
    con.close()


@pytest.mark.parametrize("name", list(QUERIES))
def test_all_page_queries_execute(database, name):
    database.execute(query(name)).fetchall()


def test_selection_uses_code_and_window_not_province_name(database):
    rows = database.execute(query("seleccion_deficit", "01", "2021-2025")).fetchall()
    assert len(rows) == 1 and rows[0][:3] == ("2021-2025", "01", "First province")
    assert len(database.execute(query("ventanas_deficit")).fetchall()) == 2
    assert database.execute(query("territorios_deficit")).fetchone()[0] == "NACIONAL"


def test_period_labels_do_not_gain_decimal_year_suffixes(database):
    # Evidence exports integer SQL types as browser-queryable doubles.
    database.execute("alter table deficit.comparisons alter column flow_start type double")
    database.execute("alter table deficit.comparisons alter column flow_end type double")
    rows = database.execute(query("ventanas_deficit")).fetchall()
    assert [r[-1] for r in rows] == [
        "2021–2024 (años completos)",
        "2021–2025 (años completos)",
    ]


def test_partial_totals_are_not_plotted_as_exact_gaps(database):
    rows = database.execute(query("saldos_deficit")).fetchall()
    assert rows[0][1] == 20
    assert rows[1][1] is None
    counts = database.execute(query("cantidades_deficit")).fetchall()
    assert [r[1] for r in counts] == [90, 70, 60]
    assert database.execute(query("cobertura_deficit")).fetchone() == (
        96,
        95,
        1,
        "Incompleta: suma publicada, no total",
    )


def test_published_zero_negative_growth_and_negative_gaps_remain_visible(database):
    counts = database.execute(query("cantidades_deficit", "01")).fetchall()
    assert [r[1] for r in counts] == [-10, 20, 0]
    assert [r[1] for r in database.execute(query("saldos_deficit", "01")).fetchall()] == [-30, -10]
    assert (
        database.execute(query("cobertura_deficit", "01")).fetchone()[-1]
        == "Completa en la ventana"
    )


def test_missing_stock_is_not_backfilled_or_replaced_by_zero(database):
    database.execute(
        "update deficit.comparisons set stock_change=NULL, gap_stock=NULL where cpro='01'"
    )
    assert database.execute(query("cantidades_deficit", "01")).fetchall()[1][1] is None
    assert database.execute(query("saldos_deficit", "01")).fetchone()[1] is None


def test_window_comparison_keeps_both_windows_and_province_table_excludes_national(database):
    windows = database.execute(query("ventanas_comparadas_deficit", "01")).fetchall()
    assert [r[0] for r in windows] == ["2021-2024", "2021-2025"]
    provinces = database.execute(query("provincias_deficit")).fetchall()
    assert {r[0] for r in provinces} == {"01", "02"}
    assert any(r[-1] == 1 and r[-3] is None for r in provinces)
    assert any(r[2] < 0 for r in provinces)


def test_explainer_links_metadata_and_caveats():
    assert "(/deficit/)" in (ROOT / "evidence/pages/index.md").read_text()
    assert "(/deficit/)" in (ROOT / "evidence/pages/acceso.md").read_text()
    assert '"deficit/index.html"' in (ROOT / "scripts/fix_build_meta.py").read_text()
    page = PAGE.read_text()
    normalized = " ".join(page.split())
    for text in (
        "Ninguna de las dos restas cuenta viviendas disponibles ni hogares sin casa",
        "Una celda ausente no es cero",
        "cota superior del saldo",
        "31 de diciembre de 2020",
        "1 de enero de 2025",
        "no tasas anuales ni una previsión",
        "no se dibuja una barra",
    ):
        assert text in normalized
    for route in re.findall(r"\]\(/([\w-]+)/\)", page):
        assert (ROOT / "evidence/pages" / f"{route}.md").exists()
