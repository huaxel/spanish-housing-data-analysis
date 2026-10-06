"""Panel: adjusted description of annual CCAA price changes.

Outcome: IPV general YoY % change. Regressors (all YoY): absorption
(new dwellings per additional inhabitant; missing when population shrinks),
mortgage-count growth, net household income growth, 20-34 share change (pp).
CCAA + year fixed effects (year FEs absorb the national rate cycle);
SEs clustered by CCAA (CR1V). Adjusted description only — income, credit
and population are jointly determined with prices; nothing here is a
structural or causal estimate. Writes artifacts/panel_adjusted.json.
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
    SELECT ccaa, anyo, viviendas_total, poblacion, ipv_general,
           hip_viv_num, renta_hogar_neta, share_20_34
    FROM mart_ccaa_anual WHERE ccaa != 'Nacional' ORDER BY ccaa, anyo
""").fetchall()

by_ccaa: dict[str, list] = {}
for r in ROWS:
    by_ccaa.setdefault(r[0], []).append(r)

obs = []
for ccaa, rows in by_ccaa.items():
    for prev, cur in zip(rows, rows[1:], strict=False):
        d_pop = cur[3] - prev[3]
        obs.append(
            {
                "ccaa": ccaa,
                "anyo": cur[1],
                "d_ipv": (cur[4] - prev[4]) / prev[4] * 100,
                "absor": (cur[2] - prev[2]) / d_pop if d_pop > 0 else None,
                "d_hip": (cur[5] - prev[5]) / prev[5] * 100,
                "d_renta": (cur[6] - prev[6]) / prev[6] * 100
                if prev[6] is not None and cur[6] is not None
                else None,
                "d_coh": (cur[7] - prev[7]) * 100
                if cur[7] is not None and prev[7] is not None
                else None,  # percentage points
            }
        )


def run(spec: list[str]) -> dict:
    rows = [o for o in obs if all(o[v] is not None for v in ["d_ipv", *spec])]
    ccaas = sorted({o["ccaa"] for o in rows})
    years = sorted({o["anyo"] for o in rows})[1:]
    means = {c: {v: 0.0 for v in ["d_ipv", *spec]} for c in ccaas}
    counts = {c: 0 for c in ccaas}
    for o in rows:
        counts[o["ccaa"]] += 1
        for v in ["d_ipv", *spec]:
            means[o["ccaa"]][v] += o[v]
    for c in ccaas:
        for v in means[c]:
            means[c][v] /= counts[c]
    x, y, cl = [], [], []
    for o in rows:
        m = means[o["ccaa"]]
        y.append(o["d_ipv"] - m["d_ipv"])
        x.append(
            [o[v] - m[v] for v in spec]
            + [1.0 if o["anyo"] == t else 0.0 for t in years]
        )
        cl.append(o["ccaa"])
    fit = ols.ols_cluster(x, y, cl)
    out = {
        "spec": spec,
        "n": fit["n"],
        "clusters": fit["clusters"],
        "years": [rows[0]["anyo"], rows[-1]["anyo"]],
        "r2_within": round(fit["r2"], 3),
        "coefs": {},
    }
    for i, v in enumerate(spec):
        b, s = fit["beta"][i], fit["se"][i]
        out["coefs"][v] = {
            "b": round(b, 3),
            "se": round(s, 3),
            "t": round(b / s, 2) if s > 0 else None,
            "ci95": [round(b - 1.96 * s, 3), round(b + 1.96 * s, 3)],
        }
    return out


results = {
    "s0_absorption_only": run(["absor"]),
    "s1_with_demand_controls": run(["absor", "d_hip", "d_renta", "d_coh"]),
    "undefined_absorption_dropped": sum(1 for o in obs if o["absor"] is None),
    "total_yoy_rows": len(obs),
}

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "panel_adjusted.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)

for name, r in results.items():
    if not isinstance(r, dict) or "coefs" not in r:
        continue
    print(f"== {name}: n={r['n']} G={r['clusters']} R2={r['r2_within']} ==")
    for v, c in r["coefs"].items():
        print(f"  {v}: b={c['b']} se={c['se']} t={c['t']} ci95={c['ci95']}")
n_drop = results["undefined_absorption_dropped"]
n_tot = results["total_yoy_rows"]
print(f"dropped undefined-absorption rows: {n_drop}/{n_tot}")
