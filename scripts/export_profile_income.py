"""Standalone ADRH net household income for the municipal profile.

Projects only neta_hogar from the pinned municipal parquet into a separate
presentation sidecar. It never joins rent, computes a ratio, fills missing
values, or rewrites raw inputs, marts, or the existing access sidecar.
--check verifies exact rows and input/exporter proof without writing.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import manifest, ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

INPUT = RAW / "parquet/adrh_renta_municipal.parquet"
DATABASE = PROCESSED / "profile_income.duckdb"
YEARS = set(range(2015, 2024))
CPROS = {f"{p:02d}" for p in range(1, 53)}
SCHEMA = pa.schema(
    [
        ("codigo", pa.string()),
        ("municipio", pa.string()),
        ("cpro", pa.string()),
        ("anyo", pa.int64()),
        ("renta_neta_hogar", pa.int64()),
    ]
)


def project(rows):
    projected = []
    seen = set()
    years_by_code = {}
    expected_codes = set()
    for row in rows:
        expected_codes.add(row["codigo"])
        if row["indicador"] != "neta_hogar":
            continue
        code, cpro, year = row["codigo"], row["cpro"], row["anyo"]
        if (
            not isinstance(code, str)
            or not re.fullmatch(r"[0-9]{5}", code)
            or code[:2] != cpro
            or cpro not in CPROS
            or code.endswith("999")
        ):
            raise ValueError(f"Invalid municipal income key {code!r}/{cpro!r}")
        if isinstance(year, bool) or not isinstance(year, int) or year not in YEARS:
            raise ValueError(f"Unexpected income year {year!r}")
        name = row["municipio"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Missing municipal income label {code}")
        value = row["renta_eur"]
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise ValueError(f"Invalid net household income {code}/{year}")
        key = (code, year)
        if key in seen:
            raise ValueError(f"Duplicate municipal income key {key}")
        seen.add(key)
        years_by_code.setdefault(code, set()).add(year)
        projected.append(
            {
                "codigo": code,
                "municipio": name,
                "cpro": cpro,
                "anyo": year,
                "renta_neta_hogar": value,
            }
        )
    if (
        not projected
        or set(years_by_code) != expected_codes
        or any(years != YEARS for years in years_by_code.values())
    ):
        raise ValueError("Municipal income grid is empty or has missing year records")
    return sorted(projected, key=lambda row: (row["codigo"], row["anyo"]))


def source_rows():
    relative = str(INPUT.relative_to(ROOT))
    pins = manifest.load().get("sha256", {})
    if relative not in pins:
        raise ValueError(f"Unpinned profile income input: {relative}")
    missing, changed = manifest.check({relative: pins[relative]})
    if missing or changed:
        raise ValueError(f"Profile income input missing={missing}, changed={changed}")
    rows = project(pq.read_table(INPUT).to_pylist())
    if {row["cpro"] for row in rows} != CPROS:
        raise ValueError("Standalone income province coverage changed")
    metadata = {"input_sha": pins[relative], "export_script_sha": ols.sha_file(__file__)}
    return pa.Table.from_pylist(rows, schema=SCHEMA), metadata


def verify(table, metadata):
    if not DATABASE.is_file():
        raise ValueError("Missing standalone profile income; run make profile-income")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        actual = con.execute("select * from municipal order by codigo, anyo").to_arrow_table()
        actual_meta = dict(con.execute("select key, value from export_meta").fetchall())
    if not actual.cast(SCHEMA).equals(table) or actual_meta != metadata:
        raise ValueError("Profile income stale or changed; run make profile-income")
    print(f"profile income: {table.num_rows} rows; exact pinned projection verified")


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
            con.execute("create or replace table municipal as select * from derived")
            con.execute("create or replace table export_meta(key varchar, value varchar)")
            con.executemany("insert into export_meta values (?, ?)", list(metadata.items()))
        tmp.replace(DATABASE)
    verify(table, metadata)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, duckdb.Error) as error:
        raise SystemExit(f"profile income: {error}") from error
