"""Coverage is household location, never rental-contract coverage."""

import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "evidence/pages/stock-2021.md"


def query():
    return re.search(r"```sql seleccion_alineada\n(.*?)\n```", PAGE.read_text(), re.S).group(1)


def run(rows):
    with duckdb.connect() as c:
        c.execute("create schema alignment")
        c.execute(
            "create table alignment.perfiles(codigo varchar,hogares bigint,"
            "viviendas bigint,renta_vc double)"
        )
        if rows:
            c.executemany("insert into alignment.perfiles values (?,?,?,?)", rows)
        return c.execute(query()).fetchall()


def test_municipality_and_household_shares_are_different():
    observed, missing = run([("A", 900, 1000, 7), ("B", 50, 60, None), ("C", 50, None, None)])
    assert observed[1] == 1 and observed[2] == pytest.approx(1 / 3)
    assert observed[3:5] == (1, 900) and observed[5] == pytest.approx(0.9)
    assert observed[6:] == (1, "completo")
    assert missing[1] == 2 and missing[4] == 100 and missing[5] == pytest.approx(0.1)
    assert missing[6] == 1  # missing stock is not zero housing, nor redistributed


def test_one_missing_household_count_suppresses_both_shares():
    result = run([("A", 900, 1000, 7), ("B", None, None, None), ("C", 50, 60, None)])
    assert result[0][4] == 900 and result[1][4] == 50
    assert result[1][1] == 2 and result[1][3] == 1
    assert all(r[5] is None and r[-1] == "denominador_incompleto" for r in result)


def test_all_missing_counts_stay_null_not_zero():
    result = run([("A", None, 3, 7), ("B", None, None, None)])
    assert all(r[4] is None and r[5] is None for r in result)


def test_zero_denominator_is_not_full_or_zero_coverage():
    result = run([("A", 0, 3, 7), ("B", 0, None, None)])
    assert all(r[4] == 0 and r[5] is None and r[-1] == "denominador_cero" for r in result)


@pytest.mark.parametrize("price", [None, 7])
def test_empty_group_has_known_zero_count_not_missing_counts(price):
    result = run([("A", 100, 120, price)])
    populated, empty = (result[0], result[1]) if price else (result[1], result[0])
    assert populated[1:6] == (1, 1.0, 1, 100, 1.0)
    assert empty[1:7] == (0, 0.0, 0, 0, 0.0, 0)


def test_empty_universe_never_divides_by_zero():
    result = run([])
    assert len(result) == 2
    assert all(
        r[1] == 0 and r[2] is None and r[5] is None and r[-1] == "sin_universo" for r in result
    )


def test_no_weighted_rent_or_contract_coverage_claim():
    text = PAGE.read_text()
    for phrase in [
        "hogares de todas las tenencias",
        "no mide cobertura de contratos",
        "No se ponderan medianas de renta",
        "denominador_incompleto",
    ]:
        assert phrase in text
    assert "renta_vc" in query() and "sum(renta_vc)" not in query()
