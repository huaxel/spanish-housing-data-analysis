"""EXPLORATORY: does land constraint shape the migration -> price gradient?

Uses the terrain series from `scripts/probe_saiz_gis.py` (design B's input,
which did not exist before this session) together with the design-A panel.
Not a new research design — three diagnostics, in increasing order of
interpretive weight:

  1. PREMISE. Does undevelopable-land share predict *less* building?
     Saiz's logic requires constrained provinces to add less stock per
     capita. If this is null or wrong-signed, the whole instrument premise
     is in doubt and tests 2-3 are moot.
  2. EXCLUSION THREAT. Does terrain predict price changes directly,
     conditional on province + year FE? A large direct effect is exactly
     the amenity/tourism confound the review brief flags for design B,
     and it is what a valid instrument must NOT have.
  3. MECHANISM. Split the design-A IV by terrain constraint. Saiz logic
     predicts a larger tau where land is scarce. Uses the same estimator
     stack (2SLS, first-stage F, AR set) as `iv_migration.py`.

Everything here is descriptive/exploratory. Nothing is merged into
synthesis; conclusions need the independent read (docs/review_brief.md).
Writes artifacts/panel_saiz.json.
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
# Annual-flow instrument (repair 2026-10-07, same flaw as the IV): predicted
# year-t inflow from base-year levels x year-over-year national growth.
PRED = json.loads((ROOT / "artifacts" / "bartik_predicted.json").read_text())[
    "pred_annual_flow_per_1000_1998pop"
]

# --- terrain crosswalk: project provincia name -> probe name -------------
RENAME = {
    "Coruña, A": "A Coruña",
    "Balears, Illes": "Illes Balears",
    "Palmas, Las": "Las Palmas",
    "Rioja, La": "La Rioja",
}
probe = {
    r["provincia"]: r
    for r in json.loads((ROOT / "explorations" / "saiz_probe_results.json").read_text())
}
DIM = con.execute("SELECT cpro, provincia FROM dim_territorio").fetchall()

CONSTRAINT: dict[str, float] = {}
for cpro, name in DIM:
    if name == "Ceuta y Melilla":
        a, b = probe["Ceuta"], probe["Melilla"]
        w = a["land_km2"] + b["land_km2"]
        CONSTRAINT[cpro] = (
            a["undevelopable_share"] * a["land_km2"] + b["undevelopable_share"] * b["land_km2"]
        ) / w
    else:
        CONSTRAINT[cpro] = probe[RENAME.get(name, name)]["undevelopable_share"]

assert len(CONSTRAINT) == 51, len(CONSTRAINT)

# --- panel -----------------------------------------------------------------
by_unit: dict[str, list] = {}
for r in ROWS:
    by_unit.setdefault(r[0], []).append(r)

obs = []
for cpro, rows in by_unit.items():
    for prev, cur in zip(rows, rows[1:], strict=False):
        if cur[1] < 1999 or cur[1] > 2021 or cur[1] != prev[1] + 1:
            continue
        f_cur = STOCK.get((cpro, cur[1]), 0)
        f_prv = STOCK.get((cpro, prev[1]), 0)
        dv = None
        if cur[4] is not None and prev[4] is not None and cur[2]:
            dv = (cur[4] - prev[4]) / cur[2] * 1000
        obs.append(
            {
                "cpro": cpro,
                "anyo": cur[1],
                "constraint": CONSTRAINT[cpro],
                "d_eur": (
                    None
                    if cur[3] is None or prev[3] in (None, 0)
                    else (cur[3] - prev[3]) / prev[3] * 100
                ),
                "build": dv,
                "exposure": (f_cur - f_prv) / cur[2] * 1000 if cur[2] else None,
                "pred": PRED.get(cpro, {}).get(str(cur[1])),
            }
        )


def cross_model(rows, dep):
    """dep on [constraint] + year dummies, NO province FE.

    Constraint is time-invariant, so province FE absorbs it exactly. These
    two diagnostics are therefore cross-sectional comparisons (with year FE),
    and are labelled as associations, not within-province effects.
    """
    rows = [o for o in rows if o[dep] is not None and o["constraint"] is not None]
    years = sorted({o["anyo"] for o in rows})[1:]
    y, x, cl = [], [], []
    for o in rows:
        y.append(o[dep])
        # constant + year dummies (drop one year). Dropping the dummy WITHOUT
        # a constant would leave the excluded year with no intercept, letting
        # it dominate the fit and flip the sign of the constraint coefficient.
        x.append([o["constraint"], 1.0] + [1.0 if o["anyo"] == t else 0.0 for t in years])
        cl.append(o["cpro"])
    return y, x, cl


def build(subset, spec_extra=None):
    """Design-A panel restricted by `subset`, mirroring iv_migration.build."""
    rows = [
        o
        for o in obs
        if o["exposure"] is not None
        and o["pred"] is not None
        and o["d_eur"] is not None
        and subset(o)
    ]
    # Correct two-way within: year dummies are unit-demeaned too
    # (demeaned X + raw dummies biases the coefficients; fixed 2026-10-06).
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


def run_iv(y, d, w, z, cl, rows, label):
    o = ols.ols_cluster([[di] + wi for di, wi in zip(d, w, strict=True)], y, cl)
    t = ols.tsls(y, d, w, z, cl)
    fs = ols.first_stage_f(d, w, z, cl)
    ar = ols.ar_ci(y, d, w, z, cl, lo=-2.0, hi=5.0, steps=141)
    inside = [b for b, k in zip(ar["grid"], ar["keep"], strict=True) if k]
    return {
        "spec": label,
        "n": len(y),
        "clusters": len(set(cl)),
        "ols": {"tau": round(o["beta"][0], 3), "se": round(o["se"][0], 3)},
        "tsls": {"tau": round(t["tau"], 3), "se": round(t["se"], 3)},
        "first_stage_F": fs["F"],
        "ar_set": [min(inside), max(inside)] if inside else [],
    }


results: dict[str, object] = {}

# --- 1. premise: does constraint predict less building? -------------------
y, x, cl = cross_model(obs, "build")
fit = ols.ols_cluster(x, y, cl)
results["premise_build_on_constraint"] = {
    "coef_per_0p1": round(fit["beta"][0] * 0.1, 3),
    "se_per_0p1": round(fit["se"][0] * 0.1, 3),
    "n": fit["n"],
    "clusters": len(set(cl)),
    "note": (
        "cross-sectional, year FE, no province FE (constraint is time-invariant); "
        "dwellings added per 1000 pop; negative == Saiz premise holds"
    ),
}

# --- 2. exclusion threat: does constraint predict prices directly? --------
y, x, cl = cross_model(obs, "d_eur")
fit = ols.ols_cluster(x, y, cl)
results["exclusion_d_eur_on_constraint"] = {
    "coef_per_0p1": round(fit["beta"][0] * 0.1, 3),
    "se_per_0p1": round(fit["se"][0] * 0.1, 3),
    "n": fit["n"],
    "clusters": len(set(cl)),
    "note": (
        "cross-sectional, year FE; direct terrain -> price channel; large == "
        "design B exclusion at risk"
    ),
}

# --- 3. mechanism: split the design-A IV by terrain constraint ------------
med = sorted(CONSTRAINT.values())[len(CONSTRAINT) // 2]
results["median_constraint"] = round(med, 4)
for label, pred in (
    ("low_constraint", lambda o: o["constraint"] <= med),
    ("high_constraint", lambda o: o["constraint"] > med),
):
    y, d, w, z, cl, rows = build(pred)
    results[label] = run_iv(y, d, w, z, cl, rows, label)
    print(json.dumps(results[label], indent=1))

# interaction, descriptive only (OLS): exposure x constraint, province+year FE
rows = [
    o for o in obs if o["exposure"] is not None and o["d_eur"] is not None and o["pred"] is not None
]
# Correct two-way within (demeaned X + demeaned year dummies; fixed 2026-10-06).
# The interaction uses demeaned exposure x raw constraint: constraint is
# time-invariant, so its unit mean is itself and dm*e == (e - ebar)*c.
units = [o["cpro"] for o in rows]
periods = [o["anyo"] for o in rows]
inter = [o["exposure"] * o["constraint"] for o in rows]
series = {
    "d_eur": [o["d_eur"] for o in rows],
    "exposure": [o["exposure"] for o in rows],
    "inter": inter,
}
y, cols_dm, w, _kept = ols.two_way_within(
    units, periods, series["d_eur"], [series["exposure"], series["inter"]]
)
x = [[cols_dm[0][i], cols_dm[1][i]] + w[i] for i in range(len(rows))]
cl = list(units)
fit = ols.ols_cluster(x, y, cl)
wb = ols.wild_bootstrap_t(x, y, cl, j=1, reps=999)
results["interaction_ols"] = {
    "tau_exposure": round(fit["beta"][0], 3),
    "tau_exposure_se": round(fit["se"][0], 3),
    "interaction": round(fit["beta"][1], 3),
    "interaction_se": round(fit["se"][1], 3),
    "wild_p_interaction": wb["p"],
    "wild_t_interaction": wb["t_obs"],
    "n": fit["n"],
    "clusters": len(set(cl)),
    "note": "descriptive; exposure is endogenous here, so do not read as causal",
}
print(json.dumps(results["interaction_ols"], indent=1))

results["_meta"] = ols.model_meta(
    __file__, ["data/processed/marts.duckdb", "artifacts/bartik_predicted.json"]
)
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "panel_saiz.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
(ROOT / "explorations" / "panel_saiz_results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
