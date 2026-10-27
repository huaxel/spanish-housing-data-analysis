"""Presentation-only deficit arithmetic; no refit or central-mart writes.

Reuses the fresh deficit artifact and pinned monthly completions. Annual
MIVAU stock is at Dec 31: calendar years a..b compare stock(b)-stock(a-1),
while ECP Jan-1 households compare households(b+1)-households(a).
Missing completion cells give a published subtotal, never an exact total.
Use --check for read-only exact derivation and source-proof verification.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

DATABASE = PROCESSED / "deficit.duckdb"
ARTIFACT = ROOT / "artifacts/deficit_vivienda.json"
ESTIMATOR = ROOT / "explorations/deficit_vivienda.py"
MARTS = PROCESSED / "marts.duckdb"
MONTHLY = RAW / "parquet/mivau_terminadas.parquet"
HOUSEHOLDS = RAW / "parquet/ecp_hog_prov.parquet"
WINDOWS = {"2021-2024": (2021, 2024), "2021-2025": (2021, 2025)}
PROVINCES = {f"{p:02d}" for p in range(1, 51)} | {"51+52"}
SCHEMA = pa.schema(
    [(name, pa.string()) for name in ("window_key", "cpro", "provincia")]
    + [
        (name, pa.int64())
        for name in (
            "flow_start",
            "flow_end",
            "stock_start_year",
            "stock_end_year",
            "household_start_year",
            "household_end_year",
            "household_change",
            "stock_change",
            "completions_observed",
            "completion_cells_expected",
            "completion_cells_observed",
            "completion_cells_missing",
            "gap_stock",
            "gap_completions",
            "gap_completions_upper",
        )
    ]
)


def integer(value, label, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label}: expected integer")
    if nonnegative and value < 0:
        raise ValueError(f"{label}: negative count")
    return value


def coverage(monthly, first, last):
    """Count every province x month x regime cell, including absent records."""
    cells = {}
    for row in monthly:
        if row["estado"] != "Terminadas" or not first <= row["anyo"] <= last:
            continue
        key = (row["cpro"], row["anyo"], row["mes"], row["tipo"])
        if (
            row["cpro"] not in {f"{p:02d}" for p in range(1, 53)}
            or not 1 <= row["mes"] <= 12
            or row["tipo"] not in ("Libre", "Protegida")
        ):
            raise ValueError(f"Invalid completion key {key}")
        if key in cells:
            raise ValueError(f"Duplicate completion cell {key}")
        value = row["viviendas"]
        if value is not None:
            integer(value, "completion", nonnegative=True)
        cells[key] = value
    result = {}
    for cpro in sorted(PROVINCES):
        parts = ("51", "52") if cpro == "51+52" else (cpro,)
        values = [
            cells.get((part, year, month, regime))
            for part in parts
            for year in range(first, last + 1)
            for month in range(1, 13)
            for regime in ("Libre", "Protegida")
        ]
        observed = [v for v in values if v is not None]
        result[cpro] = (len(values), len(observed), sum(observed) if observed else None)
    return result


def build_rows(payload, stocks, monthly):
    if set(payload["windows"]) != set(WINDOWS):
        raise ValueError("Deficit artifact window set changed")
    stock_map = {}
    for row in stocks:
        key = (row["cpro"], row["anyo"])
        if key in stock_map:
            raise ValueError(f"Duplicate stock endpoint {key}")
        if row["viviendas_total"] is not None:
            integer(row["viviendas_total"], "stock", nonnegative=True)
        stock_map[key] = row["viviendas_total"]
    rows = []
    for window, (first, last) in WINDOWS.items():
        source = payload["windows"][window]
        entries = source["provinces"]
        codes = [v["cpro"] for v in entries.values()]
        if len(codes) != len(PROVINCES) or set(codes) != PROVINCES:
            raise ValueError("Deficit province coverage changed or duplicated")
        counts = coverage(monthly, first, last)
        provincial = []
        for name, entry in entries.items():
            code = entry["cpro"]
            created = integer(entry["creation"], "household change")
            expected, observed, subtotal = counts[code]
            finished = integer(entry["terminadas"], "artifact completions", nonnegative=True)
            if finished != (subtotal if subtotal is not None else 0):
                raise ValueError(f"Artifact/monthly completions disagree: {window}/{code}")
            if integer(entry["deficit_v2"], "artifact gap") != created - finished:
                raise ValueError("Artifact gap arithmetic changed")
            initial, final = (stock_map.get((code, year)) for year in (first - 1, last))
            delta = None if initial is None or final is None else final - initial
            upper = None if subtotal is None else created - subtotal
            provincial.append(
                {
                    "window_key": window,
                    "cpro": code,
                    "provincia": name,
                    "flow_start": first,
                    "flow_end": last,
                    "stock_start_year": first - 1,
                    "stock_end_year": last,
                    "household_start_year": first,
                    "household_end_year": last + 1,
                    "household_change": created,
                    "stock_change": delta,
                    "completions_observed": subtotal,
                    "completion_cells_expected": expected,
                    "completion_cells_observed": observed,
                    "completion_cells_missing": expected - observed,
                    "gap_stock": None if delta is None else created - delta,
                    "gap_completions": upper if expected == observed else None,
                    "gap_completions_upper": upper,
                }
            )
        if sum(e["deficit_v2"] for e in entries.values()) != source["national"]["deficit_v2"]:
            raise ValueError("Artifact national/provincial arithmetic disagrees")
        national = {
            key: provincial[0][key]
            for key in (
                "window_key",
                "flow_start",
                "flow_end",
                "stock_start_year",
                "stock_end_year",
                "household_start_year",
                "household_end_year",
            )
        }
        national.update(cpro="NACIONAL", provincia="España (suma provincial)")
        for field in (
            "household_change",
            "stock_change",
            "completions_observed",
            "completion_cells_expected",
            "completion_cells_observed",
            "completion_cells_missing",
            "gap_stock",
            "gap_completions",
            "gap_completions_upper",
        ):
            values = [r[field] for r in provincial]
            national[field] = None if any(v is None for v in values) else sum(values)
        rows.extend([*provincial, national])
    return sorted(rows, key=lambda r: (r["window_key"], r["cpro"]))


def source_rows():
    if not ARTIFACT.exists():
        raise ValueError("Missing deficit artifact; run make analysis")
    payload = json.loads(ARTIFACT.read_text())
    inputs = [str(p.relative_to(ROOT)) for p in (MARTS, MONTHLY, HOUSEHOLDS)]
    expected = ols.model_meta(str(ESTIMATOR), inputs)
    if payload.get("_meta") != expected:
        raise ValueError("Stale deficit artifact; run make analysis")
    with duckdb.connect(str(MARTS), read_only=True) as con:
        stocks = (
            con.execute(
                "select cpro, anyo, viviendas_total from mart_provincia_anual "
                "where anyo in (2020, 2024, 2025)"
            )
            .to_arrow_table()
            .to_pylist()
        )
    rows = build_rows(payload, stocks, pq.read_table(MONTHLY).to_pylist())
    metadata = {
        "export_script_sha": ols.sha_file(__file__),
        "artifact_sha": ols.sha_file(ARTIFACT),
        "source_meta": json.dumps(expected, sort_keys=True),
    }
    return pa.Table.from_pylist(rows, schema=SCHEMA), metadata


def verify(table, metadata):
    if not DATABASE.exists():
        raise ValueError("Missing deficit presentation sidecar; run make deficit")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        actual = con.execute("select * from comparisons order by window_key, cpro").to_arrow_table()
        actual_meta = dict(con.execute("select key, value from export_meta").fetchall())
    if not actual.cast(SCHEMA).equals(table) or actual_meta != metadata:
        raise ValueError("Deficit presentation sidecar stale or changed; run make deficit")
    print(f"deficit: {table.num_rows} comparison rows; exact source proof verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    table, metadata = source_rows()
    if not args.check:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        tmp = DATABASE.with_suffix(".tmp.duckdb")
        with duckdb.connect(str(tmp)) as con:
            con.register("derived", table)
            con.execute("create or replace table comparisons as select * from derived")
            con.execute("create or replace table export_meta(key varchar, value varchar)")
            con.executemany("insert into export_meta values (?, ?)", list(metadata.items()))
        tmp.replace(DATABASE)
    verify(table, metadata)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, duckdb.Error) as error:
        raise SystemExit(f"deficit: {error}") from error
