"""Tests for Spain's Housing Claim Ledger builder and outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_claim_ledger_artifact_integrity():
    path = ROOT / "artifacts/claim_ledger.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text())
    claims = data["claims"]
    bridges = data["bridges"]
    assert len(claims) == 7
    assert len(bridges) >= 10
    claim_ids = {c["claim_id"] for c in claims}
    assert len(claim_ids) == 7
    for c in claims:
        assert c["public_claim"]
        assert c["verdict"]
        assert c["pinned_finding"]
        assert c["deep_dive_path"].startswith("/")
    for b in bridges:
        assert b["claim_id"] in claim_ids
        assert isinstance(b["value_num"], (int, float))
        assert b["unit"]
        assert b["why_it_differs"]
