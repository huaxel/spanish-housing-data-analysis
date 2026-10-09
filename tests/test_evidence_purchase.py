"""Offline arithmetic and input contracts for the buyer scenario page."""

import math
import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "evidence/pages/compra.md"
TEXT = PAGE.read_text()
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", TEXT, re.DOTALL))
DEFAULTS = {
    "precio": 250000,
    "financiado": 80,
    "plazo": 30,
    "tipo": 3,
    "gastos": 10,
    "ingresos": 36000,
    "ahorro": 50000,
    "otras_deudas": 0,
}


def query(name, **overrides):
    values = DEFAULTS | overrides
    sql = QUERIES[name]
    for key, value in values.items():
        sql = sql.replace("${inputs." + key + "}", str(value))
    for source in QUERIES:
        token = "${" + source + "}"
        if token in sql:
            sql = sql.replace(token, f"({query(source, **overrides)})")
    return sql


@pytest.fixture
def database():
    with duckdb.connect() as con:
        con.execute("""
            create schema housing;
            create table housing.mart_ccaa_anual (
                ccaa varchar, anyo integer, eur_m2_libre double, renta_hogar_neta double
            );
            insert into housing.mart_ccaa_anual values
            ('Madrid, Comunidad de', 2024, 3000, 40000),
            ('Madrid, Comunidad de', 2025, 9999, 99999),
            ('Nacional', 2024, 2000, 30000)
        """)
        yield con


def records(database, name, **overrides):
    result = database.execute(query(name, **overrides))
    columns = [description[0] for description in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def annuity_by_discounted_payments(principal, annual_pct, years):
    months = years * 12
    rate = annual_pct / 1200
    # Independent formulation: principal equals present value of equal payments.
    return principal / math.fsum((1 + rate) ** -month for month in range(1, months + 1))


@pytest.mark.parametrize("name", list(QUERIES))
def test_all_queries_execute(database, name):
    assert records(database, name)


def test_defaults_and_numeric_bounds_match_visible_controls():
    sliders = re.findall(r"<Slider\s+(.*?)/>", TEXT, re.DOTALL)
    defaults = {}
    for slider in sliders:
        name = re.search(r"\bname=(\w+)", slider)[1]
        defaults[name] = float(re.search(r"\bdefaultValue=([\d.]+)", slider)[1])
        minimum = float(re.search(r"\bmin=([\d.]+)", slider)[1])
        maximum = float(re.search(r"\bmax=([\d.]+)", slider)[1])
        assert minimum <= defaults[name] <= maximum
    assert defaults == DEFAULTS


def test_default_cash_identity_and_liquidity_shortfall(database):
    row = records(database, "efectivo_compra")[0]
    assert row["prestamo"] == 200000
    assert row["entrada"] == pytest.approx(50000)
    assert row["gastos_iniciales"] == 25000
    assert row["efectivo_necesario"] == 75000
    assert row["falta_efectivo"] == 25000
    assert row["ahorro_restante"] == 0
    assert row["precio"] == pytest.approx(row["prestamo"] + row["entrada"])


@pytest.mark.parametrize("rate,term", [(0, 1), (0.25, 40), (3, 30), (10, 40)])
def test_annuity_and_interest_match_independent_present_value(database, rate, term):
    for row in records(database, "cuotas_compra", tipo=rate, plazo=term):
        expected = annuity_by_discounted_payments(200000, row["tipo_escenario_pct"], term)
        assert row["cuota_mensual"] == pytest.approx(expected, rel=1e-10)
        assert row["intereses_total"] == pytest.approx(expected * term * 12 - 200000, abs=1e-6)
        assert row["pagos_hipoteca_total"] == pytest.approx(
            row["prestamo"] + row["intereses_total"]
        )
        assert row["cuota_ingreso_pct"] == pytest.approx(100 * expected / 3000)
        assert row["meses"] == term * 12


def test_rate_sensitivity_is_percentage_points_not_relative_change(database):
    rows = records(database, "cuotas_compra")
    assert [row["tipo_escenario_pct"] for row in rows] == [3, 4, 5]
    assert rows[0]["cuota_mensual"] < rows[1]["cuota_mensual"] < rows[2]["cuota_mensual"]


def test_cash_surplus_and_no_borrowing_with_other_debt(database):
    cash = records(database, "efectivo_compra", financiado=0, ahorro=300000)[0]
    assert cash["efectivo_necesario"] == 275000
    assert cash["falta_efectivo"] == 0
    assert cash["ahorro_restante"] == 25000
    for row in records(database, "cuotas_compra", financiado=0, otras_deudas=600):
        assert row["cuota_mensual"] == row["intereses_total"] == 0
        assert row["cuota_ingreso_pct"] == 0
        assert row["deuda_ingreso_pct"] == 20
        assert row["tras_deuda"] == 2400


def test_full_price_financing_does_not_finance_acquisition_costs(database):
    row = records(database, "efectivo_compra", financiado=100)[0]
    assert row["entrada"] == 0
    assert row["prestamo"] == row["precio"]
    assert row["efectivo_necesario"] == row["gastos_iniciales"] == 25000


def test_other_debt_does_not_change_mortgage_or_total_interest(database):
    a = records(database, "cuotas_compra")[0]
    b = records(database, "cuotas_compra", otras_deudas=3000, ingresos=12000)[0]
    assert a["cuota_mensual"] == b["cuota_mensual"]
    assert a["intereses_total"] == b["intereses_total"]
    assert b["deuda_ingreso_pct"] > 100  # no clipping into an apparently affordable result
    assert b["tras_deuda"] < 0


@pytest.mark.parametrize(
    "override",
    [
        {"precio": 0},
        {"precio": 1000001},
        {"financiado": -1},
        {"financiado": 101},
        {"plazo": 0},
        {"plazo": 41},
        {"plazo": 1.5},
        {"tipo": -0.25},
        {"tipo": 11},
        {"gastos": -1},
        {"gastos": 21},
        {"ingresos": 0},
        {"ahorro": -1},
        {"otras_deudas": -1},
        {"tipo": None},
        {"tipo": ""},
        {"tipo": "nan"},
        {"precio": "inf"},
    ],
)
def test_invalid_inputs_do_not_fabricate_results(database, override):
    for name in ("supuestos_compra", "efectivo_compra", "cuotas_compra"):
        assert records(database, name, **override) == []


@pytest.mark.parametrize("financed", [0, 100])
def test_valid_boundary_scenarios_remain_finite(database, financed):
    rows = records(
        database,
        "cuotas_compra",
        precio=1000000,
        financiado=financed,
        plazo=40,
        tipo=10,
        ingresos=12000,
        gastos=20,
        ahorro=0,
        otras_deudas=3000,
    )
    assert len(rows) == 3
    for row in rows:
        assert all(math.isfinite(v) for v in row.values() if isinstance(v, (int, float)))


def test_calculator_is_linked_and_has_route_metadata():
    assert "(/compra/)" in (ROOT / "evidence/pages/acceso.md").read_text()
    assert '"compra/index.html"' in (ROOT / "scripts/fix_build_meta.py").read_text()


def test_regional_reference_does_not_feed_buyer_assumptions(database):
    assert records(database, "referencias_compra") == [
        {
            "ccaa": "Madrid, Comunidad de",
            "anyo": 2024,
            "eur_m2_libre": 3000,
            "renta_hogar_neta": 40000,
        }
    ]
    before = records(database, "cuotas_compra")
    database.execute("delete from housing.mart_ccaa_anual")
    assert records(database, "cuotas_compra") == before


def test_slider_interpolation_uses_scalar_inputs_not_dropdown_value_property():
    tokens = re.findall(r"\$\{inputs\.(.*?)\}", TEXT)
    assert set(tokens) == set(DEFAULTS)
    assert all(".value" not in token for token in tokens)
