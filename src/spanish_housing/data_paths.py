"""Central data paths. All pipeline artefacts live under data/ (git-ignored)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
MANIFEST = DATA / "input_manifest.json"
MARTS_DB = PROCESSED / "marts.duckdb"

for _d in (RAW, PROCESSED):
    _d.mkdir(parents=True, exist_ok=True)
