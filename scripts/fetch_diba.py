"""Fetch Diputació de Barcelona municipal housing open data (DIBA).

Source: https://media.diba.cat/diba/indicadors-habitatge/data/opendata/opendata.zip
(Observatori Local d'Habitatge; 311 municipalities, cp1252 CSVs, table codes
mapped in tb_indicadors.csv). This fetcher pins the ZIP and extracts:
  M19 sale €/m² (2013-), M23 monthly rent (2005-), H9a registered vacant
  dwellings (2018-), H18a tourist dwellings (2015-), M11d rent burden % and
  M11e mortgage burden % (2015-2022).
Writes data/raw/diba_opendata.zip + data/raw/parquet/diba_<code>.parquet
"""

from __future__ import annotations

import csv
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://media.diba.cat/diba/indicadors-habitatge/data/opendata/opendata.zip"
RAW_ZIP = RAW / "diba_opendata.zip"
TABLES = {"m19": "sale_eur_m2", "m23": "rent_month", "h9a": "vacant_reg",
          "h18a": "tourist", "m11d": "rent_burden", "m11e": "mortgage_burden"}


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip", dir=RAW) as tmp:
        with urllib.request.urlopen(URL, timeout=300) as resp:  # noqa: S310 (pinned host)
            tmp.write(resp.read())
        tmp_path = tmp.name
    Path(tmp_path).replace(RAW_ZIP)
    manifest.record("data/raw/diba_opendata.zip",
                    {"url": URL, "publisher": "Diputació de Barcelona",
                     "accessed": "2026-10-06"})
    with zipfile.ZipFile(RAW_ZIP) as z:
        names = {n.lower(): n for n in z.namelist()}
        munis = {r["mun_ine"]: r["mun_nom"].strip() for r in
                 csv.DictReader(z.open(names["municipis.csv"]).read().decode("cp1252").splitlines(),
                                delimiter=";")}
        for code, label in TABLES.items():
            fname = names.get(f"tb_{code}.csv")
            if fname is None:
                raise SystemExit(f"diba: tb_{code}.csv missing from ZIP")
            content = z.open(fname).read().decode("cp1252")
            # '08' is the province aggregate, absent from municipis.csv.
            munis = dict(munis, **{"08": "Barcelona (provincia)"})
            rows = []
            for r in csv.DictReader(content.splitlines(), delimiter=";"):
                raw = (r["val"] or "").strip()
                # Catalan number format: '.' thousands, ',' decimals.
                val = float(raw.replace(".", "").replace(",", ".")) if raw else None
                rows.append({"mun_ine": r["mun_ine"],
                             "municipio": munis.get(r["mun_ine"], "?"),
                             "anyo": int(r["any_"]), "valor": val})
            unknown = {r["mun_ine"] for r in rows if r["municipio"] == "?"}
            if unknown:
                raise SystemExit(f"diba {code}: unknown mun_ine {sorted(unknown)[:5]}")
            out = RAW / "parquet" / f"diba_{code}.parquet"
            n = csvx.write_parquet(rows, out)
            manifest.record(f"data/raw/parquet/diba_{code}.parquet",
                            {"url": URL, "publisher": "Diputació de Barcelona",
                             "accessed": "2026-10-06", "note": f"tb_{code} ({label})"})
            print(f"diba {code} ({label}): {n} rows")


if __name__ == "__main__":
    main()
