"""Fetch ECH annual households by provincia (2014-2020).

ECH "Hogares: Resultados por provincias" (t20/p274/serie/def/p03/l0):
03003 = provincia x tipo de hogar x habitaciones. Keeps the Total x Total
margin only (thousands of households -> units). ECH ended 2020; ECP
hogares continue from 2021 (definitional seam documented in methods).
Writes data/raw/ech_hogares.csv + .parquet
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://www.ine.es/jaxi/files/_px/csv_bd/t20/p274/serie/def/p03/l0/03003.csv"
RAW_CSV = RAW / "ech_hogares.csv"
RAW_PARQUET = RAW / "parquet" / "ech_hogares.parquet"


def num(v: str) -> float | None:
    """Spanish decimals with mixed thousands marks ('18.689,8' and '18,689.8')."""
    v = (v or "").strip()
    if v in ("", "..", "."):
        return None
    if "." in v and "," in v:
        # Last separator is the decimal mark.
        if v.rfind(".") > v.rfind(","):
            v = v.replace(",", "")
        else:
            v = v.replace(".", "").replace(",", ".")
    elif v.count(",") == 1 and len(v.split(",")[1]) <= 2:
        v = v.replace(",", ".")
    else:
        v = v.replace(",", "")
    return float(v)


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
            "provincia": r["Provincias"],
            "anyo": int(r["periodo"]),
            "hogares": round(num(r["Total"]) * 1000),
        }
        for r in rows
        if r["Tipo de hogar"] == "Total (tipo de hogar)"
        and r["Número de habitaciones de la vivienda"] == "Total"
        and r["Provincias"] != "Total"
        and num(r["Total"]) is not None
    ]
    if not out:
        raise SystemExit("ECH hogares: zero rows — format changed?")
    n = csvx.write_parquet(out, RAW_PARQUET)
    manifest.record(
        "data/raw/ech_hogares.csv",
        {"url": URL, "publisher": "INE", "operation": "ECH", "accessed": "2026-10-06"},
    )
    manifest.record(
        "data/raw/parquet/ech_hogares.parquet",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "ECH",
            "accessed": "2026-10-06",
            "note": "Total x Total margin only; thousands -> units",
        },
    )
    yrs = sorted({r["anyo"] for r in out})
    print(f"ECH hogares: {n} rows, {yrs[0]}-{yrs[-1]}")


if __name__ == "__main__":
    main()
