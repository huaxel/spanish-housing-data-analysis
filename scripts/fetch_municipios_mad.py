"""Fetch Comunidad de Madrid mirror: valor tasado vivienda libre by municipio.

Source (MIVAU series mirrored by datos.comunidad.madrid, Base 2005):
https://datos.comunidad.madrid/dataset/8cb70b8c-c1e2-43f7-826a-1a22c573a743/resource/ef4a2c7a-4273-4116-9ff2-d5f77020ca04/download/valor-tasado-de-la-vivienda-libre-por-municipios-de-mas-de-25.00-habitantes.-total-base-2005.-mu.csv
Annual rows (Año;...;Valor en Euros/m2); '-' = unpublished. cp1252 encoding.
Writes data/raw/valor_municipal_madrid.csv + .parquet (Libre only, annual).
Caveat: third-party mirror of MIVAU; cross-checked against provincial VDP006
for Madrid where years overlap (see verify printout in build step — manual).
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = (
    "https://datos.comunidad.madrid/dataset/8cb70b8c-c1e2-43f7-826a-1a22c573a743"
    "/resource/ef4a2c7a-4273-4116-9ff2-d5f77020ca04/download/"
    "valor-tasado-de-la-vivienda-libre-por-municipios-de-mas-de-25.00-habitantes."
    "-total-base-2005.-mu.csv"
)
RAW_CSV = RAW / "valor_municipal_madrid.csv"
RAW_PARQUET = RAW / "parquet" / "valor_municipal_madrid.parquet"


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=120) as resp:  # noqa: S310 (pinned host)
            raw = resp.read()
        tmp.write(raw.decode("cp1252").encode("utf-8"))
        tmp_path = tmp.name
    Path(tmp_path).replace(RAW_CSV)
    _, rows = csvx.read_csv_records(RAW_CSV, delimiter=";")
    keep = [r for r in rows if (r["Valor"] or "").strip() not in ("", "-")]
    n = csvx.write_parquet(keep, RAW_PARQUET)
    manifest.record(
        "data/raw/valor_municipal_madrid.csv",
        {
            "url": URL,
            "publisher": "datos.comunidad.madrid (MIVAU mirror)",
            "accessed": "2026-10-06",
            "note": "cp1252 original; stored as UTF-8",
        },
    )
    manifest.record(
        "data/raw/parquet/valor_municipal_madrid.parquet",
        {
            "url": URL,
            "publisher": "datos.comunidad.madrid (MIVAU mirror)",
            "accessed": "2026-10-06",
            "note": "published values only; '-' dropped, counted in print",
        },
    )
    print(f"municipios madrid: {n} valued rows ({len(rows) - n} unpublished '-')")


if __name__ == "__main__":
    main()
