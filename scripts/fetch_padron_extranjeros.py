"""Fetch padrón foreign stock by provincia (1998-2022): the shift-share base.

Static jaxi (t20/e245/p08/l0/03005): TOTAL EXTRANJEROS x Ambos sexos margin
only (full nationality detail stays in the pinned raw). Annual stocks —
the Bartik *shares* half; the surge-by-origin half is still queued
(see identification memo).
Writes data/raw/padron_extranjeros.csv + .parquet
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://www.ine.es/jaxi/files/_px/csv_bd/t20/e245/p08/l0/03005.csv"
RAW_CSV = RAW / "padron_extranjeros.csv"
RAW_PARQUET = RAW / "parquet" / "padron_extranjeros.parquet"
RAW_DETAIL = RAW / "parquet" / "padron_extranjeros_origen.parquet"


def num(v: str) -> int | None:
    v = (v or "").strip()
    if v in ("", "..", "."):
        return None
    return int(v.replace(".", "").replace(",", ""))


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=300) as resp:  # noqa: S310 (pinned host)
            tmp.write(resp.read())
        tmp_path = tmp.name
    Path(tmp_path).replace(RAW_CSV)
    _, rows = csvx.read_csv_records(RAW_CSV, delimiter="\t")
    out, detail = [], []
    for r in rows:
        v = num(r["Total"])
        if v is None:
            continue
        if r["Provincias"] == "TOTAL ESPAÑA":
            cpro, name = "00", "Total España"
        else:
            cpro, _, name = r["Provincias"].partition(" ")
        detail.append(
            {
                "nacionalidad": r["Nacionalidad"],
                "cpro": cpro,
                "provincia": name,
                "sexo": r["Sexo"],
                "anyo": int(r["Periodo"]),
                "personas": v,
            }
        )
        if r["Nacionalidad"] != "TOTAL EXTRANJEROS" or r["Sexo"] != "Ambos sexos":
            continue
        if r["Provincias"] == "TOTAL ESPAÑA":
            continue
        out.append({"cpro": cpro, "provincia": name, "anyo": int(r["Periodo"]), "extranjeros": v})
    if not out:
        raise SystemExit("padron_extranjeros: zero rows — format changed?")
    n = csvx.write_parquet(out, RAW_PARQUET)
    nd = csvx.write_parquet(detail, RAW_DETAIL)
    manifest.record(
        "data/raw/padron_extranjeros.csv",
        {"url": URL, "publisher": "INE", "operation": "Padrón e245", "accessed": "2026-10-06"},
    )
    manifest.record(
        "data/raw/parquet/padron_extranjeros.parquet",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "Padrón e245",
            "accessed": "2026-10-06",
            "note": "TOTAL EXTRANJEROS x Ambos sexos only; full detail in raw CSV",
        },
    )
    manifest.record(
        "data/raw/parquet/padron_extranjeros_origen.parquet",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "Padrón e245",
            "accessed": "2026-10-06",
            "note": "all 137 nacionalidades x sexo (rollups duplicate leaves)",
        },
    )
    yrs = sorted({r["anyo"] for r in out})
    print(f"padron_extranjeros: {n} margin + {nd} detail rows, {yrs[0]}-{yrs[-1]}")


if __name__ == "__main__":
    main()
