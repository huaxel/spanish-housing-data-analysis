"""Build the IRAV summary artifact and Evidence table from the pinned series.

Reads `data/raw/parquet/irav.parquet` (fetch_irav.py) and writes:

- `data/processed/irav.duckdb` — table `irav_nacional` for the /politica/ page;
- `artifacts/irav.json` — the summary the audit and the narrative quote
  (window, latest, bounds, annual means) plus a `_meta` freshness key.

The series is a rolling 24-month window of the *annual variation* of the
statutory rent-update reference (Ley 12/2023), national only. Nothing here is
an observed rent: it is the ceiling INE publishes for updating an existing
lease, so it is reported beside — never as — the INCASÒL contractual rents.

Use --check to verify the artifact and the DuckDB match the pinned parquet.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

PARQUET = RAW / "parquet" / "irav.parquet"
DUCKDB_OUT = PROCESSED / "irav.duckdb"
ARTIFACT_OUT = ROOT / "artifacts/irav.json"
TABLE_URL = "https://www.ine.es/jaxiT3/Tabla.htm?t=72975"


def build() -> dict:
    if not PARQUET.is_file():
        raise SystemExit(f"IRAV: {PARQUET.relative_to(ROOT)} missing — run fetch_irav.py")
    rows = pq.read_table(PARQUET).to_pylist()
    if not rows:
        raise SystemExit("IRAV: pinned series is empty")
    rows.sort(key=lambda r: (r["anyo"], r["mes"]))

    def label(r: dict) -> str:
        return f"{r['anyo']}-{r['mes']:02d}"

    by_year: dict[int, list[float]] = {}
    for r in rows:
        by_year.setdefault(r["anyo"], []).append(r["irav_pct"])
    lo = min(rows, key=lambda r: r["irav_pct"])
    hi = max(rows, key=lambda r: r["irav_pct"])
    latest = rows[-1]
    return {
        "source": {
            "operation_id": 481,
            "table_id": 72975,
            "url": TABLE_URL,
            "publisher": "INE · Índice de Referencia de Arrendamientos de Vivienda",
        },
        "window": {"first": label(rows[0]), "last": label(latest), "months": len(rows)},
        "latest": {"period": label(latest), "irav_pct": latest["irav_pct"]},
        "bounds": {
            "min": {"period": label(lo), "irav_pct": lo["irav_pct"]},
            "max": {"period": label(hi), "irav_pct": hi["irav_pct"]},
        },
        "annual_means": [
            {
                "anyo": anyo,
                "mean_pct": round(statistics.mean(vals), 2),
                "months": len(vals),
            }
            for anyo, vals in sorted(by_year.items())
        ],
        "series": rows,
        "_meta": ols.model_meta(__file__, [str(PARQUET.relative_to(ROOT))]),
    }


def write_duckdb(data: dict) -> None:
    tmp = DUCKDB_OUT.with_suffix(".duckdb.tmp")
    if tmp.exists():
        tmp.unlink()
    con = duckdb.connect(str(tmp))
    con.register("irav_tbl", pa.Table.from_pylist(data["series"]))
    con.execute("CREATE TABLE irav_nacional AS SELECT * FROM irav_tbl")
    con.close()
    tmp.replace(DUCKDB_OUT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify artifact and DuckDB match")
    args = parser.parse_args()

    data = build()
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not ARTIFACT_OUT.is_file() or ARTIFACT_OUT.read_text() != payload:
            raise SystemExit("Stale artifacts/irav.json; re-run build_irav_index.py")
        if not DUCKDB_OUT.is_file():
            raise SystemExit("Missing data/processed/irav.duckdb")
        print(
            f"irav: verified {data['window']['months']} months "
            f"({data['window']['first']} → {data['window']['last']})"
        )
        return

    ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_OUT.write_text(payload)
    write_duckdb(data)
    print(
        f"irav: {data['window']['months']} months, latest {data['latest']['period']} "
        f"{data['latest']['irav_pct']:+.2f}% (min {data['bounds']['min']['irav_pct']:+.2f}%, "
        f"max {data['bounds']['max']['irav_pct']:+.2f}%)"
    )


if __name__ == "__main__":
    main()
