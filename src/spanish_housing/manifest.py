"""SHA-256 input manifest: record what was fetched, verify before building.

Mirrors the four-prices discipline on a smaller scale: every raw input is
pinned by bytes; build_marts refuses to run on unpinned or changed inputs
(re-run make fetch to re-pin — there is deliberately no --refresh-manifest
escape hatch).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .data_paths import MANIFEST


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load() -> dict:
    if not MANIFEST.exists():
        return {"snapshot_date": None, "sha256": {}, "sources": {}}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def record(relative_path: str, source: dict) -> None:
    """Pin one file: hash its current bytes and store its source metadata.

    sort_keys makes regeneration byte-identical regardless of the order
    fetch scripts run in; without it the committed manifest's byte order
    silently depends on fetch sequence.
    """
    import datetime

    man = load()
    man["snapshot_date"] = datetime.date.today().isoformat()
    full = Path(__file__).resolve().parents[2] / relative_path
    man.setdefault("sha256", {})[relative_path] = sha256(full)
    man.setdefault("sources", {})[relative_path] = source
    MANIFEST.write_text(
        json.dumps(man, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def snapshot_age_days(man: dict, today: date | None = None) -> int | None:
    """Age of the manifest snapshot in days; None if missing/unparseable."""
    snap = man.get("snapshot_date")
    if not snap:
        return None
    try:
        return ((today or date.today()) - date.fromisoformat(snap)).days
    except ValueError:
        return None


def check(expected: dict[str, str]) -> tuple[list[str], list[str]]:
    """Return (missing, mismatched) relative paths vs current bytes."""
    missing, mismatched = [], []
    root = Path(__file__).resolve().parents[2]
    for rel, digest in expected.items():
        p = root / rel
        if not p.exists():
            missing.append(rel)
        elif sha256(p) != digest:
            mismatched.append(rel)
    return missing, mismatched
