"""Fetch INE 2011 census dwelling types by municipio (CENSOPV table 3456).

Pattern '{Municipio}. {Tipo}. Total habitantes. Vivienda.' with Tipo in
Total viviendas / Vivienda familiar / principal / no principal / secundaria /
vacía / colectiva. Municipalities > 2,000 inhabitants, 2011 only.
Writes data/raw/censo2011_municipios.json + .parquet (all of Spain; Madrid
cut happens at build against the municipal valor list).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLE_ID = 3456
TIPOS = {
    "Total viviendas",
    "Vivienda familiar",
    "Vivienda principal",
    "Vivienda no principal",
    "Vivienda secundaria",
    "Vivienda vacía",
    "Vivienda colectiva",
}


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    payload = ine_api.get_table(TABLE_ID)
    if isinstance(payload, dict):
        raise SystemExit(f"CENSOPV 3456: {payload}")
    (RAW / "censo2011_municipios.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    rows, skipped = [], []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        if len(parts) != 4 or parts[1] not in TIPOS:
            skipped.append(s["Nombre"])
            continue
        for x in s["Data"]:
            rows.append(
                {
                    "municipio": parts[0],
                    "tipo": parts[1],
                    "anyo": x["Anyo"],
                    "viviendas": int(x["Valor"]),
                    "serie_cod": s["COD"],
                }
            )
    if not rows:
        raise SystemExit("censo2011: zero rows — format changed?")
    out = RAW / "parquet" / "censo2011_municipios.parquet"
    pq.write_table(pa.Table.from_pylist(rows), out)
    manifest.record(
        "data/raw/censo2011_municipios.json",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "CENSOPV",
            "accessed": date.today().isoformat(),
        },
    )
    manifest.record(
        "data/raw/parquet/censo2011_municipios.parquet",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "CENSOPV",
            "accessed": date.today().isoformat(),
        },
    )
    munis = len({r["municipio"] for r in rows})
    print(f"censo2011: {len(rows)} rows, {munis} municipios; skipped {len(skipped)}")


if __name__ == "__main__":
    main()
