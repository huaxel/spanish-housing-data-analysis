"""Tests for Spain's Housing Claim Ledger builder and outputs."""

from __future__ import annotations

import json
import re
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
    assert len(claims) == 8
    assert len(bridges) >= 10
    claim_ids = {c["claim_id"] for c in claims}
    assert len(claim_ids) == 8
    for c in claims:
        assert c["public_claim"]
        assert c["verdict"]
        assert c["pinned_finding"]
        assert c["deep_dive_path"].startswith("/")
    exempt = data.get("bridge_exempt", {})
    assert set(exempt) <= claim_ids
    for claim_id, reason in exempt.items():
        assert reason and len(reason) > 20, f"exemption needs a reason: {claim_id}"
    bridged = {b["claim_id"] for b in bridges}
    assert bridged | set(exempt) == claim_ids, (
        f"claims with neither bridge nor exemption: {claim_ids - bridged - set(exempt)}"
    )
    for b in bridges:
        assert b["claim_id"] in claim_ids
        assert isinstance(b["value_num"], (int, float))
        assert b["unit"]
        assert b["why_it_differs"]


NUMBERS_ES = {5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve", 10: "diez"}


def test_the_public_page_states_the_number_of_claims_it_renders():
    """The page said "siete" while the ledger carried eight claims."""
    path = ROOT / "artifacts/claim_ledger.json"
    if not path.is_file():
        return
    claims = json.loads(path.read_text())["claims"]
    page = (ROOT / "evidence/pages/afirmaciones.md").read_text()
    word = NUMBERS_ES[len(claims)]
    assert f"las {word} afirmaciones" in page, (
        f"the ledger has {len(claims)} claims ({word}) but the page does not say so"
    )
    assert f"de {word} afirmaciones" in page, "the evidence panel definition is stale"
    rows = int(re.search(r"<DataTable[^>]*rows=(\d+)", page).group(1))
    assert rows >= len(claims), f"DataTable shows {rows} rows for {len(claims)} claims"
