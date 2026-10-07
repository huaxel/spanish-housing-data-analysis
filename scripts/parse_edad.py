"""Parse age detail from the pinned ECP CCAA raw JSON (no download).

Reads data/raw/ecp_pob_ccaa.json (pinned by fetch_ecp.py) and aggregates
single years of age into bands at 1-January (FK_Periodo 19), Total sexo.
Bands: 0-19, 20-34, 35-49, 50-64, 65+. Writes
data/raw/parquet/ecp_edad_ccaa.parquet (+ manifest record, same source).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

BANDS = [(0, 19, "0-19"), (20, 34, "20-34"), (35, 49, "35-49"), (50, 64, "50-64"), (65, 200, "65+")]
AGE_RE = re.compile(r"^(\d+)\s+años?$")


def band(age_label: str) -> str | None:
    if age_label == "Todas las edades":
        return "total"
    if age_label in ("100 y más años", "85 y más años"):
        return "65+"
    m = AGE_RE.match(age_label)
    if not m:
        return None
    age = int(m.group(1))
    for lo, hi, name in BANDS:
        if lo <= age <= hi:
            return name
    return None


def main() -> None:
    payload = json.loads((RAW / "ecp_pob_ccaa.json").read_text(encoding="utf-8"))
    buckets: dict[tuple[str, int, str], int] = {}
    skipped: list[str] = []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        if len(parts) != 5:
            skipped.append(s["Nombre"])
            continue
        if parts[0] == "Total Nacional":
            if parts[2] != "Total":
                skipped.append(s["Nombre"])
                continue
            terr = parts[0]
        elif parts[0] == "Total":
            terr = parts[2]
        else:
            skipped.append(s["Nombre"])
            continue
        if parts[1] in ("100 años", "100 y más años"):
            # Centenarians are inside '85 y más años' (verified: 85+ equals
            # sum(85-99 singles) + 100+); keep the grouped series only.
            skipped.append(s["Nombre"] + " [centenarians, in 85+]")
            continue
        m85 = AGE_RE.match(parts[1])
        if m85 and int(m85.group(1)) >= 85:
            # Single years 85-99 are inside '85 y más años' (verified:
            # sum(85-99) + 100+ == 85+); keep the grouped series only.
            skipped.append(s["Nombre"] + " [85-99, in 85+]")
            continue
        b = band(parts[1])
        if b is None:
            skipped.append(s["Nombre"])
            continue
        for x in s["Data"]:
            if x["FK_Periodo"] != 19:
                continue
            key = (terr, x["Anyo"], b)
            buckets[key] = buckets.get(key, 0) + int(x["Valor"])
    # Consistency: bands must sum to the published total (Total sexo rows).
    # Tolerance 2e-4 relative: early ECP back-series years carry integer-
    # rounding noise (observed <= 1.1e-4); true overlaps were ~2.5e-2.
    totals = {(t, a): v for (t, a, b), v in buckets.items() if b == "total"}
    worst = 0.0
    bad = []
    for (t, a), v in totals.items():
        s = sum(w for (tt, aa, b), w in buckets.items() if tt == t and aa == a and b != "total")
        rel = abs(s - v) / v
        worst = max(worst, rel)
        if rel > 2e-4:
            bad.append((t, a, s - v))
    print(f"age-band/total max relative deviation: {worst:.2e}")
    if bad:
        raise SystemExit(f"age bands do not sum to total: {bad[:5]}")
    rows = [
        {"territorio": t, "anyo": a, "banda": b, "poblacion": v}
        for (t, a, b), v in sorted(buckets.items())
    ]
    out = RAW / "parquet" / "ecp_edad_ccaa.parquet"
    pq.write_table(pa.Table.from_pylist(rows), out)
    manifest.record(
        "data/raw/parquet/ecp_edad_ccaa.parquet",
        {
            "api": "wstempus/DATOS_TABLA/56940",
            "operation": "ECP",
            "accessed": date.today().isoformat(),
            "note": "1-Jan age bands parsed from pinned ecp_pob_ccaa.json",
        },
    )
    n_terr = len({t for (t, _a, _b) in buckets})
    print(f"edad: {len(rows)} rows, {n_terr} territorios; skipped {len(skipped)} series")


if __name__ == "__main__":
    main()
