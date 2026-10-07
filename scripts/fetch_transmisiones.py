"""Fetch INE Transmisiones: dwelling transactions by CCAA/provincia (jaxiT3 6155).

Layout: Total Nacional | CCAA ('01 Andalucía'..'18 Ceuta','19 Melilla') |
Provincias | Régimen y estado | Periodo | Total. Categories: Total, nueva,
usada, libre, protegida. Annual 2007-. Dots are thousands separators.
Writes data/raw/transmisiones.csv + .parquet
"""

from __future__ import annotations

import re
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://www.ine.es/jaxiT3/files/t/csv_bd/6155.csv"
RAW_CSV = RAW / "transmisiones.csv"
RAW_PARQUET = RAW / "parquet" / "transmisiones.parquet"
CATS = {
    "Viviendas: Total": "total",
    "Vivienda nueva": "nueva",
    "Vivienda usada": "usada",
    "Vivienda libre": "libre",
    "Vivienda protegida": "protegida",
}


def strip_code(s: str) -> str:
    return re.sub(r"^\d+\s+", "", s or "").strip()


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=180) as resp:  # noqa: S310 (pinned host)
            tmp.write(resp.read())
        tmp_path = tmp.name
    Path(tmp_path).replace(RAW_CSV)
    _, rows = csvx.read_csv_records(RAW_CSV, delimiter="\t")
    out, skipped = [], []
    for r in rows:
        if r["Régimen y estado"] not in CATS:
            skipped.append(r["Régimen y estado"])
            continue
        ccaa = strip_code(r["Comunidades y Ciudades Autónomas"])
        prov = strip_code(r["Provincias"])
        terr = prov or ccaa or "Total Nacional"
        out.append(
            {
                "territorio": terr,
                "grain": "provincia" if prov else ("ccaa" if ccaa else "nacional"),
                "categoria": CATS[r["Régimen y estado"]],
                "anyo": int(r["Periodo"]),
                "transacciones": int(r["Total"].replace(".", "")),
            }
        )
    if not out:
        raise SystemExit("transmisiones: zero rows — format changed?")
    n = csvx.write_parquet(out, RAW_PARQUET)
    manifest.record(
        "data/raw/transmisiones.csv",
        {
            "url": URL,
            "publisher": "INE (registradores)",
            "operation": "Transmisiones",
            "accessed": date.today().isoformat(),
        },
    )
    manifest.record(
        "data/raw/parquet/transmisiones.parquet",
        {
            "url": URL,
            "publisher": "INE (registradores)",
            "operation": "Transmisiones",
            "accessed": date.today().isoformat(),
        },
    )
    print(f"transmisiones: {n} rows; skipped {len(set(skipped))} categories")


if __name__ == "__main__":
    main()
