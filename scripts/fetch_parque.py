"""Fetch MIVAU Estimación del Parque de Viviendas (CSV, open data).

Source: https://datos.mivau.gob.es/dataset/VDP002_01
Direct: https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP002_01.csv
Grain: provincia x año x tipo (Vivienda_Principal / Vivienda_No_Principal /
  Viviendas_Totales). Method: Censos 2001/2011/2021 + yearly flows; rebased.
Upstream renamed its columns and categories and zero-padded the territory codes
(seen 2026-11-26). The parquet keeps the names above, which build_marts reads;
the CSV keeps the published bytes. Any other layout is rejected.
Writes data/raw/parque_viviendas.csv + data/raw/parquet/parque_viviendas.parquet
"""

from __future__ import annotations

import csv
import io
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP002_01.csv"
RAW_CSV = RAW / "parque_viviendas.csv"
RAW_PARQUET = RAW / "parquet" / "parque_viviendas.parquet"
# Published column -> parquet column, in published order.
COLUMNS = {
    "COD_CCAA": "CODAUTO",
    "NOM_CCAA": "Comunidad_Autónoma",
    "COD_PROV": "CPRO",
    "NOM_PROV": "Provincia",
    "ANIO": "Año",
    "CATEGORIA_PARQUE": "Tipo_Vivienda",
    "NUM_VIVIENDAS": "Valor",
}
TIPOS = {
    "Principal": "Vivienda_Principal",
    "No_Principal": "Vivienda_No_Principal",
    "Totales": "Viviendas_Totales",
}


def parse(text: str) -> list[dict]:
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=";")
    header = next(reader, [])
    if header != list(COLUMNS):
        raise ValueError(f"parque: unexpected header {header}")
    rows = []
    for record in reader:
        if not record:
            continue
        if len(record) != len(COLUMNS):
            raise ValueError(f"parque: ragged row {record}")
        row = dict(zip(COLUMNS.values(), record, strict=True))
        if row["Tipo_Vivienda"] not in TIPOS:
            raise ValueError(f"parque: unknown category {row['Tipo_Vivienda']!r}")
        row["Tipo_Vivienda"] = TIPOS[row["Tipo_Vivienda"]]
        for code in ("CODAUTO", "CPRO"):
            # Blank CPRO marks the Ceuta y Melilla aggregate; keep it blank.
            if row[code]:
                if not row[code].isdigit():
                    raise ValueError(f"parque: non-numeric {code} {row[code]!r}")
                row[code] = str(int(row[code]))
        # Published as plain digits; build_marts also strips separators.
        if not row["Valor"].isdigit():
            raise ValueError(f"parque: non-numeric value {row['Valor']!r}")
        if not row["Año"].isdigit():
            raise ValueError(f"parque: non-numeric year {row['Año']!r}")
        rows.append(row)
    if not rows:
        raise ValueError("parque: no data rows")
    return rows


def validate_coverage(rows: list[dict]) -> None:
    """50 provinces plus Ceuta y Melilla, each year and type exactly once."""
    cells = [(r["CPRO"], int(r["Año"]), r["Tipo_Vivienda"]) for r in rows]
    if len(set(cells)) != len(cells):
        raise ValueError("parque: duplicate cell")
    provinces = {c[0] for c in cells}
    years = {c[1] for c in cells}
    if len(provinces) != 51 or "" not in provinces:
        raise ValueError(f"parque: expected 50 provinces plus aggregate, got {len(provinces)}")
    if years != set(range(2001, max(max(years), 2025) + 1)):
        raise ValueError("parque: year range moved or has gaps")
    if len(cells) != len(provinces) * len(years) * len(TIPOS):
        raise ValueError("parque: incomplete territory x year x type grid")


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=120) as resp:  # noqa: S310 (pinned host)
            tmp.write(resp.read())
        tmp_path = Path(tmp.name)
    # Validate before replacing the local input; BOM + ';'-separated.
    try:
        rows = parse(tmp_path.read_text(encoding="utf-8-sig"))
        validate_coverage(rows)
    except ValueError:
        tmp_path.unlink()
        raise
    tmp_path.replace(RAW_CSV)
    n = csvx.write_parquet(rows, RAW_PARQUET)
    manifest.record(
        "data/raw/parque_viviendas.csv",
        {
            "url": URL,
            "publisher": "MIVAU",
            "dataset": "VDP002_01",
            "accessed": date.today().isoformat(),
            "note": "(parsed copy in data/raw/parquet/)",
        },
    )
    manifest.record(
        "data/raw/parquet/parque_viviendas.parquet",
        {
            "url": URL,
            "publisher": "MIVAU",
            "dataset": "VDP002_01",
            "accessed": date.today().isoformat(),
            "note": "parquet mirror of the pinned CSV",
        },
    )
    print(f"parque: {n} rows -> {RAW_PARQUET}")


if __name__ == "__main__":
    main()
