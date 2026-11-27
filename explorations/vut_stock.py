"""What the official tourist-dwelling register says, and what it cannot say.

The repo's tourist claim is built on intensity panels (travellers and nights per
resident), which measure *flow*. This script reads INE's municipal tourist
dwelling register (VTE, operation 410, tables 39363/39366), which measures the
*stock* — what the public debate is actually about — and reports it with its own
accounting:

- national stock and beds in the latest snapshot, plus the path since 2020;
- concentration: how much of the municipal stock sits in the top municipios;
- official shares: INE's own "% of tourist dwellings over census dwellings",
  whose median and upper tail say how local the phenomenon is;
- coverage: how many register rows can be joined to the repo's municipal
  dimension, and how much stock that covers. INE ships no municipality code in
  the data payload and 2,227 labels belong to more than one territory, so a
  chunk of the stock is *not* assignable here — that is reported, never guessed.

Framing: a register counts what administrations have declared, not what exists.
Every reading below is a floor on the true stock and says nothing about rents;
the rent question is the panel in `panel_tourist.py`, which finds no
intra-municipal association.

Outputs: artifacts/vut_stock.json with an `_meta` freshness key.
Use --check to verify the artifact matches the pinned inputs.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402
from spanish_housing.ine_api import norm_name as N  # noqa: E402

VUT_PARQUET = RAW / "parquet" / "vut_municipal.parquet"
MARTS = PROCESSED / "marts.duckdb"
ARTIFACT = ROOT / "artifacts/vut_stock.json"


def load() -> list[dict]:
    return pq.read_table(VUT_PARQUET).to_pylist()


def latest_snapshot(rows: list[dict]) -> tuple[int, int]:
    return max((r["anyo"], r["periodo"]) for r in rows)


def build() -> dict:
    rows = load()
    year, period = latest_snapshot(rows)
    snap = [r for r in rows if (r["anyo"], r["periodo"]) == (year, period)]

    def national(medida: str) -> float:
        return next(
            r["valor"]
            for r in snap
            if r["territorio"] == "Total Nacional" and r["medida"] == medida
        )

    con = duckdb.connect(str(MARTS), read_only=True)
    try:
        muni_names = {
            N(r[0]) for r in con.execute("select distinct municipio from muni_all").fetchall()
        }
    finally:
        con.close()

    stock = {
        r["territorio"]: r["valor"]
        for r in snap
        if r["medida"] == "viviendas_turisticas"
        and r["nivel"] == "municipio"
        and r["territorio"] != "Total Nacional"
    }
    assignable = {k: v for k, v in stock.items() if N(k) in muni_names}
    # Ambiguous labels mix province aggregates with their capitals, so their
    # summed stock is not a quantity: only the row count is reported.
    ambiguous_rows = sum(
        1 for r in snap if r["medida"] == "viviendas_turisticas" and r["nivel"] == "ambiguo"
    )

    ranked = sorted(assignable.items(), key=lambda kv: -kv[1])
    assigned_total = sum(assignable.values())
    top10 = sum(v for _k, v in ranked[:10])

    shares = sorted(
        r["valor"]
        for r in snap
        if r["medida"] == "pct_censadas"
        and r["nivel"] == "municipio"
        and r["territorio"] != "Total Nacional"
        and r["valor"] > 0
    )

    # Path: national stock at each published snapshot, oldest → newest.
    path = sorted(
        (
            (r["anyo"], r["periodo"], r["valor"])
            for r in rows
            if r["territorio"] == "Total Nacional" and r["medida"] == "viviendas_turisticas"
        ),
        key=lambda t: (t[0], t[1]),
    )
    first = path[0]

    return {
        "source": {
            "operation_id": 410,
            "tables": [39363, 39366],
            "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=39363",
            "publisher": "INE · Viviendas turísticas en España (VTE)",
            "note": "register snapshot; declared tourist dwellings, a floor on the true stock",
        },
        "snapshot": {"year": year, "period": period},
        "national": {
            "viviendas_turisticas": national("viviendas_turisticas"),
            "plazas": national("plazas"),
            "plazas_por_vivienda": national("plazas_por_vivienda"),
            "pct_censadas": national("pct_censadas"),
        },
        "path": {
            "first_year": first[0],
            "first_period": first[1],
            "first_value": first[2],
            "change_pct": round(100.0 * (national("viviendas_turisticas") / first[2] - 1.0), 2),
        },
        "concentration": {
            "top10_municipios": [k for k, _v in ranked[:10]],
            "top10_share_of_assigned_pct": round(100.0 * top10 / assigned_total, 2),
            "top_municipio": ranked[0][0],
            "top_municipio_vut": ranked[0][1],
        },
        "shares": {
            "n_municipios": len(shares),
            "median_pct": round(statistics.median(shares), 2),
            "p90_pct": round(shares[int(0.9 * len(shares))], 2),
            "max_pct": round(shares[-1], 2),
            "share_above_5pct": round(100.0 * sum(1 for v in shares if v > 5.0) / len(shares), 2),
        },
        "coverage": {
            "rows_in_snapshot": len(snap),
            "municipio_rows": len(stock),
            "joined_to_muni_all": len(assignable),
            "ambiguous_rows": ambiguous_rows,
            "assigned_stock": assigned_total,
            "assigned_share_of_national_pct": round(
                100.0 * assigned_total / national("viviendas_turisticas"), 2
            ),
        },
        "_meta": ols.model_meta(
            __file__, [str(VUT_PARQUET.relative_to(ROOT)), str(MARTS.relative_to(ROOT))]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify artifact matches inputs")
    args = parser.parse_args()

    data = build()
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_text() != payload:
            raise SystemExit("Stale artifacts/vut_stock.json; re-run vut_stock.py")
        print("vut_stock: verified")
        return
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload)

    nat = data["national"]
    conc = data["concentration"]
    sh = data["shares"]
    cov = data["coverage"]
    print(
        f"national {nat['viviendas_turisticas']:,.0f} VUT / {nat['plazas']:,.0f} plazas "
        f"({nat['pct_censadas']}% of census dwellings)"
    )
    print(f"  top municipio {conc['top_municipio']} = {conc['top_municipio_vut']:,.0f}")
    print(f"  top-10 share of assigned stock: {conc['top10_share_of_assigned_pct']}%")
    print(
        f"  municipal shares: median {sh['median_pct']}%, p90 {sh['p90_pct']}%, "
        f"max {sh['max_pct']}%, above 5% = {sh['share_above_5pct']}%"
    )
    print(
        f"  coverage: assigned {cov['assigned_share_of_national_pct']}% of national stock "
        f"({cov['ambiguous_rows']} ambiguous rows left unassigned)"
    )


if __name__ == "__main__":
    main()
