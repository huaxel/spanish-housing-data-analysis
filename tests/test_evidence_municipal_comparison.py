"""Two municipalities are compared on identical published measure/year support."""

import re
from pathlib import Path

import pytest

import test_evidence_profile as profile_contracts

profile_database = profile_contracts.database

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "evidence/pages/comparar-municipios.md"
QUERIES = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.S))
DEFAULTS = {
    "municipio_a": "28079",
    "municipio_b": "01001",
    "metrica_municipal": "alquiler",
    "desde_municipal": "2021",
    "hasta_municipal": "2024",
}


def query(name, **overrides):
    inputs = DEFAULTS | {k: str(v) for k, v in overrides.items()}

    def render(key):
        sql = re.sub(r"\$\{inputs\.(\w+)\.value\}", lambda m: inputs[m[1]], QUERIES[key])
        return re.sub(r"\$\{(\w+)\}", lambda m: "(" + render(m[1]) + ")", sql)

    return render(name)


@pytest.fixture
def database(profile_database):
    con = profile_database
    con.execute("""
        insert into serpavi_municipal values
        ('28079','Same name','Madrid',2021,'ALQM2_LV_M_VC',0),
        ('28079','Same name','Madrid',2023,'ALQM2_LV_M_VC',30),
        ('01001','Same name','Álava',2021,'ALQM2_LV_M_VC',6),
        ('01001','Same name','Álava',2022,'ALQM2_LV_M_VC',NULL)
    """)
    return con


@pytest.mark.parametrize("name", list(QUERIES))
def test_all_comparison_queries_execute(database, name):
    database.execute(query(name)).fetchall()


def test_calendar_retains_noncommon_years_and_real_zero(database):
    rows = database.execute(query("calendario_comparable")).fetchall()
    assert rows == [
        (2021, 0, 6, True, "Año común: incluido", -6),
        (2022, 10, None, False, "Solo A: excluido del gráfico", None),
        (2023, 30, 8, True, "Año común: incluido", 22),
        (2024, 12, None, False, "Solo A: excluido del gráfico", None),
    ]
    coverage = database.execute(query("cobertura_comparable")).fetchone()
    assert coverage[:8] == (2021, 2024, 4, 4, 2, 2, 2, "2021, 2023")


def test_both_chart_series_are_masked_outside_common_support(database):
    rows = database.execute(query("serie_comun")).fetchall()
    assert len(rows) == 8
    assert all(r[-1] is None for r in rows if r[0] in (2022, 2024))
    assert [r[-1] for r in rows if r[0] == 2021] == [0, 6]
    assert {r[2] for r in rows} == {"01001", "28079"}
    # Homonyms do not collapse into the same chart series.
    assert len({r[4] for r in rows}) == 2
    assert {r[5] for r in rows} == {"alquiler"}
    assert {r[6] for r in rows} == {"€/m²/mes nominales"}


def test_inverted_years_have_identical_calendar_coverage_and_series(database):
    for name in ("calendario_comparable", "cobertura_comparable", "serie_comun"):
        assert (
            database.execute(query(name)).fetchall()
            == database.execute(query(name, desde_municipal=2024, hasta_municipal=2021)).fetchall()
        )


def test_swapping_municipalities_reverses_only_the_valid_difference(database):
    before = database.execute(query("calendario_comparable")).fetchall()
    after = database.execute(
        query("calendario_comparable", municipio_a="01001", municipio_b="28079")
    ).fetchall()
    for a, b in zip(before, after, strict=True):
        assert a[0] == b[0] and a[1:3] == (b[2], b[1]) and a[3] == b[3]
        assert b[-1] == (None if a[-1] is None else -a[-1])
    assert after[1][-2] == "Solo B: excluido del gráfico"


def test_same_municipality_is_one_series_not_an_independent_zero_gap(database):
    rows = database.execute(query("serie_comun", municipio_b="28079")).fetchall()
    assert len(rows) == 4 and {r[1] for r in rows} == {"A"}
    assert all(
        r[-1] is None
        for r in database.execute(query("calendario_comparable", municipio_b="28079")).fetchall()
    )
    assert (
        database.execute(query("cobertura_comparable", municipio_b="28079")).fetchone()[-1]
        == "Mismo municipio: sin contraste A − B"
    )


def test_no_common_years_never_backfills_or_invents_comparison(database):
    coverage = database.execute(query("cobertura_comparable", municipio_b="05001")).fetchone()
    assert coverage[5:8] == (0, 4, None)
    assert coverage[-1] == "Sin años comunes: no hay comparación"
    assert all(
        r[-1] is None
        for r in database.execute(query("serie_comun", municipio_b="05001")).fetchall()
    )


def test_income_zero_without_rent_is_compared_only_as_income(database):
    coverage = database.execute(
        query("cobertura_comparable", municipio_b="05003", metrica_municipal="ingresos")
    ).fetchone()
    assert coverage[5:8] == (1, 3, "2023")
    row = next(
        r
        for r in database.execute(
            query("calendario_comparable", municipio_b="05003", metrica_municipal="ingresos")
        ).fetchall()
        if r[0] == 2023
    )
    assert row[1:4] == (36000, 0, True)
    assert database.execute(query("cobertura_comparable", municipio_b="05003")).fetchone()[5] == 0


def test_proxy_uses_its_original_intersection_not_standalone_income(database):
    assert (
        database.execute(query("cobertura_comparable", metrica_municipal="ingresos")).fetchone()[5]
        == 1
    )
    assert (
        database.execute(query("cobertura_comparable", metrica_municipal="proxy")).fetchone()[5]
        == 0
    )
    rows = database.execute(query("serie_comun", metrica_municipal="proxy")).fetchall()
    assert all(r[-1] is None for r in rows)
    metric = database.execute(query("medida_aplicada", metrica_municipal="proxy")).fetchone()
    assert "puntos porcentuales" in metric[-1]


def test_one_year_window_is_inclusive_without_substitute_endpoints(database):
    row = database.execute(
        query("cobertura_comparable", desde_municipal=2024, hasta_municipal=2024)
    ).fetchone()
    assert row[:7] == (2024, 2024, 1, 1, 0, 0, 1)
    assert row[-1] == "Sin años comunes: no hay comparación"


def test_census_is_separate_from_measure_window_and_keeps_suppression(database):
    names = ("contexto_comparable",)
    rows = database.execute(query(names[0])).fetchall()
    assert len(rows) == 4 and all(r[3] == 2021 for r in rows)
    assert rows[1][4:6] == (90, None)
    assert rows[1][-1] == "No mostrado: secciones suprimidas"
    assert rows[3][4:6] == (0, None)
    assert (
        rows
        == database.execute(
            query(names[0], metrica_municipal="proxy", desde_municipal=2024, hasta_municipal=2024)
        ).fetchall()
    )


def test_catalogue_uses_the_existing_profile_contract_with_names_as_labels(database):
    from test_evidence_profile import QUERIES as profile_queries

    assert QUERIES["municipios_comparables"] == profile_queries["municipios_perfil"]
    rows = database.execute(query("seleccion_comparable")).fetchall()
    assert [r[1] for r in rows] == ["28079", "01001"]
    assert rows[0][2] == rows[1][2]  # same display name, separate code/province


def test_page_navigation_metadata_and_necessary_limits():
    assert "(/comparar-municipios/)" in (ROOT / "evidence/pages/perfil.md").read_text()
    assert '"comparar-municipios/index.html"' in (ROOT / "scripts/fix_build_meta.py").read_text()
    text = " ".join(PAGE.read_text().split())
    for phrase in (
        "no es un ranking",
        "no empareja viviendas",
        "un dato ausente no es cero",
        "contexto censal",
        "no se recalcula",
        "no se interpolan",
    ):
        assert phrase in text.lower()
    for route in re.findall(r"\]\(/([\w-]+)/\)", PAGE.read_text()):
        assert (ROOT / "evidence/pages" / f"{route}.md").exists()
