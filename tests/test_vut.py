"""Tests for municipality-coded INE tourist-dwelling observations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "explorations"))

import vut_stock  # noqa: E402

import fetch_vut_municipal as vut  # noqa: E402


def _csv(rows, *, counts=True):
    header = [*vut.GEO, *(["Viviendas y plazas"] if counts else []), "Periodo", "Total"]
    return ("\ufeff" + "\n".join(";".join(row) for row in [header, *rows])).encode()


def _counts():
    return [
        ("Total Nacional", "", "", "", "Viviendas turísticas", "2026M05", "1.001"),
        ("Total Nacional", "13 Madrid", "28 Madrid", "", "Viviendas turísticas", "2026M05", "900"),
        (
            "Total Nacional",
            "13 Madrid",
            "28 Madrid",
            "28079 Madrid",
            "Viviendas turísticas",
            "2026M05",
            "850",
        ),
        (
            "Total Nacional",
            "09 Cataluña",
            "08 Barcelona",
            "08019 Barcelona",
            "Viviendas turísticas",
            "2026M05",
            "151",
        ),
    ]


def test_explicit_codes_distinguish_province_and_city_and_keep_leading_zero():
    national, province, madrid, barcelona = vut.parse(_csv(_counts()), 39363)
    assert (national["nivel"], national["valor"]) == ("nacional", 1001)
    assert (province["nivel"], province["codigo_ine"]) == ("agregado", None)
    assert (madrid["nivel"], madrid["codigo_ine"], madrid["valor"]) == ("municipio", "28079", 850)
    assert (barcelona["codigo_ine"], barcelona["territorio"]) == ("08019", "Barcelona")


def test_homonyms_have_separate_codes_not_merged_by_label():
    fixture = _counts()
    fixture[2] = (*fixture[2][:3], "28079 Villa", *fixture[2][4:])
    fixture[3] = (*fixture[3][:3], "08019 Villa", *fixture[3][4:])
    rows = vut.parse(_csv(fixture), 39363)
    assert [r["codigo_ine"] for r in rows if r["territorio"] == "Villa"] == ["28079", "08019"]


def test_rows_with_duplicate_keys_or_mismatched_provinces_are_rejected():
    fixture = _counts()
    with pytest.raises(ValueError, match="duplicate geography"):
        vut.parse(_csv([*fixture, fixture[-1]]), 39363)
    fixture[-1] = (*fixture[-1][:3], "28079 Barcelona", *fixture[-1][4:])
    with pytest.raises(ValueError, match="invalid municipality/province"):
        vut.parse(_csv(fixture), 39363)


def test_municipal_counts_must_sum_to_national_for_every_period():
    fixture = _counts()
    previous = [(*row[:-2], "2025M11", row[-1]) for row in fixture[:-1]]
    with pytest.raises(ValueError, match="do not sum to national counts"):
        vut.parse(_csv([*fixture, *previous]), 39363)


def test_missing_cells_are_not_zero_filled_and_decimal_commas_are_preserved():
    rows = vut.parse(
        _csv(
            [
                ("Total Nacional", "", "", "", "2026M05", "1,28"),
                ("Total Nacional", "Andalucía", "29 Málaga", "29067 Málaga", "2026M05", ""),
                ("Total Nacional", "Madrid", "28 Madrid", "28079 Madrid", "2026M05", "0,71"),
            ],
            counts=False,
        ),
        39366,
    )
    assert [(r["codigo_ine"], r["valor"]) for r in rows] == [(None, 1.28), ("28079", 0.71)]


def test_share_without_stock_observation_is_rejected():
    shares = _csv(
        [
            ("Total Nacional", "", "", "", "2026M05", "1,28"),
            ("Total Nacional", "Andalucía", "29 Málaga", "29067 Málaga", "2026M05", "3,17"),
        ],
        counts=False,
    )
    with pytest.raises(ValueError, match="share without a corresponding stock observation"):
        vut.derive({39363: _csv(_counts()), 39366: shares})


def test_municipal_map_has_official_codes_for_capitals():
    assert {"28079", "29067", "08019", "41091"} <= vut_stock.map_codes(vut_stock.MUNICIPAL_MAP)


def test_artifact_reports_code_coverage_and_skew():
    path = ROOT / "artifacts/vut_stock.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text())
    nat = data["national"]
    cov = data["coverage"]
    shares = data["shares"]
    assert nat["viviendas_turisticas"] > 0 and nat["plazas"] > nat["viviendas_turisticas"]
    assert cov["assigned_stock"] + cov["unassigned_stock"] == nat["viviendas_turisticas"]
    assert cov["matched_map_rows"] + cov["unassigned_rows"] == cov["municipio_rows"]
    assert len(cov["unmatched_map_codes"]) == cov["unassigned_rows"]
    assert shares["median_pct"] < shares["p90_pct"] < shares["max_pct"]
    if data["snapshot"] == {"year": 2026, "period": 5}:
        assert cov["matched_map_rows"] == cov["municipio_rows"] == 8131
        assert {"Madrid", "Málaga", "Barcelona", "Sevilla"} <= set(
            data["concentration"]["top10_municipios"]
        )
    assert (
        data["source"]["methodology_url"]
        == "https://www.ine.es/experimental/viv_turistica/experimental_viv_turistica.htm"
    )
    assert data["_meta"]["script_sha"] and data["_meta"]["data_sha"]
