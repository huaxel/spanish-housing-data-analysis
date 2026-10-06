"""Bartik surge half: national net change by origin from pinned stocks.

surge[o,t] = stock[o,t] - stock[o,t-1] at national grain (all provinces).
Net change conflates inflows, outflows, deaths and naturalizations
(naturalized citizens leave the Extranjero count) — a proxy for the
inflow surge, not the surge itself. Descriptive input to a future
shift-share; NOT an estimate of anything (see identification.md).
Writes artifacts/bartik_surge.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)

rows = con.execute("""
    SELECT nacionalidad, anyo, SUM(personas) AS stock
    FROM padron_extranjeros_origen
    WHERE sexo = 'Ambos sexos' AND cpro != '00'
    GROUP BY nacionalidad, anyo
    ORDER BY nacionalidad, anyo
""").fetchall()

by_origin: dict[str, dict[int, int]] = {}
for nac, anyo, stock in rows:
    by_origin.setdefault(nac, {})[anyo] = stock

LEAVES = [n for n in by_origin if not n.isupper() and n != "TOTAL EXTRANJEROS"]

surge = {}
for nac in LEAVES:
    s = by_origin[nac]
    yrs = sorted(s)
    surge[nac] = {y: s[y] - s[y - 1] for y in yrs if y - 1 in s}

peaks = {nac: max(vals.items(), key=lambda kv: kv[1]) for nac, vals in surge.items() if vals}
top = sorted(peaks.items(), key=lambda kv: kv[1][1], reverse=True)[:12]

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "bartik_surge.json").write_text(
    json.dumps(
        {"surge": surge, "top_peak_years": [(n, y, v) for n, (y, v) in top]},
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("== top origin peak net-change years ==")
for nac, (y, v) in top:
    print(f"  {nac}: {y} +{v:,}")
