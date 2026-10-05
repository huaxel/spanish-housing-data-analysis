"""Exploration 03: the young-adult squeeze (20-34 cohort vs households vs prices).

Reads mart_ccaa_anual. Descriptive only. Writes artifacts/exploration_03.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)


def rows(sql: str, params: list | None = None) -> list[dict]:
    cur = con.execute(sql, params or [])
    return [dict(zip([d[0] for d in cur.description], r, strict=True)) for r in cur.fetchall()]


young = rows(
    """WITH a AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2007),
            b AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2019),
            c AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2025)
     SELECT c.ccaa, a.pob_20_34 AS y2007, b.pob_20_34 AS y2019, c.pob_20_34 AS y2025,
            ROUND((b.pob_20_34 - a.pob_20_34) / a.pob_20_34 * 100, 1) AS pct_07_19,
            ROUND((c.pob_20_34 - b.pob_20_34) / b.pob_20_34 * 100, 1) AS pct_19_25,
            ROUND(c.share_20_34 * 100, 2) AS share25,
            c.afford_90m2_years AS afford24_src,
            (SELECT afford_90m2_years FROM mart_ccaa_anual
             WHERE ccaa = c.ccaa AND anyo = 2024) AS afford24
     FROM a JOIN b ON a.ccaa = b.ccaa JOIN c ON b.ccaa = c.ccaa
     WHERE c.ccaa != 'Nacional' ORDER BY pct_19_25 DESC"""
)

hh = rows(
    """WITH a AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2021),
            b AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2025)
     SELECT b.ccaa, b.hogares - a.hogares AS d_hog,
            b.pob_20_34 - a.pob_20_34 AS d_young
     FROM a JOIN b ON a.ccaa = b.ccaa
     WHERE b.ccaa != 'Nacional' AND a.hogares IS NOT NULL
     ORDER BY d_hog DESC"""
)

out = {"young_trajectory": young, "households_vs_young_2021_2025": hh}
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "exploration_03.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)

print("== 20-34 trajectory by CCAA (07-19 collapse, 19-25 refill) ==")
for r in young:
    print(
        f"{r['ccaa']}: {r['y2007']} -> {r['y2019']} ({r['pct_07_19']:+.1f}%) "
        f"-> {r['y2025']} ({r['pct_19_25']:+.1f}%) share25={r['share25']}% "
        f"afford24={r['afford24']}"
    )
print("\n== 2021-2025: new households vs young-adult change ==")
for r in hh:
    print(f"{r['ccaa']}: d_hog={r['d_hog']} d_young={r['d_young']:+}")
