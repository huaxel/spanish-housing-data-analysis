"""Fetch INE tourist dwellings (VTE): viviendas turísticas by CCAA/provincia.

Tables 39364 (counts) + 46141 (adds % sobre censadas, cross-check only).
Pattern: '{Terr}. {Viviendas turísticas|Plazas|...}. Dato base.' Monthly
stock snapshots from 2020 — keep December (or latest month) per year, NOT
annual means (a registry stock, not a flow).
Writes data/raw/turisticas_{ccaa_prov}.json + .parquet (single table grain
column: nacional/ccaa/provincia resolved at build).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLES = {39364: "counts", 46141: "con_pct"}


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    for table_id, tag in TABLES.items():
        payload = ine_api.get_table(table_id)
        if isinstance(payload, dict):
            raise SystemExit(f"VTE {table_id}: {payload}")
        # Uniprovincial CCAA appear twice (CCAA + provincial series, same Nombre).
        # Verified identical values (2026-10-06) — enforce, then keep first.
        seen: dict[str, dict] = {}
        for s in payload:
            if s["Nombre"] in seen:
                a = {(x["Anyo"], x["FK_Periodo"]): x["Valor"] for x in seen[s["Nombre"]]["Data"]}
                b = {(x["Anyo"], x["FK_Periodo"]): x["Valor"] for x in s["Data"]}
                if a != b:
                    raise SystemExit(f"VTE {table_id}: duplicate {s['COD']} differs — investigate")
                continue
            seen[s["Nombre"]] = s
        payload = list(seen.values())
        by_ym: dict[tuple[str, int, int], dict] = {}
        skipped: list[str] = []
        for s in payload:
            parts = ine_api.split_nombre(s["Nombre"])
            if len(parts) != 3 or parts[2] != "Dato base":
                skipped.append(s["Nombre"])
                continue
            for x in s["Data"]:
                by_ym.setdefault((parts[0], x["Anyo"], x["FK_Periodo"]), {})[parts[1]] = x["Valor"]
        # December snapshot per (terr, year); fall back to latest month.
        rows = []
        pivot: dict[tuple[str, int], dict[int, dict]] = {}
        for (terr, anyo, per), m in by_ym.items():
            pivot.setdefault((terr, anyo), {})[per] = m
        for (terr, anyo), months in sorted(pivot.items()):
            dec = months.get(12, months[max(months)])
            if "Viviendas turísticas" not in dec:
                continue
            rows.append(
                {
                    "territorio": terr,
                    "anyo": anyo,
                    "viv_turisticas": int(dec["Viviendas turísticas"]),
                    "plazas": dec.get("Plazas"),
                    "pct_censadas": dec.get(
                        "Porcentaje de viviendas turísticas sobre el total de viviendas censadas"
                    ),
                    "mes": 12 if 12 in months else max(months),
                }
            )
        out = RAW / "parquet" / f"turisticas_{tag}.parquet"
        pq.write_table(pa.Table.from_pylist(rows), out)
        (RAW / f"turisticas_{tag}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        manifest.record(
            f"data/raw/turisticas_{tag}.json",
            {
                "api": f"wstempus/DATOS_TABLA/{table_id}",
                "operation": "VTE",
                "accessed": date.today().isoformat(),
            },
        )
        manifest.record(
            f"data/raw/parquet/turisticas_{tag}.parquet",
            {
                "api": f"wstempus/DATOS_TABLA/{table_id}",
                "operation": "VTE",
                "accessed": date.today().isoformat(),
                "note": "December snapshot per year",
            },
        )
        print(f"turisticas {tag}: {len(rows)} rows; skipped {len(skipped)}")


if __name__ == "__main__":
    main()
