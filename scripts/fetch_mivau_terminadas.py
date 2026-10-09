"""Pinned MIVAU iniciadas/terminadas dwellings (VDP005_01, CSV, monthly).

Source: Ministerio de Vivienda y Agenda Urbana open-data CSV (viviendas
iniciadas y terminadas by protection regime, CPRO, month). Libre +
protected completions are the Ministerio flow this repo's deficit
exploration compares against ECP household creation; visados proper
(CSCAE) are a different series and are NOT fetched here.

Missing monthly cells (Valor == '') are kept null, never zero-filled;
the exploration accounts and bounds them. Use --offline to rebuild
exclusively from the already pinned CSV input. Use --check to verify
pins and exact derivation without writing.
"""

from __future__ import annotations

import argparse
import csv
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

URL = "https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP005_01.csv"
RAW_CSV = RAW / "mivau_iniciadas_terminadas.csv"
PARQUET = RAW / "parquet" / "mivau_terminadas.parquet"
HEADER = [
    "Año",
    "Mes_Numero",
    "Valor",
    "Tipo_de_Vivienda",
    "Estado",
    "CODAUTO",
    "Comunidad_Autónoma",
    "CPRO",
    "Provincia",
]
ESTADOS = ("Iniciadas", "Terminadas")
TIPOS = ("Libre", "Protegida")
# CPRO codes as published (unpadded '1'..'52'); 51/52 are Ceuta/Melilla.
CPROS = {str(n) for n in range(1, 53)}
SCHEMA = pa.schema(
    [
        ("cpro", pa.string()),
        ("provincia", pa.string()),
        ("ccaa", pa.string()),
        ("anyo", pa.int64()),
        ("mes", pa.int64()),
        ("tipo", pa.string()),
        ("estado", pa.string()),
        ("viviendas", pa.int64()),
    ]
)


def parse_number(text: str, label: str):
    text = text.strip()
    if text == "":
        return None
    if not text.isdigit():
        raise ValueError(f"terminadas: nonnumeric value {label!r}")
    return int(text)


def parse(text: str) -> list[dict]:
    lines = text.lstrip("﻿").splitlines()
    reader = csv.reader(lines, delimiter=";")
    header = next(reader)
    if header != HEADER:
        raise ValueError(f"terminadas: unexpected header {header}")
    rows = []
    seen = set()
    for record in reader:
        if not any(cell.strip() for cell in record):
            continue
        if len(record) != len(HEADER):
            raise ValueError(f"terminadas: ragged row {record}")
        rec = dict(zip(HEADER, record, strict=True))
        try:
            anyo, mes = int(rec["Año"]), int(rec["Mes_Numero"])
        except ValueError:
            raise ValueError(f"terminadas: nonnumeric year/month {record}") from None
        if not 2008 <= anyo <= 2100:
            raise ValueError(f"terminadas: year out of range {anyo}")
        if not 1 <= mes <= 12:
            raise ValueError(f"terminadas: month out of range {mes}")
        if rec["Estado"] not in ESTADOS:
            raise ValueError(f"terminadas: unknown estado {rec['Estado']!r}")
        if rec["Tipo_de_Vivienda"] not in TIPOS:
            raise ValueError(f"terminadas: unknown tipo {rec['Tipo_de_Vivienda']!r}")
        if rec["CPRO"] not in CPROS:
            raise ValueError(f"terminadas: unknown CPRO {rec['CPRO']!r}")
        if not rec["Provincia"].strip() or not rec["Comunidad_Autónoma"].strip():
            raise ValueError(f"terminadas: blank territory label {record}")
        key = (rec["CPRO"], anyo, mes, rec["Tipo_de_Vivienda"], rec["Estado"])
        if key in seen:
            raise ValueError(f"terminadas: duplicate cell {key}")
        seen.add(key)
        rows.append(
            {
                "cpro": rec["CPRO"].zfill(2),
                "provincia": rec["Provincia"].strip(),
                "ccaa": rec["Comunidad_Autónoma"].strip(),
                "anyo": anyo,
                "mes": mes,
                "tipo": rec["Tipo_de_Vivienda"],
                "estado": rec["Estado"],
                "viviendas": parse_number(rec["Valor"], f"{key}"),
            }
        )
    if not rows or not any(r["viviendas"] is not None for r in rows):
        raise ValueError("terminadas: no observed values")
    return rows


def validate_coverage(rows: list[dict]) -> None:
    """Dataset-level invariants: no silently dropped province, stable start."""
    if {r["cpro"] for r in rows} != {c.zfill(2) for c in CPROS}:
        raise ValueError("terminadas: silently dropped province")
    if min(r["anyo"] for r in rows) != 2008:
        raise ValueError("terminadas: series start moved")


def pinned_rows() -> list[dict]:
    man = manifest.load()
    rel = str(RAW_CSV.relative_to(ROOT))
    if rel not in man["sha256"]:
        raise ValueError(f"Unpinned input {rel}; run fetch_mivau_terminadas.py")
    missing, mismatched = manifest.check({rel: man["sha256"][rel]})
    if missing or mismatched:
        raise ValueError(f"Terminadas input missing={missing}, changed={mismatched}")
    rows = parse(RAW_CSV.read_text(encoding="utf-8-sig"))
    validate_coverage(rows)
    return rows


def write_parquet(rows: list[dict]) -> None:
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, PARQUET)


def record_outputs(note: str) -> None:
    for path in [PARQUET]:
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "publisher": "MIVAU, viviendas iniciadas y terminadas (VDP005_01)",
                "accessed": date.today().isoformat(),
                "note": note,
            },
        )


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
            raise ValueError("Terminadas parquet stale vs parser + pinned input")
        print(f"terminadas: {len(rows)} monthly cells; pins and derivation verified")
        return
    if not args.offline:
        req = urllib.request.Request(URL, headers={"User-Agent": "housing-data-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=300) as response:  # noqa: S310
            contents = response.read()
        parse(contents.decode("utf-8-sig"))  # validate before replacing local input
        tmp = RAW_CSV.with_suffix(".tmp")
        tmp.write_bytes(contents)
        tmp.replace(RAW_CSV)
        manifest.record(
            str(RAW_CSV.relative_to(ROOT)),
            {
                "url": URL,
                "publisher": "MIVAU, viviendas iniciadas y terminadas (VDP005_01)",
                "accessed": date.today().isoformat(),
                "note": "Monthly iniciadas/terminadas by regime and CPRO; missing months kept null",
            },
        )
    rows = pinned_rows()
    write_parquet(rows)
    note = "Derived from pinned mivau_iniciadas_terminadas.csv"
    record_outputs(note + " by fetch_mivau_terminadas.py")
    missing = sum(1 for r in rows if r["viviendas"] is None)
    where = PARQUET.relative_to(ROOT)
    print(f"terminadas: {len(rows)} monthly cells ({missing} missing); parquet {where}")


if __name__ == "__main__":
    main()
