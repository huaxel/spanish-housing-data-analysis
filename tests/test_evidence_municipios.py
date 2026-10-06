"""Exercise the municipios page SQL without downloaded data or Node."""

import re
from pathlib import Path

import duckdb
import pytest

PAGE = Path(__file__).resolve().parents[1] / "evidence/pages/municipios.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.DOTALL))
MADRID_DEFAULTS = ["Madrid", "Parla", "Pozuelo de Alarcón", "Fuenlabrada"]
BCN_DEFAULTS = [
    "Barcelona",
    "L'Hospitalet de Llobregat",
    "Badalona",
    "Santa Coloma de Gramenet",
]


def as_list(values):
    escaped = (v.replace("'", "''") for v in values)
    return "(" + ", ".join(f"'{v}'" for v in escaped) + ")"


def render_query(name, mad=MADRID_DEFAULTS, bcn=BCN_DEFAULTS):
    sql = QUERIES[name]
    sql = sql.replace("${inputs.munis_mad.value}", as_list(mad))
    sql = sql.replace("${inputs.munis_bcn.value}", as_list(bcn))
    return sql


@pytest.fixture
def database():
    con = duckdb.connect()
    con.execute("create schema housing")
    con.execute("""
        create table housing.muni_madrid (
            municipio varchar, anyo double, eur_m2 double, poblacion integer
        )
    """)
    con.execute("""
        create table housing.muni_bcn (
            municipio varchar, anyo double, sale_eur_m2 double,
            rent_month double, rent_burden double,
            mortgage_burden double, tourist double
        )
    """)
    for municipio in MADRID_DEFAULTS + ["Alcobendas"]:
        for year in [2005, 2013, 2025]:
            con.execute(
                "insert into housing.muni_madrid values (?, ?, ?, ?)",
                [municipio, year, 3000.0 if year == 2005 else 2000.0, 100000],
            )
    for municipio in BCN_DEFAULTS + ["Sant Adrià de Besòs"]:
        for year in [2005, 2013, 2024]:
            con.execute(
                "insert into housing.muni_bcn values (?, ?, ?, ?, ?, ?, ?)",
                [
                    municipio,
                    year,
                    None if year == 2005 else 3000.0,
                    600.0,
                    None if year != 2022 else None,
                    0.5,
                    10.0,
                ],
            )
    # One burden observation inside the documented 2015-2022 window.
    con.execute(
        "insert into housing.muni_bcn"
        " values ('Barcelona', 2022, 4482.0, 1147.0, 0.51, 0.636, 10271.0)"
    )
    yield con
    con.close()


def test_madrid_series_filters_selection(database):
    rows = database.execute(render_query("serie_mad")).fetchall()
    assert {row[0] for row in rows} == set(MADRID_DEFAULTS)
    assert len(rows) == len(MADRID_DEFAULTS) * 3


def test_madrid_summary_uses_endpoints(database):
    rows = database.execute(render_query("resumen_mad")).fetchall()
    assert len(rows) == len(MADRID_DEFAULTS)
    assert all(row[1] == 2005 and row[2] == 2025 for row in rows)
    assert all(row[3] == 3000.0 and row[4] == 2000.0 for row in rows)


def test_bcn_series_and_sale_gap(database):
    rows = database.execute(render_query("serie_bcn")).fetchall()
    assert {row[0] for row in rows} == set(BCN_DEFAULTS)
    assert any(row[2] is None for row in rows)  # no sale prices before 2013


def test_bcn_summary_endpoints_and_max_burden(database):
    cells = {row[0]: row[1:] for row in database.execute(render_query("resumen_bcn")).fetchall()}
    assert cells["Barcelona"][:2] == (2013, 2024)
    # The interior 2022 observation (4482.0) must not leak into the endpoints.
    assert cells["Barcelona"][2:4] == (3000.0, 3000.0)
    assert cells["Barcelona"][8] == pytest.approx(0.51)
    assert cells["Badalona"][8] is None  # no burden observation: stays missing


def test_selector_lists_include_defaults(database):
    mad = [row[0] for row in database.execute(QUERIES["lista_mad"]).fetchall()]
    bcn = [row[0] for row in database.execute(QUERIES["lista_bcn"]).fetchall()]
    assert all(m in mad for m in MADRID_DEFAULTS)
    assert all(m in bcn for m in BCN_DEFAULTS)
