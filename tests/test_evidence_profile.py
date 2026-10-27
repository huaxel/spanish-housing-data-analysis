"""Municipal profile contracts: stable codes, explicit cuts, no invented values."""

import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "evidence/pages/perfil.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.DOTALL))
SOURCES = ROOT / "evidence/sources/housing"


def query(name, code="28079"):
    sql = QUERIES[name].replace("${inputs.municipio_perfil.value}", code)
    for dependency in ("municipios_perfil", "identidad_perfil", "cortes_perfil"):
        placeholder = "${" + dependency + "}"
        if placeholder in sql:
            sql = sql.replace(placeholder, "(" + query(dependency, code) + ")")
    return sql


@pytest.fixture
def database():
    con = duckdb.connect()
    con.execute(
        """
        create schema housing;
        create schema access;
        create schema profile_income;
        create table dim_territorio(cpro varchar, provincia varchar);
        insert into dim_territorio values ('28','Madrid'), ('01','Álava'), ('05','Ávila'),
        ('51+52','Ceuta y Melilla');
        create table profile_income.municipal (
            codigo varchar, municipio varchar, cpro varchar,
            anyo integer, renta_neta_hogar bigint
        );
        insert into profile_income.municipal values
        ('28079','ADRH Madrid','28',2021,30000),
        ('28079','ADRH Madrid','28',2023,36000),
        ('01001','ADRH Other','01',2022,30000),
        ('01001','ADRH Other','01',2023,42000),
        ('05001','New income name','05',2021,20000),
        ('05001','New income name','05',2023,22000),
        ('05002','L''Hospitalet','05',2023,0),
        ('05003','ADRH only','05',2023,0),
        ('05004','Hidden income','05',2022,25000),
        ('05004','Hidden income','05',2023,NULL);
        create table censo2021_secciones (
            cpro varchar, cmun varchar, t1_1 bigint, t18_1 bigint,
            t21_1 bigint, suprimido boolean
        );
        insert into censo2021_secciones values
        ('28','079',100,60,40,false), ('28','079',50,30,20,false),
        ('01','001',30,20,10,false), ('01','001',20,NULL,NULL,true),
        ('05','001',10,NULL,NULL,true), ('05','002',0,0,0,false);
        create table serpavi_municipal (
            codigo varchar, municipio varchar, provincia varchar,
            anyo integer, medida varchar, valor double
        );
        insert into serpavi_municipal values
        ('28079','Same name','Madrid',2024,'ALQM2_LV_M_VC',12),
        ('28079','Same name','Madrid',2024,'BI_ALVHEPCO_TVC',100),
        ('28079','Old name','Madrid',2022,'ALQM2_LV_M_VC',10),
        ('01001','Same name','Álava',2023,'ALQM2_LV_M_VC',8),
        ('05002','L''Hospitalet','Ávila',2024,'ALQM2_LV_M_VC',0),
        ('46999','Resto de la provincia','Valencia',2024,'ALQM2_LV_M_VC',99),
        ('bad','Malformed','Invalid',2024,'ALQM2_LV_M_VC',99);
        create table housing.vacancy_municipal (
            codigo varchar, municipio varchar, vac_pct double
        );
        insert into housing.vacancy_municipal values
        ('28079','Different census label',0), ('01999','Resto',90);
        create table access.rent_income (
            codigo varchar, anyo integer, alquiler_med double, contratos bigint,
            renta_neta_hogar bigint, ratio_pct double
        );
        insert into access.rent_income values
        ('28079',2021,500,40,30000,20),
        ('28079',2023,600,50,36000,20),
        ('01001',2022,400,20,30000,16),
        ('01001',2023,NULL,NULL,32000,NULL),
        ('05002',2023,0,0,30000,0);
    """
    )
    for source in ("perfil_catalogo", "perfil_censo", "perfil_alquiler", "perfil_provincias"):
        con.execute(f"create view housing.{source} as " + (SOURCES / f"{source}.sql").read_text())
    yield con
    con.close()


@pytest.mark.parametrize("name", list(QUERIES))
def test_all_profile_queries_execute(database, name):
    database.execute(query(name)).fetchall()


def indicators(database, code="28079"):
    rows = database.execute(query("indicadores_perfil", code)).fetchall()
    assert len(rows) == 7
    return {row[0]: row for row in rows}


def test_catalogue_keeps_leading_zero_codes_homonyms_and_rentless_places(database):
    rows = database.execute(query("municipios_perfil")).fetchall()
    by_code = {r[0]: r for r in rows}
    assert set(by_code) == {"28079", "01001", "05001", "05002", "05003", "05004"}
    assert by_code["28079"][1] == by_code["01001"][1] == "Same name"
    assert by_code["28079"][-1] != by_code["01001"][-1]
    assert by_code["05001"][1:4] == ("New income name", "Ávila", "ADRH")
    assert by_code["05003"][3] == "ADRH"
    assert "05001" in by_code["05001"][-1]
    assert by_code["05002"][1] == "L'Hospitalet"
    assert database.execute(query("identidad_perfil", "01001")).fetchone()[0] == "01001"


def test_census_suppression_never_turns_partial_sum_into_total(database):
    rows = {r[0]: r[1:] for r in database.execute("select * from housing.perfil_censo").fetchall()}
    assert rows["28079"] == (2021, 2, 0, 150, 90, 60)
    assert rows["01001"] == (2021, 2, 1, 50, None, None)
    assert rows["05001"] == (2021, 1, 1, 10, None, None)
    cells = indicators(database, "01001")
    assert cells[1][3] == 50
    assert cells[2][3] is None and "suprimidas" in cells[2][-1]
    assert cells[3][3] is None and "suprimidas" in cells[3][-1]


def test_null_census_count_is_withheld_even_without_suppression_flag(database):
    database.execute("update censo2021_secciones set t18_1=NULL where cpro='28'")
    assert indicators(database)[2][3] is None


def test_latest_global_cuts_do_not_backfill_older_local_values(database):
    assert database.execute(query("cortes_perfil")).fetchone() == (2024, 2023, 2023)
    cells = indicators(database, "01001")
    assert cells[5][2:4] == (2024, None)
    assert cells[6][2:4] == (2023, 42000)
    assert cells[7][2:4] == (2023, None)
    assert "Sin dato" in cells[7][-1]


def test_indicators_do_not_join_on_name_or_recompute_mixed_year_ratio(database):
    cells = indicators(database)
    assert cells[4][3] == 0  # census label differs; code still matches
    assert cells[5][2:4] == (2024, 12)
    assert cells[6][2:4] == (2023, 36000)
    assert cells[7][2:4] == (2023, 20)  # use reviewed same-year proxy only
    other = indicators(database, "01001")
    assert other[4][3] is None  # not Madrid's zero, nor its Resto aggregate


def test_zero_is_published_but_rentless_municipality_stays_selectable(database):
    cells = indicators(database, "05002")
    for number in (1, 2, 3, 5, 6, 7):
        assert cells[number][3] == 0
        assert cells[number][-1] == "Dato publicado"
    cells = indicators(database, "05001")
    assert cells[5][3] is None
    assert cells[6][3] == 22000 and cells[6][-1] == "Dato publicado"
    assert cells[7][3] is None


def test_calendars_keep_absent_years_and_unknown_markets(database):
    rows = database.execute(query("historia_alquiler_perfil")).fetchall()
    assert rows == [(2022, 10, None), (2023, None, None), (2024, 12, 100)]
    rows = database.execute(query("historia_proxy_perfil")).fetchall()
    assert rows == [(2021, 500, 30000, 20), (2022, None, None, None), (2023, 600, 36000, 20)]
    assert all(
        r[1:] == (None, None)
        for r in database.execute(query("historia_alquiler_perfil", "05001")).fetchall()
    )


def test_duplicate_rental_measures_are_withheld_not_averaged(database):
    database.execute("""
        insert into serpavi_municipal values
        ('28079','Same name','Madrid',2024,'ALQM2_LV_M_VC',90)
    """)
    assert indicators(database)[5][3] is None


def test_unavailable_source_years_do_not_remove_missing_indicator_rows(database):
    database.execute("delete from access.rent_income")
    cells = indicators(database)
    assert cells[6][2:4] == (2023, 36000)
    assert cells[7][2:4] == (None, None)
    database.execute("delete from profile_income.municipal")
    assert indicators(database)[6][2:4] == (None, None)


def test_profile_navigation_metadata_and_caveats():
    assert "(/perfil/)" in (ROOT / "evidence/pages/index.md").read_text()
    assert "(/perfil/)" in (ROOT / "evidence/pages/municipios.md").read_text()
    assert '"perfil/index.html"' in (ROOT / "scripts/fix_build_meta.py").read_text()
    page = PAGE.read_text()
    for phrase in (
        "Un dato ausente no es cero",
        "no el último dato disponible de cada municipio",
        "Ingresos sin exigir datos de alquiler",
        "el proxy sigue usando exclusivamente",
        "sin puntuación",
        "no es una tasa de sobrecarga",
        "no armoniza cambios de límites",
    ):
        assert phrase.lower() in page.lower()
    assert "value=codigo label=etiqueta" in page
    assert page.count('handleMissing="gap"') == 3
    for route in re.findall(r"\]\(/([\w-]+)/\)", page):
        assert (ROOT / "evidence/pages" / f"{route}.md").exists()


def test_standalone_income_does_not_fill_the_reviewed_proxy(database):
    cells = indicators(database, "01001")
    assert cells[6][3] == 42000  # independent ADRH row, not the cross's 32000
    assert cells[7][3] is None
    proxy = database.execute(query("historia_proxy_perfil", "01001")).fetchall()
    assert proxy[-1][2:] == (32000, None)  # reviewed intersection is unchanged


def test_adrh_only_municipality_keeps_unknown_census_and_rent(database):
    cells = indicators(database, "05003")
    assert all(cells[n][3] is None for n in (1, 2, 3, 4, 5, 7))
    assert cells[6][3] == 0 and cells[6][-1] == "Dato publicado"


def test_missing_income_is_not_backfilled_from_older_year(database):
    cells = indicators(database, "05004")
    assert cells[6][2:4] == (2023, None)
    assert cells[6][-1] == "Sin dato en este corte ADRH"
    history = database.execute(query("historia_ingresos_perfil", "05004")).fetchall()
    assert history == [(2021, None), (2022, 25000), (2023, None)]


def test_income_calendar_preserves_interior_gaps_independent_of_rent(database):
    history = database.execute(query("historia_ingresos_perfil", "05001")).fetchall()
    assert history == [(2021, 20000), (2022, None), (2023, 22000)]


def test_income_edition_does_not_change_proxy_year_or_recalculate_proxy(database):
    database.execute(
        "insert into profile_income.municipal values ('28079','Madrid','28',2024,99000)"
    )
    cells = indicators(database)
    assert cells[6][2:4] == (2024, 99000)
    assert cells[7][2:4] == (2023, 20)


def test_province_labels_keep_ceuta_and_melilla_individual(database):
    rows = database.execute("select * from housing.perfil_provincias").fetchall()
    assert ("51", "Ceuta") in rows and ("52", "Melilla") in rows
    assert not any(r[0] == "51+52" for r in rows)
