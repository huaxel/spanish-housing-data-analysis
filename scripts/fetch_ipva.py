"""Pin INE IPVA table 59060: annual municipal rent price indices and variations.

JAXI supplies official municipality codes, unlike the series names in WSTEMPUS.
Keep national and provincial remainder observations separately from municipalities.
--offline derives parquet from the pinned bytes; --check verifies both pins and rows.
"""

from __future__ import annotations

import argparse
import csv
import io
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

URL = "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/59060.csv"
RAW_CSV = RAW / "ipva_municipal_59060.csv"
PARQUET = RAW / "parquet/ipva_municipal.parquet"
SCHEMA = pa.schema(
    [
        ("codigo_ine", pa.string()),
        ("territorio", pa.string()),
        ("nivel", pa.string()),
        ("medida", pa.string()),
        ("anyo", pa.int16()),
        ("valor", pa.float64()),
    ]
)
MEASURES = {"Índice": "indice", "Variación anual": "variacion"}


def parse(data: bytes) -> list[dict]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), delimiter=";")
    if reader.fieldnames != ["Municipio", "Tipo de dato", "Periodo", "Total"]:
        raise ValueError(f"IPVA: unexpected columns {reader.fieldnames}")
    rows, seen = [], set()
    for row in reader:
        if None in row or None in row.values():
            raise ValueError(f"IPVA: malformed row {reader.line_num}")
        label = row["Municipio"].strip()
        code = None
        if label == "Total Nacional":
            level = "nacional"
        elif label.startswith("Resto "):
            level = "resto_provincia"
        elif match := re.fullmatch(r"([0-9]{5}) (\S.*)", label):
            level = "municipio"
            code, label = match.groups()
        else:
            raise ValueError(f"IPVA: unknown geography {label!r}")
        measure = MEASURES.get(row["Tipo de dato"])
        if measure is None or not re.fullmatch(r"[0-9]{4}", row["Periodo"]):
            raise ValueError(f"IPVA: unexpected measure or annual period at row {reader.line_num}")
        year = int(row["Periodo"])
        key = (level, code or label, year, measure)
        if key in seen:
            raise ValueError(f"IPVA: duplicate observation {key}")
        seen.add(key)
        raw = row["Total"].strip()
        if raw in ("", ".."):
            continue  # unpublished, never a zero index or zero change
        if not re.fullmatch(r"-?[0-9]+(?:,[0-9]+)?", raw):
            raise ValueError(f"IPVA: invalid value {raw!r}")
        value = float(raw.replace(",", "."))
        if measure == "indice" and value <= 0:
            raise ValueError(f"IPVA: nonpositive index {key}")
        rows.append(
            dict(
                codigo_ine=code,
                territorio=label,
                nivel=level,
                medida=measure,
                anyo=year,
                valor=value,
            )
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw_key, parquet_key = (str(p.relative_to(ROOT)) for p in (RAW_CSV, PARQUET))
    pins = manifest.load()["sha256"]
    if args.check or args.offline:
        checked = [raw_key, parquet_key] if args.check else [raw_key]
        missing, changed = manifest.check({k: pins.get(k, "") for k in checked})
        if missing or changed:
            raise SystemExit(f"IPVA: missing or changed pins: {missing + changed}")
        data = RAW_CSV.read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=90) as response:
            data = response.read()
    rows = parse(data)
    # Reject a truncated response before replacing either input. A new release
    # may add years but must retain the complete published reference history.
    indices = [r for r in rows if r["medida"] == "indice"]
    national = {r["anyo"] for r in indices if r["nivel"] == "nacional"}
    municipal = {r["anyo"] for r in indices if r["nivel"] == "municipio"}
    if national != municipal or not set(range(2011, 2025)) <= national:
        raise SystemExit("IPVA: missing national or municipal annual index history")
    for y in national:
        if sum(r["nivel"] == "municipio" and r["anyo"] == y for r in indices) < 500:
            raise SystemExit(f"IPVA: too few municipal index observations in {y}")
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    if args.check:
        if not table.equals(pq.read_table(PARQUET)):
            raise SystemExit("IPVA: parquet stale vs parser + pinned CSV")
        print(f"ipva: {len(rows)} cells; input pins and coded rows verified")
        return
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    tmp = PARQUET.with_suffix(".tmp")
    pq.write_table(table, tmp)
    if not args.offline:
        raw_tmp = RAW_CSV.with_suffix(".tmp")
        raw_tmp.write_bytes(data)
        raw_tmp.replace(RAW_CSV)
        manifest.record(
            raw_key,
            {
                "publisher": "INE · IPVA",
                "url": URL,
                "accessed": date.today().isoformat(),
                "note": "Coded municipal, national and province-remainder series",
            },
        )
    tmp.replace(PARQUET)
    manifest.record(
        parquet_key,
        {
            "publisher": "INE · IPVA",
            "accessed": date.today().isoformat(),
            "note": "Derived from pinned JAXI ipva_municipal_59060.csv",
        },
    )
    print(f"ipva: {len(rows)} coded and aggregate cells; latest index year {max(national)}")


if __name__ == "__main__":
    main()
