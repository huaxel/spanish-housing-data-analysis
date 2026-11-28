"""Pin INE's semiannual municipal VTE estimates from the coded JAXI downloads.

Tables 39363 (dwellings and beds) and 39366 (share of census dwellings)
contain official five-digit municipality codes and explicit geographic levels
in CSV. Preserve the published snapshot history and require every municipal
stock sum to reconcile with its national total.

--offline rebuilds from pinned CSVs; --check verifies pins and derivation.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

TABLES = {table_id: RAW / f"vut_municipal_{table_id}.csv" for table_id in (39363, 39366)}
CSV_URL = "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/{table_id}.csv"
PARQUET = RAW / "parquet" / "vut_municipal.parquet"
SCHEMA = pa.schema(
    [
        ("codigo_ine", pa.string()),
        ("territorio", pa.string()),
        ("nivel", pa.string()),
        ("medida", pa.string()),
        ("anyo", pa.int16()),
        ("periodo", pa.int8()),
        ("valor", pa.float64()),
    ]
)
GEO = ["Total Nacional", "Comunidades y Ciudades Autónomas", "Provincias", "Municipios"]
MEASURES = {
    "Viviendas turísticas": "viviendas_turisticas",
    "Plazas": "plazas",
    "Plazas por vivienda turística": "plazas_por_vivienda",
}
COUNTS = {"viviendas_turisticas", "plazas"}
SPANISH_NUMBER = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]+)?")


def parse(data: bytes, table_id: int) -> list[dict]:
    """Separate levels by populated geographic fields, never by names or values."""
    has_counts = table_id == 39363
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), delimiter=";")
    expected = [*GEO, *(["Viviendas y plazas"] if has_counts else []), "Periodo", "Total"]
    if reader.fieldnames != expected:
        raise ValueError(f"VUT {table_id}: unexpected CSV columns: {reader.fieldnames}")
    rows = []
    seen = set()
    national: dict[tuple[int, int, str], float] = {}
    stock: Counter[tuple[int, int, str]] = Counter()
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"VUT {table_id}: malformed CSV row at line {reader.line_num}")
        value_text = row["Total"].strip()
        if value_text in ("", ".."):
            continue  # unpublished, not zero
        y, sep, m = row["Periodo"].partition("M")
        if not sep or not re.fullmatch(r"[0-9]{4}", y) or m not in ("02", "05", "08", "11"):
            raise ValueError(f"VUT {table_id}: unrecognized period {row['Periodo']!r}")
        year, period = int(y), int(m)
        measure = MEASURES[row["Viviendas y plazas"]] if has_counts else "pct_censadas"
        if not SPANISH_NUMBER.fullmatch(value_text) or (measure in COUNTS and "," in value_text):
            raise ValueError(f"VUT {table_id}: invalid {measure} value {value_text!r}")
        value = float(value_text.replace(".", "").replace(",", "."))
        country, region, province, municipality = (row[k].strip() for k in GEO)
        if country != "Total Nacional":
            raise ValueError(f"VUT {table_id}: unexpected national label {country!r}")
        code = None
        label = municipality or province or region or country
        if municipality:
            code, _, label = municipality.partition(" ")
            if (
                not re.fullmatch(r"[0-9]{5}", code)
                or not label
                or not province.startswith(code[:2] + " ")
            ):
                raise ValueError(
                    f"VUT {table_id}: invalid municipality/province pair "
                    f"{municipality!r} / {province!r}"
                )
            level = "municipio"
        else:
            level = "agregado" if province or region else "nacional"
        geography = code if code is not None else (region, province)
        key = (geography, year, period, measure)
        if key in seen:
            raise ValueError(f"VUT {table_id}: duplicate geography/period/measure {key}")
        seen.add(key)
        snapshot = (year, period, measure)
        if level == "nacional":
            national[snapshot] = value
        if level == "municipio" and measure == "viviendas_turisticas":
            stock[snapshot] += value
        rows.append(
            dict(
                codigo_ine=code,
                territorio=label,
                nivel=level,
                medida=measure,
                anyo=year,
                periodo=period,
                valor=value,
            )
        )
    if not national or not any(row["nivel"] == "municipio" for row in rows):
        raise ValueError(f"VUT {table_id}: missing national or municipal observations")
    if has_counts and (
        not stock
        or dict(stock) != {k: v for k, v in national.items() if k[2] == "viviendas_turisticas"}
    ):
        raise ValueError(f"VUT {table_id}: municipal dwelling counts do not sum to national counts")
    return rows


def derive(sources: dict[int, bytes]) -> list[dict]:
    rows = [row for table_id in TABLES for row in parse(sources[table_id], table_id)]
    stock, shares = set(), set()
    for row in rows:
        if row["nivel"] not in ("nacional", "municipio"):
            continue
        key = (row["codigo_ine"], row["anyo"], row["periodo"])
        if row["medida"] == "viviendas_turisticas":
            stock.add(key)
        elif row["medida"] == "pct_censadas":
            shares.add(key)
    if shares - stock:
        raise ValueError("VUT: published share without a corresponding stock observation")
    if {key for key in stock if key[0] is None} != {key for key in shares if key[0] is None}:
        raise ValueError("VUT: count and share tables have different national snapshots")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        pins = manifest.load()["sha256"]
        paths = [*TABLES.values(), PARQUET]
        keys = [str(p.relative_to(ROOT)) for p in paths]
        missing, mismatched = manifest.check({k: pins.get(k, "") for k in keys})
        if missing or mismatched:
            raise SystemExit(f"VUT: input pins missing or changed: {missing + mismatched}")

    if args.offline or args.check:
        sources = {table_id: path.read_bytes() for table_id, path in TABLES.items()}
    else:
        sources = {}
        for table_id in TABLES:
            with urllib.request.urlopen(CSV_URL.format(table_id=table_id), timeout=90) as response:
                sources[table_id] = response.read()
    rows = derive(sources)  # validate the full release before replacing any pin
    if args.check:
        if pq.read_table(PARQUET).to_pylist() != rows:
            raise SystemExit("VUT: parquet stale vs parser + pinned inputs")
        print(f"vut: {len(rows)} cells; pins and municipal sums verified")
        return
    for table_id, path in TABLES.items():
        if not args.offline:
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(sources[table_id])
            tmp.replace(path)
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "publisher": "INE · Viviendas turísticas en España (VTE)",
                "url": CSV_URL.format(table_id=table_id),
                "accessed": date.today().isoformat(),
                "note": "JAXI CSV with official municipality codes and explicit geographic levels",
            },
        )
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    tmp = PARQUET.with_suffix(".tmp")
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), tmp)
    tmp.replace(PARQUET)
    manifest.record(
        str(PARQUET.relative_to(ROOT)),
        {
            "publisher": "INE · VTE municipal",
            "accessed": date.today().isoformat(),
            "note": "Derived from pinned municipality-coded JAXI CSVs",
        },
    )
    print(f"vut: {len(rows)} cells | municipality-coded observations reconciled")


if __name__ == "__main__":
    main()
