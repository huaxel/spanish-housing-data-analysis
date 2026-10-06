"""Fetch INE IPC general index (base 2021): CCAA + Nacional monthly.

- 76136: '{Terr}. Índice general. Índice.' monthly, 2002- (CCAA + Nacional
  + Ceuta/Melilla separately). Index levels only — variations recomputed
  locally, never pinned.
Keeps monthly rows (territorio, anyo, mes, ipc); marts annualise.
Writes data/raw/ipc_ccaa.json + .parquet
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLE_ID = 76136
MONTHS = set(range(1, 13))


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    payload = ine_api.get_table(TABLE_ID)
    if isinstance(payload, dict):
        raise SystemExit(f"IPC {TABLE_ID}: {payload}")
    rows, skipped = [], []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        if len(parts) != 3 or parts[1] != "Índice general" or parts[2] != "Índice":
            skipped.append(s["Nombre"])
            continue
        for x in s["Data"]:
            if x["FK_Periodo"] not in MONTHS:
                skipped.append(f"{s['Nombre']} periodo={x['FK_Periodo']}")
                continue
            rows.append(
                {
                    "territorio": parts[0],
                    "anyo": x["Anyo"],
                    "mes": x["FK_Periodo"],
                    "ipc": x["Valor"],
                }
            )
    if not rows:
        raise SystemExit("IPC: zero rows — format changed?")
    rows.sort(key=lambda r: (r["territorio"], r["anyo"], r["mes"]))
    pq.write_table(pa.Table.from_pylist(rows), RAW / "parquet" / "ipc_ccaa.parquet")
    (RAW / "ipc_ccaa.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    manifest.record(
        "data/raw/ipc_ccaa.json",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "IPC general",
            "accessed": "2026-10-06",
        },
    )
    manifest.record(
        "data/raw/parquet/ipc_ccaa.parquet",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "IPC general",
            "accessed": "2026-10-06",
            "note": "general index levels only; base 2021",
        },
    )
    print(f"ipc: {len(rows)} monthly rows; skipped {len(skipped)} series")


if __name__ == "__main__":
    main()
