"""Presentation-only export of existing tourism-panel uncertainty.

Does not refit models or invent bootstrap coefficient intervals. Source
ci95 is the estimator's normal-approximation CR1 range; wild p tests zero.
The tourist_inversion tables publish the prespecified wild-bootstrap
candidate grid (tested points and acceptance mask only, no continuous CI).
Use --check for read-only derivation/freshness verification.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import duckdb
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

ARTIFACT = ROOT / "artifacts" / "panel_tourist.json"
INVERSION = ROOT / "artifacts" / "tourist_inversion.json"
INVERSION_SCRIPT = ROOT / "scripts" / "invert_tourist.py"
ESTIMATOR = ROOT / "explorations" / "panel_tourist.py"
DATABASE = PROCESSED / "inference.duckdb"
MODELS = {
    "sale_tour_only": ("Venta", "Solo turismo", "d_sale", ["d_tour"]),
    "sale_with_pop": ("Venta", "Turismo + población", "d_sale", ["d_tour", "d_pop"]),
    "rent_tour_only": ("Alquiler", "Solo turismo", "d_rent", ["d_tour"]),
    "rent_with_pop": ("Alquiler", "Turismo + población", "d_rent", ["d_tour", "d_pop"]),
}
SCHEMA = pa.schema(
    [
        ("model_key", pa.string()),
        ("outcome", pa.string()),
        ("specification", pa.string()),
        ("b", pa.float64()),
        ("se", pa.float64()),
        ("normal_lo", pa.float64()),
        ("normal_hi", pa.float64()),
        ("wild_p_zero", pa.float64()),
        ("n", pa.int64()),
        ("clusters", pa.int64()),
        ("bootstrap_reps", pa.int64()),
    ]
)
INV_SCHEMA = pa.schema(
    [
        ("model_key", pa.string()),
        ("outcome", pa.string()),
        ("specification", pa.string()),
        ("candidate_c", pa.float64()),
        ("wild_p", pa.float64()),
        ("keep_95", pa.bool_()),
    ]
)
INV_META_SCHEMA = pa.schema(
    [
        ("model_key", pa.string()),
        ("outcome", pa.string()),
        ("specification", pa.string()),
        ("n", pa.int64()),
        ("clusters", pa.int64()),
        ("b", pa.float64()),
        ("se", pa.float64()),
        ("accepted_min_c", pa.float64()),
        ("accepted_max_c", pa.float64()),
        ("accepted_count", pa.int64()),
        ("warnings", pa.string()),
    ]
)


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Invalid numeric {label}")
    return float(value)


def positive_integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Invalid positive integer {label}")
    return value


def parse(payload):
    if {key for key in payload if not key.startswith("_")} != set(MODELS):
        raise ValueError("Unexpected tourism-panel model set")
    rows = []
    for key, (outcome, specification, y, spec) in MODELS.items():
        model = payload[key]
        if model["y"] != y or model["spec"] != spec:
            raise ValueError(f"{key}: model definition changed")
        coef = model["coefs"]["d_tour"]
        b, se = number(coef["b"], "b"), number(coef["se"], "se")
        if len(coef["ci95"]) != 2:
            raise ValueError(f"{key}: missing normal interval endpoints")
        lo, hi = [number(v, "ci95") for v in coef["ci95"]]
        if se < 0 or lo > hi or not lo <= b <= hi:
            raise ValueError(f"{key}: invalid normal interval")
        # Source rounds b/se/endpoints independently to four decimal places.
        if abs((lo + hi) / 2 - b) > 0.00011 or abs((hi - lo) / 2 - 1.96 * se) > 0.00016:
            raise ValueError(f"{key}: ci95 no longer matches the normal-approximation definition")
        bootstrap = model["wild_bootstrap"]["d_tour"]
        p = number(bootstrap["p"], "wild p")
        if not 0 < p <= 1:
            raise ValueError(f"{key}: invalid wild p")
        n = positive_integer(model["n"], "n")
        clusters = positive_integer(model["clusters"], "clusters")
        reps = positive_integer(bootstrap["reps"], "bootstrap reps")
        if clusters < 2 or clusters > n:
            raise ValueError(f"{key}: invalid cluster count")
        rows.append(
            {
                "model_key": key,
                "outcome": outcome,
                "specification": specification,
                "b": b,
                "se": se,
                "normal_lo": lo,
                "normal_hi": hi,
                "wild_p_zero": p,
                "n": n,
                "clusters": clusters,
                "bootstrap_reps": reps,
            }
        )
    return rows


def parse_inversion(payload):
    """Parse the tourist_inversion artifact into candidate and summary rows."""
    grid = payload.get("grid")
    if not isinstance(grid, list) or len(grid) < 2 or len(set(grid)) != len(grid):
        raise ValueError("Inversion grid missing or not strictly increasing")
    if grid != sorted(grid):
        raise ValueError("Inversion grid not increasing")
    if payload.get("reps") != 1999 or payload.get("seed") != 20261006:
        raise ValueError("Inversion reps/seed changed from the reviewed run")
    if payload.get("alpha") != 0.05:
        raise ValueError("Inversion alpha changed")
    if {key for key in payload if not key.startswith("_")} != {
        "grid",
        "reps",
        "seed",
        "alpha",
        "models",
    }:
        raise ValueError("Unexpected inversion artifact structure")
    if set(payload["models"]) != set(MODELS):
        raise ValueError("Unexpected inversion model set")
    candidates, summaries = [], []
    for key, (outcome, specification, y, spec) in MODELS.items():
        model = payload["models"][key]
        if model["y"] != y or model["spec"] != spec:
            raise ValueError(f"{key}: inversion model definition changed")
        p = model.get("p")
        keep = model.get("keep")
        if not isinstance(p, list) or len(p) != len(grid):
            raise ValueError(f"{key}: p grid length differs")
        if not isinstance(keep, list) or len(keep) != len(grid):
            raise ValueError(f"{key}: keep mask length differs")
        if not all(isinstance(v, bool) for v in keep):
            raise ValueError(f"{key}: keep mask malformed")
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v <= 1 for v in p
        ):
            raise ValueError(f"{key}: invalid candidate p")
        if keep != [pv >= payload["alpha"] for pv in p]:
            raise ValueError(f"{key}: keep mask inconsistent with p-values")
        warnings = model.get("warnings")
        if not isinstance(warnings, list) or not all(isinstance(w, str) for w in warnings):
            raise ValueError(f"{key}: warnings malformed")
        expected_warnings = []
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
        if warnings != expected_warnings:
            raise ValueError(f"{key}: warnings inconsistent with the acceptance mask")
        n = positive_integer(model["n"], "n")
        clusters = positive_integer(model["clusters"], "clusters")
        b = number(model["b"], "b")
        se = number(model["se"], "se")
        if se <= 0:
            raise ValueError(f"{key}: nonpositive inversion se")
        accepted = [c for c, kp in zip(grid, keep, strict=True) if kp]
        if not accepted:
            if model["warnings"] != ["no_candidate_accepted_at_this_resolution"]:
                raise ValueError(f"{key}: empty acceptance without resolution warning")
            summaries.append(
                {
                    "model_key": key,
                    "outcome": outcome,
                    "specification": specification,
                    "n": n,
                    "clusters": clusters,
                    "b": b,
                    "se": se,
                    "accepted_min_c": None,
                    "accepted_max_c": None,
                    "accepted_count": 0,
                    "warnings": ";".join(warnings),
                }
            )
        else:
            summaries.append(
                {
                    "model_key": key,
                    "outcome": outcome,
                    "specification": specification,
                    "n": n,
                    "clusters": clusters,
                    "b": b,
                    "se": se,
                    "accepted_min_c": min(accepted),
                    "accepted_max_c": max(accepted),
                    "accepted_count": len(accepted),
                    "warnings": ";".join(warnings),
                }
            )
        candidates.extend(
            {
                "model_key": key,
                "outcome": outcome,
                "specification": specification,
                "candidate_c": c,
                "wild_p": pv,
                "keep_95": kp,
            }
            for c, pv, kp in zip(grid, p, keep, strict=True)
        )
    return candidates, summaries


def source_rows():
    if not ARTIFACT.is_file():
        raise ValueError("Missing panel_tourist artifact; run make analysis, then make inference")
    payload = json.loads(ARTIFACT.read_text())
    expected = ols.model_meta(str(ESTIMATOR), ["data/processed/marts.duckdb"])
    if payload.get("_meta") != expected:
        raise ValueError(
            "Tourism artifact stale vs code/data; run make analysis, then make inference"
        )
    return parse(payload), {
        "export_script_sha": ols.sha_file(__file__),
        "source_artifact_sha": ols.sha_file(str(ARTIFACT)),
        "source_meta": json.dumps(expected, sort_keys=True),
    }


def inversion_source_rows():
    if not INVERSION.is_file():
        raise ValueError("Missing tourist_inversion artifact; run make inference")
    payload = json.loads(INVERSION.read_text())
    candidates, summaries = parse_inversion(payload)
    metadata = {
        "inversion_script_sha": ols.sha_file(INVERSION_SCRIPT),
        "inversion_artifact_sha": ols.sha_file(str(INVERSION)),
        "inversion_meta": json.dumps(payload.get("_meta", {}), sort_keys=True),
    }
    return candidates, summaries, metadata


def canonical(rows):
    return sorted(rows, key=lambda row: row["model_key"])


def canonical_inv(rows):
    return sorted(rows, key=lambda row: (row["model_key"], row["candidate_c"]))


def verify(rows, metadata, inv_rows, inv_meta_rows, inv_metadata):
    if not DATABASE.is_file():
        raise ValueError("Missing inference sidecar; run make inference")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        actual = con.execute("select * from tourism_panel").to_arrow_table().to_pylist()
        actual_inv = con.execute("select * from tourism_inversion").to_arrow_table().to_pylist()
        actual_inv_meta = (
            con.execute("select * from tourism_inversion_meta").to_arrow_table().to_pylist()
        )
        actual_meta = dict(con.execute("select key, value from export_meta").fetchall())
    expected_meta = {**metadata, **inv_metadata}
    if (
        canonical(actual) != canonical(rows)
        or canonical_inv(actual_inv) != canonical_inv(inv_rows)
        or canonical(actual_inv_meta) != canonical(inv_meta_rows)
        or actual_meta != expected_meta
    ):
        raise ValueError("Inference sidecar stale or changed; run make inference")
    print(
        f"inference: {len(rows)} model rows, {len(inv_rows)} candidate rows, "
        "exact source and derivation verified"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows, metadata = source_rows()
    inv_rows, inv_meta_rows, inv_metadata = inversion_source_rows()
    if args.check:
        verify(rows, metadata, inv_rows, inv_meta_rows, inv_metadata)
        return
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    inv_table = pa.Table.from_pylist(inv_rows, schema=INV_SCHEMA)
    inv_meta_table = pa.Table.from_pylist(inv_meta_rows, schema=INV_META_SCHEMA)
    tmp = DATABASE.with_suffix(".tmp.duckdb")
    with duckdb.connect(str(tmp)) as con:
        con.register("rows_input", table)
        con.execute("create or replace table tourism_panel as select * from rows_input")
        con.register("inv_input", inv_table)
        con.execute("create or replace table tourism_inversion as select * from inv_input")
        con.register("inv_meta_input", inv_meta_table)
        con.execute(
            "create or replace table tourism_inversion_meta as select * from inv_meta_input"
        )
        con.execute("create or replace table export_meta (key varchar, value varchar)")
        con.executemany(
            "insert into export_meta values (?, ?)",
            list({**metadata, **inv_metadata}.items()),
        )
    tmp.replace(DATABASE)
    verify(rows, metadata, inv_rows, inv_meta_rows, inv_metadata)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, duckdb.Error) as error:
        raise SystemExit(f"inference: {error}") from error
