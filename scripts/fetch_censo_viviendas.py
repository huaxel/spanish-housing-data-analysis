"""Fetch INE census dwelling anchors (2001/2011, provincias + CCAA).

Source: INE jaxi CSV
https://www.ine.es/jaxi/files/_px/csv_bd/t20/e244/viviendas/p07/nal02.csv
Columns (tab-separated): Total Nacional | Comunidades y Ciudades Autónomas |
Provincias | Tipo de vivienda | Periodo | Total
2021 census dwellings: TODO — pin the 2021 table once located (see
scripts/ine_discover.py); the MIVAU parque series already embeds the 2021
rebase, so the 2021 join works without this file.
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

URL = "https://www.ine.es/jaxi/files/_px/csv_bd/t20/e244/viviendas/p07/nal02.csv"
RAW_CSV = RAW / "censo_viviendas_2001_2011.csv"
RAW_PARQUET = RAW / "parquet" / "censo_viviendas_2001_2011.parquet"


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=120) as resp:  # noqa: S310 (pinned host)
            tmp.write(resp.read())
        tmp_path = tmp.name
    Path(tmp_path).replace(RAW_CSV)
    _, rows = csvx.read_csv_records(RAW_CSV, delimiter="\t")
    n = csvx.write_parquet(rows, RAW_PARQUET)
    manifest.record(
        "data/raw/censo_viviendas_2001_2011.csv",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "CENSOPV",
            "accessed": date.today().isoformat(),
        },
    )
    manifest.record(
        "data/raw/parquet/censo_viviendas_2001_2011.parquet",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "CENSOPV",
            "accessed": date.today().isoformat(),
        },
    )
    print(f"censo viviendas: {n} rows -> {RAW_PARQUET}")


if __name__ == "__main__":
    main()
