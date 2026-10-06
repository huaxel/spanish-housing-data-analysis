"""EXPLORATORY: the Madrid leg of the terrain-diagnostics thread.

`panel_saiz_municipal.md` named two reopen conditions for design B: a
second province, and price *levels* rather than growth. This is that run.
It is honest about what it finds: it cannot deliver the replication it
was asked for.

The join works (28/28 municipios). The spread does not. `valor_municipal`
prices cover 28 of Madrid province's 179 municipios — the big, flat,
central basin ones — and their terrain constraint spans only 0.00-0.25
against the province's 0.00-0.98. The steep municipios (Atazar 0.96,
Puebla de la Sierra 0.98, La Hiruela 0.98) are villages with no price
series. So this test has almost no leverage on the question even before
estimating anything. It runs anyway, so the record shows what was tried
and why it does not settle the question.

Writes artifacts/panel_saiz_madrid.json +
explorations/panel_saiz_madrid_results.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402
from spanish_housing.muni_names import muni_key  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)

terrain = json.loads((ROOT / "explorations" / "saiz_municipal_mad.json").read_text())
BY_KEY = {muni_key(t["municipio"]): t for t in terrain}

rows = con.execute(
    "SELECT municipio, anyo, poblacion, eur_m2 FROM muni_madrid ORDER BY municipio, anyo"
).fetchall()

by_mp: dict[str, list] = {}
for r in rows:
    by_mp.setdefault(r[0], []).append(r)

panel = []
matched = 0
for mp, rs in by_mp.items():
    t = BY_KEY.get(muni_key(mp))
    if t is None:
        continue
    matched += 1
    for prev, cur in zip(rs, rs[1:], strict=False):
        if cur[1] != prev[1] + 1:
            continue
        if cur[3] and prev[3]:
            panel.append(
                {
                    "municipio": mp,
                    "anyo": cur[1],
                    "constraint": t["undevelopable_share"],
                    "density": cur[2] / t["lau_km2"] if cur[2] and t["lau_km2"] else None,
                    "d_price": (cur[3] - prev[3]) / prev[3] * 100,
                    "log_price": math.log(cur[3]) if cur[3] else None,
                }
            )

constraints = sorted({o["constraint"] for o in panel})
results: dict[str, object] = {
    "n_municipios": matched,
    "constraint_min": round(min(constraints), 4),
    "constraint_max": round(max(constraints), 4),
    "province_constraint_max": max(t["undevelopable_share"] for t in terrain),
    "note": (
        "28/28 join, but priced municipios span only 0.00-0.25 constraint "
        "against the province's 0.00-0.98: the steep municipios are villages "
        "without price series. Weak leverage by construction."
    ),
}
print(
    f"joined {matched}/{len(by_mp)}; constraint span {min(constraints):.3f}"
    f"-{max(constraints):.3f} (province max "
    f"{results['province_constraint_max']:.3f})"
)


def cross_model(dep: str, controls=()):
    """dep on constraint + controls + year FE, clustered by municipio."""
    data = [o for o in panel if o[dep] is not None and all(o[c] is not None for c in controls)]
    years = sorted({o["anyo"] for o in data})[1:]
    y, x, cl = [], [], []
    for o in data:
        y.append(o[dep])
        x.append(
            [o["constraint"], *[o[c] for c in controls], 1.0]
            + [1.0 if o["anyo"] == t else 0.0 for t in years]
        )
        cl.append(o["municipio"])
    return ols.ols_cluster(x, y, cl), len(data), len(set(cl))


for label, (dep, ctrls) in {
    "price_growth": ("d_price", ()),
    "log_price_levels": ("log_price", ()),
    "log_price_levels_density": ("log_price", ("density",)),
}.items():
    fit, n, g = cross_model(dep, ctrls)
    per_01 = fit["beta"][0] * 0.1
    se_01 = fit["se"][0] * 0.1
    results[label] = {
        "dep": dep,
        "controls": list(ctrls),
        "coef_per_0p1": round(per_01, 4),
        "se_per_0p1": round(se_01, 4),
        "t": round(per_01 / se_01, 2) if se_01 else None,
        "n": n,
        "clusters": g,
    }
    print(f"{label:<28} {per_01:+.4f} ({se_01:.4f})  t={per_01 / se_01:+.2f}  n={n} G={g}")

(ROOT / "artifacts").mkdir(exist_ok=True)
for out in (
    ROOT / "artifacts" / "panel_saiz_madrid.json",
    ROOT / "explorations" / "panel_saiz_madrid_results.json",
):
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
