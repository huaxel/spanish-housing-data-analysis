"""Housing-access SQL contracts, independent of publisher data and Node."""

import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "evidence/pages/acceso.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.DOTALL))


def query(name):
    sql = QUERIES[name]
    for source in ("cambios_acceso", "sobrecarga_acceso"):
        sql = sql.replace("${" + source + "}", f"({QUERIES[source]})")
    return sql


@pytest.fixture
def database():
    con = duckdb.connect()
    con.execute("create schema housing")
    con.execute("""
        create table housing.mart_provincia_anual (
            cpro varchar, provincia varchar, anyo integer,
            viviendas_total double, viviendas_principales double,
            viviendas_no_principales double, hogares double,
            viv_por_hogar double
        )
    """)
    # A growing large province and a shrinking small province. Negative growth
    # is valid; growth itself is never a denominator.
    for code, name, s0, s1, h0, h1 in [
        ("28", "Madrid", 1000, 1100, 500, 600),
        ("03", "Alicante", 100, 90, 100, 100),
        ("51+52", "Ceuta y Melilla", 100, 900, 100, 100),
    ]:
        for year, stock, homes in [(2021, s0, h0), (2022, s0, h0), (2025, s1, h1)]:
            con.execute(
                "insert into housing.mart_provincia_anual values (?, ?, ?, ?, ?, ?, ?, ?)",
                [code, name, year, stock, stock * 0.8, stock * 0.2, homes, stock / homes],
            )
    # Missing endpoint, missing household level, and zero initial level.
    con.execute("""
        insert into housing.mart_provincia_anual values
        ('12', 'Castellón', 2021, 100, 80, 20, 90, 1.11),
        ('46', 'Valencia', 2021, 100, 80, 20, NULL, NULL),
        ('46', 'Valencia', 2025, 110, 90, 20, 100, 1.1),
        ('08', 'Barcelona', 2021, 0, 0, 0, 90, 0),
        ('08', 'Barcelona', 2025, 110, 90, 20, 100, 1.1)
    """)
    con.execute("""
        create table housing.vacancy_municipal (
            codigo varchar, municipio varchar, vac_pct double
        );
        insert into housing.vacancy_municipal values
        ('28079', 'Madrid', 5), ('03031', 'Benidorm', NULL),
        ('99999', 'Not selected', 90);
        create table housing.mart_ccaa_anual (
            ccaa varchar, anyo integer, eur_m2_libre double,
            renta_hogar_neta double, afford_90m2_years double
        );
        insert into housing.mart_ccaa_anual values
        ('Madrid, Comunidad de', 2024, 3000, 40000, 6.75),
        ('Madrid, Comunidad de', 2025, 9000, NULL, NULL),
        ('Nacional', 2024, 2000, 30000, 6);
        create table housing.muni_bcn (
            municipio varchar, anyo integer,
            rent_burden double, mortgage_burden double
        );
        insert into housing.muni_bcn values
        ('Barcelona', 2022, 51.2, 63.6),
        ('Badalona', 2022, NULL, 51.1),
        ('Barcelona', 2024, 90, 90)
    """)
    con.execute("""
        create schema access;
        create table access.overburden (
            breakdown varchar, group_code varchar, group_label varchar,
            survey_year integer, rate_pct double, status varchar
        );
        insert into access.overburden values
        ('income', 'TOTAL', 'Total', 2025, 7.2, ''),
        ('income', 'QU1', 'First quintile', 2025, NULL, 'u'),
        ('income', 'QU1', 'First quintile', 2024, 27.7, ''),
        ('tenure', 'RENT_MKT', 'Market rent', 2025, 26.8, ''),
        ('age', 'Y18-24', '18 to 24', 2025, 5.7, 'b')
    """)
    con.execute(
        "create table access.overburden_age_poverty(age_code varchar,age_label varchar,"
        "poverty_code varchar,poverty_label varchar,survey_year integer,rate_pct double,"
        "status varchar)"
    )
    con.execute(
        "insert into access.overburden_age_poverty values "
        "('Y18-24','18 to 24','B_60','Below 60%',2025,NULL,'u')"
    )
    con.execute("create schema ecv")
    con.execute(
        "create table ecv.joint_burden(age_code varchar,age_label varchar,"
        "poverty_code varchar,poverty_label varchar,tenure_code varchar,"
        "tenure_label varchar, survey_year integer,income_year integer,"
        "rate_pct double,status varchar,suppression_reasons varchar)"
    )
    con.execute(
        "insert into ecv.joint_burden values "
        "('TOTAL','Todas las edades','TOTAL','Toda la población','TOTAL',"
        "'Todos los regímenes',2025,2024,7.2,'available',''),"
        "('Y18-24','18–24 años','B_60','Por debajo del umbral de pobreza','RENT_MKT',"
        "'Alquiler a precio de mercado',2025,2024,NULL,'suppressed',"
        "'less_than_30_valid_households')"
    )
    for column in (
        "sample_valid_persons integer",
        "sample_valid_households integer",
        "weighted_missing_cost_loss_pct double",
    ):
        con.execute("alter table ecv.joint_burden add column " + column)
    con.execute(
        "update ecv.joint_burden set sample_valid_persons=50, "
        "sample_valid_households=29,weighted_missing_cost_loss_pct=1.5 "
        "where age_code='Y18-24'"
    )
    yield con
    con.close()


@pytest.mark.parametrize("name", list(QUERIES))
def test_all_page_queries_execute(database, name):
    database.execute(query(name)).fetchall()


def test_changes_require_exact_positive_endpoints_but_allow_negative_growth(database):
    rows = database.execute(query("cambios_acceso")).fetchall()
    assert len(rows) == 4
    assert {row[0] for row in rows} == {"28", "03"}
    assert {row[2] for row in rows} == {2021, 2022}
    assert all(row[3] == 2025 for row in rows)
    small = next(row for row in rows if row[0] == "03")
    assert small[-3:] == pytest.approx((-10, 0, -10))


def test_weighting_and_leave_one_out_are_recomputed_from_counts(database):
    rows = database.execute(query("sensibilidad_acceso")).fetchall()
    assert len(rows) == 2
    for row in rows:
        assert row[2] == 2  # excludes missing/zero endpoints and Ceuta/Melilla
        assert row[3] == pytest.approx(-10)  # equal province mean
        assert row[4] == pytest.approx(100 * (1190 / 1100 - 700 / 600))
        assert row[5:7] == pytest.approx((-10, -10))


def test_one_province_does_not_fabricate_influence_range(database):
    database.execute("delete from housing.mart_provincia_anual where cpro = '03'")
    rows = database.execute(query("sensibilidad_acceso")).fetchall()
    assert all(row[2] == 1 for row in rows)
    assert all(row[5:] == (None, None) for row in rows)


def test_stock_preserves_missing_household_ratio(database):
    rows = database.execute(query("stock_acceso")).fetchall()
    assert any(row[0] == "Valencia" and row[-1] is None for row in rows)
    assert all(row[1] in (2021, 2025) for row in rows)


def test_cost_panels_do_not_mix_vintages_or_rescale_percentages(database):
    assert database.execute(query("compra_acceso")).fetchall() == [
        ("Madrid, Comunidad de", 2024, 3000, 40000, 6.75)
    ]
    rows = database.execute(query("cargas_acceso")).fetchall()
    assert rows == [("Badalona", 2022, None, 51.1), ("Barcelona", 2022, 51.2, 63.6)]


def test_vacancy_uses_codes_and_keeps_missing_values(database):
    rows = database.execute(query("vacancia_acceso")).fetchall()
    assert rows == [("03031", "Benidorm", 2021, None), ("28079", "Madrid", 2021, 5)]


def test_page_is_linked_and_claim_register_is_audited():
    assert "(/acceso/)" in (ROOT / "evidence/pages/index.md").read_text()
    assert '"docs/housing_access.md"' in (ROOT / "scripts/audit_doc_numbers.py").read_text()
    assert '"acceso/index.html"' in (ROOT / "scripts/fix_build_meta.py").read_text()


def test_national_burden_uses_latest_survey_year_without_backfilling(database):
    assert database.execute(query("periodo_sobrecarga")).fetchone() == (2025,)
    rows = database.execute(query("sobrecarga_ingresos")).fetchall()
    assert len(rows) == 2
    assert all(row[3] == 2025 for row in rows)
    low = next(row for row in rows if row[1] == "QU1")
    assert low[-2:] == (None, "u")
    assert database.execute(query("sobrecarga_edad")).fetchone()[-1] == "b"


def test_ecv_selectors_and_null_suppression(database):
    sql = QUERIES["ecv_cruce_seleccionado"]
    for placeholder, label in [
        ("ecv_edad", "18–24 años"),
        ("ecv_pobreza_sel", "Por debajo del umbral de pobreza"),
        ("ecv_tenencia", "Alquiler a precio de mercado"),
    ]:
        sql = sql.replace("${inputs." + placeholder + ".value}", label)
    result = database.execute(sql).fetchone()
    assert result[8] is None
    assert result[-1] == "less_than_30_valid_households"
    assert "Tasa no mostrada" in result[-2]
    page = PAGE.read_text()
    for phrase in [
        "Estimación descriptiva propia",
        "no por quintiles",
        "menos de 50 personas válidas",
        "menos de 30 hogares distintos válidos",
        "más del 5%",
        "no es cero",
        "No hay intervalos de diseño",
        "jóvenes co-residentes",
        "No representa",
    ]:
        assert phrase.lower() in page.lower()


def test_market_rent_matrix_keeps_all_disjoint_coordinates_and_hidden_rates(database):
    database.execute(
        "insert into ecv.joint_burden values "
        "('Y30-64','30–64 años','A_60','Above','RENT_MKT','Market rent',"
        "2025,2024,0,'available','',100,50,0),"
        "('Y18-24','18–24 años','A_60','Above','OWN_L','Mortgage',"
        "2025,2024,9,'available','',100,50,0),"
        "('TOTAL','All','B_60','Below','RENT_MKT','Market rent',"
        "2025,2024,NULL,'marginal_not_published','margin',100,50,0)"
    )
    rows = database.execute(query("ecv_comparacion_renta")).fetchall()
    assert len(rows) == 2
    hidden, zero = rows
    assert hidden[:3] == (2025, 2024, "Y18-24")
    assert hidden[6] is None
    assert hidden[7:10] == (50, 29, 1.5)
    assert hidden[-1] == "less_than_30_valid_households"
    assert zero[6] == 0
    assert not any(r[2] == "TOTAL" or r[4] == "TOTAL" for r in rows)
    sql = query("ecv_comparacion_renta").lower()
    assert "rate_pct is not null" not in sql and "limit " not in sql
    assert "sum(" not in sql and "avg(" not in sql and "coalesce(" not in sql
