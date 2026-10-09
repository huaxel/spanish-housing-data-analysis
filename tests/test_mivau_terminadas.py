"""Offline MIVAU iniciadas/terminadas parser contracts."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_mivau_terminadas as ft  # noqa: E402

HEADER = "Año;Mes_Numero;Valor;Tipo_de_Vivienda;Estado;CODAUTO;Comunidad_Autónoma;CPRO;Provincia"


def line(
    anyo=2021,
    mes=1,
    valor="10",
    tipo="Libre",
    estado="Terminadas",
    cpro="8",
    prov="Barcelona",
    cc="9",
    ccaa="Cataluña",
):
    return f"{anyo};{mes};{valor};{tipo};{estado};{cc};{ccaa};{cpro};{prov}"


def text(*lines):
    return "\n".join([HEADER, *lines]) + "\n"


def test_parse_pads_cpro_and_keeps_missing_null():
    rows = ft.parse(text(line(), line(mes=2, valor="")))
    assert [(r["cpro"], r["mes"], r["viviendas"]) for r in rows] == [
        ("08", 1, 10),
        ("08", 2, None),
    ]
    assert rows[0]["provincia"] == "Barcelona"


def test_bad_header_fails():
    with pytest.raises(ValueError, match="header"):
        ft.parse("a;b;c\n")


def test_unknown_estado_tipo_cpro_fail():
    with pytest.raises(ValueError, match="estado"):
        ft.parse(text(line(estado="Reformadas")))
    with pytest.raises(ValueError, match="tipo"):
        ft.parse(text(line(tipo="Rural")))
    with pytest.raises(ValueError, match="CPRO"):
        ft.parse(text(line(cpro="99")))


def test_year_month_bounds_fail():
    with pytest.raises(ValueError, match="year"):
        ft.parse(text(line(anyo=1999)))
    with pytest.raises(ValueError, match="month"):
        ft.parse(text(line(mes=13)))


def test_nonnumeric_value_fails():
    with pytest.raises(ValueError, match="nonnumeric"):
        ft.parse(text(line(valor="1.5")))


def test_duplicate_and_ragged_fail():
    with pytest.raises(ValueError, match="duplicate"):
        ft.parse(text(line(), line()))
    with pytest.raises(ValueError, match="ragged"):
        ft.parse(text(line() + ";extra"))


def test_blank_labels_fail():
    with pytest.raises(ValueError, match="blank territory"):
        ft.parse(text(line(prov=" ")))


def test_no_observed_values_fails():
    with pytest.raises(ValueError, match="no observed"):
        ft.parse(text(line(valor="")))


def test_validate_coverage_rejects_dropped_province_and_moved_start():
    rows = [{"cpro": "08", "anyo": 2008}]
    with pytest.raises(ValueError, match="dropped province"):
        ft.validate_coverage(rows)
    full = [{"cpro": str(n).zfill(2), "anyo": 2009} for n in range(1, 53)]
    with pytest.raises(ValueError, match="series start"):
        ft.validate_coverage(full)
    good = [{"cpro": str(n).zfill(2), "anyo": 2008} for n in range(1, 53)]
    ft.validate_coverage(good)
