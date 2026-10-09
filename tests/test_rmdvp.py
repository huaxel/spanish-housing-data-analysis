"""Offline RMDVP table-01 parser tests. No network, no data/ dependency."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_rmdvp import (  # noqa: E402
    EXPECTED_WINDOW_START,
    _month_end_serial,
    parse_rmdvp_rows,
)

YYYYMM = "202608"
MONTH_END = _month_end_serial(YYYYMM)


def blank_grid(nrows=34):
    return [["" for _ in range(24)] for _ in range(nrows)]


def muni_row(prov, muni, ine, sol, ins, act, can, cad):
    r = [""] * 24
    r[6], r[9], r[13] = f"'{prov}'", f"'{muni}'", f"'{ine}'"
    r[17], r[18], r[19], r[21], r[23] = sol, ins, act, can, cad
    return r


def prov_row(prov, sol, ins, act, can, cad):
    r = [""] * 24
    r[5], r[9] = f"'{prov}'", "'Total'"
    r[17], r[18], r[19], r[21], r[23] = sol, ins, act, can, cad
    return r


def base_grid():
    g = blank_grid()
    g[6][0] = "'RMDVP solicitudes e inscripciones'"
    g[3][11] = "'Solicitudes y estado de inscripciones'"
    g[7][0] = "'Registros Municipales de Demandantes de Vivienda Protegida'"
    g[12][4] = "'Fecha de Solicitud está entre:'"
    g[12][12] = EXPECTED_WINDOW_START
    g[11][15] = MONTH_END
    g[13][3] = "'Provincias:'"
    g[13][7] = "'ALMERÍA, CÁDIZ, CÓRDOBA, GRANADA, HUELVA, JAÉN, MÁLAGA, SEVILLA'"
    g[19][5], g[19][9], g[19][13] = "'Provincia'", "'Municipio'", "'Código INE'"
    g[19][17], g[19][18] = "'Solicitudes'", "'Inscripciones'"
    g[20][18], g[20][19] = "'Total'", "'Activas'"
    g[20][21], g[20][23] = "'Canceladas por Adjudicación'", "'Caducadas y otros'"
    # Two Almería municipalities, consistent subtotal + grand total.
    g[21] = muni_row("ALMERÍA", "Abla", "04001", "'10'", "'8'", "'5'", "'1'", 2.0)
    g[22] = muni_row("ALMERÍA", "Abrucena", "04002", 20.0, 12.0, 7.0, 2.0, 3.0)
    g[23] = prov_row("ALMERÍA", 30, 20, 12, 3, 5)
    for i, p in enumerate(["CÁDIZ", "CÓRDOBA", "GRANADA", "HUELVA", "JAÉN", "MÁLAGA", "SEVILLA"]):
        g[24 + i] = prov_row(p, 0, 0, 0, 0, 0)
    g[31][5] = "'Total'"
    g[31][17], g[31][18], g[31][19] = 30, 20, 12
    g[31][21], g[31][23] = 3, 5
    g[32][5] = "'Fecha de Ejecución del informe: '"
    g[32][10] = MONTH_END + 15
    return g


def test_happy_path():
    rows = parse_rmdvp_rows(base_grid(), YYYYMM)
    by = {(r["grano"], r["ine"] or r["provincia"] or "total"): r for r in rows}
    abla = by[("municipio", "04001")]
    assert abla["municipio"] == "Abla" and abla["cpro"] == "04"
    assert (abla["solicitudes"], abla["inscripciones"]) == (10, 8)
    assert isinstance(abla["caducadas"], int)
    assert by[("provincia", "ALMERÍA")]["inscripciones"] == 20
    total = by[("total_andalucia", "total")]
    assert total["inscripciones"] == 20 and total["ine"] is None
    assert len(rows) == 2 + 8 + 1


def test_header_drift_fails():
    g = base_grid()
    g[19][9] = "'Municipios'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_filter_end_must_be_month_end():
    g = base_grid()
    g[11][15] = MONTH_END - 1
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_window_start_drift_fails():
    g = base_grid()
    g[12][12] = EXPECTED_WINDOW_START + 365
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_identity_mismatch_fails():
    g = base_grid()
    g[21][19] = "'6'"  # 6+1+2 != 8
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_province_subtotal_mismatch_fails():
    g = base_grid()
    g[21][18] = "'9'"  # identity preserved (6+1+2), subtotal now wrong
    g[21][19] = "'6'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_total_mismatch_fails():
    g = base_grid()
    g[31][17] = 31
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_duplicate_ine_fails():
    g = base_grid()
    g[22][13] = "'04001'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_bad_ine_prefix_fails():
    g = base_grid()
    g[21][13] = "'28001'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_missing_province_subtotal_fails():
    g = base_grid()
    del g[24]  # drop CADIZ subtotal: drift assert, not row classifier
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_no_total_row_fails():
    g = base_grid()
    del g[32]  # exec row
    del g[31]  # Total row; truncate trailing blanks to reach end-of-grid
    g = g[:31]
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_negative_count_fails():
    g = base_grid()
    g[21][17] = "'-3'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_blank_row_before_footer_ok():
    g = base_grid()
    g.insert(32, [""] * 24)  # publisher blank row, as in 2020-12
    rows = parse_rmdvp_rows(g, YYYYMM)
    assert rows[-1]["grano"] == "total_andalucia"


def test_ine_province_mismatch_fails():
    g = base_grid()
    g[21][13] = "'11001'"  # Cádiz INE under an ALMERÍA label
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_title_drift_fails():
    g = base_grid()
    g[6][0] = "'RMDVP solicitudes'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_subtitle_drift_fails():
    g = base_grid()
    g[3][11] = "'Solicitudes'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_province_filter_drift_fails():
    g = base_grid()
    g[13][7] = "'ALMERÍA, CÁDIZ'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_filter_label_drift_fails():
    g = base_grid()
    g[12][4] = "'Fecha entre:'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_column_count_drift_fails():
    g = [row[:20] for row in base_grid()]
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_bad_province_label_fails():
    g = base_grid()
    g[21][6] = "'LEÓN'"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_exec_predates_month_end_fails():
    g = base_grid()
    g[32][10] = MONTH_END - 30
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_non_numeric_exec_serial_fails():
    g = base_grid()
    g[32][10] = "''"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_empty_count_fails():
    g = base_grid()
    g[21][17] = "''"
    with pytest.raises(SystemExit):
        parse_rmdvp_rows(g, YYYYMM)


def test_month_end_serials():
    assert _month_end_serial("202101") == 44227
    assert _month_end_serial("202608") == 46265
    assert _month_end_serial("202402") == 45351  # leap February
    assert _month_end_serial("202302") == 44985
