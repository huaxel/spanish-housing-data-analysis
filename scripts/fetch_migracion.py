"""Fetch EM foreign immigration flows by provincia (2008-2021).

- 24322: '[sexo]. [provincia]. [nacionalidad]. Flujo de inmigraciones
  procedentes del extranjero. [edad].' (positions swap for Nacional rows,
  skipped — provinces + Ceuta/Melilla only; Nacional summed locally).
Keeps sexo == Ambos sexos, all nacionalidad values (Total/Española/
Extranjero), edad == Total. Annual flows (FK_Periodo 28 only).
Writes data/raw/migracion_flujos.json + .parquet
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

TABLE_ID = 24322
ANNUAL = 28


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    payload = ine_api.get_table(TABLE_ID)
    if isinstance(payload, dict):
        raise SystemExit(f"EM {TABLE_ID}: {payload}")
    rows, skipped = [], []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        if len(parts) != 5 or parts[0] != "Ambos sexos":
            skipped.append(s["Nombre"])
            continue
        _sexo, terr, nac, medida, edad = parts
        if medida != "Flujo de inmigraciones procedentes del extranjero" or edad != "Total":
            skipped.append(s["Nombre"])
            continue
        if terr == "Total Nacional":
            skipped.append(s["Nombre"] + " (summed locally)")
            continue
        for x in s["Data"]:
            if x["FK_Periodo"] != ANNUAL:
                skipped.append(f"{s['Nombre']} periodo={x['FK_Periodo']}")
                continue
            rows.append(
                {
                    "provincia": terr,
                    "anyo": x["Anyo"],
                    "nacionalidad": nac,
                    "flujo": x["Valor"],
                }
            )
    if not rows:
        raise SystemExit("migracion: zero rows — format changed?")
    rows.sort(key=lambda r: (r["provincia"], r["nacionalidad"], r["anyo"]))
    pq.write_table(pa.Table.from_pylist(rows), RAW / "parquet" / "migracion_flujos.parquet")
    (RAW / "migracion_flujos.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    manifest.record(
        "data/raw/migracion_flujos.json",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "EM flujos",
            "accessed": date.today().isoformat(),
        },
    )
    manifest.record(
        "data/raw/parquet/migracion_flujos.parquet",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "EM flujos",
            "accessed": date.today().isoformat(),
            "note": "Ambos sexos, Total edad; annual (FK_Periodo 28) only",
        },
    )
    yrs = sorted({r["anyo"] for r in rows})
    print(f"migracion: {len(rows)} rows, {yrs[0]}-{yrs[-1]}; skipped {len(skipped)}")


if __name__ == "__main__":
    main()
