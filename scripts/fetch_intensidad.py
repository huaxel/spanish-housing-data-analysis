"""Fetch INE Censo 2021 viviendas por intensidad de uso (table 59531).

The 2021 census replaced the classic principal/secundaria/vacía split
(field-agent based) with an objective classification from **electricity
consumption** over the year before 1-Jan-2021. This table publishes it at
national / CCAA / province / municipio grain as a static jaxiT3 CSV.

Rows per municipio (18 measures): Viviendas totales, Viviendas vacías
(below the minimum threshold), Mediana consumo anual (kWh), 15 consumption
bands. Municipios are named individually (3,139) or rolled into a
"Resto de {provincia}" aggregate (46, code ending 999) — NOT all 8,131
municipios are named (small ones aggregate; documented in the probe).

Verified 2026-10-06: national total 26,623,708, vacías 3,828,307 (14.4%),
municipal sum equals national. See
docs/explorations/censo_anual_probe.md §Viviendas por intensidad de uso.

Writes data/raw/censo2021_intensidad.csv (pinned) +
data/raw/parquet/censo2021_intensidad.parquet (municipio-grain rows).
"""

from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLE_ID = 59531
URL = f"https://www.ine.es/jaxi/files/tpx/csv_bd/{TABLE_ID}.csv"
ACCESSED = "2026-10-06"

# National anchors (2021): the table's own totals, pinned here.
TOTAL_2021 = 26_623_708
VACIAS_2021 = 3_828_307


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)


def parse_rows(csv_path: Path) -> list[dict]:
    """Municipio-grain rows: named municipios + Resto aggregates."""
    rows: list[dict] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rdr = csv.reader(f, delimiter="\t")
        next(rdr)  # header
        for x in rdr:
            if len(x) < 6:
                continue
            mun = x[3].strip()
            if not mun:
                continue  # national / CCAA / province rows skipped (municipio grain only)
            code, name = mun.split(" ", 1) if " " in mun else (mun, "")
            v = x[5].replace(".", "")
            rows.append(
                {
                    "codigo": code,
                    "municipio": name,
                    "provincia_cod": x[2].split()[0],
                    "medida": x[4],
                    "valor": int(v),
                }
            )
    return rows


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    raw_csv = RAW / "censo2021_intensidad.csv"
    download(URL, raw_csv)
    manifest.record(
        "data/raw/censo2021_intensidad.csv",
        {
            "url": URL,
            "operation": "Censo 2021 viviendas por intensidad de uso (59531)",
            "accessed": ACCESSED,
            "note": "static jaxi CSV; tab-separated, dot-thousands, BOM; 18 measures",
        },
    )
    rows = parse_rows(raw_csv)
    if not rows:
        raise SystemExit("intensidad: zero municipio rows — format changed?")

    # Guards: municipal sums must match the national anchors.
    tot = sum(r["valor"] for r in rows if r["medida"] == "Viviendas totales")
    vac = sum(r["valor"] for r in rows if r["medida"] == "Viviendas vacías")
    if tot != TOTAL_2021:
        raise SystemExit(f"intensidad: municipal total {tot:,} != {TOTAL_2021:,} — drift")
    if vac != VACIAS_2021:
        raise SystemExit(f"intensidad: municipal vacías {vac:,} != {VACIAS_2021:,} — drift")
    n_munis = len({r["codigo"] for r in rows})
    n_resto = sum(1 for r in rows if r["codigo"].endswith("999"))

    out = RAW / "parquet" / "censo2021_intensidad.parquet"
    pq.write_table(pa.Table.from_pylist(rows), out)
    manifest.record(
        "data/raw/parquet/censo2021_intensidad.parquet",
        {
            "url": URL,
            "operation": "Censo 2021 viviendas por intensidad de uso (59531)",
            "accessed": ACCESSED,
            "note": "municipio grain; named + Resto aggregates; 18 measures",
        },
    )
    print(
        f"intensidad: {len(rows)} rows, {n_munis} municipios ({n_resto} Resto), "
        f"total {tot:,} vacías {vac:,} ({vac / tot * 100:.1f}%)"
    )


if __name__ == "__main__":
    main()
