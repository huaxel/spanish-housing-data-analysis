"""Fetch INE's official household projection (PROH, operation 70, table 54562).

`Proyección de Hogares`: households at 1 January by territory, household size
and year, 2026–2040, for the 17 CCAA, their provinces, Ceuta/Melilla and the
national total. This is INE's own projection, published as an official
statistic — the repo uses it as an external input about *household formation*,
never as this project's forecast, and never as a demand or price model.

Why it matters: the repo's central question is households versus stock, and
until now the household side ended at the last observed ECP year. PROH extends
it under INE's own assumptions, which lets the synthesis state whether the
observed two-group pattern (metropolitan scarcity vs interior overhang) is
projected to persist — a question the project can answer with official data
instead of extrapolating.

Semantics: projection base is INE's, refreshed with its own vintage; the 2026
value already differs from the observed ECP count at 1 Jan 2026 (the projection
was built before that release), so levels are not interchangeable with ECP.
Only the projected trajectory is used here.

Writes data/raw/proh_54562.json (byte evidence) +
data/raw/parquet/proh_hogares.parquet. --offline rebuilds from the pinned JSON;
--check verifies pins and exact derivation without writing.
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

TABLE_ID = 54562
RAW_JSON = RAW / "proh_54562.json"
PARQUET = RAW / "parquet" / "proh_hogares.parquet"
SCHEMA = pa.schema(
    [
        ("territorio", pa.string()),
        ("medida", pa.string()),
        ("anyo", pa.int16()),
        ("valor", pa.float64()),
    ]
)
SIZES = {"Total", "1", "2", "3", "4 y más", "Tamaño medio del hogar"}
ANNUAL_PERIODO = 28
FIRST_YEAR, LAST_YEAR = 2026, 2040


def parse(payload: list[dict]) -> list[dict]:
    """Flatten '<territorio>. <medida>.' series (measure position varies)."""
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"PROH {TABLE_ID}: unexpected payload {type(payload).__name__}")
    # Uniprovincial territories (Balears, Cantabria, La Rioja, Ceuta, Melilla)
    # are published twice — once as CCAA, once as province — under identical
    # labels. Collapse them, but fail loudly if the two copies ever disagree.
    cells: dict[tuple[str, str, int], float] = {}
    for series in payload:
        parts = [p.strip() for p in series["Nombre"].split(".") if p.strip()]
        if len(parts) != 2:
            raise ValueError(f"PROH: unexpected series name {series['Nombre']!r}")
        sizes = [p for p in parts if p in SIZES]
        if len(sizes) != 1:
            raise ValueError(f"PROH: no unique measure in {series['Nombre']!r}")
        medida = sizes[0]
        territorio = parts[0] if parts[1] == medida else parts[1]
        for obs in series["Data"]:
            if obs["FK_Periodo"] != ANNUAL_PERIODO:
                raise ValueError(f"PROH: non-annual period in {series['Nombre']!r}")
            if obs.get("Valor") is None:
                continue
            key = (territorio, medida, int(obs["Anyo"]))
            value = float(obs["Valor"])
            if key in cells and cells[key] != value:
                raise ValueError(f"PROH: duplicated cell disagrees with itself: {key}")
            cells[key] = value
    rows = [
        {"territorio": t, "medida": m, "anyo": y, "valor": v}
        for (t, m, y), v in sorted(cells.items())
    ]
    years = sorted({r["anyo"] for r in rows})
    if years[0] != FIRST_YEAR or years[-1] != LAST_YEAR:
        raise ValueError(f"PROH: expected {FIRST_YEAR}-{LAST_YEAR}, got {years[0]}-{years[-1]}")
    if "Total Nacional" not in {r["territorio"] for r in rows}:
        raise ValueError("PROH: national total missing")
    # Size shares must be additive to the total in every territory-year.
    bad = []
    totals: dict[tuple[str, int], float] = {}
    parts_sum: dict[tuple[str, int], float] = {}
    for r in rows:
        if r["medida"] == "Total":
            totals[(r["territorio"], r["anyo"])] = r["valor"]
        elif r["medida"] in {"1", "2", "3", "4 y más"}:
            key = (r["territorio"], r["anyo"])
            parts_sum[key] = parts_sum.get(key, 0.0) + r["valor"]
    for key, total in totals.items():
        if key in parts_sum and abs(parts_sum[key] - total) > 1.0:
            bad.append((key, total, parts_sum[key]))
    if bad:
        raise ValueError(f"PROH: size components do not add to the total: {bad[:3]}")
    return rows


def pinned_rows() -> list[dict]:
    if not RAW_JSON.is_file():
        raise SystemExit(f"PROH: {RAW_JSON.relative_to(ROOT)} missing — run without --offline")
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
            raise SystemExit("PROH: parquet stale vs parser + pinned input")
        territorios = len({r["territorio"] for r in rows})
        print(f"proh: {len(rows)} rows, {territorios} territorios; pins verified")
        return

    if not args.offline:
        payload = ine_api.get_table(TABLE_ID, date=f"{FIRST_YEAR}0101:{LAST_YEAR}1231")
        if isinstance(payload, dict):
            raise SystemExit(f"PROH {TABLE_ID}: {payload}")
        rows = parse(payload)  # validate before replacing the pinned copy
        tmp = RAW_JSON.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(RAW_JSON)
        manifest.record(
            str(RAW_JSON.relative_to(ROOT)),
            {
                "api": f"wstempus/DATOS_TABLA/{TABLE_ID}?date={FIRST_YEAR}0101:{LAST_YEAR}1231",
                "publisher": "INE · Proyección de Hogares (PROH)",
                "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=54562",
                "accessed": date.today().isoformat(),
                "note": (
                    "Households at 1 January by territory and size, INE projection "
                    f"{FIRST_YEAR}-{LAST_YEAR}; projection base predates the latest ECP release"
                ),
            },
        )
    rows = pinned_rows()
    write_parquet(rows)
    manifest.record(
        str(PARQUET.relative_to(ROOT)),
        {
            "publisher": "INE · Proyección de Hogares (PROH)",
            "accessed": date.today().isoformat(),
            "note": "Derived from pinned proh_54562.json by fetch_proh.py",
        },
    )
    nat = [r for r in rows if r["territorio"] == "Total Nacional" and r["medida"] == "Total"]
    first = next(r for r in nat if r["anyo"] == FIRST_YEAR)
    last = next(r for r in nat if r["anyo"] == LAST_YEAR)
    print(
        f"proh: {len(rows)} rows, {len({r['territorio'] for r in rows})} territorios | "
        f"national {first['valor']:,.0f} ({FIRST_YEAR}) → {last['valor']:,.0f} ({LAST_YEAR})"
    )


if __name__ == "__main__":
    main()
