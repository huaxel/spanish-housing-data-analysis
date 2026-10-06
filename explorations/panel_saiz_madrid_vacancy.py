"""EXPLORATORY: the last terrain reopen path — vacancy for steep villages.

`panel_saiz_municipal.md` §Madrid leg concluded the design-B reopen
condition ("a second province, price levels") cannot be met: priced
municipios span only 0.00-0.25 constraint while steep villages (0.9+)
have no price series. This script tests the one remaining variant:
**vacancy by electricity consumption (59531)**, which covers 3,139
named municipios and might reach the villages prices miss.

Findings (written to artifacts/madrid_vacancy_terrain.json):

1. The steepest Madrid villages (Hiruela 0.984, Puebla de la Sierra
   0.982, Atazar 0.960, Patones 0.898, Acebeda 0.892, Somosierra 0.888,
   Horcajuelo 0.852) are all rolled into "28999 Resto de Madrid" — NOT
   individually in the vacancy table. Only Cercedilla (0.826, ~7k pop)
   is named. The selection problem is structural: the terrain-relevant
   tail aggregates away everywhere, not just in prices.
2. On the 135 named Madrid municipios with both terrain (0.00-0.826)
   and vacancy (2.7-38.5%): constraint→vacancy is positive (Pearson
   0.375, Spearman 0.557). But the highest-vacancy named ones are rural
   south-east periphery (Carabaña 39%, Valdelaguna 33%, Orusco 33%),
   not mountains — the same centrality gradient that explained the
   negative price-levels association, wearing a different proxy. It
   adds no identification: terrain correlates with everything, again.

Verdict: the reopen condition stands unmet, now tested on a second
outcome. Design B stays unbuilt.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402
from spanish_housing.muni_names import muni_key  # noqa: E402

terrain = json.loads((ROOT / "explorations" / "saiz_municipal_mad.json").read_text())
BY_KEY = {muni_key(t["municipio"]): t for t in terrain}

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)
vac_rows = con.execute(
    """
    SELECT codigo,
      SUM(CASE WHEN medida='Viviendas totales' THEN valor END) tot,
      SUM(CASE WHEN medida='Viviendas vacías' THEN valor END) vac,
      MAX(municipio) muni
    FROM censo2021_intensidad WHERE provincia_cod='28' GROUP BY codigo
    """
).fetchall()

STEEP = [
    "Hiruela, La",
    "Puebla de la Sierra",
    "Atazar, El",
    "Patones",
    "Acebeda, La",
    "Somosierra",
    "Horcajuelo de la Sierra",
]
steep_status = []
for name in STEEP:
    t = BY_KEY[muni_key(name)]
    in_vac = any(muni_key(m) == muni_key(name) for _, _, _, m in vac_rows)
    steep_status.append(
        {
            "municipio": name,
            "constraint": round(t["undevelopable_share"], 4),
            "in_vacancy_table": in_vac,
        }
    )

xs, ys = [], []
for _code, tot, vn, m in vac_rows:
    k = muni_key(m)
    if k in BY_KEY and tot:
        xs.append(BY_KEY[k]["undevelopable_share"])
        ys.append(vn / tot * 100)


def _rank(v: list[float]) -> list[float]:
    s = sorted(v)
    return [s.index(a) + 1 for a in v]


n = len(xs)
out = {
    "n_named_both": n,
    "constraint_min": round(min(xs), 4),
    "constraint_max": round(max(xs), 4),
    "vacancy_min": round(min(ys), 2),
    "vacancy_max": round(max(ys), 2),
    "pearson": round(statistics.correlation(xs, ys), 3),
    "spearman": round(statistics.correlation(_rank(xs), _rank(ys)), 3),
    "steep_villages_in_table": sum(1 for s in steep_status if s["in_vacancy_table"]),
    "steep_villages_total": len(steep_status),
    "steep_status": steep_status,
}
print(
    f"n={n} constraint {out['constraint_min']}-{out['constraint_max']} "
    f"vac {out['vacancy_min']}-{out['vacancy_max']} "
    f"pearson={out['pearson']} spearman={out['spearman']}"
)
print(f"steep villages in vacancy table: {out['steep_villages_in_table']}/{len(steep_status)}")

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "madrid_vacancy_terrain.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
