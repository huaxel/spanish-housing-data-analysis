"""Fetch INE ECV renta media por hogar por CCAA (Tempus3 table 9949).

Operation ECV. Series: '{Terr}. {Renta neta media por hogar |
Renta media por hogar (con alquiler imputado)}. Base 2013.' (2008-).
Table 49146 is byte-identical content (verified 2026-10-06) — not fetched.

TIMING NOTE (methods §1): ECV survey year Y reports incomes of calendar
year Y-1. The parser stores renta_anyo = Anyo - 1. Never join survey year
to price year without this lag.
Writes data/raw/renta_hogar_ccaa.json + .parquet (both indicators).
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

TABLE_ID = 9949
RAW_JSON = RAW / "renta_hogar_ccaa.json"
RAW_PARQUET = RAW / "parquet" / "renta_hogar_ccaa.parquet"
INDICATORS = {
    "Renta neta media por hogar": "neta",
    "Renta media por hogar (con alquiler imputado)": "con_alquiler_imputado",
}


def parse(payload: list[dict]) -> tuple[list[dict], list[str]]:
    rows, skipped = [], []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        if len(parts) != 3 or parts[2] != "Base 2013" or parts[1] not in INDICATORS:
            skipped.append(s["Nombre"])
            continue
        for d in s["Data"]:
            rows.append(
                {
                    "territorio": parts[0],
                    "indicador": INDICATORS[parts[1]],
                    "renta_anyo": d["Anyo"] - 1,  # ECV reports previous-year income
                    "encuesta_anyo": d["Anyo"],
                    "renta_eur": d["Valor"],
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
        raise SystemExit("renta parse: zero rows — upstream format changed?")
    neta = {r["renta_anyo"] for r in rows if r["indicador"] == "neta"}
    print(
        f"renta: {len(rows)} rows, neta years {min(neta)}–{max(neta)}, "
        f"skipped {len(skipped)} series"
    )
    pq.write_table(pa.Table.from_pylist(rows), RAW_PARQUET)
    manifest.record(
        "data/raw/renta_hogar_ccaa.json",
        {"api": f"wstempus/DATOS_TABLA/{TABLE_ID}", "operation": "ECV", "accessed": "2026-10-06"},
    )
    manifest.record(
        "data/raw/parquet/renta_hogar_ccaa.parquet",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "ECV",
            "accessed": "2026-10-06",
            "note": "renta_anyo = encuesta_anyo - 1",
        },
    )


if __name__ == "__main__":
    main()
