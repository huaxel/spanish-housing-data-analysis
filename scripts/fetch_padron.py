"""Fetch INE Padrón (Revisión padronal, DPOP) población por provincia (table 2852)
and CCAA (table 2853). Annual 1996–2021.

CAVEAT (docs/methods.md): the Revisión del Padrón series ends 2021; from 2022
INE publishes Cifras de Población. 2022+ is intentionally missing until the
successor table is pinned — do not forward-fill.
Series Nombre: "{Territorio}. {Total|Hombres|Mujeres}. Total habitantes. Personas."
Writes data/raw/padron_provincia.json + .parquet (and _ccaa variants).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402
import pyarrow as pa  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLES = {2852: "provincia", 2853: "ccaa"}
SEXOS = {"Total", "Hombres", "Mujeres"}


def parse(payload: list[dict]) -> tuple[list[dict], list[str]]:
    rows, skipped = [], []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        if len(parts) != 4 or parts[1] not in SEXOS or parts[2] != "Total habitantes":
            skipped.append(s["Nombre"])
            continue
        for d in s["Data"]:
            rows.append(
                {
                    "territorio": parts[0],
                    "sexo": parts[1],
                    "anyo": d["Anyo"],
                    "poblacion": int(d["Valor"]),
                    "serie_cod": s["COD"],
                }
            )
    return rows, skipped


def fetch_one(table_id: int, grain: str) -> None:
    payload = ine_api.get_table(table_id)
    raw_json = RAW / f"padron_{grain}.json"
    raw_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    rows, skipped = parse(payload)
    if not rows:
        raise SystemExit(f"padron {grain}: zero rows — upstream format changed?")
    totals = [r for r in rows if r["sexo"] == "Total"]
    out = RAW / "parquet" / f"padron_{grain}.parquet"
    con = duckdb.connect()
    con.register("padron_rows", pa.Table.from_pylist(totals))
    con.execute(f"COPY (SELECT * FROM padron_rows) TO '{out}' (FORMAT PARQUET)")
    manifest.record(
        f"data/raw/padron_{grain}.json",
        {"api": f"wstempus/DATOS_TABLA/{table_id}", "operation": "DPOP", "accessed": "2026-10-05"},
    )
    manifest.record(
        f"data/raw/parquet/padron_{grain}.parquet",
        {
            "api": f"wstempus/DATOS_TABLA/{table_id}",
            "operation": "DPOP",
            "accessed": "2026-10-05",
            "note": "sexo=Total only",
        },
    )
    print(f"padron {grain}: {len(totals)} rows; skipped {len(skipped)} series")


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    for table_id, grain in TABLES.items():
        fetch_one(table_id, grain)


if __name__ == "__main__":
    main()
