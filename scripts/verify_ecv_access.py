"""Verify INE ECV 2025 housing-access sidecar pins and exact derivation."""

from __future__ import annotations

import duckdb
import pyarrow.parquet as pq

from fetch_ecv_access import (
    DATABASE,
    PARQUET,
    ROOT,
    TABLES,
    manifest,
    pinned_rows,
    validate_headlines,
)


def _order(row):
    # Geo is part of the key: every CCAA row of 79637 shares group_label TOTAL.
    return (row["tpx"], row["group_label"], row["geo"], row["measure"])


def canonical(rows):
    return sorted(rows, key=_order)


def main():
    man = manifest.load()
    expected = {}
    for path in [PARQUET, DATABASE]:
        rel = str(path.relative_to(ROOT))
        if rel not in man["sha256"]:
            raise ValueError(f"Access sidecar not pinned: {rel}")
        expected[rel] = man["sha256"][rel]
    missing, mismatched = manifest.check(expected)
    if missing or mismatched:
        raise ValueError(f"Access sidecar missing={missing}, changed={mismatched}")
    rows = canonical(pinned_rows())
    validate_headlines(rows)
    if canonical(pq.read_table(PARQUET).to_pylist()) != rows:
        raise ValueError("Access parquet stale vs parser + pinned inputs")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        for name in ("access_moves", "access_blocked", "access_youth"):
            table = con.execute(f"select * from {name}").to_arrow_table().to_pylist()
            want = [r for r in rows if r["block"] == name]
            order = sorted(table, key=_order)
            if order != canonical(want):
                raise ValueError(f"Access database table {name} stale vs derivation")
    tables = sorted({row["tpx"] for row in rows})
    if tables != sorted(TABLES):
        raise ValueError(f"Access tables {tables} vs pinned {sorted(TABLES)}")
    print(f"ecv access: {len(rows)} cells verified")


if __name__ == "__main__":
    main()
