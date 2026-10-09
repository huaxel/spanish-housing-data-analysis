"""Pinned Eurostat EU-SILC housing-conditions cells: overcrowding, under-occupation,
median housing-cost burden.

Sidecar database: central marts and their estimator input hashes stay unchanged;
results land in the existing housing_access.duckdb sidecar as new tables.
Rates describe persons in private households, NOT shares of households.
Medians (ilc_lvho08*) are medians of the burden distribution, not rates, but share
the same percent unit and bounds. Each breakdown is a separate published marginal;
only sex=T / poverty=TOTAL slices are kept from the three-way cuts.
Use --offline to rebuild exclusively from already pinned JSON-stat inputs.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
# code: (table, breakdown, group dimension, groups kept).
DATASETS = {
    "ilc_lvho05a": (
        "overcrowding",
        "age",
        "age",
        ("TOTAL", "Y_LT18", "Y18-64", "Y_GE65"),
    ),
    "ilc_lvho05c": (
        "overcrowding",
        "tenure",
        "tenure",
        ("OWN_L", "OWN_NL", "RENT_MKT", "RENT_FR"),
    ),
    "ilc_lvho05d": (
        "overcrowding",
        "deg_urb",
        "deg_urb",
        ("DEG1", "DEG2", "DEG3"),
    ),
    "ilc_lvho05q": (
        "overcrowding",
        "quant_inc",
        "quant_inc",
        ("TOTAL", "QU1", "QU2", "QU3", "QU4", "QU5"),
    ),
    "ilc_lvho50a": (
        "underoccupation",
        "age",
        "age",
        ("TOTAL", "Y_LT18", "Y18-64", "Y_GE65"),
    ),
    "ilc_lvho50c": ("underoccupation", "tenure", "tenure", ("TOTAL", "OWN", "RENT")),
    "ilc_lvho50d": (
        "underoccupation",
        "deg_urb",
        "deg_urb",
        ("DEG1", "DEG2", "DEG3"),
    ),
    "ilc_lvho08a": (
        "burden_median",
        "age",
        "age",
        ("TOTAL", "Y_LT18", "Y18-64", "Y_GE65"),
    ),
    "ilc_lvho08b": (
        "burden_median",
        "deg_urb",
        "deg_urb",
        ("DEG1", "DEG2", "DEG3"),
    ),
}
# Datasets with sex/rskpovth dimensions beyond the group cut.
THREE_WAY = {"ilc_lvho05a", "ilc_lvho50a", "ilc_lvho08a"}
# Datasets whose group cut carries a national TOTAL cell for cross-cut agreement.
WITH_TOTAL = {"ilc_lvho05a", "ilc_lvho05q", "ilc_lvho50a", "ilc_lvho50c"}
PARQUET = RAW / "parquet" / "housing_conditions.parquet"
DATABASE = PROCESSED / "housing_access.duckdb"
SCHEMA = pa.schema(
    [
        ("dataset", pa.string()),
        ("table", pa.string()),
        ("breakdown", pa.string()),
        ("group_code", pa.string()),
        ("group_label", pa.string()),
        ("geo", pa.string()),
        ("survey_year", pa.int64()),
        ("rate_pct", pa.float64()),
        ("status", pa.string()),
        ("updated", pa.string()),
    ]
)


def url(code: str) -> str:
    return f"{BASE}{code}?lang=EN&geo=ES&unit=PC&freq=A"


def cells(container, index):
    if isinstance(container, dict):
        return container.get(str(index))
    if isinstance(container, list):
        return container[index] if index < len(container) else None
    if container is None:
        return None
    raise ValueError("Unexpected JSON-stat cell container")


def parse(payload: dict, code: str) -> list[dict]:
    table, breakdown, group_dimension, groups = DATASETS[code]
    ids, sizes = payload["id"], payload["size"]
    expected = {"freq", "unit", "geo", "time", group_dimension}
    if code in THREE_WAY:
        expected |= {"sex", "rskpovth"}
    if len(ids) != len(set(ids)) or set(ids) != expected or len(ids) != len(sizes):
        raise ValueError(f"{code}: unexpected dimensions {ids}")
    categories = []
    for dim, size in zip(ids, sizes, strict=True):
        index = payload["dimension"][dim]["category"]["index"]
        # JSON-stat accepts either ordered lists or code->position objects.
        ordered = (
            index
            if isinstance(index, list)
            else [k for k, _ in sorted(index.items(), key=lambda kv: kv[1])]
        )
        if len(ordered) != size or len(set(ordered)) != size:
            raise ValueError(f"{code}: invalid category index for {dim}")
        if isinstance(index, dict) and set(index.values()) != set(range(size)):
            raise ValueError(f"{code}: non-contiguous category index for {dim}")
        categories.append(ordered)
    dimensions = dict(zip(ids, categories, strict=True))
    for dim, required in {"geo": ["ES"], "freq": ["A"], "unit": ["PC"]}.items():
        if dimensions[dim] != required:
            raise ValueError(f"{code}: unexpected {dim} selection")
    if not set(groups) <= set(dimensions[group_dimension]):
        raise ValueError(f"{code}: missing required groups")
    rows = []
    # itertools.product traverses row-major JSON-stat order, time usually last.
    for index, coordinates in enumerate(itertools.product(*categories)):
        cell = dict(zip(ids, coordinates, strict=True))
        if cell[group_dimension] not in groups:
            continue
        if code in THREE_WAY and (cell["sex"] != "T" or cell["rskpovth"] != "TOTAL"):
            continue
        value = cells(payload.get("value"), index)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (float, int)):
                raise ValueError(f"{code}: nonnumeric rate")
            value = float(value)
            if not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError(f"{code}: rate out of bounds")
        rows.append(
            {
                "dataset": code,
                "table": table,
                "breakdown": breakdown,
                "group_code": cell[group_dimension],
                "group_label": payload["dimension"][group_dimension]["category"]["label"][
                    cell[group_dimension]
                ],
                "geo": "ES",
                "survey_year": int(cell["time"]),
                "rate_pct": value,
                "status": cells(payload.get("status"), index) or "",
                "updated": payload.get("updated", ""),
            }
        )
    if not rows or not any(r["rate_pct"] is not None for r in rows):
        raise ValueError(f"{code}: no observed rates")
    return rows


def raw_path(code):
    return RAW / f"eurostat_{code}_ES.json"


def pinned_rows() -> list[dict]:
    man = manifest.load()
    expected = {}
    for code in DATASETS:
        rel = str(raw_path(code).relative_to(ROOT))
        if rel not in man["sha256"]:
            raise ValueError(f"Unpinned input {rel}; run fetch_housing_conditions.py")
        expected[rel] = man["sha256"][rel]
    missing, mismatched = manifest.check(expected)
    if missing or mismatched:
        raise ValueError(f"Conditions inputs missing={missing}, changed={mismatched}")
    rows = []
    for code in DATASETS:
        rows.extend(parse(json.loads(raw_path(code).read_text()), code))
    return rows


def validate_totals(rows):
    # National TOTAL cells must agree across breakdowns of the same table.
    # Medians never aggregate, so burden_median is excluded by construction.
    # Each (table, year) needs at least two TOTAL sources: a single source
    # would pass vacuously if a dataset ever dropped its TOTAL cell.
    totals = {}
    for row in rows:
        if (
            row["dataset"] in WITH_TOTAL
            and row["group_code"] == "TOTAL"
            and row["rate_pct"] is not None
        ):
            totals.setdefault((row["table"], row["survey_year"]), []).append(row["rate_pct"])
    for key, values in totals.items():
        if len(values) < 2:
            raise ValueError(f"Single TOTAL source for {key}: agreement uncheckable")
        if max(values) - min(values) > 0.15:
            raise ValueError("National totals disagree across breakdowns")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not args.offline:
        for code in DATASETS:
            req = urllib.request.Request(
                url(code), headers={"User-Agent": "housing-data-analysis/1.0"}
            )
            with urllib.request.urlopen(req, timeout=120) as response:  # noqa: S310
                contents = response.read()
            parse(json.loads(contents), code)  # validate before replacing local input
            path = raw_path(code)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(contents)
            tmp.replace(path)
            manifest.record(
                str(path.relative_to(ROOT)),
                {
                    "url": url(code),
                    "publisher": "Eurostat, EU-SILC",
                    "accessed": date.today().isoformat(),
                    "note": "ES, annual person rates/medians; published marginals only",
                },
            )
    rows = pinned_rows()
    validate_totals(rows)
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, PARQUET)
    # CREATE OR REPLACE on the live sidecar: existing overburden tables are
    # untouched, and each statement is atomic, so an interrupted build is
    # safely resumable. A tmp-file replace (as in burden fetches) would
    # drop the other tables, so it must not be used here.
    by_table = {}
    for row in rows:
        by_table.setdefault(row["table"], []).append(row)
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DATABASE)) as con:
        for name, table_rows in by_table.items():
            con.register("conditions_input", pa.Table.from_pylist(table_rows))
            con.execute(f"create or replace table {name} as select * from conditions_input")
            con.unregister("conditions_input")
    for path in [PARQUET, DATABASE]:
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "publisher": "Eurostat, EU-SILC",
                "accessed": date.today().isoformat(),
                "note": (
                    "Derived from pinned eurostat_ilc_lvho{05a,05c,05d,05q,"
                    "50a,50c,50d,08a,08b}_ES.json by fetch_housing_conditions.py"
                ),
            },
        )
    print(f"housing conditions: {len(rows)} cells; sidecar {DATABASE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
