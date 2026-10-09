"""Wild-bootstrap inversion grid for the tourism-panel d_tour coefficient.

Reconstructs the four panel_tourist model designs from marts.duckdb WITHOUT
modifying the original estimator, verifies the reconstruction against the
fresh panel_tourist.json artifact, then inverts the wild-cluster bootstrap-t
test over a PRESPECIFIED grid of candidate magnitudes (H0: coefficient = c).
Common random numbers make p-values comparable across candidates; candidate
c = 0 with the same seed/reps reproduces the legacy zero-null wild-bootstrap
routine exactly; candidate c = 0 therefore reproduces the published zero-null
wild p in panel_tourist.json (1999 reps, same seed).

The artifact stores TESTED POINTS ONLY: per-candidate p and an acceptance
mask at the nominal 95% level, plus boundary warnings. It is not a
continuous confidence interval, causal range or equivalence proof.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import (
    ols,  # noqa: E402
    wild_grid,  # noqa: E402
)
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

ESTIMATOR = ROOT / "explorations" / "panel_tourist.py"
ARTIFACT = ROOT / "artifacts" / "tourist_inversion.json"
SOURCE = ROOT / "artifacts" / "panel_tourist.json"
DATABASE = PROCESSED / "marts.duckdb"
MODELS = {
    "sale_tour_only": ("Venta", "Solo turismo", "d_sale", ["d_tour"]),
    "sale_with_pop": ("Venta", "Turismo + población", "d_sale", ["d_tour", "d_pop"]),
    "rent_tour_only": ("Alquiler", "Solo turismo", "d_rent", ["d_tour"]),
    "rent_with_pop": ("Alquiler", "Turismo + población", "d_rent", ["d_tour", "d_pop"]),
}
# Prespecified BEFORE any grid p-value is computed: symmetric magnitudes in
# percentage points per unit of exposure, 0.1 pp steps, 41 candidates.
GRID = [round(-2.0 + 0.1 * s, 4) for s in range(41)]
REPS = 1999
SEED = 20261006
ALPHA = 0.05


def design(ykey: str, spec: list[str]):
    """Rebuild the panel_tourist design exactly (unit+year FE, clustered)."""
    con = duckdb.connect(str(DATABASE), read_only=True)
    rows = con.execute(
        "SELECT municipio, anyo, poblacion, sale_eur_m2, rent_month, tourist "
        "FROM muni_bcn ORDER BY municipio, anyo"
    ).fetchall()
    con.close()
    by_muni: dict[str, list] = {}
    for r in rows:
        by_muni.setdefault(r[0], []).append(r)
    obs = []
    for muni, mrows in by_muni.items():
        for prev, cur in zip(mrows, mrows[1:], strict=False):
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
    keep = [o for o in obs if o[ykey] is not None and all(o[v] is not None for v in spec)]
    units = [o["muni"] for o in keep]
    periods = [o["anyo"] for o in keep]
    series = {v: [o[v] for o in keep] for v in [ykey, *spec]}
    y, cols_dm, w, _kept = ols.two_way_within(
        units, periods, series[ykey], [series[v] for v in spec]
    )
    x = [[c[i] for c in cols_dm] + w[i] for i in range(len(keep))]
    return x, y, list(units), len(keep), len(set(units))


def fit(x, y, cl):
    result = ols.ols_cluster(x, y, cl)
    return result["n"], result["clusters"], result["beta"][0], result["se"][0]


def grid_for(x, y, cl):
    result = wild_grid.wild_bootstrap_t_grid(x, y, cl, j=0, grid=GRID, reps=REPS, seed=SEED)
    return {
        "p": result["p"],
        "keep": result["keep"],
        "warnings": result["warnings"],
    }


def source_is_fresh() -> dict:
    if not SOURCE.is_file():
        raise ValueError("Missing panel_tourist artifact; run make analysis first")
    payload = json.loads(SOURCE.read_text())
    expected = ols.model_meta(str(ESTIMATOR), [str(DATABASE.relative_to(ROOT))])
    if payload.get("_meta") != expected:
        raise ValueError("panel_tourist artifact stale vs code/data; run make analysis")
    return payload


def meta() -> dict:
    result = ols.model_meta(
        str(Path(__file__).resolve()),
        [str(DATABASE.relative_to(ROOT)), str(SOURCE.relative_to(ROOT))],
    )
    # The grid algorithm lives in wild_grid.py, which model_meta does not
    # cover; pin it so a helper change fails the artifact freshness check.
    result["wild_grid_sha"] = ols.sha_file(str(ROOT / "src/spanish_housing/wild_grid.py"))
    return result


def compute(payload: dict) -> dict:
    results = {"models": {}}
    for key, (outcome, specification, y, spec) in MODELS.items():
        x, yvec, cl, n, g = design(y, spec)
        source_n, source_g, source_b, source_se = fit(x, yvec, cl)
        artifact = payload[key]
        if artifact["y"] != y or artifact["spec"] != spec:
            raise ValueError(f"{key}: model definition changed")
        if source_n != artifact["n"] or source_g != artifact["clusters"]:
            raise ValueError(f"{key}: reconstructed sample/clusters differ")
        b, se = artifact["coefs"]["d_tour"]["b"], artifact["coefs"]["d_tour"]["se"]
        if abs(round(source_b, 4) - b) > 1e-9 or abs(round(source_se, 4) - se) > 1e-9:
            raise ValueError(f"{key}: reconstructed fit differs from published artifact")
        grid_result = grid_for(x, yvec, cl)
        zero_p = artifact["wild_bootstrap"]["d_tour"]["p"]
        if grid_result["p"][GRID.index(0.0)] != round(zero_p, 4):
            raise ValueError(f"{key}: grid c=0 p differs from published zero-null wild p")
        results["models"][key] = {
            "outcome": outcome,
            "specification": specification,
            "y": y,
            "spec": spec,
            "n": n,
            "clusters": g,
            "b": round(source_b, 4),
            "se": round(source_se, 4),
            **grid_result,
        }
    results["grid"] = GRID
    results["reps"] = REPS
    results["seed"] = SEED
    results["alpha"] = ALPHA
    results["_meta"] = meta()
    return results


def cheap_check(stored: dict) -> dict:
    """Cheap `--check`: recompute design fits and the c=0 zero-null anchor.

    The full grid is a deterministic pure function of (design, seed, reps,
    grid, alpha, ols.py). Verifying the design anchor (n/clusters/b/se), the
    exact c=0 wild p, the grid constants and the stored hashes therefore
    catches every stale-input or code-change path without re-running the
    41-candidate x 4-model bootstrap on every `make verify`.
    """
    source_is_fresh()  # raises when the source artifact is stale
    if stored.get("grid") != GRID or stored.get("reps") != REPS:
        raise ValueError("stored grid/reps changed; recompute")
    if stored.get("seed") != SEED or stored.get("alpha") != ALPHA:
        raise ValueError("stored seed/alpha changed; recompute")
    if stored.get("_meta") != meta():
        raise ValueError("tourist_inversion artifact stale vs code/data; run make inference")
    for key, (_outcome, _specification, y, spec) in MODELS.items():
        model = stored["models"].get(key)
        if not model:
            raise ValueError(f"{key}: missing from stored inversion artifact")
        if model["y"] != y or model["spec"] != spec:
            raise ValueError(f"{key}: model definition changed")
        x, yvec, cl, n, g = design(y, spec)
        source_n, source_g, source_b, source_se = fit(x, yvec, cl)
        if (n, g) != (model["n"], model["clusters"]):
            raise ValueError(f"{key}: sample/clusters differ")
        if (round(source_b, 4), round(source_se, 4)) != (model["b"], model["se"]):
            raise ValueError(f"{key}: reconstructed fit differs")
        zero = wild_grid.wild_bootstrap_t_grid(x, yvec, cl, j=0, grid=[0.0], reps=REPS, seed=SEED)
        if zero["p"][0] != model["p"][GRID.index(0.0)]:
            raise ValueError(f"{key}: c=0 wild p differs from stored grid anchor")
        if len(model["p"]) != len(GRID) or len(model["keep"]) != len(GRID):
            raise ValueError(f"{key}: grid length differs")
        if not all(isinstance(v, bool) for v in model["keep"]):
            raise ValueError(f"{key}: keep mask malformed")
        if model["keep"] != [pv >= ALPHA for pv in model["p"]]:
            raise ValueError(f"{key}: keep mask inconsistent with p-values")
        expected_warnings = []
        keep = model["keep"]
        if not any(keep):
            expected_warnings.append("no_candidate_accepted_at_this_resolution")
        if keep and keep[0]:
            expected_warnings.append("accepted_set_may_extend_below_grid")
        if keep and keep[-1]:
            expected_warnings.append("accepted_set_may_extend_above_grid")
        if any(keep):
            first = keep.index(True)
            last = len(keep) - 1 - keep[::-1].index(True)
            if any(not keep[s] for s in range(first, last + 1)):
                expected_warnings.append("disjoint_accepted_set")
        if model.get("warnings") != expected_warnings:
            raise ValueError(f"{key}: warnings inconsistent with the acceptance mask")
        if not all(0 < p <= 1 for p in model["p"]):
            raise ValueError(f"{key}: invalid p-value")
    print(f"tourist_inversion: {len(stored['models'])} models, grid anchors and meta verified")
    return stored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        if not ARTIFACT.is_file():
            raise SystemExit("Missing tourist_inversion artifact; run make inference")
        cheap_check(json.loads(ARTIFACT.read_text()))
        return
    try:
        results = (
            cheap_check(json.loads(ARTIFACT.read_text()))
            if ARTIFACT.is_file()
            else compute(source_is_fresh())
        )
    except ValueError:
        results = compute(source_is_fresh())
    (ROOT / "artifacts").mkdir(exist_ok=True)
    ARTIFACT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {ARTIFACT.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, duckdb.Error) as error:
        raise SystemExit(f"tourist_inversion: {error}") from error
