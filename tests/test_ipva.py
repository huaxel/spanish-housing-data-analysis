"""Tests for the IPVA municipal rent index fetch and the SERPAVI cross-check."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "explorations"))

import fetch_ipva  # noqa: E402


def _series(nombre: str, points: list[tuple[int, float | None]]) -> dict:
    return {
        "Nombre": nombre,
        "Data": [{"Anyo": y, "FK_Periodo": 28, "Valor": v} for y, v in points],
    }


def _payload(year_pairs: list[tuple[int, float]]) -> list[dict]:
    return [
        _series("Albacete. Índice. Total. ", year_pairs),
        _series("Albacete. Variación anual. Total. ", year_pairs),
        _series("Almansa. Índice. Total. ", year_pairs),
        _series("Almansa. Variación anual. Total. ", year_pairs),
    ] + [_series(f"Municipio{i}. Índice. Total. ", year_pairs) for i in range(500)]


def test_parse_handles_municipal_and_national_label_shapes():
    years = [(2012, 100.0), (2013, 101.5), (2023, 118.7)]
    payload = _payload(years) + [
        _series("Total Nacional. Total. Índice. ", years),
        _series("Total Nacional. Total. Variación anual. ", years),
    ]
    rows = fetch_ipva.parse(payload)
    assert {(r["municipio"], r["medida"]) for r in rows} >= {
        ("Albacete", "indice"),
        ("Albacete", "variacion"),
        ("Total Nacional", "indice"),
    }
    assert all(r["anyo"] in {2012, 2013, 2023} for r in rows)


def test_parse_drops_unpublished_cells_instead_of_zero_filling():
    payload = _payload([(2012, 100.0), (2013, None), (2023, 118.7)])
    rows = fetch_ipva.parse(payload)
    assert all(r["valor"] is not None for r in rows)
    assert not [r for r in rows if r["anyo"] == 2013]


def test_parse_rejects_non_annual_periods():
    payload = _payload([(2012, 100.0), (2013, 101.5), (2023, 118.7)])
    payload[0]["Data"][0]["FK_Periodo"] = 21  # quarterly code in an annual table
    try:
        fetch_ipva.parse(payload)
    except ValueError as exc:
        assert "non-annual" in str(exc)
    else:  # pragma: no cover - guard
        raise AssertionError("quarterly period accepted in an annual table")


def test_artifact_agrees_on_rank_and_disagrees_on_level():
    path = ROOT / "artifacts/ipva_rent_index.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text())
    cov = data["coverage"]
    assert cov["matched"] + cov["unmatched"] == cov["ipva_municipios"]
    for w in data["windows"]:
        assert w["n"] > 0
        # Positive rank agreement is the corroboration claim; a level gap that
        # scales with SERPAVI's own change is the divergence claim.
        assert 0.0 < w["spearman"] <= 1.0
        assert 0.0 < w["pearson"] <= 1.0
        assert w["gap_pp"]["p10"] <= w["gap_pp"]["median"] <= w["gap_pp"]["p90"]
        quartiles = w["quartiles_by_serpavi_change"]
        assert [q["quartile"] for q in quartiles] == [1, 2, 3, 4]
        # Gaps must widen (grow more negative) with SERPAVI's own change:
        # composition drift, not a constant instrument offset.
        gaps = [q["median_gap_pp"] for q in quartiles]
        assert gaps == sorted(gaps, reverse=True), gaps
    assert data["_meta"]["script_sha"] and data["_meta"]["data_sha"]
