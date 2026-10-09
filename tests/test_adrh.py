"""Offline INE ADRH municipal income parser contracts."""

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_adrh as fa  # noqa: E402

HEADER = "Municipios;Distritos;Secciones;Indicadores de renta media;Periodo;Total"


def line(
    mun="01001 Alegría-Dulantzi",
    dist="",
    secc="",
    ind="Renta neta media por hogar",
    anyo=2023,
    valor="16.429",
):
    return f"{mun};{dist};{secc};{ind};{anyo};{valor}"


def text(*lines):
    return "\r\n".join([HEADER, *lines]) + "\r\n"


def parse(s):
    return fa.parse(io.StringIO(s, newline=""))


def test_parse_extracts_code_indicator_and_suppression():
    rows = parse(
        text(
            line(),
            line(ind="Mediana de la renta por unidad de consumo", valor="."),
            line(ind="Media de la renta por unidad de consumo", anyo=2019, valor='""'),
        )
    )
    assert [(r["codigo"], r["indicador"], r["anyo"], r["renta_eur"]) for r in rows] == [
        ("01001", "neta_hogar", 2023, 16429),
        ("01001", "uc_mediana", 2023, None),
        ("01001", "uc_media", 2019, None),
    ]
    assert rows[0]["cpro"] == "01"


def test_section_and_district_rows_are_skipped():
    rows = parse(
        text(
            line(dist="5200108 Melilla distrito 08"),
            line(secc="5200108015 Melilla sección 08015", valor="53.022"),
            line(),
        )
    )
    assert [(r["codigo"], r["renta_eur"]) for r in rows] == [("01001", 16429)]


def test_bad_header_fails():
    with pytest.raises(ValueError, match="header"):
        parse("a;b;c;d;e;f\n")


def test_blank_municipality_without_geo_fails():
    with pytest.raises(ValueError, match="blank municipality"):
        parse(text(line(mun="")))


def test_label_without_code_fails():
    with pytest.raises(ValueError, match="without code"):
        parse(text(line(mun="Alegría-Dulantzi")))


def test_unknown_indicator_and_year_fail():
    with pytest.raises(ValueError, match="unknown indicator"):
        parse(text(line(ind="Renta media")))
    with pytest.raises(ValueError, match="year out of range"):
        parse(text(line(anyo=2014)))


def test_unparsable_value_fails():
    with pytest.raises(ValueError, match="unparsable value"):
        parse(text(line(valor="16,429")))


def test_duplicate_cell_fails():
    with pytest.raises(ValueError, match="duplicate"):
        parse(text(line(), line()))


def test_ragged_row_fails():
    with pytest.raises(ValueError, match="ragged"):
        parse(text("01001 A;;;Renta neta media por hogar;2023;1;2"))


def test_no_observed_values_fails():
    with pytest.raises(ValueError, match="no observed"):
        parse(
            text(
                line(valor="."),
                line(ind="Renta neta media por persona", valor='""'),
            )
        )
