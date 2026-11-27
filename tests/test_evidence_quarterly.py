"""Offline SQL contracts for the Barcelona quarterly charts."""

import re
from pathlib import Path

import duckdb
import pytest

PAGE = Path(__file__).resolve().parents[1] / "evidence/pages/municipios.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(encoding="utf-8"), re.S))
CHARTS = {
    "serie_trim_bcn": ("barrios_bcn_lloguer_trimestral", ["lloguer_m2"]),
    "serie_compra_bcn": ("barrios_bcn_compraventes", ["eur_m2_total", "trx_total"]),
}


def run(name: str, rows: list[tuple], number_type: str) -> list[tuple]:
    """rows: (barrio, year, quarter, value or None); the browser may deliver doubles."""
    table, columns = CHARTS[name]
    con = duckdb.connect()
    con.execute("create schema housing")
    extra = "".join(f", {column} double" for column in columns)
    con.execute(
        f"create table housing.{table} "
        f"(ambit varchar, nom varchar, anyo {number_type}, trimestre {number_type}{extra})"
    )
    for barrio, year, quarter, value in rows:
        values = ["barri", barrio, year, quarter, *[value] * len(columns)]
        marks = ",".join("?" * len(values))
        con.execute(f"insert into housing.{table} values ({marks})", values)
    sql = QUERIES[name].replace("${inputs.barris_bcn.value}", "('A', 'B')")
    return [row[:3] for row in con.execute(sql).fetchall()]


@pytest.mark.parametrize("number_type", ["bigint", "double"])
@pytest.mark.parametrize("name", CHARTS)
def test_missing_quarters_stay_visible_and_in_order(name, number_type):
    rows = [
        ("A", 2019, 4, 10.0),
        ("A", 2021, 1, 12.0),
        ("B", 2021, 1, 20.0),
        ("A", 2021, 2, None),  # trailing placeholders must not extend the axis
        ("B", 2021, 3, None),
        ("C", 2018, 1, 99.0),  # not selected
    ]
    result = run(name, rows, number_type)
    labels = list(dict.fromkeys(row[0] for row in result))
    assert labels == ["T4 2019", "T1 2020", "T2 2020", "T3 2020", "T4 2020", "T1 2021"]
    assert [row[1] for row in result] == ["A", "B"] * len(labels)
    published = {(label, barrio): value for label, barrio, value in result if value is not None}
    assert published == {("T4 2019", "A"): 10.0, ("T1 2021", "A"): 12.0, ("T1 2021", "B"): 20.0}


@pytest.mark.parametrize("name", CHARTS)
def test_selection_without_published_values_is_empty(name):
    assert run(name, [("A", 2021, 1, None)], "bigint") == []


@pytest.mark.parametrize("name", CHARTS)
def test_chart_keeps_query_order_and_thins_labels(name):
    page = PAGE.read_text(encoding="utf-8")
    tag = re.search(rf"<Chart data=\{{{name}\}}.*?</Chart>", page, re.S).group(0)
    assert "x=trimestre" in tag
    assert "sort=false" in tag
    # LineChart drops this prop, and Evidence treats a boolean false as unset;
    # either way every label is squeezed in and truncated.
    assert 'showAllXAxisLabels="false"' in tag
    # Isolated quarters have no line, so every marker must be drawn.
    assert "showAllSymbol: true" in tag
