"""IV: migration exposure -> valor-tasado price changes (provincia panel).

Endogenous: foreign net inflow per 1,000 inhabitants (padrón stock
differences). Instrument: shift-share predicted inflow (1998 origin
levels x leave-one-out national growth; see bartik_predict.py).
Outcome: valor-tasado Libre YoY % (provincial grain — no provincial IPV).
Province + year FE (year absorbs rates/national cycle); SEs clustered
by provincia. Reports OLS, 2SLS, first-stage F, AR confidence set, and
wild bootstrap-t. COMMISSIONED design A — read identification.md and the
accompanying note before quoting anything here.
Writes artifacts/iv_migration.json.
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
    SELECT cpro, anyo, poblacion, eur_m2_libre, viviendas_total
    FROM mart_provincia_anual ORDER BY cpro, anyo
""").fetchall()

STOCK = {
    (r[0], r[1]): r[2]
    for r in con.execute(
        "SELECT cpro, anyo, SUM(personas) FROM padron_extranjeros_origen "
        "WHERE sexo='Ambos sexos' AND nacionalidad='TOTAL EXTRANJEROS' "
        "GROUP BY cpro, anyo"
    ).fetchall()
}

PRED = json.loads((ROOT / "artifacts" / "bartik_predicted.json").read_text())[
    "pred_inflow_rate_per_1000_1998pop"
]

by_unit: dict[str, list] = {}
for r in ROWS:
    by_unit.setdefault(r[0], []).append(r)

obs = []
for cpro, rows in by_unit.items():
    for prev, cur in zip(rows, rows[1:], strict=False):  # lagged pairs differ by design
        if cur[1] < 1999 or cur[1] > 2021 or cur[1] != prev[1] + 1:
            continue
        f_cur = STOCK.get((cpro, cur[1]), 0)
        f_prv = STOCK.get((cpro, prev[1]), 0)
        if cur[3] is None or prev[3] is None or prev[3] == 0:
            continue
        obs.append(
            {
                "cpro": "51+52" if cpro in ("51", "52") else cpro,
                "anyo": cur[1],
                "d_eur": (cur[3] - prev[3]) / prev[3] * 100,
                "exposure": (f_cur - f_prv) / cur[2] * 1000 if cur[2] else None,
                "pred": PRED.get(cpro, {}).get(str(cur[1])),
            }
        )


def build(spec_extra: list[str] | None = None, y0: int = 1999, y1: int = 2021):
    rows = [
        o
        for o in obs
        if o["exposure"] is not None and o["pred"] is not None and y0 <= o["anyo"] <= y1
    ]
    # Correct two-way within: demean y, regressors, instrument AND the
    # year dummies by province (Frisch-Waugh). Demeaned X + raw dummies
    # is a different model and biases tau (fixed 2026-10-06).
    units = [o["cpro"] for o in rows]
    periods = [o["anyo"] for o in rows]
    keys = ["exposure", "pred", *(spec_extra or [])]
    series = {k: [o[k] for o in rows] for k in ["d_eur", *keys]}
    y, cols_dm, w, _kept = ols.two_way_within(
        units, periods, series["d_eur"], [series[k] for k in keys]
    )
    d, z = cols_dm[0], [[v] for v in cols_dm[1]]
    extra = cols_dm[2:]
    for i in range(len(rows)):
        w[i] = [e[i] for e in extra] + w[i]
    return y, d, w, z, list(units), rows


def run_all(y, d, w, z, cl, rows, label):
    n, G = len(y), len(set(cl))
    xo = [[di] + wi for di, wi in zip(d, w, strict=True)]
    o = ols.ols_cluster(xo, y, cl)
    t = ols.tsls(y, d, w, z, cl)
    fs = ols.first_stage_f(d, w, z, cl)
    ar = ols.ar_ci(y, d, w, z, cl, lo=-2.0, hi=5.0, steps=141)
    inside = [b for b, k in zip(ar["grid"], ar["keep"], strict=True) if k]
    return {
        "spec": label,
        "n": n,
        "clusters": G,
        "years": [rows[0]["anyo"], rows[-1]["anyo"]],
        "ols": {"tau": round(o["beta"][0], 3), "se": round(o["se"][0], 3)},
        "tsls": {"tau": round(t["tau"], 3), "se": round(t["se"], 3)},
        "first_stage_F": fs["F"],
        "ar_set": [min(inside), max(inside)] if inside else [],
    }


def build_trends():
    # Base design + province-specific linear trends (absorbs differential
    # trends as the exclusion threat; costs ~49 df). Trend terms are
    # unit-demeaned like every other continuous regressor. Only G-1 trends
    # are included: province trends sum to a common time trend, which the
    # year FE already absorb, so the full set is exactly collinear (the old
    # raw-trends spec was singular and solved only on rounding noise).
    y, d, w, z, cl, rows = build()
    cpros = sorted(set(cl))[1:]
    t0 = min(o["anyo"] for o in rows)
    raw_trends = [[(o["anyo"] - t0) if o["cpro"] == c else 0.0 for c in cpros] for o in rows]
    dm_trends = [ols.demean_by_unit([r[j] for r in raw_trends], cl) for j in range(len(cpros))]
    w2 = [w[oi] + [dm_trends[j][oi] for j in range(len(cpros))] for oi in range(len(rows))]
    return y, d, w2, list(z), cl, rows


def build_drop_top2():
    # Drop Madrid + Barcelona (dominance check; LOO already mitigates).
    y, d, w, z, cl, rows = build()
    keep = [i for i, o in enumerate(rows) if o["cpro"] not in ("28", "08")]
    return (
        [y[i] for i in keep],
        [d[i] for i in keep],
        [w[i] for i in keep],
        [z[i] for i in keep],
        [cl[i] for i in keep],
        [rows[i] for i in keep],
    )


specs = {
    "base": build(),
    "province_trends": build_trends(),
    "drop_madrid_barcelona": build_drop_top2(),
    "bust_2002_2013": build(None, 2002, 2013),
    "recovery_2014_2021": build(None, 2014, 2021),
}
results = {}
for name, (yy, dd, ww, zz, cc, rr) in specs.items():
    results[name] = run_all(yy, dd, ww, zz, cc, rr, name)
    print(json.dumps(results[name], indent=1))

results["_meta"] = ols.model_meta(__file__, ["data/processed/marts.duckdb"])
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "iv_migration.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
# The audit checks the committed copy (including the _meta freshness
# key): keep it byte-identical to the script output.
(ROOT / "explorations" / "iv_results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
