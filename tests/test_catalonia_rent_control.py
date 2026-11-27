"""Tests for Catalonia rent-control fetcher and DiD evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "explorations"))

import fetch_catalonia_rent_control as fetcher  # noqa: E402


def test_norm_name_handles_articles_and_accents():
    assert fetcher.norm_name("Hospitalet de Llobregat, l'") == "l hospitalet de llobregat"
    assert fetcher.norm_name("l'Hospitalet de Llobregat") == "l hospitalet de llobregat"
    assert fetcher.norm_name("Masnou, el") == "el masnou"
    assert fetcher.norm_name("Castell d'Aro, Platja d'Aro i S'Agaró") == (
        "castell d aro platja d aro i s agaro"
    )


def test_pinned_boe_wave_counts_and_disjoint():
    w1_path = fetcher.RAW_FILES["boe_wave1"][0]
    w2_path = fetcher.RAW_FILES["boe_wave2"][0]
    if not (w1_path.is_file() and w2_path.is_file()):
        return
    w1 = fetcher.parse_boe_municipalities(w1_path, expected_count=140)
    w2 = fetcher.parse_boe_municipalities(w2_path, expected_count=131)
    assert len(w1) == 140
    assert len(w2) == 131
    assert "Barcelona" in w1
    assert "Vinyols i els Arcs" in w2
    assert "Castell d'Aro, Platja d'Aro i S'Agaró" in w2


def test_catalonia_artifact_structure_and_bounds():
    artifact = ROOT / "artifacts/catalonia_rent_control.json"
    if not artifact.is_file():
        return
    data = json.loads(artifact.read_text())
    assert data["meta"]["active_munis_by_wave"]["1"] >= 135
    assert data["meta"]["active_munis_by_wave"]["2"] >= 120
    assert len(data["did_summary"]) == 12
    # Cleanest design (Wave 1 vs Wave 2) has both rent and contract estimates + wild_p
    a_rows = {r["outcome_id"]: r for r in data["did_summary"] if r["design_id"] == "A_w1_vs_w2"}
    assert set(a_rows) == {"log_rent", "log_contracts", "temporada_share"}
    assert a_rows["log_rent"]["wild_p"] is not None
    assert a_rows["log_contracts"]["wild_p"] is not None
    # No zero rents leaked into group series
    for row in data["group_series"]:
        if row["rent_weighted_eur"] is not None:
            assert row["rent_weighted_eur"] > 100.0
