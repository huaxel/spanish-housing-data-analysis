"""Fetch 2011 census dwelling vintage by provincia (jaxi p01/01011a).

Layout: Tipo de vivienda | TN | CCAA | Provincias | Año de construcción
(agregado) | Total. Types 2.1 principales / 2.21 secundarias / 2.22 vacias.
Max band 'De 2002 a 2011' (2011 census — vintage of the boom, not 2021).
'..' = suppressed, kept missing.
Writes data/raw/censo2011_vintage.csv + .parquet
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://www.ine.es/jaxi/files/_px/csv_bd/t20/e244/viviendas/p01/01011a.csv"
RAW_CSV = RAW / "censo2011_vintage.csv"
RAW_PARQUET = RAW / "parquet" / "censo2011_vintage.parquet"
TIPOS = {
    "2.1 Total viviendas principales": "principal",
    "2.21 Viviendas secundarias": "secundaria",
    "2.22 Viviendas vacias": "vacia",
}


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
        if r["Tipo de vivienda"] not in TIPOS:
            skipped.append(r["Tipo de vivienda"])
            continue
        v = (r["Total"] or "").strip()
        # Spanish thousands use dots here ('18.083.692'); '..' = suppressed.
        num = int(v.replace(".", "").replace(",", "")) if v not in ("", "..") else None
        out.append(
            {
                "ccaa": r["Comunidades y Ciudades Autónomas"],
                "provincia": r["Provincias"],
                "tipo": TIPOS[r["Tipo de vivienda"]],
                "vintage": r["Año de construcción (agregado) del edificio"],
                "viviendas": num,
            }
        )
    if not out:
        raise SystemExit("vintage: zero rows — format changed?")
    n = csvx.write_parquet(out, RAW_PARQUET)
    manifest.record(
        "data/raw/censo2011_vintage.csv",
        {"url": URL, "publisher": "INE", "operation": "CENSOPV 2011", "accessed": "2026-10-06"},
    )
    manifest.record(
        "data/raw/parquet/censo2011_vintage.parquet",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "CENSOPV 2011",
            "accessed": "2026-10-06",
            "note": "'..' suppressed kept missing",
        },
    )
    print(f"vintage: {n} rows; skipped types {sorted(set(skipped))}")


if __name__ == "__main__":
    main()
