"""Fetch MIVAU Estimación del Parque de Viviendas (CSV, open data).

Source: https://datos.mivau.gob.es/dataset/VDP002_01
Direct: https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP002_01.csv
Grain: provincia x año x tipo (Vivienda_Principal / Vivienda_No_Principal /
  Viviendas_Totales). Method: Censos 2001/2011/2021 + yearly flows; rebased.
Writes data/raw/parque_viviendas.csv + data/raw/parquet/parque_viviendas.parquet
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP002_01.csv"
RAW_CSV = RAW / "parque_viviendas.csv"
RAW_PARQUET = RAW / "parquet" / "parque_viviendas.parquet"


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=120) as resp:  # noqa: S310 (pinned host)
            tmp.write(resp.read())
        tmp_path = tmp.name
    # Atomic replace only after a complete download.
    Path(tmp_path).replace(RAW_CSV)
    # BOM + ';'-separated (verified 2026-10-05).
    _, rows = csvx.read_csv_records(RAW_CSV, delimiter=";")
    n = csvx.write_parquet(rows, RAW_PARQUET)
    manifest.record(
        "data/raw/parque_viviendas.csv",
        {
            "url": URL,
            "publisher": "MIVAU",
            "dataset": "VDP002_01",
            "accessed": "2026-10-05",
            "note": "(parsed copy in data/raw/parquet/)",
        },
    )
    manifest.record(
        "data/raw/parquet/parque_viviendas.parquet",
        {
            "url": URL,
            "publisher": "MIVAU",
            "dataset": "VDP002_01",
            "accessed": "2026-10-05",
            "note": "parquet mirror of the pinned CSV",
        },
    )
    print(f"parque: {n} rows -> {RAW_PARQUET}")


if __name__ == "__main__":
    main()
