"""Read-only May 2026 pilot; see docs/explorations/vut_registry_pilot.md."""

from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from spanish_housing.data_paths import PROCESSED, RAW
from spanish_housing.ine_api import norm_name


def snapshot(series):
    values = [d["Valor"] for d in series["Data"] if (d["Anyo"], d["FK_Periodo"]) == (2026, 5)]
    if len(values) > 1:
        raise ValueError(f"Repeated May 2026 cell for {series['COD']}")
    return values[0] if values else None


def identify_municipal_series(mixed_rows, aggregates):
    """Remove confirmed aggregate series IDs, not similar names or values."""
    mixed = {row["COD"]: row for row in mixed_rows}
    by_id = {row["COD"]: row for row in aggregates}
    if len(mixed) != len(mixed_rows) or len(by_id) != len(aggregates):
        raise ValueError("Duplicate INE series ID")
    for code, row in by_id.items():
        match = mixed.get(code)
        if match is None or (row["Nombre"], snapshot(row)) != (
            match["Nombre"],
            snapshot(match),
        ):
            raise ValueError(f"Aggregate cross-check failed: {code}")
    national = snapshot(mixed["VTE71"])
    residual = []
    suffix = ". Viviendas turísticas. Dato base."
    for code, row in mixed.items():
        name = row["Nombre"].strip()
        if code not in by_id and name.endswith(suffix):
            value = snapshot(row)
            if value is not None:
                residual.append((name.removesuffix(suffix), int(value), code))
    if not residual or sum(value for _, value, _ in residual) != national:
        raise ValueError("Municipal series do not sum to the national snapshot")
    return int(national), residual


def registry_count(path: Path):
    # Count IDs only. Do not output unit addresses or identifiers.
    with zipfile.ZipFile(path) as archive:
        csvs = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(csvs) != 1:
            raise ValueError(f"Expected one CSV in {path.name}")
        with archive.open(csvs[0]) as member:
            rows = csv.DictReader(io.TextIOWrapper(member, encoding="utf-8-sig"))
            ids = [r["NUMERO_REGISTRE_GENERALITAT"].strip().upper() for r in rows]
    return len(ids), len(set(ids) - {""})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "aggregate_table", type=Path, help="Complete, non-deduplicated INE 39364 JSON"
    )
    parser.add_argument("barcelona_archives", type=Path, nargs="+")
    args = parser.parse_args()
    national, rows = identify_municipal_series(
        json.loads((RAW / "vut_municipal_39363.json").read_text()),
        json.loads(args.aggregate_table.read_text()),
    )
    name_counts = Counter(norm_name(name) for name, _, _ in rows)
    dimension = defaultdict(set)
    with duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True) as con:
        for province, name in con.sql("select distinct cpro, municipio from muni_all").fetchall():
            dimension[norm_name(name)].add((province, name))
    missing = sorted(
        (
            (value, name, code)
            for name, value, code in rows
            if len(dimension[norm_name(name)]) != 1 or name_counts[norm_name(name)] != 1
        ),
        reverse=True,
    )
    missing_stock = sum(value for value, _, _ in missing)
    print(f"Municipal series: {len(rows):,}; total: {national:,}; unmatched: {missing_stock:,}")
    print(f"Unmatched series: {len(missing)}; largest four: {missing[:4]}")
    print(f"Largest four / unmatched stock: {sum(r[0] for r in missing[:4]) / missing_stock:.2%}")
    for archive in args.barcelona_archives:
        records, registration_ids = registry_count(archive)
        print(
            f"{archive.name}: {records:,} records; {registration_ids:,} distinct registration IDs"
        )


if __name__ == "__main__":
    main()
