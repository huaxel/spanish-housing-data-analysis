"""Verify Eurostat housing-conditions sidecar pins and exact derivation."""

from __future__ import annotations

import duckdb
import pyarrow.parquet as pq

from fetch_housing_conditions import (
    DATABASE,
    PARQUET,
    ROOT,
    manifest,
    pinned_rows,
    validate_totals,
)


def canonical(rows):
    return sorted(rows, key=lambda r: (r["dataset"], r["group_code"], r["survey_year"]))


def main():
    man = manifest.load()
    expected = {}
    for path in [PARQUET, DATABASE]:
        rel = str(path.relative_to(ROOT))
        if rel not in man["sha256"]:
            raise ValueError(f"Conditions sidecar not pinned: {rel}")
        expected[rel] = man["sha256"][rel]
    missing, mismatched = manifest.check(expected)
    if missing or mismatched:
        raise ValueError(f"Conditions sidecar missing={missing}, changed={mismatched}")
    rows = canonical(pinned_rows())
    validate_totals(rows)
    if canonical(pq.read_table(PARQUET).to_pylist()) != rows:
        raise ValueError("Conditions parquet stale vs parser + pinned inputs")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        for name in ("overcrowding", "underoccupation", "burden_median"):
            table = con.execute(f"select * from {name}").to_arrow_table().to_pylist()
            want = [r for r in rows if r["table"] == name]
            if sorted(
                table, key=lambda r: (r["dataset"], r["group_code"], r["survey_year"])
            ) != canonical(want):
                raise ValueError(f"Conditions database table {name} stale vs derivation")
    print(f"housing conditions: {len(rows)} cells verified")


if __name__ == "__main__":
    main()
