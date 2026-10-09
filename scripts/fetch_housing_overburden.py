"""Pinned Eurostat EU-SILC housing-cost burden marginals and age-poverty cells.

Sidecar database: central marts and their estimator input hashes stay unchanged.
Rates describe persons in private households, NOT shares of households.
Income, age and tenure remain separate marginals; age-poverty is a direct published cross.
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
DATASETS = {
    "ilc_lvho07a": ("age", "age", ("TOTAL", "Y18-24", "Y25-29", "Y18-64", "Y_GE65")),
    "ilc_lvho07b": ("income", "quant_inc", ("TOTAL", "QU1", "QU2", "QU3", "QU4", "QU5")),
    "ilc_lvho07c": ("tenure", "tenure", ("TOTAL", "OWN_L", "OWN_NL", "RENT_MKT", "RENT_FR")),
}
PARQUET = RAW / "parquet" / "housing_overburden.parquet"
DATABASE = PROCESSED / "housing_access.duckdb"
JOINT_PARQUET = RAW / "parquet" / "housing_overburden_age_poverty.parquet"
JOINT_SCHEMA = pa.schema(
    [
        ("dataset", pa.string()),
        ("age_code", pa.string()),
        ("age_label", pa.string()),
        ("poverty_code", pa.string()),
        ("poverty_label", pa.string()),
        ("geo", pa.string()),
        ("survey_year", pa.int64()),
        ("rate_pct", pa.float64()),
        ("status", pa.string()),
        ("updated", pa.string()),
    ]
)
SCHEMA = pa.schema(
    [
        ("dataset", pa.string()),
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
    breakdown, group_dimension, groups = DATASETS[code]
    ids, sizes = payload["id"], payload["size"]
    expected = {"freq", "unit", "geo", "time", group_dimension}
    if breakdown == "age":
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
        if breakdown == "age" and (cell["sex"] != "T" or cell["rskpovth"] != "TOTAL"):
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


def parse_age_poverty(payload):
    code = "ilc_lvho07a"
    parse(payload, code)  # validate the same dimensions, units, geography and indexing
    categories = []
    for dim in payload["id"]:
        index = payload["dimension"][dim]["category"]["index"]
        categories.append(
            index
            if isinstance(index, list)
            else [k for k, _ in sorted(index.items(), key=lambda kv: kv[1])]
        )
    dims = dict(zip(payload["id"], categories, strict=True))
    if not {"A_60", "B_60", "TOTAL"} <= set(dims["rskpovth"]) or "T" not in dims["sex"]:
        raise ValueError("Missing published poverty/total-sex categories")
    rows = []
    for index, coords in enumerate(itertools.product(*categories)):
        cell = dict(zip(payload["id"], coords, strict=True))
        if (
            cell["sex"] != "T"
            or cell["rskpovth"] not in {"A_60", "B_60"}
            or cell["age"] not in DATASETS[code][2]
        ):
            continue
        value = cells(payload.get("value"), index)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Nonnumeric joint burden rate")
            value = float(value)
            if not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError("Joint burden rate out of bounds")
        flag = cells(payload.get("status"), index)
        if flag is None:
            flag = ""
        if not isinstance(flag, str):
            raise ValueError("Invalid joint burden status")
        rows.append(
            {
                "dataset": code,
                "age_code": cell["age"],
                "age_label": payload["dimension"]["age"]["category"]["label"][cell["age"]],
                "poverty_code": cell["rskpovth"],
                "poverty_label": payload["dimension"]["rskpovth"]["category"]["label"][
                    cell["rskpovth"]
                ],
                "geo": "ES",
                "survey_year": int(cell["time"]),
                "rate_pct": value,
                "status": flag,
                "updated": payload.get("updated", ""),
            }
        )
    return rows


def pinned_joint_rows():
    pinned_rows()  # all input pins and original marginal contracts remain enforced
    return parse_age_poverty(json.loads(raw_path("ilc_lvho07a").read_text()))


def raw_path(code):
    return RAW / f"eurostat_{code}_ES.json"


def pinned_rows() -> list[dict]:
    man = manifest.load()
    expected = {}
    for code in DATASETS:
        rel = str(raw_path(code).relative_to(ROOT))
        if rel not in man["sha256"]:
            raise ValueError(f"Unpinned input {rel}; run fetch_housing_overburden.py")
        expected[rel] = man["sha256"][rel]
    missing, mismatched = manifest.check(expected)
    if missing or mismatched:
        raise ValueError(f"Burden inputs missing={missing}, changed={mismatched}")
    rows = []
    for code in DATASETS:
        rows.extend(parse(json.loads(raw_path(code).read_text()), code))
    return rows


def validate_totals(rows):
    totals = {}
    for row in rows:
        if row["group_code"] == "TOTAL" and row["rate_pct"] is not None:
            totals.setdefault(row["survey_year"], []).append(row["rate_pct"])
    if any(max(values) - min(values) > 0.15 for values in totals.values()):
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
                    "note": "ES, annual person rates; marginals and direct age-poverty cells",
                },
            )
    rows = pinned_rows()
    validate_totals(rows)
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    joint = pa.Table.from_pylist(pinned_joint_rows(), schema=JOINT_SCHEMA)
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, PARQUET)
    pq.write_table(joint, JOINT_PARQUET)
    tmp_db = DATABASE.with_suffix(".tmp.duckdb")
    # CREATE OR REPLACE makes an interrupted build safely resumable.
    with duckdb.connect(str(tmp_db)) as con:
        con.register("burden_input", table)
        con.execute("create or replace table overburden as select * from burden_input")
        con.register("joint_input", joint)
        con.execute("create or replace table overburden_age_poverty as select * from joint_input")
    tmp_db.replace(DATABASE)
    for path in [PARQUET, JOINT_PARQUET, DATABASE]:
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "publisher": "Eurostat, EU-SILC",
                "accessed": date.today().isoformat(),
                "note": (
                    "Derived from pinned eurostat_ilc_lvho07[a,b,c]_ES.json "
                    "by fetch_housing_overburden.py"
                ),
            },
        )
    print(f"housing overburden: {len(rows)} cells; sidecar {DATABASE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
