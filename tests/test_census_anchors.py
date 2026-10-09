"""Offline census-2001/2011 anchor mapping tests. No network, no data/ dependency."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_marts import CENSO_0111_MAX_GAP_PCT, census_0111_anchor_rows  # noqa: E402

CCAA = {"01": "CCAA Multi", "02": "CCAA Multi", "03": "CCAA Single"}
# 'BB' has no census province rows (single-province CCAA land only in the
# CCAA rows) but is a known mart cpro, mirroring production.
PROV = {"AA": "01", "ALICANTE ALACANT": "02", "BB": "03"}


def row(prov, ccaa, tipo, periodo, total):
    return {
        "Provincias": prov,
        "Comunidades y Ciudades Autónomas": ccaa,
        "Tipo de vivienda": tipo,
        "Periodo": periodo,
        "Total": total,
    }


P = "Total viviendas principales (2.1)"
NP = "Total viviendas no principales (2.2)"


def dot(n):
    return f"{n:,}".replace(",", ".")


def fixture_rows():
    rows = []
    for periodo in ("2001", "2011"):
        mult = 1 if periodo == "2001" else 10
        rows += [
            row("AA", "", P, periodo, dot(100 * mult)),
            row("AA", "", NP, periodo, dot(20 * mult)),
            row("Alicante/Alacant", "", P, periodo, dot(200 * mult)),
            row("Alicante/Alacant", "", NP, periodo, dot(40 * mult)),
        ]
    # CCAA rows: single-province consumed, multi-province checked, cities aggregated.
    for periodo in ("2001", "2011"):
        mult = 1 if periodo == "2001" else 10
        rows += [
            row("", "CCAA Single", P, periodo, dot(50 * mult)),
            row("", "CCAA Single", NP, periodo, dot(10 * mult)),
            row("", "CCAA Multi", P, periodo, dot(300 * mult)),
            row("", "CCAA Multi", NP, periodo, dot(60 * mult)),
            row("", "Ceuta", P, periodo, dot(5 * mult)),
            row("", "Ceuta", NP, periodo, dot(1 * mult)),
            row("", "Melilla", P, periodo, dot(7 * mult)),
            row("", "Melilla", NP, periodo, dot(2 * mult)),
        ]
    # Nacional rows reconcile exactly with the parts (provinces + single
    # CCAA + cities — multi-province CCAA aggregates never counted twice).
    for periodo in ("2001", "2011"):
        mult = 1 if periodo == "2001" else 10
        rows += [
            row("", "", P, periodo, dot((100 + 200 + 50 + 5 + 7) * mult)),
            row("", "", NP, periodo, dot((20 + 40 + 10 + 1 + 2) * mult)),
        ]
    return rows


def test_maps_all_grains_and_reconciles_nacional():
    rows = census_0111_anchor_rows(fixture_rows(), PROV, CCAA)
    by_key = {(r["cpro"], r["periodo"]): r for r in rows}
    assert len(rows) == 8  # 2 prov + 1 single + 51+52, both periodos
    assert by_key[("01", 2001)]["viviendas"] == 120
    assert by_key[("01", 2001)]["grano"] == "provincia"
    assert by_key[("02", 2011)]["viviendas"] == 2400
    assert by_key[("03", 2001)]["viviendas"] == 60
    assert by_key[("03", 2001)]["grano"] == "ccaa_uniprovincial"
    assert by_key[("51+52", 2011)]["viviendas"] == 150
    assert by_key[("51+52", 2011)]["grano"] == "ceuta_melilla"


def test_unmapped_provincia_fails():
    rows = fixture_rows() + [row("ZZ", "", P, "2001", "9"), row("ZZ", "", NP, "2001", "1")]
    with pytest.raises(SystemExit, match="unmapped provincia"):
        census_0111_anchor_rows(rows, PROV, CCAA)


def test_empty_and_comma_totals_fail():
    bad_empty = [
        dict(r, Total="") if r["Provincias"] == "AA" and r["Periodo"] == "2001" else r
        for r in fixture_rows()
    ]
    with pytest.raises(SystemExit, match="unparsable Total"):
        census_0111_anchor_rows(bad_empty, PROV, CCAA)
    bad_comma = [
        dict(r, Total="1,234") if r["Provincias"] == "AA" and r["Periodo"] == "2001" else r
        for r in fixture_rows()
    ]
    with pytest.raises(SystemExit, match="unparsable Total"):
        census_0111_anchor_rows(bad_comma, PROV, CCAA)


def test_tipo_and_periodo_drift_fail():
    bad_tipo = fixture_rows() + [row("AA", "", "Viviendas (9.9)", "2001", "1")]
    with pytest.raises(SystemExit, match="tipo drift"):
        census_0111_anchor_rows(bad_tipo, PROV, CCAA)
    bad_periodo = [
        dict(r, Periodo="2021") if r["Provincias"] == "AA" else r for r in fixture_rows()
    ]
    with pytest.raises(SystemExit, match="periodo drift"):
        census_0111_anchor_rows(bad_periodo, PROV, CCAA)


def test_missing_city_and_double_count_fail():
    no_melilla = [r for r in fixture_rows() if r["Comunidades y Ciudades Autónomas"] != "Melilla"]
    with pytest.raises(SystemExit, match="missing MELILLA"):
        census_0111_anchor_rows(no_melilla, PROV, CCAA)
    prov03 = {**PROV, "CC": "03"}
    doubled = fixture_rows() + [row("CC", "", P, "2001", "3"), row("CC", "", NP, "2001", "1")]
    with pytest.raises(SystemExit, match="double-counted"):
        census_0111_anchor_rows(doubled, prov03, CCAA)


def test_ccaa_province_and_nacional_mismatch_fail():
    off_by_two = [
        dict(r, Total="362")
        if r["Comunidades y Ciudades Autónomas"] == "CCAA Multi" and r["Periodo"] == "2001"
        else r
        for r in fixture_rows()
    ]
    with pytest.raises(SystemExit, match="disagrees with its provinces"):
        census_0111_anchor_rows(off_by_two, PROV, CCAA)
    bad_nacional = [
        dict(r, Total="999")
        if not r["Provincias"] and not r["Comunidades y Ciudades Autónomas"]
        else r
        for r in fixture_rows()
    ]
    with pytest.raises(SystemExit, match="nacional mismatch"):
        census_0111_anchor_rows(bad_nacional, PROV, CCAA)


def test_unknown_ccaa_grain_fails():
    rows = fixture_rows() + [
        row("", "Atlantis", P, "2001", "1"),
        row("", "Atlantis", NP, "2001", "1"),
    ]
    with pytest.raises(SystemExit, match="unknown CCAA grain"):
        census_0111_anchor_rows(rows, PROV, CCAA)


def test_gap_threshold_is_pinned():
    assert CENSO_0111_MAX_GAP_PCT == 2.0
