"""Offline MIVAU started/finished-dwelling parser contracts."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_mivau_terminadas as ft  # noqa: E402


def line(
    anyo=2021,
    mes=1,
    valor="10",
    regimen="Libre",
    estado="Terminada",
    cpro="08",
    prov="Barcelona",
    cc="09",
    ccaa="Cataluña",
):
    return f"{cc};{ccaa};{cpro};{prov};{anyo};{mes};{regimen};{estado};{valor}"


def approval(valor="10", tipo="Protegida", tramite="Calificación", estado="Definitiva", mes=1):
    return f"09;Cataluña;08;Barcelona;2021;{mes};{tipo};{tramite};{estado};{valor}"


def text(*lines, header=ft.HEADER_FREE):
    return "\n".join([";".join(header), *lines]) + "\n"


def vp(*lines):
    return text(*lines, header=ft.HEADER_PROTECTED)


def test_free_regime_spellings_and_missing_null():
    rows = ft.parse_free(text(line(), line(mes=2, valor="", regimen="Libres", estado="Iniciada")))
    assert [(r["cpro"], r["tipo"], r["estado"], r["viviendas"]) for r in rows] == [
        ("08", "Libre", "Terminadas", 10),
        ("08", "Libre", "Iniciadas", None),
    ]


def test_protected_takes_only_final_approvals():
    rows = ft.parse_protected(
        vp(
            approval(valor="7"),
            # Two unlabelled provisional entries per cell are published; unused.
            approval(valor="1", estado="Provisional"),
            approval(valor="2", estado="Provisional"),
            approval(tipo="Rehabilitación", tramite="Aprobaciones"),
        )
    )
    assert [(r["tipo"], r["estado"], r["viviendas"]) for r in rows] == [
        ("Protegida", "Terminadas", 7)
    ]


@pytest.mark.parametrize("parse", [ft.parse_free, ft.parse_protected])
def test_bad_or_previous_header_fails(parse):
    previous = (
        "Año;Mes_Numero;Valor;Tipo_de_Vivienda;Estado;CODAUTO;Comunidad_Autónoma;CPRO;Provincia\n"
    )
    for source in ("a;b;c\n", previous, ""):
        with pytest.raises(ValueError, match="header"):
            parse(source)


def test_unknown_categories_fail():
    with pytest.raises(ValueError, match="estado"):
        ft.parse_free(text(line(estado="Reformada")))
    # Protected rows reappearing in VDP005 would double count with VDP007.
    with pytest.raises(ValueError, match="regimen"):
        ft.parse_free(text(line(regimen="Protegida")))
    with pytest.raises(ValueError, match="CPRO"):
        ft.parse_free(text(line(cpro="99")))
    with pytest.raises(ValueError, match="approval block"):
        ft.parse_protected(vp(approval(estado="Otra")))


def test_year_month_value_bounds_fail():
    with pytest.raises(ValueError, match="year"):
        ft.parse_free(text(line(anyo=1999)))
    with pytest.raises(ValueError, match="month"):
        ft.parse_free(text(line(mes=13)))
    with pytest.raises(ValueError, match="nonnumeric"):
        ft.parse_free(text(line(valor="1.5")))


def test_duplicate_ragged_blank_and_empty_fail():
    with pytest.raises(ValueError, match="duplicate"):
        ft.parse_free(text(line(), line(regimen="Libres")))
    with pytest.raises(ValueError, match="duplicate"):
        ft.parse_protected(vp(approval(), approval()))
    with pytest.raises(ValueError, match="ragged"):
        ft.parse_free(text(line() + ";extra"))
    with pytest.raises(ValueError, match="blank territory"):
        ft.parse_free(text(line(prov=" ")))
    with pytest.raises(ValueError, match="no observed"):
        ft.parse_free(text(line(valor="")))


def test_validate_coverage_rejects_dropped_province_and_moved_start():
    with pytest.raises(ValueError, match="dropped province"):
        ft.validate_coverage([{"cpro": "08", "anyo": 2008}])
    with pytest.raises(ValueError, match="series start"):
        ft.validate_coverage([{"cpro": c, "anyo": 2009} for c in ft.CPROS])
    ft.validate_coverage([{"cpro": c, "anyo": 2008} for c in ft.CPROS])


def bulletin_rows():
    series = (("Libre", "Iniciadas"), ("Libre", "Terminadas"), ("Protegida", "Terminadas"))
    return [
        {"anyo": year, "tipo": tipo, "estado": estado, "viviendas": value}
        for year, values in ft.BULLETIN.items()
        for (tipo, estado), value in zip(series, values, strict=True)
    ]


def test_bulletin_anchor_accepts_published_totals():
    assert sorted(ft.BULLETIN) == list(range(2008, 2025))
    # Transcription cross-check: the bulletin prints 100,980 completions in 2024.
    assert sum(ft.BULLETIN[2024][1:]) == 100980
    ft.validate_bulletin(bulletin_rows())


def test_bulletin_anchor_rejects_short_protected_series():
    rows = bulletin_rows()
    for row in rows:
        if (row["anyo"], row["tipo"]) == (2024, "Protegida"):
            row["viviendas"] = 1134
    with pytest.raises(ValueError, match="Protegida Terminadas 2024 = 1134"):
        ft.validate_bulletin(rows)


def grid(end=(2025, 12)):
    return [
        {"cpro": c, "anyo": y, "mes": m, "tipo": "Protegida", "estado": "Terminadas"}
        for c in ft.CPROS
        for y in range(2008, end[0] + 1)
        for m in range(1, 13)
        if (y, m) <= end
    ]


def test_grid_rejects_missing_late_rows_and_short_series():
    ft.validate_grid(grid())
    ft.validate_grid(grid((2026, 3)))
    madrid_december = ("28", 2025, 12)
    with pytest.raises(ValueError, match="gaps"):
        ft.validate_grid(
            [r for r in grid((2026, 3)) if (r["cpro"], r["anyo"], r["mes"]) != madrid_december]
        )
    with pytest.raises(ValueError, match="ends"):
        ft.validate_grid(grid((2024, 12)))
