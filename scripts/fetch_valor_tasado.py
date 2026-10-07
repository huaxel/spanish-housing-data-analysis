"""Fetch MIVAU Valor Tasado de la Vivienda (VDP006_01, CSV open data).

Source: https://datos.mivau.gob.es/dataset/VDP006_01
Direct: https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP006_01.csv
Columns: Año;Trimestre;Valor(€/m²);Régimen(Libre/Protegida);CPRO;Provincia;
  Comunidad_Autónoma;CODAUTO. Quarterly, from 1995.
Empty Valor = unpublished (insufficient appraisals) — kept missing, never zero.
Writes data/raw/valor_tasado.csv + data/raw/parquet/valor_tasado.parquet
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP006_01.csv"
RAW_CSV = RAW / "valor_tasado.csv"
RAW_PARQUET = RAW / "parquet" / "valor_tasado.parquet"


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=180) as resp:  # noqa: S310 (pinned host)
            tmp.write(resp.read())
        tmp_path = tmp.name
    Path(tmp_path).replace(RAW_CSV)
    _, rows = csvx.read_csv_records(RAW_CSV, delimiter=";")
    n = csvx.write_parquet(rows, RAW_PARQUET)
    manifest.record(
        "data/raw/valor_tasado.csv",
        {
            "url": URL,
            "publisher": "MIVAU",
            "dataset": "VDP006_01",
            "accessed": date.today().isoformat(),
            "note": "(parsed copy in data/raw/parquet/)",
        },
    )
    manifest.record(
        "data/raw/parquet/valor_tasado.parquet",
        {
            "url": URL,
            "publisher": "MIVAU",
            "dataset": "VDP006_01",
            "accessed": date.today().isoformat(),
            "note": "raw quarterly rows; empty Valor = unpublished",
        },
    )
    print(f"valor tasado: {n} rows -> {RAW_PARQUET}")


if __name__ == "__main__":
    main()
