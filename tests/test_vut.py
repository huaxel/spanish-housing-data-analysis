"""Tests for the municipal tourist-dwelling estimate fetch and its accounting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_vut_municipal as vut  # noqa: E402


def _series(nombre: str, valor: float, anyo: int = 2026, periodo: int = 5) -> dict:
    return {
        "Nombre": nombre,
        "Data": [{"Anyo": anyo, "FK_Periodo": periodo, "Valor": valor}],
    }


def _payload(extra: list[dict] | None = None) -> list[dict]:
    rows = [_series("Total Nacional. Viviendas turísticas. Dato base. ", 341001.0)]
    rows.append(_series("Total Nacional. Plazas. Dato base. ", 1714702.0))
    for i in range(100):
        rows.append(_series(f"Municipio{i}. Viviendas turísticas. Dato base. ", 10.0 + i))
    return rows + (extra or [])


def test_parse_maps_measures_and_keeps_snapshots():
    rows = vut.parse(_payload(), 39363)
    nat = [r for r in rows if r["territorio"] == "Total Nacional"]
    assert {(r["medida"], r["valor"]) for r in nat} == {
        ("viviendas_turisticas", 341001.0),
        ("plazas", 1714702.0),
    }
    assert all(r["anyo"] == 2026 and r["periodo"] == 5 for r in rows)


def test_parse_marks_duplicated_labels_ambiguous_instead_of_guessing():
    # Same label twice with different values: a province and its capital, or two
    # provinces. The rows must survive but be flagged, never silently assigned.
    extra = [
        _series("Segovia. Viviendas turísticas. Dato base. ", 875.0),
        _series("Segovia. Viviendas turísticas. Dato base. ", 101.0),
    ]
    rows = vut.parse(_payload(extra), 39363)
    segovia = [r for r in rows if r["territorio"] == "Segovia"]
    assert len(segovia) == 2
    assert {r["nivel"] for r in segovia} == {"ambiguo"}
    assert {r["valor"] for r in segovia} == {875.0, 101.0}


def test_parse_gives_unique_labels_the_municipio_level():
    rows = vut.parse(_payload(), 39363)
    assert {r["nivel"] for r in rows if r["territorio"] == "Municipio0"} == {"municipio"}


def test_parse_rejects_payloads_without_a_national_total():
    try:
        vut.parse([_series("Municipio0. Viviendas turísticas. Dato base. ", 5.0)], 39363)
    except ValueError as exc:
        assert "national total" in str(exc)
    else:  # pragma: no cover - guard
        raise AssertionError("payload without national total accepted")


def test_parse_drops_unpublished_cells():
    payload = _payload()
    payload[1]["Data"][0]["Valor"] = None
    rows = vut.parse(payload, 39363)
    assert not [r for r in rows if r["medida"] == "plazas"]


def test_artifact_reports_coverage_and_skew():
    path = ROOT / "artifacts/vut_stock.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text())
    nat = data["national"]
    cov = data["coverage"]
    sh = data["shares"]
    assert nat["viviendas_turisticas"] > 0 and nat["plazas"] > nat["viviendas_turisticas"]
    # The assigned subset should not exceed the national estimate.
    assert 0 < cov["assigned_stock"] <= nat["viviendas_turisticas"]
    assert 0 < cov["assigned_share_of_national_pct"] <= 100
    # The published shares in this vintage show a long right tail.
    assert sh["median_pct"] < sh["p90_pct"] < sh["max_pct"]
    assert 0 < sh["share_above_5pct"] < 100
    assert (
        data["source"]["methodology_url"]
        == "https://www.ine.es/experimental/viv_turistica/experimental_viv_turistica.htm"
    )
    assert data["_meta"]["script_sha"] and data["_meta"]["data_sha"]
