"""Offline contracts for the editorial entry point; no publisher data needed."""

import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "evidence/pages/reportaje.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.DOTALL))


@pytest.fixture
def database():
    con = duckdb.connect()
    con.execute("create schema housing; create schema access")
    con.execute("""
        create table housing.mart_ccaa_anual (
            ccaa varchar, anyo integer, viviendas_total double, hogares double,
            ipv_general double, viv_por_1000_hab double, hip_viv_num double,
            viv_por_hogar double
        );
        insert into housing.mart_ccaa_anual values
        ('Nacional',2020,90,999999,60,500,200,2.25),
        ('Nacional',2021,100,50,70,500,200,2),
        ('Nacional',2022,110,70,80,500,200,1.57),
        ('Nacional',2023,105,80,85,500,200,1.31),
        ('Nacional',2024,115,90,90,500,200,1.28),
        ('Nacional',2025,120,100,100,500,200,1.2),
        ('Complete',2020,100,NULL,70,500,200,NULL),
        ('Complete',2021,900,50,70,500,200,18),
        ('Complete',2024,120,999,100,500,200,NULL),
        ('Complete',2025,9000,100,100,500,200,90),
        ('Missing',2021,100,50,70,500,200,2),
        ('Null',2020,NULL,NULL,70,500,200,NULL),
        ('Null',2021,100,50,70,500,200,2),
        ('Null',2024,120,999,100,500,200,NULL),
        ('Null',2025,9000,100,100,500,200,90),
        ('Zero',2020,0,NULL,70,500,200,0),
        ('Zero',2021,100,50,70,500,200,2),
        ('Zero',2024,120,999,100,500,200,NULL),
        ('Zero',2025,9000,100,100,500,200,90),
        ('Shrinking',2020,100,NULL,70,500,200,NULL),
        ('Shrinking',2021,900,50,70,500,200,18),
        ('Shrinking',2024,90,999,100,500,200,NULL),
        ('Shrinking',2025,9000,100,100,500,200,90),
        ('No household growth',2020,100,NULL,70,500,200,NULL),
        ('No household growth',2021,900,50,70,500,200,18),
        ('No household growth',2024,120,999,100,500,200,NULL),
        ('No household growth',2025,9000,50,100,500,200,180);
        create table housing.vacancy_municipal (
            codigo varchar, municipio varchar, vac_pct double
        );
        insert into housing.vacancy_municipal values
        ('28079','Madrid',0), ('03031','Benidorm',NULL);
        create table housing.aeat_viviendas_uso (
            anyo integer, grano varchar, n_total double, n_habitual double,
            n_arrendadas double, n_disposicion double
        );
        insert into housing.aeat_viviendas_uso values
        (2024,'provincia',100,60,10,30),
        (2024,'ccaa_uniprovincial',300,120,60,120),
        (2024,'ccaa',100,60,10,30),
        (2024,'total',10000,10000,0,0),
        (2023,'provincia',10000,10000,0,0);
        create table access.overburden (
            breakdown varchar, group_code varchar, group_label varchar,
            survey_year integer, rate_pct double, status varchar
        );
        insert into access.overburden values
        ('income','TOTAL','Total',2025,7.2,''),
        ('income','QU1','First quintile',2025,NULL,'u'),
        ('income','QU2','Second quintile',2025,0,''),
        ('income','QU1','First quintile',2024,27.7,''),
        ('tenure','RENT_MKT','Market rent',2026,26.8,'');
    """)
    yield con
    con.close()


@pytest.mark.parametrize("name", list(QUERIES))
def test_all_reportaje_queries_execute(database, name):
    database.execute(QUERIES[name]).fetchall()


def test_annual_changes_use_corresponding_december_and_january_boundaries(database):
    rows = database.execute(QUERIES["aportes_anuales"]).fetchall()
    assert len(rows) == 8
    assert {r[0] for r in rows} == {2021, 2022, 2023, 2024}
    assert (2021, "Parque modelado (neto)", 10) in rows
    assert (2021, "Hogares ECP (neto)", 20) in rows
    assert (2023, "Parque modelado (neto)", -5) in rows
    assert (2024, "Hogares ECP (neto)", 10) in rows
    assert database.execute(QUERIES["balance_nacional"]).fetchone() == (25, 50)
    assert sum(r[2] for r in rows if r[1] == "Parque modelado (neto)") == 25
    assert sum(r[2] for r in rows if r[1] == "Hogares ECP (neto)") == 50


def test_missing_years_preserve_calendar_and_never_bridge_gaps(database):
    database.execute("delete from housing.mart_ccaa_anual where ccaa='Nacional' and anyo=2022")
    cells = {(r[0], r[1]): r[2] for r in database.execute(QUERIES["aportes_anuales"]).fetchall()}
    assert len(cells) == 8
    assert cells[2021, "Hogares ECP (neto)"] is None
    assert cells[2021, "Parque modelado (neto)"] == 10
    assert cells[2022, "Hogares ECP (neto)"] is None
    assert cells[2022, "Parque modelado (neto)"] is None
    assert cells[2023, "Parque modelado (neto)"] is None
    assert cells[2023, "Hogares ECP (neto)"] == 10
    assert cells[2024, "Parque modelado (neto)"] == 10


def test_unrelated_ech_households_and_later_park_values_cannot_change_the_balance(database):
    names = ("balance_nacional", "aportes_anuales", "cobertura_ccaa", "cierre")
    before = {name: database.execute(QUERIES[name]).fetchall() for name in names}
    # ECH 2020 is not a household endpoint; Dec 2025 stock is after this window.
    database.execute("update housing.mart_ccaa_anual set hogares=123 where anyo=2020")
    database.execute("update housing.mart_ccaa_anual set viviendas_total=999999 where anyo=2025")
    assert before == {name: database.execute(QUERIES[name]).fetchall() for name in names}


def test_ratio_requires_complete_positive_endpoints_not_positive_stock_growth(database):
    rows = database.execute(QUERIES["cobertura_ccaa"]).fetchall()
    assert rows == [
        ("Shrinking", -10, 50, -0.2),
        ("Complete", 20, 50, 0.4),
    ]


def test_household_chart_does_not_connect_ech_ecp_seam(database):
    rows = database.execute(QUERIES["cierre"]).fetchall()
    assert [row[0] for row in rows] == list(range(2021, 2026))
    assert [row[1] for row in rows] == list(range(2020, 2025))
    assert rows[0][-1] == pytest.approx(90 / 50)
    assert rows[-1][-1] == pytest.approx(115 / 100)


def test_missing_previous_december_stock_leaves_household_ratio_unknown(database):
    database.execute("delete from housing.mart_ccaa_anual where ccaa='Nacional' and anyo=2020")
    first = database.execute(QUERIES["cierre"]).fetchone()
    assert first == (2021, None, None, 50, None)
    assert database.execute(QUERIES["balance_nacional"]).fetchone() == (None, 50)


def test_aeat_shares_use_counts_and_nonoverlapping_geography(database):
    rows = database.execute(QUERIES["aeat_usos"]).fetchall()
    assert [row[1] for row in rows] == pytest.approx([45, 17.5, 37.5])


def test_burden_uses_latest_income_year_and_keeps_nulls_flags_and_zero(database):
    rows = database.execute(QUERIES["carga_por_renta"]).fetchall()
    assert len(rows) == 3
    assert all(row[2] == 2025 for row in rows)
    assert next(row for row in rows if row[0] == "QU1")[-2:] == (None, "u")
    assert next(row for row in rows if row[0] == "QU2")[-2:] == (0, "")


def test_vacancy_preserves_codes_and_missing_values(database):
    rows = database.execute(QUERIES["vac_municipios"]).fetchall()
    assert rows == [("28079", "Madrid", 0, 0), ("03031", "Benidorm", None, None)]


def test_editorial_entry_point_is_linked_audited_and_has_metadata():
    assert "(/reportaje/)" in (ROOT / "evidence/pages/index.md").read_text()
    assert '"evidence/pages/reportaje.md"' in (ROOT / "scripts/audit_doc_numbers.py").read_text()
    assert '"reportaje/index.html"' in (ROOT / "scripts/fix_build_meta.py").read_text()
    page = PAGE.read_text()
    for phrase in (
        "variaciones netas",
        "el parque se mide al 31 de diciembre",
        "sin restar hogares ECH de 2020",
        "no equivale a oferta disponible",
        "vivienda equivalente",
        "un dato ausente no es cero",
        "no por hogares",
        "no identifican efectos causales",
    ):
        assert phrase in page
    for route in re.findall(r"\]\(/([\w-]+)/\)", page):
        assert (ROOT / "evidence/pages" / f"{route}.md").exists()
