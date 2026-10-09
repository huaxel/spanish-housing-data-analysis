"""Presentation-only export of existing tourism-panel uncertainty.

Does not refit models or invent bootstrap coefficient intervals. Source
ci95 is the estimator's normal-approximation CR1 range; wild p tests zero.
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


def canonical(rows):
    return sorted(rows, key=lambda row: row["model_key"])


def verify(rows, metadata):
    if not DATABASE.is_file():
        raise ValueError("Missing inference sidecar; run make inference")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        actual = con.execute("select * from tourism_panel").to_arrow_table().to_pylist()
        actual_meta = dict(con.execute("select key, value from export_meta").fetchall())
    if canonical(actual) != canonical(rows) or actual_meta != metadata:
        raise ValueError("Inference sidecar stale or changed; run make inference")
    print(f"inference: {len(rows)} model rows, exact source and derivation verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows, metadata = source_rows()
    if args.check:
        verify(rows, metadata)
        return
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    tmp = DATABASE.with_suffix(".tmp.duckdb")
    with duckdb.connect(str(tmp)) as con:
        con.register("rows_input", table)
        con.execute("create or replace table tourism_panel as select * from rows_input")
        con.execute("create or replace table export_meta (key varchar, value varchar)")
        con.executemany("insert into export_meta values (?, ?)", list(metadata.items()))
    tmp.replace(DATABASE)
    verify(rows, metadata)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, duckdb.Error) as error:
        raise SystemExit(f"inference: {error}") from error
