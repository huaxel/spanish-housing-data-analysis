"""A property-count-weighted record-date proxy, never individual dwelling ages."""

import math
import re
from pathlib import Path

import duckdb
import pytest

PAGE = Path(__file__).resolve().parents[1] / "evidence/pages/stock.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.S))


@pytest.fixture
def weighted(monkeypatch):
    monkeypatch.syspath_prepend(str(PAGE.parents[2] / "scripts"))
    import analyze_stock_rent

    with duckdb.connect() as con:
        con.execute("create schema stock")
        con.execute(
            "create table stock.buildings (barrio_id varchar, match_status varchar, "
            "year_start integer, dwelling_properties bigint)"
        )
        yield con, analyze_stock_rent


def evaluate(fixture, name, overrides=None):
    con, analysis = fixture
    qs = {**QUERIES, **(overrides or {})}
    cur = con.execute(analysis.expand(qs[name], qs))
    return [dict(zip([c[0] for c in cur.description], row, strict=True)) for row in cur.fetchall()]


def add(fixture, rows):
    fixture[0].executemany("insert into stock.buildings values (?,?,?,?)", rows)


def test_many_small_old_records_do_not_outweigh_a_large_new_record(weighted):
    add(
        weighted,
        [
            ("A", "matched", 1900, 1),
            ("A", "matched", 1910, 1),
            ("A", "matched", 1920, 1),
            ("A", "matched", 1975, 1000),
        ],
    )
    row = evaluate(weighted, "fechas_stock_ponderadas")[0]
    assert row == {"idg": "A", "mediana_anyo_minimo_ponderada": 1975, "inmuebles_con_fecha": 1003}
    con, _ = weighted
    assert (
        con.execute("select quantile_disc(year_start,0.5) from stock.buildings").fetchone()[0]
        == 1910
    )


def test_ties_and_even_weight_choose_lower_discrete_median(weighted):
    add(weighted, [("A", "matched", 1900, 2), ("A", "matched", 1900, 3), ("A", "matched", 1980, 5)])
    row = evaluate(weighted, "fechas_stock_ponderadas")[0]
    assert row["mediana_anyo_minimo_ponderada"] == 1900 and row["inmuebles_con_fecha"] == 10


def test_equal_weights_agree_with_existing_quantile_disc(weighted):
    add(weighted, [("A", "matched", y, 1) for y in [1910, 1940, 1960, 1980]])
    row = evaluate(weighted, "fechas_stock_ponderadas")[0]
    con, _ = weighted
    assert (
        row["mediana_anyo_minimo_ponderada"]
        == con.execute("select quantile_disc(year_start,0.5) from stock.buildings").fetchone()[0]
    )


def test_null_zero_weights_missing_dates_and_unassigned_do_not_enter_median(weighted):
    add(
        weighted,
        [
            ("A", "matched", 1950, 1),
            ("A", "matched", 2000, 2),
            ("A", "matched", None, 20),
            ("A", "matched", 1850, 0),
            ("A", "matched", 1800, None),
            ("A", "outside_barrios", 1700, 999999),
        ],
    )
    row = evaluate(weighted, "fechas_stock_ponderadas")[0]
    assert row["mediana_anyo_minimo_ponderada"] == 2000 and row["inmuebles_con_fecha"] == 3


def test_property_weight_coverage_preserves_all_missing_and_no_stock_cases(weighted):
    add(
        weighted,
        [
            ("A", "matched", 1950, 1),
            ("A", "matched", 2000, 2),
            ("A", "matched", None, 20),
            ("B", "matched", None, 3),
        ],
    )
    con, _ = weighted
    con.execute("""create table context as
        select 'A' as idg,'Alpha' as barrio,'D' as distrito,1950 as mediana_anyo_minimo,
               2 as registros_con_fecha,23 as inmuebles_vivienda union all
        select 'B','Beta','D',null,0,3 union all
        select 'C','Excluded','D',null,0,null""")
    rows = evaluate(
        weighted, "stock_fechas_sensibilidad", {"stock_barrios": "select * from context"}
    )
    a, b, c = rows
    assert a["pesos_con_fecha"] == 3 and a["pesos_sin_fecha"] == 20
    assert a["fraccion_peso_con_fecha"] == pytest.approx(3 / 23)
    assert b["mediana_anyo_minimo_ponderada"] is None and b["pesos_sin_fecha"] == 3
    assert b["fraccion_peso_con_fecha"] == 0
    assert c["inmuebles_vivienda"] is None and c["pesos_sin_fecha"] is None
    assert c["fraccion_peso_con_fecha"] is None


def test_huge_integer_weights_are_exact_without_replication(weighted):
    n = 2**53
    add(weighted, [("A", "matched", 1900, n + 1), ("A", "matched", 2000, n + 2)])
    row = evaluate(weighted, "fechas_stock_ponderadas")[0]
    assert row["mediana_anyo_minimo_ponderada"] == 2000
    assert row["inmuebles_con_fecha"] == 2 * n + 3


@pytest.mark.parametrize(
    "values",
    [
        [(1900, 1), (1920, 3), (1980, 2)],
        [(1900, 4), (1900, 2), (2000, 1)],
        [(1975, 1)],
        [(None, 5), (1900, 1), (1980, 0)],
    ],
)
def test_small_weighted_samples_match_replicated_discrete_oracle(weighted, values):
    add(weighted, [("A", "matched", year, weight) for year, weight in values])
    expanded = sorted(year for year, weight in values if year is not None for _ in range(weight))
    expected = expanded[math.ceil(len(expanded) / 2) - 1]
    assert (
        evaluate(weighted, "fechas_stock_ponderadas")[0]["mediana_anyo_minimo_ponderada"]
        == expected
    )


def test_no_valid_dates_has_no_manufactured_median(weighted):
    add(weighted, [("A", "matched", None, 100), ("A", "matched", 1900, 0)])
    assert evaluate(weighted, "fechas_stock_ponderadas") == []


def test_page_labels_weighted_date_as_record_proxy_not_dwelling_age():
    page = PAGE.read_text()
    assert "Todo el peso hereda el año mínimo del registro BU" in page
    assert "no una mediana de edad de las viviendas" in page
    assert "mediana discreta inferior" in page
