"""Tests for INE ECV 2025 distributional policy microsimulation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_ecv_microsim as sim  # noqa: E402


def test_effort_ratio_edge_cases():
    assert sim.effort_ratio(0.0, 20_000.0, 0.0) == 0.0
    assert sim.effort_ratio(500.0, 0.0, 0.0) > 0.40
    assert abs(sim.effort_ratio(500.0, 20_000.0, 0.0) - 0.30) < 1e-9
    # Allowance reduces both net cost and net income per Eurostat LC-ILC 39-09 rev.1
    assert abs(sim.effort_ratio(500.0, 20_000.0, 2_000.0) - (4_000.0 / 18_000.0)) < 1e-9


def test_ecv_microsim_artifact_monotonicity_and_bounds():
    path = ROOT / "artifacts/ecv_microsim.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text())
    by_id = {s["scenario_id"]: s for s in data["scenarios"]}
    assert set(by_id) == {
        "baseline",
        "bono_joven_0pt",
        "bono_joven_50pt",
        "renta_q1_q2",
        "tope_5pct",
        "escudo_30pct",
    }
    base = by_id["baseline"]
    # Every relief scenario must strictly reduce market-renter overburden vs baseline
    for sid in ("bono_joven_0pt", "bono_joven_50pt", "renta_q1_q2", "tope_5pct", "escudo_30pct"):
        assert by_id[sid]["overburden_40_mkt_pct"] < base["overburden_40_mkt_pct"]
        assert by_id[sid]["hh_lifted_out_40"] > 0
    # 50% landlord pass-through must lift fewer households at the same fiscal cost
    assert (
        by_id["bono_joven_50pt"]["fiscal_cost_meur"] == by_id["bono_joven_0pt"]["fiscal_cost_meur"]
    )
    assert (
        by_id["bono_joven_50pt"]["hh_lifted_out_40"] < by_id["bono_joven_0pt"]["hh_lifted_out_40"]
    )
    # Rent cap has 0 direct fiscal cost and spills substantially into Q3-Q5
    assert by_id["tope_5pct"]["fiscal_cost_meur"] == 0.0
    assert by_id["tope_5pct"]["relief_to_q1_q2_pct"] < 60.0
    # Progressive Q1-Q2 shield delivers 100% of relief to Q1-Q2
    assert by_id["escudo_30pct"]["relief_to_q1_q2_pct"] == 100.0
