"""Fetch INE's rental price index at municipal grain (IPVA, operation 432, table 59060).

`Índice de Precios de Vivienda en Alquiler`, municipal cut: annual index levels
and annual variation for the 764 municipios above the 10,000-inhabitant
threshold INE uses for this table, 2012–2023. The table is name-keyed — it
publishes no municipality code — so joins go through
`spanish_housing.muni_names.muni_key` and the exploration reports the coverage
it achieves (it is not a silent inner join).

Why it matters: SERPAVI (MIVAU tax-deposit exploitation) is the repo's only
municipal rent *level* series. The IPVA is a second official municipal rent
series produced from a different instrument (price index, not median of filed
contracts), so it can test whether SERPAVI's municipal trajectory is
independently corroborated rather than assumed.

Semantics: an index of asking/paid rent prices, quality-controlled by INE and
weighted by its own dwelling mix; NOT a median of signed contracts, and not
comparable to SERPAVI's level in absolute terms. Only changes are comparable,
and only up to 2023 (the last year published here).

Writes data/raw/ipva_municipal_59060.json (byte evidence) +
data/raw/parquet/ipva_municipal.parquet. --offline rebuilds from the pinned
JSON; --check verifies pins and exact derivation without writing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

TABLE_ID = 59060
RAW_JSON = RAW / "ipva_municipal_59060.json"
PARQUET = RAW / "parquet" / "ipva_municipal.parquet"
SCHEMA = pa.schema(
    [
        ("municipio", pa.string()),
        ("medida", pa.string()),
        ("anyo", pa.int16()),
        ("valor", pa.float64()),
    ]
)
MEASURES = {"Índice": "indice", "Variación anual": "variacion"}
ANNUAL_PERIODO = 28  # FK_Periodo for annual observations in this table
NATIONAL = "Total Nacional"


def parse(payload: list[dict]) -> list[dict]:
    """Flatten '<municipio>. <medida>. Total.' series into long rows."""
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"IPVA {TABLE_ID}: unexpected payload {type(payload).__name__}")
    rows: list[dict] = []
    for series in payload:
        parts = [p.strip() for p in series["Nombre"].split(".") if p.strip()]
        # Two label shapes coexist: "<municipio>. <medida>. Total." for the
        # municipal cut and "Total Nacional. Total. <medida>." for the national
        # aggregate. Locate the measure by name instead of by position.
        found = [p for p in parts[1:] if p in MEASURES]
        if len(found) != 1:
            raise ValueError(f"IPVA: unexpected series name {series['Nombre']!r}")
        municipio, medida = parts[0], MEASURES[found[0]]
        for obs in series["Data"]:
            if obs["FK_Periodo"] != ANNUAL_PERIODO:
                raise ValueError(f"IPVA: non-annual period in {series['Nombre']!r}")
            if obs.get("Valor") is None:
                continue  # unpublished cell: dropped, never zero-filled
            rows.append(
                {
                    "municipio": municipio,
                    "medida": medida,
                    "anyo": int(obs["Anyo"]),
                    "valor": float(obs["Valor"]),
                }
            )
    rows.sort(key=lambda r: (r["municipio"], r["medida"], r["anyo"]))
    keys = {(r["municipio"], r["medida"], r["anyo"]) for r in rows}
    if len(keys) != len(rows):
        raise ValueError("IPVA: duplicate municipio/medida/year rows")
    years = sorted({r["anyo"] for r in rows})
    if years[0] != 2012 or years[-1] != 2023:
        raise ValueError(f"IPVA: expected years 2012-2023, got {years[0]}-{years[-1]}")
    if len({r["municipio"] for r in rows}) < 500:
        raise ValueError("IPVA: fewer than 500 municipios — table layout changed?")
    return rows


def pinned_rows() -> list[dict]:
    if not RAW_JSON.is_file():
        raise SystemExit(f"IPVA: {RAW_JSON.relative_to(ROOT)} missing — run without --offline")
    return parse(json.loads(RAW_JSON.read_text(encoding="utf-8")))


def write_parquet(rows: list[dict]) -> None:
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), PARQUET)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        rows = pinned_rows()
        if pq.read_table(PARQUET).to_pylist() != rows:
            raise SystemExit("IPVA: parquet stale vs parser + pinned input")
        munis = len({r["municipio"] for r in rows})
        print(f"ipva: {len(rows)} municipio-measure-years, {munis} municipios; pins verified")
        return

    if not args.offline:
        payload = ine_api.get_table(TABLE_ID, date="20120101:20231231")
        if isinstance(payload, dict):
            raise SystemExit(f"IPVA {TABLE_ID}: {payload}")
        rows = parse(payload)  # validate before replacing the pinned copy
        tmp = RAW_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(RAW_JSON)
        manifest.record(
            str(RAW_JSON.relative_to(ROOT)),
            {
                "api": f"wstempus/DATOS_TABLA/{TABLE_ID}?date=20120101:20231231",
                "publisher": "INE · Índice de Precios de Vivienda en Alquiler (IPVA), municipal",
                "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=59060",
                "accessed": date.today().isoformat(),
                "note": (
                    "Municipios >10,000 habitantes only; name-keyed (no codes); "
                    "annual index and annual variation 2012-2023"
                ),
            },
        )
    rows = pinned_rows()
    write_parquet(rows)
    manifest.record(
        str(PARQUET.relative_to(ROOT)),
        {
            "publisher": "INE · IPVA municipal",
            "accessed": date.today().isoformat(),
            "note": "Derived from pinned ipva_municipal_59060.json by fetch_ipva.py",
        },
    )
    munis = len({r["municipio"] for r in rows})
    nacional = [r for r in rows if r["municipio"] == NATIONAL and r["medida"] == "indice"]
    print(
        f"ipva: {len(rows)} rows, {munis} municipios "
        f"(national index 2023 = {nacional[-1]['valor'] if nacional else 'n/a'})"
    )


if __name__ == "__main__":
    main()
