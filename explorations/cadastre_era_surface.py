"""Surface/era matrix: cadastre era profiles split by building-size quartiles.

Descriptive exploration only: splits the housing-bearing cadastre BU records
(earliest component construction year, gross floor area, declared housing
properties) into equal-count gross_floor_m2 quartiles and cross-tabulates
era mix per size class and size mix per era. No trend claim, no causal
claim, no significance testing.

Note the unit of analysis: a BU record's gross_floor_m2 is the whole
building/parcel gross area, not per-dwelling area; m2_per_property divides
it by declared housing properties and is only a coarse per-unit proxy.
Writes artifacts/cadastre_era_surface.json.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

STOCK_DB = PROCESSED / "stock.duckdb"
ARTIFACT = ROOT / "artifacts" / "cadastre_era_surface.json"
ERAS = [
    (0, 1950, "Pre-1951"),
    (1951, 1970, "1951-1970"),
    (1971, 1990, "1971-1990"),
    (1991, 2010, "1991-2010"),
    (2011, 9999, "2011+"),
]


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def era_of(year: int) -> str | None:
    for lo, hi, label in ERAS:
        if lo <= year <= hi:
            return label
    return None


def main():
    mod = _load_module("cadastre_age_rent", "explorations/cadastre_age_rent.py")
    if not STOCK_DB.is_file():
        raise SystemExit("Missing stock sidecar; run make stock-rent first")
    con = duckdb.connect(str(STOCK_DB), read_only=True)
    total_records = con.execute(
        "select count(*) from buildings "
        "where dwelling_properties > 0 and gross_floor_m2 is not null"
    ).fetchone()[0]
    rows = con.execute(
        "select barrio_id, year_start, dwelling_properties, gross_floor_m2 "
        "from buildings "
        "where dwelling_properties > 0 and gross_floor_m2 is not null "
        "and year_start is not null"
    ).fetchall()
    con.close()

    floors = sorted(r[3] for r in rows)
    n = len(floors)
    q1 = floors[n // 4]
    q2 = floors[n // 2]
    q3 = floors[3 * n // 4]

    def quartile(floor: float) -> int:
        if floor <= q1:
            return 1
        if floor <= q2:
            return 2
        if floor <= q3:
            return 3
        return 4

    era_props = {e[2]: 0 for e in ERAS}
    quart_era_props = {q: {e[2]: 0 for e in ERAS} for q in (1, 2, 3, 4)}
    quart_meta = {q: {"records": 0, "props": 0, "years": []} for q in (1, 2, 3, 4)}
    era_meta = {e[2]: {"records": 0, "props": 0, "floors": [], "m2_props": []} for e in ERAS}
    for _bid, year, props, floor in rows:
        e = era_of(year)
        q = quartile(floor)
        era_props[e] += props
        quart_era_props[q][e] += props
        quart_meta[q]["records"] += 1
        quart_meta[q]["props"] += props
        quart_meta[q]["years"].extend([year] * props)
        era_meta[e]["records"] += 1
        era_meta[e]["props"] += props
        era_meta[e]["floors"].append(floor)
        era_meta[e]["m2_props"].append(floor / props)

    total_props = sum(era_props.values())
    quartiles_out = []
    for q in (1, 2, 3, 4):
        m = quart_meta[q]
        era_share = {
            label: round(quart_era_props[q][label] / m["props"] * 100, 1) for _, _, label in ERAS
        }
        quartiles_out.append(
            {
                "quartile": q,
                "floor_upper_m2": [None, q1, q2, q3, None][q],
                "n_records": m["records"],
                "n_properties": m["props"],
                "median_year_property_weighted": median(m["years"]),
                "era_share_pct": era_share,
            }
        )
    eras_out = []
    for _, _, label in ERAS:
        m = era_meta[label]
        quart_share = {
            q: round(quart_era_props[q][label] / m["props"] * 100, 1) for q in (1, 2, 3, 4)
        }
        eras_out.append(
            {
                "era": label,
                "n_records": m["records"],
                "n_properties": m["props"],
                "property_share_pct": round(m["props"] / total_props * 100, 1),
                "median_gross_floor_m2": median(m["floors"]),
                "median_m2_per_property": round(median(m["m2_props"]), 1),
                "quartile_share_pct": quart_share,
            }
        )

    results = {
        "method": (
            "Descriptive cross-tabulation; equal-count record quartiles of "
            "gross_floor_m2; property-weighted era shares; no trend, causal "
            "or significance claim"
        ),
        "definitions": {
            "gross_floor_m2": "BU record gross floor area of the whole building/parcel",
            "m2_per_property": (
                "gross_floor_m2 divided by declared housing properties; coarse per-unit proxy"
            ),
            "age": (
                "Record earliest component construction year; record-date proxy, not dwelling age"
            ),
        },
        "coverage": {
            "records_with_floor_and_properties": total_records,
            "records_with_valid_year": len(rows),
            "records_dropped_no_year": total_records - len(rows),
        },
        "quartile_cutoffs_m2": {"q1": q1, "q2": q2, "q3": q3},
        "spearman_year_vs_floor_record_level": round(
            mod.spearman([r[1] for r in rows], [r[3] for r in rows]), 6
        ),
        "quartiles": quartiles_out,
        "eras": eras_out,
        "_meta": ols.model_meta(
            str(Path(__file__).resolve()),
            [str(STOCK_DB.relative_to(ROOT))],
        ),
    }
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}: {len(rows)} records, "
        f"cutoffs {q1}/{q2}/{q3} m2, "
        f"spearman year-floor {results['spearman_year_vs_floor_record_level']}"
    )


if __name__ == "__main__":
    main()
