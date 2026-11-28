"""Export rental-register flow and tourist-band tables for the /alquiler/ page.

Projects the already-audited artifacts into a standalone presentation sidecar
(`data/processed/rental_registers.duckdb`):
  - `bcn_depositos_vs_stock`: Barcelona habitual deposit filings, cancellations,
    and net balance (INCASÒL, 2019–2025) alongside the annual change in declared
    rental contracts (SERPAVI, 2019–2024; NULL in 2025 where SERPAVI has not
    published yet).
  - `cat_vut_banda`: Catalonia INE VTE tourist-dwelling snapshots (2020-08 to
    2026-05).

--check verifies exact rows and input/exporter hashes without writing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import duckdb
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

OCCUPANCY_ARTIFACT = ROOT / "artifacts/occupancy_catalonia.json"
CONTRAST_ARTIFACT = ROOT / "artifacts/serpavi_deposit_contrast.json"
VUT_ARTIFACT = ROOT / "artifacts/vut_seasonal_deposits.json"
DATABASE = PROCESSED / "rental_registers.duckdb"

BCN_SCHEMA = pa.schema(
    [
        ("anyo", pa.int64()),
        ("altas_fianza", pa.int64()),
        ("bajas_fianza", pa.int64()),
        ("saldo_fianzas", pa.int64()),
        ("cambio_stock_declarado", pa.int64()),
    ]
)

VUT_SCHEMA = pa.schema(
    [
        ("periodo", pa.string()),
        ("viviendas_turisticas", pa.int64()),
    ]
)


def build_tables(occupancy: dict, contrast: dict, vut: dict) -> tuple[pa.Table, pa.Table]:
    history = occupancy["balances"]["history"]["barcelona_habitual"]
    reconciliation = contrast["reconciliation"]
    if not history:
        raise ValueError("Missing barcelona_habitual deposit history")

    bcn_rows = []
    for year_str in sorted(history, key=int):
        year = int(year_str)
        entry = history[year_str]
        rec = reconciliation.get(year_str)
        if rec is not None and rec["deposit_balance"] != entry["balance"]:
            raise ValueError(
                f"Barcelona {year} balance mismatch: "
                f"occupancy={entry['balance']} vs contrast={rec['deposit_balance']}"
            )
        bcn_rows.append(
            {
                "anyo": year,
                "altas_fianza": int(entry["entries"]),
                "bajas_fianza": int(entry["cancellations"]),
                "saldo_fianzas": int(entry["balance"]),
                "cambio_stock_declarado": (
                    int(rec["declared_stock_change"]) if rec is not None else None
                ),
            }
        )

    tourist_stock = vut["tourist_stock"]
    if not tourist_stock:
        raise ValueError("Missing Catalonia tourist_stock snapshots")

    vut_rows = []
    for period in sorted(tourist_stock):
        if not re.fullmatch(r"\d{4}-\d{2}", period):
            raise ValueError(f"Unexpected VTE snapshot period: {period!r}")
        vut_rows.append(
            {
                "periodo": period,
                "viviendas_turisticas": int(tourist_stock[period]),
            }
        )

    return (
        pa.Table.from_pylist(bcn_rows, schema=BCN_SCHEMA),
        pa.Table.from_pylist(vut_rows, schema=VUT_SCHEMA),
    )


def source_tables() -> tuple[pa.Table, pa.Table, dict[str, str]]:
    for path in (OCCUPANCY_ARTIFACT, CONTRAST_ARTIFACT, VUT_ARTIFACT):
        if not path.is_file():
            raise ValueError(f"Missing artifact {path.relative_to(ROOT)}; run make analysis")
    occupancy = json.loads(OCCUPANCY_ARTIFACT.read_text())
    contrast = json.loads(CONTRAST_ARTIFACT.read_text())
    vut = json.loads(VUT_ARTIFACT.read_text())
    bcn_table, vut_table = build_tables(occupancy, contrast, vut)
    metadata = {
        "occupancy_sha": ols.sha_file(OCCUPANCY_ARTIFACT),
        "contrast_sha": ols.sha_file(CONTRAST_ARTIFACT),
        "vut_sha": ols.sha_file(VUT_ARTIFACT),
        "export_script_sha": ols.sha_file(__file__),
    }
    return bcn_table, vut_table, metadata


def verify(bcn_table: pa.Table, vut_table: pa.Table, metadata: dict[str, str]) -> None:
    if not DATABASE.is_file():
        raise ValueError("Missing rental_registers.duckdb; run make rental-registers")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        actual_bcn = con.execute(
            "select * from bcn_depositos_vs_stock order by anyo"
        ).to_arrow_table()
        actual_vut = con.execute("select * from cat_vut_banda order by periodo").to_arrow_table()
        actual_meta = dict(con.execute("select key, value from export_meta").fetchall())
    if (
        not actual_bcn.cast(BCN_SCHEMA).equals(bcn_table)
        or not actual_vut.cast(VUT_SCHEMA).equals(vut_table)
        or actual_meta != metadata
    ):
        raise ValueError("rental_registers.duckdb stale or changed; run make rental-registers")
    print(
        f"rental registers: {bcn_table.num_rows} Barcelona deposit years, "
        f"{vut_table.num_rows} Catalonia VTE snapshots verified"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    bcn_table, vut_table, metadata = source_tables()
    if not args.check:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        tmp = DATABASE.with_suffix(".tmp.duckdb")
        if tmp.exists():
            tmp.unlink()
        with duckdb.connect(str(tmp)) as con:
            con.register("bcn_derived", bcn_table)
            con.register("vut_derived", vut_table)
            con.execute(
                "create or replace table bcn_depositos_vs_stock as select * from bcn_derived"
            )
            con.execute("create or replace table cat_vut_banda as select * from vut_derived")
            con.execute("create or replace table export_meta(key varchar, value varchar)")
            con.executemany("insert into export_meta values (?, ?)", list(metadata.items()))
        tmp.replace(DATABASE)
    verify(bcn_table, vut_table, metadata)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, duckdb.Error) as error:
        raise SystemExit(f"rental registers: {error}") from error
