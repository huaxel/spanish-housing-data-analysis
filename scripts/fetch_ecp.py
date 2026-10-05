"""Fetch INE Estadística Continua de Población (ECP, operation Id 450).

- Población residente a 1 de enero: CCAA table 56940
  ('{Sexo}. Todas las edades. {CCAA}. ...'), provincia table 56945
  (date-bounded: full fetch is volume-blocked by INE).
- Hogares en viviendas familiares a 1 de enero (total): CCAA 60131, provincia 60133
  ('{Terr}. Total. Hogares en viviendas familiares. Número.').

Annual convention: FK_Periodo == 19 with Anyo Y == 1 January of Y
(Fecha 31-Dec Y-1; verified 2026-10-05). Any deviation fails loudly.

Writes data/raw/ecp_{pob,hog}_{ccaa,prov}.json + data/raw/parquet/ecp_*.parquet
(parsed 1-Jan rows only; raw JSON retains all quarters for audit).
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

# NOTE: provincial ECP population (table 56945) is unreachable: DATOS_TABLA
# refuses it at every date window ('restricciones de volumen'), SERIES_TABLA
# returns empty, and DATOS_METADATAOPERACION filters match nothing
# (probed 2026-10-06). Consequence: provincia mart ends 2021 (Padrón);
# CCAA/Nacional continue on ECP. See docs/sources.md.
TABLES = {
    (56940, "pob_ccaa"): {},
    (60131, "hog_ccaa"): {},
    (60133, "hog_prov"): {},
}
SEXOS = {"Total", "Hombres", "Mujeres"}
JAN = 19  # FK_Periodo for the 1-January reference date


def jan1_date(d: dict) -> dt.date:
    return dt.datetime.fromtimestamp(d["Fecha"] / 1000, dt.UTC).date()


def check_jania_convention(payload: list[dict], table_id: int) -> None:
    probe = payload[0]["Data"]
    jan = [x for x in probe if x["FK_Periodo"] == JAN]
    if not jan:
        raise SystemExit(f"ECP {table_id}: no FK_Periodo==19 — convention broken")
    for x in jan:
        if jan1_date(x) != dt.date(x["Anyo"] - 1, 12, 31):
            raise SystemExit(
                f"ECP {table_id}: FK_Periodo 19 is not 1-Jan "
                f"(anyo={x['Anyo']}, fecha={jan1_date(x)})"
            )


def parse_pob(payload: list[dict]) -> tuple[list[dict], list[str]]:
    rows, skipped = [], []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        terr: str | None = None
        if len(parts) != 5 or parts[1] != "Todas las edades":
            skipped.append(s["Nombre"])
            continue
        if parts[0] in SEXOS:
            # CCAA/prov pattern: '{Sexo}. Todas las edades. {Terr}. ...'
            if parts[0] != "Total":
                skipped.append(s["Nombre"])
                continue
            terr = parts[2]
        elif parts[0] == "Total Nacional" and parts[2] in SEXOS:
            # Nacional pattern: 'Total Nacional. Todas las edades. {Sexo}. ...'
            if parts[2] != "Total":
                skipped.append(s["Nombre"])
                continue
            terr = parts[0]
        else:
            skipped.append(s["Nombre"])
            continue
        for x in s["Data"]:
            if x["FK_Periodo"] != JAN:
                continue
            rows.append(
                {
                    "territorio": terr,
                    "anyo": x["Anyo"],
                    "poblacion": int(x["Valor"]),
                    "serie_cod": s["COD"],
                }
            )
    return rows, skipped


def parse_hog(payload: list[dict]) -> tuple[list[dict], list[str]]:
    rows, skipped = [], []
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        if len(parts) != 4 or parts[2] != "Hogares en viviendas familiares":
            skipped.append(s["Nombre"])
            continue
        if parts[1] != "Total":
            continue  # tamaño detail queued; v1 keeps household totals
        for x in s["Data"]:
            if x["FK_Periodo"] != JAN:
                continue
            rows.append(
                {
                    "territorio": parts[0],
                    "anyo": x["Anyo"],
                    "hogares": int(x["Valor"]),
                    "serie_cod": s["COD"],
                }
            )
    return rows, skipped


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    for (table_id, kind), opts in TABLES.items():
        payload = ine_api.get_table(table_id, **opts)
        if isinstance(payload, dict):  # INE volume/error envelope
            raise SystemExit(f"ECP {table_id}: {payload}")
        check_jania_convention(payload, table_id)
        raw_json = RAW / f"ecp_{kind}.json"
        raw_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        parser = parse_pob if kind.startswith("pob") else parse_hog
        rows, skipped = parser(payload)
        if not rows:
            raise SystemExit(f"ECP {kind}: zero 1-Jan rows — format changed?")
        out = RAW / "parquet" / f"ecp_{kind}.parquet"
        pq.write_table(pa.Table.from_pylist(rows), out)
        manifest.record(
            f"data/raw/ecp_{kind}.json",
            {
                "api": f"wstempus/DATOS_TABLA/{table_id}",
                "operation": "ECP",
                "accessed": "2026-10-06",
                **opts,
            },
        )
        manifest.record(
            f"data/raw/parquet/ecp_{kind}.parquet",
            {
                "api": f"wstempus/DATOS_TABLA/{table_id}",
                "operation": "ECP",
                "accessed": "2026-10-06",
                "note": "1-Jan (FK_Periodo 19) rows only",
            },
        )
        print(f"ecp {kind}: {len(rows)} 1-Jan rows; skipped {len(skipped)} series")


if __name__ == "__main__":
    main()
