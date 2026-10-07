"""Fetch 2011 census household size x tenure by CCAA/provincia (jaxi p01/02015).

Layout: TN | CCAA | Provincias | Tamaño del hogar | Régimen de tenencia | Total.
Tenures: propia pagada / con hipoteca / herencia / alquilada / cedida / otra.
Missing markers: '', '..', '.' (single dot!) — all kept missing. Dots are
thousands separators.
Writes data/raw/censo2011_tenencia.csv + .parquet
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://www.ine.es/jaxi/files/_px/csv_bd/t20/e244/hogares/p01/02015.csv"
RAW_CSV = RAW / "censo2011_tenencia.csv"
RAW_PARQUET = RAW / "parquet" / "censo2011_tenencia.parquet"


def num(v: str) -> int | None:
    v = (v or "").strip()
    if v in ("", "..", "."):
        return None
    return int(v.replace(".", "").replace(",", ""))


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=180) as resp:  # noqa: S310 (pinned host)
            tmp.write(resp.read())
        tmp_path = tmp.name
    Path(tmp_path).replace(RAW_CSV)
    _, rows = csvx.read_csv_records(RAW_CSV, delimiter="\t")
    out = [
        {
            "ccaa": r["Comunidades y Ciudades Autónomas"],
            "provincia": r["Provincias"],
            "tamano": r["Tamaño del hogar"],
            "tenencia": r["Régimen de tenencia"],
            "hogares": num(r["Total"]),
        }
        for r in rows
    ]
    if not out:
        raise SystemExit("tenencia: zero rows — format changed?")
    n = csvx.write_parquet([r for r in out if r["hogares"] is not None], RAW_PARQUET)
    manifest.record(
        "data/raw/censo2011_tenencia.csv",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "CENSOPV 2011",
            "accessed": date.today().isoformat(),
        },
    )
    manifest.record(
        "data/raw/parquet/censo2011_tenencia.parquet",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "CENSOPV 2011",
            "accessed": date.today().isoformat(),
            "note": "missing cells dropped",
        },
    )
    print(f"tenencia: {n} valued rows ({len(out) - n} missing)")


if __name__ == "__main__":
    main()
