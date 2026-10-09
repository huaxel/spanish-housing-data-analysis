"""Verify Eurostat sidecar pins and exact derivation, without modifying data."""

from __future__ import annotations

import duckdb
import pyarrow.parquet as pq

from fetch_housing_overburden import (
    DATABASE,
    JOINT_PARQUET,
    PARQUET,
    ROOT,
    manifest,
    pinned_joint_rows,
    pinned_rows,
    validate_totals,
)


def canonical(rows):
    return sorted(rows, key=lambda r: (r["dataset"], r["group_code"], r["survey_year"]))


def main():
    man = manifest.load()
    expected = {}
    for path in [PARQUET, JOINT_PARQUET, DATABASE]:
        rel = str(path.relative_to(ROOT))
        if rel not in man["sha256"]:
            raise SystemExit(f"Burden sidecar not pinned: {rel}; run fetch_housing_overburden.py")
        expected[rel] = man["sha256"][rel]
    missing, mismatched = manifest.check(expected)
    if missing or mismatched:
        raise SystemExit(f"Burden sidecar missing={missing}, changed={mismatched}")
    rows = canonical(pinned_rows())
    validate_totals(rows)
    if canonical(pq.read_table(PARQUET).to_pylist()) != rows:
        raise SystemExit("Burden parquet stale vs parser + pinned inputs; rebuild with --offline")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        table = con.execute("select * from overburden").to_arrow_table().to_pylist()
    if canonical(table) != rows:
        raise SystemExit("Burden database stale vs parser + pinned inputs; rebuild with --offline")
    joint = sorted(
        pinned_joint_rows(), key=lambda r: (r["age_code"], r["poverty_code"], r["survey_year"])
    )

    def ordered(values):
        return sorted(values, key=lambda r: (r["age_code"], r["poverty_code"], r["survey_year"]))

    if ordered(pq.read_table(JOINT_PARQUET).to_pylist()) != joint:
        raise SystemExit("Joint burden parquet stale vs pinned derivation; rebuild with --offline")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        values = con.execute("select * from overburden_age_poverty").to_arrow_table().to_pylist()
    if ordered(values) != joint:
        raise SystemExit("Joint burden database stale vs pinned derivation; rebuild with --offline")
    print(f"housing overburden: {len(rows)} marginal + {len(joint)} joint cells verified")


if __name__ == "__main__":
    main()
