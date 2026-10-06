"""Fetch Censo Anual de Población provincial population (INE table 68521).

Why: `mart_provincia_anual` ends in 2021 because provincial ECP population
(table 56945) is volume-blocked on the Tempus3 API. The register-based
Censo Anual de Población (the replacement for the decennial census)
publishes provincial population 2021–2025 as a **static CSV** on the jaxiT3
export path — no API call, so the block does not apply.

Source: `https://www.ine.es/jaxiT3/files/t/es/csv_bd/68521.csv`
(Población por sexo, edad (grupos quinquenales) y país de nacionalidad),
tab-separated, dot-thousands, UTF-8 BOM. ~208 MB / 2.47M rows; only the
`Total × Todas las edades × Total` margin is retained (same pattern as the
ECP fetch).

Verified 2026-10-06: 2025 national 49,128,297 = mart ECP exact; 17 CCAA
2025 census-vs-ECP all 0.0%; 2021 province-vs-padrón mean |Δ| 0.17%.
The Censo Anual and ECP are the same register-based series, so extending
the provincia mart to 2025 keeps one seam (padrón→registral at 2021).

Writes data/raw/censo_anual_pob_prov.json (raw CSV, pinned) +
data/raw/parquet/censo_anual_pob_prov.parquet (margin rows).
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

TABLE_ID = 68521
URL = f"https://www.ine.es/jaxiT3/files/t/es/csv_bd/{TABLE_ID}.csv"
MARGIN = ("Total", "Todas las edades", "Total")  # Sexo, Edad, País de nacionalidad
ACCESSED = "2026-10-06"


def download(url: str, dest: Path) -> None:
    """Download to a temp file and atomically replace; streamed, no in-RAM copy."""
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
    """Keep the Total × Todas las edades × Total margin for provinces + CCAA."""
    rows: list[dict] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rdr = csv.reader(f, delimiter="\t")
        # header: Total Nacional | CCAA | Provincias | Sexo | Edad | País | Periodo | Total
        for x in rdr:
            if len(x) < 8:
                continue
            if (x[3], x[4], x[5]) != MARGIN:
                continue
            prov = x[2].strip()
            ccaa = x[1].strip()
            if not prov and not ccaa:
                continue  # Nacional rows come from the CCAA mart (ECP)
            # Strip the leading numeric code: '01 Andalucía' -> 'Andalucía'
            name = prov if prov else ccaa
            parts = name.split(" ", 1)
            code, terr = (parts[0], parts[1]) if len(parts) == 2 else ("", name)
            if not code.isdigit():
                code = ""
            rows.append(
                {
                    "granularity": "provincia" if prov else "ccaa",
                    "code": code,
                    "territorio": terr,
                    "anyo": int(x[6]),
                    "poblacion": int(x[7].replace(".", "")),
                }
            )
    return rows


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    raw_csv = RAW / f"censo_anual_{TABLE_ID}.csv"
    download(URL, raw_csv)
    manifest.record(
        f"data/raw/censo_anual_{TABLE_ID}.csv",
        {
            "url": URL,
            "operation": "Censo Anual de Población (68521)",
            "accessed": ACCESSED,
            "note": "static jaxiT3 CSV export; 208 MB; tab-separated, dot-thousands, BOM",
        },
    )
    rows = parse_rows(raw_csv)
    if not rows:
        raise SystemExit("censo anual: zero margin rows — format changed?")
    # Guard: national total via provinces must match the known 2025 figure.
    prov_2025 = {
        r["code"]: r["poblacion"]
        for r in rows
        if r["granularity"] == "provincia" and r["anyo"] == 2025
    }
    total_2025 = sum(prov_2025.values())
    if total_2025 != 49_128_297:
        raise SystemExit(
            f"censo anual 2025 provincial sum {total_2025:,} != 49,128,297 (mart ECP) — drift?"
        )
    out = RAW / "parquet" / "censo_anual_pob_prov.parquet"
    pq.write_table(pa.Table.from_pylist(rows), out)
    manifest.record(
        "data/raw/parquet/censo_anual_pob_prov.parquet",
        {
            "url": URL,
            "operation": "Censo Anual de Población (68521)",
            "accessed": ACCESSED,
            "note": "Total × Todas las edades × Total margin only; 2021-2025",
        },
    )
    n_prov = sum(1 for r in rows if r["granularity"] == "provincia")
    print(f"censo anual: {len(rows)} margin rows ({n_prov} province × 5 years)")


if __name__ == "__main__":
    main()
