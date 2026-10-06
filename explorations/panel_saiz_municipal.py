"""EXPLORATORY: the same terrain diagnostics at municipal grain.

`panel_saiz.md` found the provincial version of these tests null and
concluded the honest upgrade is municipal, because a provincia averages
mountains with valleys — and that averaging may be what erases the
mechanism. Within Barcelona province the terrain measure spans 0.00
(Llagosta, Badia del Vallès) to 1.00 (Gisclareny): the variation the
provincial test threw away.

Data: `explorations/saiz_municipal_bcn.json` (311 municipios, built by
`scripts/probe_saiz_gis.py --municipal 08`) joined to `muni_bcn`
(DIBA + VTE, 2007-2024), which carries ACTUAL construction flows
(starts, completions) — better than the provincial run, which had only
stock changes.

  1. PREMISE: do constrained municipios build less? Now testable with
     real construction, at the grain Saiz's mechanism lives at.
  2. EXCLUSION: does constraint predict price growth directly?

Still descriptive/exploratory. Writes artifacts/panel_saiz_municipal.json
and explorations/panel_saiz_municipal_results.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402
from spanish_housing.muni_names import muni_key  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)

# Explicit alias, never a silent merge: Santa Maria de Corcó was officially
# renamed L'Esquirol in 2014 (same INE code 08254). DIBA still uses the old
# name, GISCO 2021 carries the new one. muni_key() cannot see this because
# the stem genuinely changed, so it must be declared here.
ALIASES = {"SANTA MARIA DE CORCO": "ESQUIROL"}

terrain = json.loads((ROOT / "explorations" / "saiz_municipal_bcn.json").read_text())
BY_KEY: dict[str, dict] = {}
for t in terrain:
    k = muni_key(t["municipio"])
    BY_KEY[ALIASES.get(k, k)] = t

rows = con.execute("""
    SELECT municipio, anyo, poblacion, starts, completions, sale_eur_m2, rent_month
    FROM muni_bcn ORDER BY municipio, anyo
""").fetchall()

by_mp: dict[str, list] = {}
for r in rows:
    by_mp.setdefault(r[0], []).append(r)

panel = []
unmatched = []
for mp, rs in by_mp.items():
    k = muni_key(mp)
    t = BY_KEY.get(ALIASES.get(k, k))
    if t is None:
        unmatched.append(mp)
        continue
    for prev, cur in zip(rs, rs[1:], strict=False):
        if cur[1] != prev[1] + 1:
            continue
        pop = cur[2]
        panel.append(
            {
                "municipio": mp,
                "anyo": cur[1],
                "constraint": t["undevelopable_share"],
                "lau_km2": t["lau_km2"],
                "density": pop / t["lau_km2"] if pop and t["lau_km2"] else None,
                "starts_pc": (cur[3] / pop * 1000) if cur[3] is not None and pop else None,
                "completions_pc": (cur[4] / pop * 1000) if cur[4] is not None and pop else None,
                "d_price": (
                    (cur[5] - prev[5]) / prev[5] * 100 if cur[5] is not None and prev[5] else None
                ),
                "d_rent": (
                    (cur[6] - prev[6]) / prev[6] * 100 if cur[6] is not None and prev[6] else None
                ),
            }
        )

print(f"municipios joined: {len(by_mp) - len(unmatched)}/{len(by_mp)}")
if unmatched:
    print("UNMATCHED:", unmatched)


def cross_model(dep: str, controls=()):
    """dep on constraint + controls + year FE, SEs clustered by municipio.

    No municipio FE: constraint is time-invariant and would be absorbed.
    """
    data = [
        o
        for o in panel
        if o[dep] is not None
        and o["constraint"] is not None
        and all(o[c] is not None for c in controls)
    ]
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


results: dict[str, object] = {"n_municipios": len(by_mp) - len(unmatched)}

specs = {
    "premise_starts": ("starts_pc", ()),
    "premise_completions": ("completions_pc", ()),
    "exclusion_price": ("d_price", ()),
    "premise_starts_density": ("starts_pc", ("density",)),
    "exclusion_price_density": ("d_price", ("density",)),
}
for label, (dep, ctrls) in specs.items():
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
    print(f"{label:<26} {per_01:+.3f} ({se_01:.3f})  t={per_01 / se_01:+.2f}  n={n} G={g}")

for key in ("starts_pc", "d_price"):
    v = [o[key] for o in panel if o[key] is not None]
    results[f"mean_{key}"] = round(sum(v) / len(v), 4)
    print(f"mean {key} = {results[f'mean_{key}']}")

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "panel_saiz_municipal.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
(ROOT / "explorations" / "panel_saiz_municipal_results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
