"""Fetch INE's municipal tourist-dwelling register (VTE, operation 410).

Two tables, both municipio-grain, each publishing the *snapshot history* of
the register (irregular reference months — Feb/Aug before 2024, then
May/Nov — from 2020 to the current release):

- 39363 `Viviendas turísticas, plazas, plazas por vivienda turística`: the
  official count of tourist dwellings and beds per municipio;
- 39366 `Porcentaje de viviendas turísticas sobre el total de viviendas
  censadas`: the same stock as a share of census dwellings, i.e. INE's own
  denominator rather than one we invent.

Why the municipal cut matters here: the repo's tourist claim is built on
*tourist intensity* panels (travellers and nights), which measure flow, never
stock. This table measures the stock — the thing the public debate is actually
about ("cuántos pisos turísticos hay") — with official provenance.

Semantics: a register snapshot of declared tourist dwellings under the current
normative definition, refreshed monthly (the CCAA/provincial cut is already
pinned by `fetch_turisticas.py` for its December snapshots; these municipal
tables publish only the latest month, so no per-year history is kept).
Under-registration is the known limitation of every such register: the count is
what administrations have licensed/registered, not what exists.

Writes data/raw/vut_municipal_39363.json, data/raw/vut_municipal_39366.json
(byte evidence) + data/raw/parquet/vut_municipal.parquet.
--offline rebuilds from the pinned JSONs; --check verifies pins and derivation.
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

TABLES = {
    39363: RAW / "vut_municipal_39363.json",
    39366: RAW / "vut_municipal_39366.json",
}
PARQUET = RAW / "parquet" / "vut_municipal.parquet"
SCHEMA = pa.schema(
    [
        ("territorio", pa.string()),
        ("nivel", pa.string()),
        ("medida", pa.string()),
        ("anyo", pa.int16()),
        ("periodo", pa.int8()),
        ("valor", pa.float64()),
    ]
)
MEASURES = {
    "Viviendas turísticas": "viviendas_turisticas",
    "Plazas": "plazas",
    "Plazas por vivienda turística": "plazas_por_vivienda",
    "Porcentaje de viviendas turísticas sobre el total de viviendas censadas": "pct_censadas",
}


def parse(payload: list[dict], table_id: int) -> list[dict]:
    """Flatten '<territorio>. <medida>. Dato base.' series into long rows.

    Each series carries the full snapshot history (irregular reference months),
    so rows are keyed by (territorio, medida, anyo, periodo)."""
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"VUT {table_id}: unexpected payload {type(payload).__name__}")
    cells: list[dict] = []
    for series in payload:
        parts = [p.strip() for p in series["Nombre"].split(".") if p.strip()]
        measures = [p for p in parts if p in MEASURES]
        if len(measures) != 1:
            raise ValueError(f"VUT {table_id}: no unique measure in {series['Nombre']!r}")
        medida = MEASURES[measures[0]]
        territorio = parts[0] if parts[0] not in MEASURES else parts[-2]
        for obs in series["Data"]:
            if obs.get("Valor") is None:
                continue  # unpublished cell: dropped, never zero-filled
            key = (territorio, medida, int(obs["Anyo"]), int(obs["FK_Periodo"]))
            cells.append(
                {
                    **dict(zip(("territorio", "medida", "anyo", "periodo"), key, strict=True)),
                    "valor": float(obs["Valor"]),
                }
            )
    if not cells:
        raise ValueError(f"VUT {table_id}: zero rows — format changed?")
    rows = sorted(cells, key=lambda r: (r["territorio"], r["medida"], r["anyo"], r["periodo"]))
    if not any(r["territorio"] == "Total Nacional" for r in rows):
        raise ValueError(f"VUT {table_id}: national total missing")
    return _label_levels(rows)


def _label_levels(rows: list[dict]) -> list[dict]:
    """Mark labels the table publishes more than once.

    INE ships no municipality code in the data payload, and Spanish municipio
    names are not unique: 2,227 labels in this table belong to two or three
    territories (a province and its capital, or the same name in two provinces),
    and their rows differ. Guessing which copy is which from the values would be
    invention, so they are labelled `ambiguo` and left for the exploration to
    report. Everything else keeps `municipio`; province-level rows with unique
    names survive that label and are dropped by the name join downstream, which
    is where the coverage accounting happens.
    """
    grouped: dict[tuple[str, str, int, int], int] = {}
    for r in rows:
        key = (r["territorio"], r["medida"], r["anyo"], r["periodo"])
        grouped[key] = grouped.get(key, 0) + 1
    out = []
    for r in rows:
        key = (r["territorio"], r["medida"], r["anyo"], r["periodo"])
        level = "ambiguo" if grouped[key] > 1 else "municipio"
        out.append({**r, "nivel": level})
    ambiguous = sum(1 for r in out if r["nivel"] == "ambiguo")
    if ambiguous > 0.4 * len(out):
        raise ValueError(f"VUT: {ambiguous}/{len(out)} rows ambiguous — layout changed?")
    out.sort(key=lambda r: (r["territorio"], r["nivel"], r["medida"], r["anyo"], r["periodo"]))
    return out


def _latest_national(rows: list[dict], medida: str) -> float:
    """National figure of the most recent snapshot (not the first row)."""
    candidates = [r for r in rows if r["territorio"] == "Total Nacional" and r["medida"] == medida]
    latest = max(candidates, key=lambda r: (r["anyo"], r["periodo"]))
    return latest["valor"]


def pinned_rows() -> list[dict]:
    rows: list[dict] = []
    for table_id, path in TABLES.items():
        if not path.is_file():
            raise SystemExit(f"VUT: {path.relative_to(ROOT)} missing — run without --offline")
        rows.extend(parse(json.loads(path.read_text(encoding="utf-8")), table_id))
    return rows


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
            raise SystemExit("VUT: parquet stale vs parser + pinned inputs")
        nat = _latest_national(rows, "viviendas_turisticas")
        print(f"vut: {len(rows)} cells; pins verified (national {nat:,.0f} in the latest snapshot)")
        return

    if not args.offline:
        for table_id, path in TABLES.items():
            payload = ine_api.get_table(table_id)
            if isinstance(payload, dict):
                raise SystemExit(f"VUT {table_id}: {payload}")
            parse(payload, table_id)  # validate before replacing the pinned copy
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
            manifest.record(
                str(path.relative_to(ROOT)),
                {
                    "api": f"wstempus/DATOS_TABLA/{table_id}",
                    "publisher": "INE · Viviendas turísticas en España (VTE), municipal",
                    "url": f"https://www.ine.es/jaxiT3/Tabla.htm?t={table_id}",
                    "accessed": date.today().isoformat(),
                    "note": (
                        "Register snapshot history, municipio grain (irregular reference "
                        "months 2020-onwards); declared tourist dwellings under the current "
                        "definition, not the true stock"
                    ),
                },
            )
    rows = pinned_rows()
    write_parquet(rows)
    manifest.record(
        str(PARQUET.relative_to(ROOT)),
        {
            "publisher": "INE · VTE municipal",
            "accessed": date.today().isoformat(),
            "note": "Derived from the pinned vut_municipal_3936*.json by fetch_vut_municipal.py",
        },
    )
    nat = _latest_national(rows, "viviendas_turisticas")
    places = _latest_national(rows, "plazas")
    print(
        f"vut: {len(rows)} cells | national {nat:,.0f} viviendas turísticas, {places:,.0f} plazas"
    )


if __name__ == "__main__":
    main()
