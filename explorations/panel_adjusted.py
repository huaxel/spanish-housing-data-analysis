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

_MIG_P = {}
for _pr, _a, _f in con.execute(
    "SELECT provincia, anyo, flujo FROM migra_anual WHERE nacionalidad='Extranjero'"
).fetchall():
    _MIG_P[(_pr, _a)] = _f
_P2C = {r[0]: r[1] for r in con.execute("SELECT provincia, ccaa FROM dim_territorio").fetchall()}
_P2C["Ceuta"] = "Ceuta y Melilla"
_P2C["Melilla"] = "Ceuta y Melilla"
MIG = {}
for (_pr, _a), _f in _MIG_P.items():
    _c = _P2C.get(_pr)
    if _c:
        MIG[(_c, _a)] = MIG.get((_c, _a), 0) + _f

by_ccaa: dict[str, list] = {}
for r in ROWS:
    by_ccaa.setdefault(r[0], []).append(r)

obs = []
for ccaa, rows in by_ccaa.items():
    for prev, cur in zip(rows, rows[1:], strict=False):
        d_pop = cur[3] - prev[3] if cur[3] is not None and prev[3] is not None else None
        obs.append(
            {
                "ccaa": ccaa,
                "anyo": cur[1],
                "d_ipv": (cur[4] - prev[4]) / prev[4] * 100
                if cur[4] is not None and prev[4]
                else None,
                "absor": (cur[2] - prev[2]) / d_pop
                if d_pop is not None and d_pop > 0 and cur[2] is not None and prev[2] is not None
                else None,
                "d_hip": (cur[5] - prev[5]) / prev[5] * 100
                if cur[5] is not None and prev[5]
                else None,
                "d_renta": (cur[6] - prev[6]) / prev[6] * 100
                if prev[6] is not None and cur[6] is not None
                else None,
                "d_coh": (cur[7] - prev[7]) * 100
                if cur[7] is not None and prev[7] is not None
                else None,  # percentage points
                "d_inmig": (
                    (MIG[(cur[0], cur[1])] - MIG[(prev[0], prev[1])])
                    / MIG[(prev[0], prev[1])]
                    * 100
                    if (cur[0], cur[1]) in MIG and (prev[0], prev[1]) in MIG
                    else None
                ),
            }
        )


LAG_VARS = ["absor", "d_hip", "d_renta"]


def attach_lags() -> None:
    """Attach prior-year values as L_<var> (None at each CCAA's first year)."""
    last: dict[str, dict] = {}
    for o in obs:
        p = last.get(o["ccaa"])
        for v in LAG_VARS:
            o["L_" + v] = p[v] if p is not None and p[v] is not None else None
        last[o["ccaa"]] = o


attach_lags()


def build_design(spec: list[str]) -> tuple[list, list, list, list]:
    rows = [o for o in obs if all(o[v] is not None for v in ["d_ipv", *spec])]
    # Correct two-way within: year dummies are unit-demeaned too
    # (demeaned X + raw dummies biases the coefficients; fixed 2026-10-06).
    units = [o["ccaa"] for o in rows]
    periods = [o["anyo"] for o in rows]
    series = {v: [o[v] for o in rows] for v in ["d_ipv", *spec]}
    y, cols_dm, w, _kept = ols.two_way_within(
        units, periods, series["d_ipv"], [series[v] for v in spec]
    )
    x = [[c[i] for c in cols_dm] + w[i] for i in range(len(rows))]
    return x, y, list(units), rows


def run(spec: list[str]) -> dict:
    x, y, cl, rows = build_design(spec)
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


BOOT_REPS = 2999  # ~30s per coefficient; min attainable p ~ 1/3000


def add_bootstrap(result: dict, spec: list[str]) -> None:
    x, y, cl, _ = build_design(spec)
    result["wild_bootstrap"] = {
        v: ols.wild_bootstrap_t(x, y, cl, j=i, reps=BOOT_REPS) for i, v in enumerate(spec)
    }


results = {
    "s0_absorption_only": run(["absor"]),
    "s1_with_demand_controls": run(["absor", "d_hip", "d_renta", "d_coh"]),
    "s2_with_lags": run(["absor", "d_hip", "d_renta", "d_coh", "L_absor", "L_d_hip", "L_d_renta"]),
    "s3_with_migration": run(["absor", "d_hip", "d_renta", "d_coh", "d_inmig"]),
    "undefined_absorption_dropped": sum(1 for o in obs if o["absor"] is None),
    "total_yoy_rows": len(obs),
}
add_bootstrap(results["s0_absorption_only"], ["absor"])
add_bootstrap(results["s1_with_demand_controls"], ["absor", "d_hip", "d_renta", "d_coh"])
add_bootstrap(
    results["s2_with_lags"],
    ["absor", "d_hip", "d_renta", "d_coh", "L_absor", "L_d_hip", "L_d_renta"],
)
add_bootstrap(
    results["s3_with_migration"],
    ["absor", "d_hip", "d_renta", "d_coh", "d_inmig"],
)

results["_meta"] = ols.model_meta(__file__, ["data/processed/marts.duckdb"])
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "panel_adjusted.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)

for name, r in results.items():
    if not isinstance(r, dict) or "coefs" not in r:
        continue
    print(f"== {name}: n={r['n']} G={r['clusters']} R2={r['r2_within']} ==")
    for v, c in r["coefs"].items():
        wb = r["wild_bootstrap"][v]
        print(f"  {v}: b={c['b']} se={c['se']} t={c['t']} ci95={c['ci95']}")
        print(f"    wild-t: t={wb['t_obs']} p={wb['p']} (reps={wb['reps']})")
n_drop = results["undefined_absorption_dropped"]
n_tot = results["total_yoy_rows"]
print(f"dropped undefined-absorption rows: {n_drop}/{n_tot}")
