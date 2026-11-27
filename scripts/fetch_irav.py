"""Fetch the INE rent-update reference index (IRAV, operation 481, table 72975).

The *Índice de Referencia de Arrendamientos de Vivienda* is the statutory
index that Ley 12/2023 substitutes for the IPC when capping the annual rent
update of an existing residential lease. INE publishes it monthly and
national only, and the public table is a **rolling 24-month window** (table
metadata: first published period 2024-M11; the 2026-11 release still carries
exactly 24 months). The single published variable is the annual variation
(percent): the table has no index level, and operation 481 has exactly one
table and one data type (inspected through the INE MCP five-step flow on
2026-11-27).

Semantics: a *reference for contract updates*, not an observed market rent,
not a mean of signed contracts and not a price index of new lettings. It is
therefore reported next to — never instead of — the INCASÒL contractual-rent
series that the Catalonia evaluation uses, and it carries no territorial
breakdown: the national figure applies to every CCAA that applies the cap.

Writes data/raw/irav_72975.json (byte evidence) +
data/raw/parquet/irav.parquet. Use --offline to rebuild only from the pinned
JSON; --check to verify pins and exact derivation without writing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

TABLE_ID = 72975
RAW_JSON = RAW / "irav_72975.json"
PARQUET = RAW / "parquet" / "irav.parquet"
SCHEMA = pa.schema([("anyo", pa.int16()), ("mes", pa.int8()), ("irav_pct", pa.float64())])
SERIES_NAME = ("Total Nacional", "Índice general", "Variación anual")
MONTHS = set(range(1, 13))


def parse(payload: list[dict]) -> list[dict]:
    """Flatten the single national series into (anyo, mes, irav_pct) rows."""
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"IRAV {TABLE_ID}: unexpected payload {type(payload).__name__}")
    rows: list[dict] = []
    for series in payload:
        if tuple(ine_api.split_nombre(series["Nombre"])) != SERIES_NAME:
            raise ValueError(f"IRAV: unexpected series {series['Nombre']!r}")
        for obs in series["Data"]:
            mes = int(obs["FK_Periodo"])
            if mes not in MONTHS:
                raise ValueError(f"IRAV: unexpected period code {mes} (expected a month)")
            rows.append({"anyo": int(obs["Anyo"]), "mes": mes, "irav_pct": float(obs["Valor"])})
    rows.sort(key=lambda r: (r["anyo"], r["mes"]))
    keys = {(r["anyo"], r["mes"]) for r in rows}
    if len(keys) != len(rows):
        raise ValueError("IRAV: duplicate month observations")
    # INE publishes a rolling window, so the first month moves every release;
    # assert contiguity and a plausible length instead of a fixed start date.
    idx = [r["anyo"] * 12 + r["mes"] for r in rows]
    if len(rows) < 2 or idx[-1] - idx[0] != len(rows) - 1:
        raise ValueError(f"IRAV: expected a contiguous monthly window, got {len(rows)} rows")
    return rows


def pinned_rows() -> list[dict]:
    if not RAW_JSON.is_file():
        raise SystemExit(f"IRAV: {RAW_JSON.relative_to(ROOT)} missing — run without --offline")
    return parse(json.loads(RAW_JSON.read_text(encoding="utf-8")))


def write_parquet(rows: list[dict]) -> None:
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), PARQUET)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        rows = pinned_rows()
        if pq.read_table(PARQUET).to_pylist() != rows:
            raise SystemExit("IRAV: parquet stale vs parser + pinned input")
        last = rows[-1]
        print(
            f"irav: {len(rows)} months of annual variation; pins verified "
            f"(last {last['anyo']}-{last['mes']:02d} = {last['irav_pct']:+.2f}%)"
        )
        return

    if not args.offline:
        payload = ine_api.get_table(TABLE_ID)
        if isinstance(payload, dict):
            raise SystemExit(f"IRAV {TABLE_ID}: {payload}")
        rows = parse(payload)  # validate before replacing the pinned copy
        if len(rows) < 12:
            raise SystemExit(
                f"IRAV: only {len(rows)} months returned; the published window should "
                "hold at least a year — refusing to replace the pinned copy"
            )
        tmp = RAW_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(RAW_JSON)
        manifest.record(
            str(RAW_JSON.relative_to(ROOT)),
            {
                "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
                "publisher": "INE · Índice de Referencia de Arrendamientos de Vivienda (IRAV)",
                "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=72975",
                "accessed": date.today().isoformat(),
                "note": (
                    "National monthly annual variation, rolling 24-month window; "
                    "statutory rent-update reference (Ley 12/2023)"
                ),
            },
        )
    rows = pinned_rows()
    write_parquet(rows)
    manifest.record(
        str(PARQUET.relative_to(ROOT)),
        {
            "publisher": "INE · Índice de Referencia de Arrendamientos de Vivienda (IRAV)",
            "accessed": date.today().isoformat(),
            "note": "Derived from pinned irav_72975.json by fetch_irav.py",
        },
    )
    last = rows[-1]
    print(
        f"irav: {len(rows)} months ({rows[0]['anyo']}-{rows[0]['mes']:02d} → "
        f"{last['anyo']}-{last['mes']:02d}); latest annual variation {last['irav_pct']:+.2f}%"
    )


if __name__ == "__main__":
    main()
