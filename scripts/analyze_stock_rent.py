"""Descriptive cross-snapshot stock/rent associations, not a causal estimator."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import fetch_cadastre_stock  # noqa: E402
import fetch_sevilla_income  # noqa: E402
from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

PAGE = ROOT / "evidence/pages/stock.md"
OUTPUT = ROOT / "artifacts/stock_rent_descriptive.json"
QUERIES = [
    "lectura_stock_renta",
    "stock_fechas_sensibilidad",
    "cobertura_stock_renta",
    "asociaciones_stock_renta",
    "omision_distrito_stock_renta",
    "cobertura_stock_ingreso",
    "sensibilidad_stock_ingreso",
    "omision_distrito_stock_ingreso",
    "resumen_omision_stock_ingreso",
]


def expand(sql, queries, stack=()):
    def reference(match):
        name = match[1]
        if name in stack or name not in queries:
            raise ValueError(f"Unknown or cyclic page query: {name}")
        return "(" + expand(queries[name], queries, (*stack, name)) + ")"

    return re.sub(r"\$\{(\w+)\}", reference, sql)


def results(con, queries):
    output = {}
    for name in QUERIES:
        cursor = con.execute(expand(queries[name], queries, (name,)))
        names = [column[0] for column in cursor.description]
        output[name] = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
    return output


def report():
    fetch_cadastre_stock.verify()
    fetch_sevilla_income.verify()
    queries = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE.read_text(), re.DOTALL))
    with duckdb.connect() as con:
        con.execute("set threads=1")
        con.execute(f"attach '{PROCESSED / 'stock.duckdb'}' as stock (read_only)")
        con.execute(f"attach '{PROCESSED / 'marts.duckdb'}' as housing (read_only)")
        con.execute(f"attach '{PROCESSED / 'income.duckdb'}' as income (read_only)")
        snapshot = con.execute(
            "select value from stock.stock_meta where key='snapshot_date'"
        ).fetchone()[0]
        rows = results(con, queries)
    return {
        "method": "Descriptive cross-snapshot; equal barrio weight; no causal/p-value/CI claim",
        "stock_snapshot": snapshot,
        "duckdb_version": duckdb.__version__,
        "date_weighting": (
            "Equal housing-bearing BU records versus declared housing-property-count weights; "
            "lower discrete median of record earliest year, not individual dwelling age"
        ),
        "income_reference_years": [2019, 2020],
        "income_definition": (
            "SIM publisher-reported mean net family income EUR; aggregation weights undocumented"
        ),
        "income_method": (
            "Same-sample average global ranks; district demeaning then "
            "income projection; correlate residuals without reranking"
        ),
        "ipra_update_year": 2022,
        "ipra_contract_window": [2019, 2021],
        "meta": {
            str(path.relative_to(ROOT)): manifest.sha256(path)
            for path in [
                PAGE,
                Path(__file__),
                PROCESSED / "stock.duckdb",
                PROCESSED / "marts.duckdb",
                PROCESSED / "income.duckdb",
                Path(fetch_sevilla_income.__file__),
                *fetch_sevilla_income.INPUTS.values(),
            ]
        },
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = report()
    if args.check:
        if not OUTPUT.is_file() or json.loads(OUTPUT.read_text()) != payload:
            raise SystemExit("Stock/rent report missing or stale; run make stock-rent")
        print("stock/rent: source/query hashes and exact descriptive results verified")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        print(json.dumps(payload["results"], indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
