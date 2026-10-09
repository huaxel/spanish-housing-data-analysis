"""Fetch INE ADRH municipal mean/median income (jaxiT3 table 30824).

Atlas de Distribución de Renta de los Hogares, "Indicadores de renta
media y mediana": the single national jaxiT3 distribution covers
municipios, distritos and secciones censales together; only rows whose
Distritos and Secciones cells are both empty are municipality grain
(~8.1k municipios x 6 indicators x 2015-2023). The smaller per-province
tables carry the same rows split geographically and are not used.

Six indicators per municipality-year: renta neta/bruta media por persona
y por hogar, and media/mediana de la renta por unidad de consumo.
Semantics: administrative-register household income (IRPF AEAT +
haciendas forales), residents in family dwellings; means over all
households/persons found in tax files, NOT renters and NOT disposable
survey income. Suppressed cells ("." in the CSV, statistical secrecy or
population thresholds) are stored null, never zero-filled; from 2020
values for municipios under 100 residents can be comarca/province
small-municipio averages per INE methodology — a publication rule the
plain CSV does not flag per row.

Standalone descriptive series only. No mart join, and no rent-to-income
ratio without an explicit proxy-semantics decision (see
docs/housing_access.md). Writes data/raw/adrh_renta_municipal.csv
(byte evidence, ~336 MB) + data/raw/parquet/adrh_renta_municipal.parquet.
Use --offline to rebuild exclusively from the pinned CSV; --check to
verify pins and exact derivation without writing.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

URL = "https://www.ine.es/jaxiT3/files/t/csv_bdsc/30824.csv"
RAW_CSV = RAW / "adrh_renta_municipal.csv"
PARQUET = RAW / "parquet" / "adrh_renta_municipal.parquet"
HEADER = [
    "Municipios",
    "Distritos",
    "Secciones",
    "Indicadores de renta media",
    "Periodo",
    "Total",
]
INDICADORES = {
    "Renta neta media por persona": "neta_persona",
    "Renta neta media por hogar": "neta_hogar",
    "Renta bruta media por persona": "bruta_persona",
    "Renta bruta media por hogar": "bruta_hogar",
    "Media de la renta por unidad de consumo": "uc_media",
    "Mediana de la renta por unidad de consumo": "uc_mediana",
}
YEARS = set(range(2015, 2024))
CPROS = {f"{n:02d}" for n in range(1, 53)}
VALUE = re.compile(r"^\d{1,3}(\.\d{3})*$")
CODE = re.compile(r"^(\d{5}) (.+)$")
SCHEMA = pa.schema(
    [
        ("codigo", pa.string()),
        ("municipio", pa.string()),
        ("cpro", pa.string()),
        ("indicador", pa.string()),
        ("anyo", pa.int64()),
        ("renta_eur", pa.int64()),
    ]
)


def parse_value(raw: str, where: str) -> int | None:
    raw = raw.strip()
    if raw in (".", ""):  # suppressed (secrecy/threshold) or not published
        return None
    if not VALUE.match(raw):
        raise ValueError(f"adrh: unparsable value {raw!r} at {where}")
    return int(raw.replace(".", ""))


def parse(text_stream) -> list[dict]:
    reader = csv.reader(text_stream, delimiter=";")
    header = next(reader)
    if header != HEADER:
        raise ValueError(f"adrh: unexpected header {header}")
    rows: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for record in reader:
        record = [cell.strip("\r") for cell in record]
        if not any(cell.strip() for cell in record):
            continue
        if len(record) != len(HEADER):
            raise ValueError(f"adrh: ragged row {record}")
        mun, dist, secc, indicador, periodo, valor = record
        if dist or secc:
            continue  # district/census-section grain: not municipality rows
        if not mun:
            raise ValueError(f"adrh: blank municipality with empty geo {record}")
        m = CODE.match(mun)
        if not m:
            raise ValueError(f"adrh: municipality label without code {mun!r}")
        codigo, municipio = m.group(1), m.group(2).strip()
        if codigo[:2] not in CPROS:
            raise ValueError(f"adrh: unknown CPRO in {codigo!r}")
        if indicador not in INDICADORES:
            raise ValueError(f"adrh: unknown indicator {indicador!r}")
        if not periodo.isdigit() or int(periodo) not in YEARS:
            raise ValueError(f"adrh: year out of range {periodo!r}")
        anyo = int(periodo)
        key = (codigo, indicador, anyo)
        if key in seen:
            raise ValueError(f"adrh: duplicate cell {key}")
        seen.add(key)
        rows.append(
            {
                "codigo": codigo,
                "municipio": municipio,
                "cpro": codigo[:2],
                "indicador": INDICADORES[indicador],
                "anyo": anyo,
                "renta_eur": parse_value(valor, str(key)),
            }
        )
    if not rows or not any(r["renta_eur"] is not None for r in rows):
        raise ValueError("adrh: no observed values")
    return rows


def validate_coverage(rows: list[dict]) -> None:
    """Dataset-level invariants: full grid, no dropped province."""
    codes = {r["codigo"] for r in rows}
    cpros = {r["cpro"] for r in rows}
    if cpros != CPROS:
        raise ValueError(f"adrh: province coverage {sorted(cpros - CPROS)} missing/dropped")
    grid: set[tuple[str, int]] = set()
    for r in rows:
        grid.add((r["codigo"], r["anyo"]))
    want = len(codes) * len(YEARS)
    if len(grid) != want:
        raise ValueError("adrh: municipio-year grid has gaps")
    per_cell: dict[tuple[str, int], int] = {}
    for r in rows:
        k = (r["codigo"], r["anyo"])
        per_cell[k] = per_cell.get(k, 0) + 1
    if set(per_cell.values()) != {len(INDICADORES)}:
        raise ValueError("adrh: indicator grid incomplete for some municipio-year")
    if min(r["anyo"] for r in rows) != 2015 or max(r["anyo"] for r in rows) != 2023:
        raise ValueError("adrh: series window moved")


def pinned_rows() -> list[dict]:
    man = manifest.load()
    rel = str(RAW_CSV.relative_to(ROOT))
    if rel not in man["sha256"]:
        raise ValueError(f"Unpinned input {rel}; run fetch_adrh.py")
    missing, mismatched = manifest.check({rel: man["sha256"][rel]})
    if missing or mismatched:
        raise ValueError(f"adrh: input missing={missing}, changed={mismatched}")
    with RAW_CSV.open(encoding="utf-8-sig", newline="") as fh:
        rows = parse(fh)
    validate_coverage(rows)
    return rows


def write_parquet(rows: list[dict]) -> None:
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, PARQUET)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        rows = pinned_rows()
        current = pq.read_table(PARQUET).to_pylist()
        want = pa.Table.from_pylist(rows, schema=SCHEMA).to_pylist()
        if current != want:
            raise ValueError("adrh: parquet stale vs parser + pinned input")
        hidden = sum(1 for r in rows if r["renta_eur"] is None)
        print(f"adrh: {len(rows)} municipal cells ({hidden} suppressed); pins verified")
        return
    if not args.offline:
        req = urllib.request.Request(URL, headers={"User-Agent": "housing-data-analysis/1.0"})
        tmp = RAW_CSV.with_suffix(".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(req, timeout=1800) as response, tmp.open("wb") as out:  # noqa: S310
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
        with tmp.open(encoding="utf-8-sig", newline="") as fh:
            rows = parse(fh)  # validate before replacing local input
        validate_coverage(rows)
        tmp.replace(RAW_CSV)
        manifest.record(
            str(RAW_CSV.relative_to(ROOT)),
            {
                "url": URL,
                "publisher": "INE ADRH, Indicadores de renta media y mediana (jaxiT3 30824)",
                "accessed": date.today().isoformat(),
                "note": "Municipality rows only; '.' suppression kept null",
            },
        )
    rows = pinned_rows()
    write_parquet(rows)
    manifest.record(
        str(PARQUET.relative_to(ROOT)),
        {
            "publisher": "INE ADRH, Indicadores de renta media y mediana (jaxiT3 30824)",
            "accessed": date.today().isoformat(),
            "note": "Derived from pinned adrh_renta_municipal.csv by fetch_adrh.py",
        },
    )
    hidden = sum(1 for r in rows if r["renta_eur"] is None)
    codes = len({r["codigo"] for r in rows})
    where = PARQUET.relative_to(ROOT)
    print(f"adrh: {len(rows)} cells, {codes} municipios, {hidden} suppressed; parquet {where}")


if __name__ == "__main__":
    main()
