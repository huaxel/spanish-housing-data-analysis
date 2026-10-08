"""Fetch Sevilla's 2024 second-hand housing offer-price workbook.

Official Ayuntamiento yearbook table 7.3.9, mirrored by FEMAS. This is
monthly asking/offer price (EUR/m²) from Fotocasa and Idealista, not a
transaction-price series. Keep publishers and their different geographies
separate; do not join the 11 Fotocasa districts to Idealista's 17 zones.
"""

from __future__ import annotations

import sys
import urllib.request
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import xlrd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = (
    "https://www.femas.es/servicios/servicio-de-estadistica/datos-estadisticos/"
    "anuarios/anuario-estadistico-de-la-ciudad-de-sevilla-2025/"
    "tablas/capitulo-7/7.3/7-3-9.xls"
)
RAW_XLS = RAW / "sevilla_anuario_2025_7_3_9.xls"
RAW_PARQUET = RAW / "parquet" / "sevilla_oferta_zona_2024.parquet"
MONTHS = [
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
]
EXPECTED_ROWS = {"Fotocasa": 11, "Idealista": 17}


def parse_workbook(contents: bytes) -> list[dict[str, object]]:
    book = xlrd.open_workbook(file_contents=contents, on_demand=True)
    if book.sheet_names() != ["HOJA"]:
        raise SystemExit(f"Unexpected yearbook sheets: {book.sheet_names()}")
    sheet = book.sheet_by_name("HOJA")
    title = str(sheet.cell_value(0, 0))
    if "AÑO 2024" not in title.upper():
        raise SystemExit(f"Unexpected yearbook title: {title}")

    provider: str | None = None
    header_seen = False
    rows: list[dict[str, object]] = []
    counts = {name: 0 for name in EXPECTED_ROWS}
    for row_idx in range(sheet.nrows):
        first = str(sheet.cell_value(row_idx, 0)).strip()
        if first in EXPECTED_ROWS:
            provider = first
            header_seen = False
            continue
        if first == "DISTRITOS SEVILLA":
            headings = [str(sheet.cell_value(row_idx, col)).strip() for col in range(1, 13)]
            if [m.upper() for m in headings] != MONTHS:
                raise SystemExit(f"Unexpected month columns: {headings}")
            header_seen = True
            continue
        if provider is None or not header_seen or not first:
            continue
        if first.startswith(("Nota:", "Fuente:")):
            continue

        for month, col in enumerate(range(1, 13), start=1):
            value = sheet.cell_value(row_idx, col)
            if isinstance(value, str):
                if value.strip().lower() in {"", "n.d.", "nd", "n/d"}:
                    value = None
                else:
                    raise SystemExit(
                        f"Unexpected value in {provider}, {first}, month {month}: {value}"
                    )
            rows.append(
                {
                    "provider": provider,
                    "zona": first,
                    "anyo": 2024,
                    "mes": month,
                    "precio_oferta_eur_m2": float(value) if value is not None else None,
                }
            )
        counts[provider] += 1
    if counts != EXPECTED_ROWS:
        raise SystemExit(f"Unexpected provider coverage: {counts}")
    if len(rows) != sum(EXPECTED_ROWS.values()) * 12:
        raise SystemExit(f"Unexpected monthly row count: {len(rows)}")
    return rows


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "housing-data-analysis/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response:  # noqa: S310 (pinned FEMAS host)
        contents = response.read()
    if not contents.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        raise SystemExit("Yearbook download is not an OLE/XLS workbook")
    RAW_XLS.write_bytes(contents)
    rows = parse_workbook(contents)
    pq.write_table(pa.Table.from_pylist(rows), RAW_PARQUET)

    for rel in (
        "data/raw/sevilla_anuario_2025_7_3_9.xls",
        "data/raw/parquet/sevilla_oferta_zona_2024.parquet",
    ):
        manifest.record(
            rel,
            {
                "url": URL,
                "publisher": "Ayuntamiento de Sevilla, Anuario 2025 table 7.3.9 (FEMAS mirror)",
                "accessed": date.today().isoformat(),
                "note": (
                    "2024 monthly second-hand housing offer prices, EUR/m²; "
                    "Fotocasa 11 districts + Idealista 17 zones kept distinct; "
                    "not transaction prices"
                ),
            },
        )
    print(f"Sevilla offer prices: {len(rows)} provider-area-month rows; {counts_summary(rows)}")


def counts_summary(rows: list[dict[str, object]]) -> str:
    return ", ".join(
        f"{provider}={sum(r['provider'] == provider for r in rows) // 12} areas"
        for provider in EXPECTED_ROWS
    )


if __name__ == "__main__":
    main()
