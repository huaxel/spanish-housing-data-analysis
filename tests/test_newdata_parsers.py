"""Offline parser tests for the three new-data fetches (2026-10-06).

Covers: Censo Anual 68521 (static CSV margin parser), SERPAVI Excel
(melt parser, year-suffix decoding, Barcelona anchor), intensidad 59531
(municipal rows + Resto aggregates). No network, no data/ dependency —
the parsers are exercised on small inline fixtures so format drift is
caught offline, like the legacy parser tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_censo_anual as ca  # noqa: E402
import fetch_intensidad as it  # noqa: E402
import fetch_serpavi as sp  # noqa: E402


def _write_csv(tmp_path, text: str) -> Path:
    p = tmp_path / "fixture.csv"
    p.write_text(text, encoding="utf-8")
    return p


# --- Censo Anual de Población (68521) ---------------------------------------


def _censo_csv() -> str:
    hdr = [
        "Total Nacional",
        "Comunidades y Ciudades Autónomas",
        "Provincias",
        "Sexo",
        "Edad",
        "País de nacionalidad",
        "Periodo",
        "Total",
    ]
    rows = [
        ["Total Nacional", "", "", "Total", "Todas las edades", "Total", "2025", "49.128.297"],
        [
            "Total Nacional",
            "13 Madrid, Comunidad de",
            "28 Madrid",
            "Total",
            "Todas las edades",
            "Total",
            "2025",
            "7.113.886",
        ],
        [
            "Total Nacional",
            "13 Madrid, Comunidad de",
            "28 Madrid",
            "Total",
            "Todas las edades",
            "Total",
            "2021",
            "6.751.251",
        ],
        [
            "Total Nacional",
            "13 Madrid, Comunidad de",
            "28 Madrid",
            "Hombres",
            "Todas las edades",
            "Total",
            "2025",
            "3.480.000",
        ],
    ]
    return "\n".join("\t".join(r) for r in [hdr] + rows) + "\n"


CENSO_CSV = _censo_csv()


def test_censo_anual_keeps_margin_only_and_decodes_year(tmp_path):
    rows = ca.parse_rows(_write_csv(tmp_path, CENSO_CSV))
    prov = [r for r in rows if r["granularity"] == "provincia"]
    assert len(prov) == 2  # 2025 + 2021 margin rows; sex/age detail skipped
    m2025 = [r for r in prov if r["anyo"] == 2025][0]
    assert m2025["code"] == "28" and m2025["territorio"] == "Madrid"
    assert m2025["poblacion"] == 7_113_886
    assert all(r["anyo"] in (2021, 2025) for r in prov)


# --- Intensidad de uso (59531) ----------------------------------------------


def _intensidad_csv() -> str:
    hdr = [
        "Total Nacional",
        "Comunidades y Ciudades Autónomas",
        "Provincias",
        "Municipios",
        "Consumo eléctrico",
        "Total",
    ]
    rows = [
        [
            "Total Nacional",
            "01 Andalucía",
            "04 Almería",
            "04001 Abla",
            "Viviendas totales",
            "1.076",
        ],
        ["Total Nacional", "01 Andalucía", "04 Almería", "04001 Abla", "Viviendas vacías", "225"],
        [
            "Total Nacional",
            "16 País Vasco",
            "01 Araba/Álava",
            "01999 Resto de Araba/Álava",
            "Viviendas totales",
            "10.788",
        ],
    ]
    return "\n".join("\t".join(r) for r in [hdr] + rows) + "\n"


INTENSIDAD_CSV = _intensidad_csv()


def test_intensidad_parses_municipio_and_resto_rows(tmp_path):
    rows = it.parse_rows(_write_csv(tmp_path, INTENSIDAD_CSV))
    assert len(rows) == 3
    abla = [r for r in rows if r["codigo"] == "04001"][0]
    assert abla["municipio"] == "Abla" and abla["medida"] == "Viviendas totales"
    assert abla["valor"] == 1076  # dot-thousands stripped
    resto = [r for r in rows if r["codigo"].endswith("999")][0]
    assert resto["codigo"] == "01999" and resto["municipio"] == "Resto de Araba/Álava"


# --- SERPAVI (MIVAU Excel melt) --------------------------------------------


def _write_xlsx(tmp_path, rows: list[list]) -> Path:
    """Minimal Municipios-sheet workbook: header + a few data rows."""
    import openpyxl

    p = tmp_path / "serpavi.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Municipios"
    hdr = ["CPRO", "NPRO", "CUMUN", "NMUN"]
    for i in range(0, 14):
        hdr.append(f"ALQM2_LV_M_VC_{11 + i}")
    # pad every row to the full header width so openpyxl never leaves a
    # None-valued header cell (the parser str()s it to "None" and rejects)
    ws.append(hdr)
    for r in rows:
        ws.append(list(r) + [None] * (len(hdr) - len(r)))
    wb.save(p)
    return p


def test_serpavi_melt_decodes_year_and_keeps_populated(tmp_path):
    p = _write_xlsx(
        tmp_path,
        [
            ["08", "Barcelona", "08019", "Barcelona"]
            + [12.0, 12.2, 12.4, 12.6, 12.8, 13.0, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.5],
            ["08", "Barcelona", "08101", "L Hospitalet de Llobregat"] + [11.0] + [None] * 13,
        ],
    )
    rows, anchors = sp.parse_municipios(p)
    # 14 populated cells in row 1 (2011-2024), 1 in row 2 (2011 only)
    assert len(rows) == 15
    years = {r["anyo"] for r in rows}
    assert years == set(range(2011, 2025))
    bcn14 = [r for r in rows if r["codigo"] == "08019" and r["anyo"] == 2014][0]
    assert bcn14["valor"] == 12.6 and bcn14["municipio"] == "Barcelona"
    assert anchors["ALQM2_LV_M_VC"] == 13.5  # Barcelona 2024 anchor
    # Blank cells are statistical suppression, not zeros
    assert all(r["valor"] != 0 for r in rows)
