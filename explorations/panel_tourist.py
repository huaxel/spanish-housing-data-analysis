"""Municipal tourist-intensity panel (Barcelona demarcation, DIBA).

y = sale/rent YoY % on change in tourist dwellings per 1,000 inhabitants,
with population-growth control; municipio + year FE; SEs clustered by
municipio. Adjusted description only — tourist licensing follows demand
(and regulation) jointly with prices; nothing here is causal.
Writes artifacts/panel_tourist.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)

ROWS = con.execute("""
    SELECT municipio, anyo, poblacion, sale_eur_m2, rent_month, tourist
    FROM muni_bcn ORDER BY municipio, anyo
""").fetchall()

by_muni: dict[str, list] = {}
for r in ROWS:
    by_muni.setdefault(r[0], []).append(r)

obs = []
for muni, rows in by_muni.items():
    for prev, cur in zip(rows, rows[1:], strict=False):
        if cur[1] != prev[1] + 1 or not cur[2] or not prev[2]:
            continue
        t_cur = cur[5] / cur[2] * 1000 if cur[5] is not None else None
        t_prv = prev[5] / prev[2] * 1000 if prev[5] is not None else None
        obs.append(
            {
                "muni": muni,
                "anyo": cur[1],
                "d_sale": (cur[3] - prev[3]) / prev[3] * 100 if cur[3] and prev[3] else None,
                "d_rent": (cur[4] - prev[4]) / prev[4] * 100 if cur[4] and prev[4] else None,
                "d_tour": t_cur - t_prv if t_cur is not None and t_prv is not None else None,
                "d_pop": (cur[2] - prev[2]) / prev[2] * 100,
            }
        )


def run(ykey: str, spec: list[str]) -> dict:
    rows = [o for o in obs if o[ykey] is not None and all(o[v] is not None for v in spec)]
    # Correct two-way within: year dummies are unit-demeaned too
    # (demeaned X + raw dummies biases the coefficients; fixed 2026-10-06).
    units = [o["muni"] for o in rows]
    periods = [o["anyo"] for o in rows]
    series = {v: [o[v] for o in rows] for v in [ykey, *spec]}
    y, cols_dm, w, _kept = ols.two_way_within(
        units, periods, series[ykey], [series[v] for v in spec]
    )
    x = [[c[i] for c in cols_dm] + w[i] for i in range(len(rows))]
    cl = list(units)
    fit = ols.ols_cluster(x, y, cl)
    out = {
        "y": ykey,
        "spec": spec,
        "n": fit["n"],
        "clusters": fit["clusters"],
        "r2_within": round(fit["r2"], 3),
        "coefs": {},
    }
    for i, v in enumerate(spec):
        b, s = fit["beta"][i], fit["se"][i]
        out["coefs"][v] = {
            "b": round(b, 4),
            "se": round(s, 4),
            "t": round(b / s, 2) if s > 0 else None,
            "ci95": [round(b - 1.96 * s, 4), round(b + 1.96 * s, 4)],
        }
    out["wild_bootstrap"] = {
        v: ols.wild_bootstrap_t(x, y, cl, j=i, reps=1999)
        for i, v in enumerate(spec)
        if v == "d_tour"
    }
    return out


results = {
    "sale_tour_only": run("d_sale", ["d_tour"]),
    "sale_with_pop": run("d_sale", ["d_tour", "d_pop"]),
    "rent_tour_only": run("d_rent", ["d_tour"]),
    "rent_with_pop": run("d_rent", ["d_tour", "d_pop"]),
}

results["_meta"] = ols.model_meta(__file__, ["data/processed/marts.duckdb"])
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "panel_tourist.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
for name, r in results.items():
    if name.startswith("_"):
        continue
    c = r["coefs"]["d_tour"]
    wb = r["wild_bootstrap"]["d_tour"]
    print(f"== {name}: n={r['n']} G={r['clusters']} R2={r['r2_within']} ==")
    print(f"   d_tour: b={c['b']} se={c['se']} t={c['t']} ci95={c['ci95']} wild-p={wb['p']}")
