"""Offline uncertainty-page SQL contracts and scalar Slider wiring."""

import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "evidence/pages/incertidumbre.md"
TEXT = PAGE.read_text()
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", TEXT, re.DOTALL))


def query(name, magnitude=0.5, model="sale"):
    sql = QUERIES[name].replace("${inputs.magnitud}", str(magnitude))
    sql = sql.replace("${inputs.inv_modelo.value}", model)
    return sql.replace("${modelos_turismo}", f"({QUERIES['modelos_turismo']})")


@pytest.fixture
def database():
    with duckdb.connect() as con:
        con.execute("""
            create schema inference;
            create table inference.tourism_panel (
                model_key varchar, outcome varchar, specification varchar,
                b double, se double, normal_lo double, normal_hi double,
                wild_p_zero double, n integer, clusters integer, bootstrap_reps integer
            );
            insert into inference.tourism_panel values
            ('rent', 'Alquiler', 'Solo turismo', 0, 0.23, -0.44, 0.46, 0.96, 2109, 253, 1999),
            ('sale', 'Venta', 'Solo turismo', -0.2, 0.31, -0.82, 0.40, 0.49, 1159, 130, 1999),
            ('edge', 'Venta', 'Frontera', 0, 0.25, -0.5, 0.5, 0.8, 100, 10, 1999),
            ('positive', 'Venta', 'Positivo', 0.5, 0.05, 0.4, 0.6, 0.1, 100, 10, 1999)
        """)
        con.execute("""
            create table inference.tourism_inversion (
                model_key varchar, outcome varchar, specification varchar,
                candidate_c double, wild_p double, keep_95 boolean
            );
            insert into inference.tourism_inversion values
            ('sale', 'Venta', 'Solo turismo', -0.5, 0.02, false),
            ('sale', 'Venta', 'Solo turismo', 0.0, 0.6, true),
            ('sale', 'Venta', 'Solo turismo', 0.5, 0.02, false)
        """)
        con.execute("""
            create table inference.tourism_inversion_meta (
                model_key varchar, outcome varchar, specification varchar,
                n integer, clusters integer, b double, se double,
                accepted_min_c double, accepted_max_c double,
                accepted_count integer, warnings varchar
            );
            insert into inference.tourism_inversion_meta values
            ('sale', 'Venta', 'Solo turismo', 1159, 130, -0.2, 0.31,
             -0.5, 0.5, 1, '')
        """)
        yield con


def test_source_table_preserves_units_and_separates_zero_null_p(database):
    rows = database.execute(query("modelos_turismo")).fetchall()
    assert len(rows) == 4
    assert rows[0][0] == "rent"
    assert rows[0][3:8] == (0, 0.23, -0.44, 0.46, 0.96)
    assert rows[0][-3:] == (2109, 253, 1999)


def test_containment_uses_both_interval_endpoints_not_beta_or_p(database):
    rows = database.execute(query("banda_turismo")).fetchall()
    cells = {row[1]: row for row in rows}
    assert cells["Solo turismo"][0] == "Venta"  # outcome remains separate
    rent = next(row for row in rows if row[0] == "Alquiler")
    sale = next(row for row in rows if row[0] == "Venta" and row[1] == "Solo turismo")
    assert rent[-1].startswith("Sí:") and sale[-1].startswith("No:")
    assert rent[-2] == 0.46 and sale[-2] == 0.82
    assert cells["Frontera"][-1].startswith("Sí:")  # exact boundary included
    assert cells["Positivo"][-1].startswith("No:")


def test_wider_band_does_not_change_estimates_or_p_values(database):
    before = database.execute(query("modelos_turismo")).fetchall()
    wider = database.execute(query("banda_turismo", 1)).fetchall()
    assert all(row[-1].startswith("Sí:") for row in wider)
    narrower = database.execute(query("banda_turismo", 0.1)).fetchall()
    assert all(row[-1].startswith("No:") for row in narrower)
    assert database.execute(query("modelos_turismo")).fetchall() == before


@pytest.mark.parametrize("magnitude", [-1, 0, 0.09, 2.1, None, "", "nan", "inf"])
def test_invalid_magnitude_returns_no_comparison(database, magnitude):
    assert database.execute(query("banda_turismo", magnitude)).fetchall() == []


def test_scalar_control_links_and_metadata_contract():
    assert "${inputs.magnitud}" in TEXT and "${inputs.magnitud.value}" not in TEXT
    assert "(/incertidumbre/)" in (ROOT / "evidence/pages/acceso.md").read_text()
    assert '"incertidumbre/index.html"' in (ROOT / "scripts/fix_build_meta.py").read_text()
    assert '"docs/uncertainty.md"' in (ROOT / "scripts/audit_doc_numbers.py").read_text()


def test_inversion_candidates_are_filterable_tested_points(database):
    for source in ("inversion_candidatos", "inversion_resumen"):
        database.execute(query(source)).fetchall()


def test_inversion_grid_contract_and_null_warnings():
    text = (ROOT / "evidence/pages/incertidumbre.md").read_text()
    assert "41 candidatos" in text and "pasos de **0,1**" in text
    assert "de **-2,0 a +2,0**" in text
    assert "1.999 réplicas" in text
    for phrase in [
        "no un\nintervalo de confianza continuo",
        "no es una prueba de equivalencia",
        "reproduce exactamente el `wild_p_zero`",
        "nulo, no cero",
    ]:
        assert phrase.replace("\n", " ") in text.replace("\n", " ")
    assert "${inputs.inv_modelo.value}" in text


def test_inversion_candidates_filter_and_summary_ranges(database):
    rows = database.execute(query("inversion_candidatos", model="sale")).fetchall()
    assert rows == [(-0.5, 0.02, "Rechazada"), (0.0, 0.6, "No rechazada"), (0.5, 0.02, "Rechazada")]
    summary = database.execute(query("inversion_resumen")).fetchall()
    assert summary[0][0:3] == ("Venta", "Solo turismo", -0.2)
    assert summary[0][5:8] == (0.5, 1, "")
