"""Tenure counts are conventional primary dwellings, not rental households."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GEO = "Municipios (con más de 50.000 habitantes) y capitales de provincia"
HEADER = GEO + "\tRégimen de tenencia de la vivienda\tTotal\n"
META = (
    "<h1>Censo de Población y Viviendas 2021</h1>"
    "<h2>Viviendas familiares principales convencionales según régimen de tenencia "
    "(capitales de provincia y municipios de más de 50.000 habitantes)</h2>"
    "<p>Unidades: viviendas</p>"
)
CATEGORIES = [
    "Total (régimen de tenencia)",
    "En propiedad",
    "En alquiler",
    "Otro régimen de tenencia",
]


@pytest.fixture
def source():
    spec = importlib.util.spec_from_file_location(
        "tenure2021", ROOT / "scripts/build_sevilla_2021.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payload(values=("2,000", "1,000", "800", "200"), code="41091", name="Sevilla"):
    return HEADER + "".join(
        f"{code} {name}\t{c}\t{v}\n" for c, v in zip(CATEGORIES, values, strict=True)
    )


def households():
    return {"41091": {"municipio": "Sevilla", "hogares": 1234}}


def test_tenure_comma_groups_not_decimal_or_household_count(source):
    result = source.tenure(payload(), META, households())
    assert result == [("41091", "Sevilla", 2000, 1000, 800, 200, "celdas_completas")]
    assert result[0][2] != households()["41091"]["hogares"]


@pytest.mark.parametrize("marker", [".", "..", ""])
def test_unpublished_category_stays_null_not_zero(source, marker):
    result = source.tenure(payload(("2,000", marker, "800", "200")), META, households())
    assert result[0][3] is None and result[0][-1] == "celdas_incompletas"


def test_published_zero_is_valid(source):
    result = source.tenure(payload(("2,000", "2,000", "0", "0")), META, households())
    assert result[0][4:6] == (0, 0) and result[0][-1] == "celdas_completas"


@pytest.mark.parametrize("value", ["-1", "1.000", "1,00", "1,000.0", "NaN"])
def test_invalid_numeric_formats_fail_closed(source, value):
    with pytest.raises(ValueError, match="count/grouping"):
        source.tenure(payload((value, "1,000", "800", "200")), META, households())


@pytest.mark.parametrize(
    "metadata",
    [
        META.replace("2021", "2022"),
        META.replace("Unidades: viviendas", "Unidades: hogares"),
        META.replace("50.000", "1.000"),
        "<script>" + META + "</script>",
    ],
)
def test_year_unit_scope_and_hidden_metadata_rejected(source, metadata):
    with pytest.raises(ValueError, match="definition/year/unit/scope"):
        source.tenure(payload(), metadata, households())


def test_duplicate_cell_even_if_same_value_rejected(source):
    with pytest.raises(ValueError, match="Duplicate"):
        source.tenure(payload() + "41091 Sevilla\tEn alquiler\t800\n", META, households())


@pytest.mark.parametrize(
    "values",
    [
        ("2,000", "1,000", "900", "200"),
        ("2,000", "1,000", "700", "200"),
        ("2,000", ".", "2,100", "200"),
    ],
)
def test_conservation_and_partial_lower_bound(source, values):
    with pytest.raises(ValueError, match="categories"):
        source.tenure(payload(values), META, households())


@pytest.mark.parametrize(
    "code,name",
    [
        ("41001", "Sevilla"),
        ("41999", "Resto de Sevilla"),
        ("41091", "Sevilla (provincia)"),
        ("41091", "Other city"),
    ],
)
def test_municipal_code_and_label_compatibility(source, code, name):
    with pytest.raises(ValueError, match="compatible"):
        source.tenure(payload(code=code, name=name), META, households())


def test_missing_category_and_scope_change_rejected(source):
    with pytest.raises(ValueError, match="Missing published"):
        source.tenure("\n".join(payload().splitlines()[:-1]) + "\n", META, households())
    with pytest.raises(ValueError, match="scope changed"):
        source.checked_tenure(payload(), META, households())


def test_wrong_schema_and_category_rejected(source):
    with pytest.raises(ValueError, match="schema"):
        source.tenure(payload().replace(GEO, "Municipios"), META, households())
    with pytest.raises(ValueError, match="code/category"):
        source.tenure(payload().replace("En alquiler", "Tipo nuevo"), META, households())


def test_page_declares_units_imputation_and_restricted_scope():
    text = (ROOT / "evidence/pages/stock-2021.md").read_text()
    for phrase in [
        "no hogares ni contratos",
        "no están cubiertas por esta tabla",
        "imputación",
        "no que\ntodos se hayan observado directamente",
        "no son dos comprobaciones independientes",
        "alignment.tenencia_contexto",
    ]:
        assert phrase in text
