"""CSV loading helpers: BOM-tolerant, all-varchar, deterministic."""

from __future__ import annotations

import csv
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def read_csv_records(path: Path, delimiter: str) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        assert reader.fieldnames is not None, f"no header in {path}"
        rows = [dict(r) for r in reader]
    return reader.fieldnames, rows


def write_parquet(rows: list[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)
    return len(rows)
