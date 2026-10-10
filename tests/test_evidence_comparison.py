"""Exercise the page's SQL contract without downloaded housing data or Node."""

import re
from pathlib import Path

import duckdb
import pytest

PAGE = Path(__file__).resolve().parents[1] / "evidence/pages/comparar.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.DOTALL))
MADRID = "Madrid, Comunidad de"
VALENCIA = "Comunitat Valenciana"


def render_query(name, a=MADRID, b=VALENCIA, start=2007, end=2025, _stack=()):
    sql = QUERIES[name]
    values = {
        "territorio_a": a,
        "territorio_b": b,
        "desde": str(start),
        "hasta": str(end),
    }
    for key, value in values.items():
        sql = sql.replace("${inputs." + key + ".value}", value)
    for token in ("${comparacion}", "${resumen_periodo}"):
        if token in sql:
            if token in _stack:
                raise ValueError(f"Circular query reference: {token}")
            rendered = render_query(token[2:-1], a, b, start, end, _stack + (token,))
            sql = sql.replace(token, f"({rendered})")
    return sql


@pytest.fixture
def database():
    con = duckdb.connect()
    con.execute("create schema housing")
    con.execute("""
        create table housing.mart_ccaa_anual (
            ccaa varchar, anyo double, ipv_general double,
            viv_por_1000_hab double, viv_por_hogar double,
            eur_m2_libre double, afford_90m2_years double,
            share_20_34 double, hip_viv_num integer, pop_source varchar
        )
    """)
    for territory in [MADRID, VALENCIA, "Nacional", "Andalucía"]:
        for year in [2007, 2021, 2025]:
            con.execute(
                "insert into housing.mart_ccaa_anual values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    territory,
                    year,
                    80.0 if year != 2025 else 100.0,
                    550.0,
                    None if year == 2007 else 1.4,
                    2000.0,
                    None if year == 2025 else 5.0,
                    0.2,
                    100,
                    "padron" if year <= 2021 else "ecp",
                ],
            )
    yield con
    con.close()


@pytest.mark.parametrize(
    ("a", "b", "start", "end", "expected_years", "expected_territories"),
    [
        (MADRID, VALENCIA, 2007, 2025, [2007, 2021, 2025], {MADRID, VALENCIA}),
        (MADRID, "Nacional", 2021, 2025, [2021, 2025], {MADRID, "Nacional"}),
        (MADRID, VALENCIA, 2025, 2021, [2021, 2025], {MADRID, VALENCIA}),
        (MADRID, VALENCIA, 2021, 2021, [2021], {MADRID, VALENCIA}),
        (MADRID, MADRID, 2007, 2025, [2007, 2021, 2025], {MADRID}),
    ],
)
def test_shared_range_and_territories(
    database, a, b, start, end, expected_years, expected_territories
):
    rows = database.execute(render_query("comparacion", a, b, start, end)).fetchall()
    assert {row[0] for row in rows} == expected_territories
    assert sorted({row[1] for row in rows}) == expected_years
    assert len(rows) == len(expected_years) * len(expected_territories)
    assert database.execute(render_query("periodo", a, b, start, end)).fetchone() == (
        min(expected_years),
        max(expected_years),
    )


@pytest.mark.parametrize("query", ["hogares_disponibles", "esfuerzo_disponible"])
def test_available_indicator_preserves_null_gaps(database, query):
    rows = database.execute(render_query(query)).fetchall()
    assert len(rows) == 6
    assert any(row[4] is None for row in rows)
    assert any(row[6] is None for row in rows)


@pytest.mark.parametrize(
    ("query", "year"), [("hogares_disponibles", 2007), ("esfuerzo_disponible", 2025)]
)
def test_unavailable_indicator_returns_empty_set(database, query, year):
    assert database.execute(render_query(query, start=year, end=year)).fetchall() == []
    # The main table still exposes the missing observations rather than hiding them.
    assert len(database.execute(render_query("comparacion", start=year, end=year)).fetchall()) == 2


def test_summary_uses_only_selected_endpoints(database):
    rows = database.execute(render_query("resumen_periodo")).fetchall()
    cells = {(row[0], row[1]): row[2:] for row in rows}
    assert cells[(MADRID.lower(), "IPV general (índice, 2025 = 100)")][:2] == (80.0, 100.0)
    assert cells[(MADRID.lower(), "Viviendas / hogar")][:2] == (None, 1.4)
    assert cells[(VALENCIA.lower(), "Renta para 90 m² (años)")][3] is None
    assert database.execute(render_query("resumen_periodo", start=2021, end=2021)).fetchall() != []


def test_direct_difference_matches_endpoint_values(database):
    rows = database.execute(render_query("diferencia_territorios")).fetchall()
    assert len(rows) == 6
    assert rows[0][:4] == (
        "Viviendas / 1.000 hab.",
        550.0,
        550.0,
        0.0,
    )
    assert " − " not in rows[0][0]
    # The IPV is rebased per territory, so an index-point gap is not a price gap.
    assert all("IPV" not in row[0] for row in rows)


def test_selector_values_come_from_mart(database):
    territories = database.execute(QUERIES["territorios"]).fetchall()
    assert ("Nacional",) in territories
    assert (MADRID,) in territories and (VALENCIA,) in territories
    assert database.execute(QUERIES["anyos"]).fetchall() == [
        (2007, "Año 2007"),
        (2021, "Año 2021"),
        (2025, "Año 2025"),
    ]
