"""Discover INE Tempus3 operation/table IDs by keyword.

Usage: uv run python scripts/ine_discover.py "Cifras de Población"
Scans OPERACIONES_DISPONIBLES pages, then lists TABLAS_OPERACION for hits.
Used to pin successor tables (Cifras de Población post-2021, ECH hogares,
MIVAU valor tasado equivalent) without hardcoding guesses.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

BASE = "https://servicios.ine.es/wstempus/js/es"


def get(url: str):
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 (pinned host)
        return json.load(resp)


def main() -> None:
    keyword = sys.argv[1] if len(sys.argv) > 1 else "Población"
    kw = keyword.lower()
    page, hits = 1, []
    while True:
        ops = get(f"{BASE}/OPERACIONES_DISPONIBLES?page={page}")
        if not ops:
            break
        for op in ops:
            if kw in op.get("Nombre", "").lower():
                hits.append(op)
        page += 1
        if page > 40:
            break
    for op in hits:
        print(f"Id={op['Id']} Codigo={op['Codigo']} Nombre={op['Nombre']}")
        try:
            for t in get(f"{BASE}/TABLAS_OPERACION/{op['Codigo'] or op['Id']}"):
                print(
                    f"    tabla {t['Id']} | {t['Nombre']} | "
                    f"{t.get('Anyo_Periodo_ini')}–{t.get('Anyo_Periodo_fin')}"
                )
        except Exception as exc:  # noqa: BLE001
            print(f"    (tables unreadable: {exc})")


if __name__ == "__main__":
    main()
