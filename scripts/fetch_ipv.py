"""Fetch INE IPV medias anuales por CCAA (Tempus3 table 80271).

Operation: IPV (Id 15), "Índices por CCAA: general, vivienda nueva y de
segunda mano. Medias anuales". Base 2015 (re-basing to 2025 in progress —
see docs/methods.md; do NOT splice vintages silently).
Series Nombre pattern: "{Territorio}. Media anual. {General|Vivienda nueva|
Vivienda segunda mano}. [+ Variación anual ...]" — only index levels kept.
Writes data/raw/ipv_ccaa_anual.json (raw API) + data/raw/parquet/ipv_ccaa_anual.parquet
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLE_ID = 80271
RAW_JSON = RAW / "ipv_ccaa_anual.json"
RAW_PARQUET = RAW / "parquet" / "ipv_ccaa_anual.parquet"

INDEX_TYPES = {"General", "Vivienda nueva", "Vivienda segunda mano"}


def parse(payload: list[dict]) -> tuple[list[dict], list[str]]:
    rows, skipped = [], []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        # e.g. ['Nacional', 'Media anual', 'General']
        if len(parts) != 3 or parts[1] != "Media anual" or parts[2] not in INDEX_TYPES:
            skipped.append(s["Nombre"])
            continue
        for d in s["Data"]:
            rows.append(
                {
                    "territorio": parts[0],
                    "tipo_vivienda": parts[2],
                    "anyo": d["Anyo"],
                    "indice": d["Valor"],
                    "serie_cod": s["COD"],
                }
            )
    return rows, skipped


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    payload = ine_api.get_table(TABLE_ID)
    RAW_JSON.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    rows, skipped = parse(payload)
    if not rows:
        raise SystemExit("IPV parse produced zero rows — upstream format changed?")
    import pyarrow as pa

    table = pa.Table.from_pylist(rows)
    con = duckdb.connect()
    con.register("ipv_rows", table)
    con.execute(f"COPY (SELECT * FROM ipv_rows) TO '{RAW_PARQUET}' (FORMAT PARQUET)")
    manifest.record(
        "data/raw/ipv_ccaa_anual.json",
        {"api": f"wstempus/DATOS_TABLA/{TABLE_ID}", "operation": "IPV", "accessed": "2026-10-05"},
    )
    manifest.record(
        "data/raw/parquet/ipv_ccaa_anual.parquet",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "IPV",
            "accessed": "2026-10-05",
            "note": "parsed index levels only",
        },
    )
    print(
        f"ipv: {len(rows)} rows, {len(set(r['territorio'] for r in rows))} territorios; "
        f"skipped {len(skipped)} non-index series "
        f"(e.g. {skipped[:2] if skipped else []})"
    )


if __name__ == "__main__":
    main()
