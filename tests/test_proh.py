"""Tests for the INE household projection (PROH) fetch and the stock pairing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_proh  # noqa: E402

YEARS = list(range(2026, 2041))


def _series(nombre: str, total: float, sizes: tuple[float, ...] = (0.3, 0.3, 0.2, 0.2)):
    return {
        "Nombre": nombre,
        "Data": [
            {"Anyo": y, "FK_Periodo": 28, "Valor": total * (1 + 0.01 * (y - 2026))} for y in YEARS
        ],
    }


def _size_series(nombre: str, total: float, sizes: tuple[float, ...]) -> list[dict]:
    labels = ["1", "2", "3", "4 y más"]
    out = []
    for label, share in zip(labels, sizes, strict=True):
        out.append(
            {
                "Nombre": f"{nombre}. {label}. "
                if not nombre.endswith(" ")
                else f"{label}. {nombre}",
                "Data": [
                    {
                        "Anyo": y,
                        "FK_Periodo": 28,
                        "Valor": total * (1 + 0.01 * (y - 2026)) * share,
                    }
                    for y in YEARS
                ],
            }
        )
    return out


def _territory(name: str, total: float) -> list[dict]:
    sizes = (0.3, 0.3, 0.2, 0.2)
    return [_series(f"{name}. Total. ", total)] + _size_series(name, total, sizes)


def _payload(extra: list[dict] | None = None) -> list[dict]:
    payload = []
    for i in range(60):
        payload += _territory(f"Provincia{i}", 1_000_000.0 + i)
    payload += _territory("Total Nacional", 50_000_000.0)
    payload += extra or []
    return payload


def test_parse_handles_both_measure_positions():
    rows = fetch_proh.parse(_payload())
    assert ("Total Nacional", "Total", 2026) in {
        (r["territorio"], r["medida"], r["anyo"]) for r in rows
    }
    # "4 y más. <territorio>." keeps the measure first: territory must still parse.
    assert any(r["territorio"] == "Total Nacional" and r["medida"] == "4 y más" for r in rows)


def test_parse_collapses_duplicated_uniprovincial_territories():
    dup = _territory("Cantabria", 500_000.0)
    rows = fetch_proh.parse(_payload(extra=dup))
    duplicated = [r for r in rows if r["territorio"] == "Cantabria" and r["medida"] == "Total"]
    assert len(duplicated) == len(YEARS)


def _scaled(territory_payload: list[dict], factor: float) -> list[dict]:
    """Same territory, internally consistent, but every level differs by `factor`."""
    out = []
    for series in territory_payload:
        out.append(
            {
                "Nombre": series["Nombre"],
                "Data": [dict(obs, Valor=obs["Valor"] * factor) for obs in series["Data"]],
            }
        )
    return out


def test_parse_rejects_two_copies_that_disagree():
    # Two identical labels (CCAA and province level) carrying different numbers.
    dup = _territory("Cantabria", 500_000.0) + _scaled(_territory("Cantabria", 500_000.0), 1.5)
    try:
        fetch_proh.parse(_payload(extra=dup))
    except ValueError as exc:
        assert "disagrees" in str(exc)
    else:  # pragma: no cover - guard
        raise AssertionError("conflicting duplicate accepted")


def test_parse_rejects_size_components_that_do_not_add_up():
    payload = _payload()
    for series in payload:
        if series["Nombre"] == "Total Nacional. 1. ":
            for obs in series["Data"]:
                obs["Valor"] *= 2.0
    try:
        fetch_proh.parse(payload)
    except ValueError as exc:
        assert "do not add" in str(exc)
    else:  # pragma: no cover - guard
        raise AssertionError("non-additive sizes accepted")


def test_artifact_reproduces_the_two_group_split():
    path = ROOT / "artifacts/proh_households.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text())
    nat = data["national"]
    assert nat["households_last"] > nat["households_first"]
    assert nat["change"] == nat["households_last"] - nat["households_first"]
    assert data["ecp_check"]["projection_minus_observed"] == (
        nat["households_first"] - data["ecp_check"]["observed_2026"]
    )
    # The projected growth must concentrate: top-4 above 50% of the total.
    assert 50.0 < data["concentration"]["top4_share_pct"] <= 100.0
    # The two-group reading: lean-stock CCAA projected to grow faster, negative r.
    pair = data["stock_pairing"]
    assert pair["lean_stock_growth_median_pct"] > pair["fat_stock_growth_median_pct"]
    assert pair["pearson_ratio_vs_growth"] < 0
    assert pair["n_ccaa"] == len(data["ccaa"])
    # Dwellings implied is an identity, never below the current stock.
    for row in data["ccaa"]:
        assert row["dwellings_implied_2040"] >= row["households_2040"]
    assert data["_meta"]["script_sha"] and data["_meta"]["data_sha"]
