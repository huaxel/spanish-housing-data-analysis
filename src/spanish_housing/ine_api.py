"""Minimal client for the INE Tempus3 JSON API (servicios.ine.es/wstempus).

Docs: https://www.ine.es/dyngs/DAB/index.htm
Pattern: GET {BASE}/js/es/DATOS_TABLA/{table_id}?nult=N  (or ?date=aaaammdd:aaaammdd)
"""

from __future__ import annotations

import json
import time
import unicodedata
import urllib.request

BASE = "https://servicios.ine.es/wstempus/js/es"


def get_table(
    table_id: int | str, *, nult: int | None = None, date: str | None = None, retries: int = 3
) -> list[dict] | dict:
    """Fetch series of a Tempus3 table. date='aaaammdd:aaaammdd' bounds volume."""
    url = f"{BASE}/DATOS_TABLA/{table_id}"
    if nult is not None:
        url += f"?nult={nult}"
    elif date is not None:
        url += f"?date={date}"
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (pinned host)
                return json.load(resp)
        except Exception as exc:  # noqa: BLE001 — retry then raise
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"INE fetch failed for table {table_id}: {last}") from last


def norm_name(s: str) -> str:
    """Upper-case, strip accents/whitespace — for territory/type matching."""
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def split_nombre(nombre: str) -> list[str]:
    """Split a Tempus3 Nombre like 'Albacete. Total. Total habitantes. Personas.'."""
    return [p.strip() for p in nombre.split(".") if p.strip()]
