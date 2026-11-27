"""Tests for the INE rent-update reference index (IRAV) fetch + summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_irav  # noqa: E402


def _payload(months: list[tuple[int, int, float]]) -> list[dict]:
    return [
        {
            "Nombre": "Total Nacional. Índice general. Variación anual. ",
            "Data": [{"Anyo": y, "FK_Periodo": m, "Valor": v} for y, m, v in months],
        }
    ]


def test_parse_flattens_and_sorts_months():
    # unsorted, contiguous months: parse must sort by (year, month)
    rows = fetch_irav.parse(_payload([(2025, 2, 2.08), (2024, 12, 2.28), (2025, 1, 2.19)]))
    assert rows == [
        {"anyo": 2024, "mes": 12, "irav_pct": 2.28},
        {"anyo": 2025, "mes": 1, "irav_pct": 2.19},
        {"anyo": 2025, "mes": 2, "irav_pct": 2.08},
    ]


def test_parse_rejects_non_month_periods():
    try:
        fetch_irav.parse(_payload([(2025, 12, 2.0), (2025, 13, 2.1)]))
    except ValueError as exc:
        assert "period code" in str(exc)
    else:  # pragma: no cover - guard
        raise AssertionError("quarter code accepted as a month")


def test_parse_rejects_gaps_in_the_rolling_window():
    # 2025-01 then 2025-03 leaves a hole: INE publishes contiguous months.
    try:
        fetch_irav.parse(_payload([(2025, 1, 2.19), (2025, 3, 1.98)]))
    except ValueError as exc:
        assert "contiguous" in str(exc)
    else:  # pragma: no cover - guard
        raise AssertionError("gap accepted")


def test_parse_rejects_unexpected_series_name():
    payload = _payload([(2025, 1, 2.19)])
    payload[0]["Nombre"] = "Total Nacional. Índice general. Índice. "
    try:
        fetch_irav.parse(payload)
    except ValueError as exc:
        assert "unexpected series" in str(exc)
    else:  # pragma: no cover - guard
        raise AssertionError("index-level series accepted as the annual variation")


def test_artifact_summary_matches_series():
    path = ROOT / "artifacts/irav.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text())
    series = data["series"]
    assert data["window"]["months"] == len(series)
    assert data["latest"]["irav_pct"] == series[-1]["irav_pct"]
    assert data["latest"]["period"] == f"{series[-1]['anyo']}-{series[-1]['mes']:02d}"
    assert data["bounds"]["min"]["irav_pct"] == min(r["irav_pct"] for r in series)
    assert data["bounds"]["max"]["irav_pct"] == max(r["irav_pct"] for r in series)
    # A rolling window: monthly contiguity, no repeated month.
    idx = [r["anyo"] * 12 + r["mes"] for r in series]
    assert idx == list(range(idx[0], idx[0] + len(idx)))
    assert len(set(idx)) == len(idx)
    # Annual means cover exactly the months present, newest year partial.
    months = sum(m["months"] for m in data["annual_means"])
    assert months == len(series)
    assert data["_meta"]["script_sha"] and data["_meta"]["data_sha"]
