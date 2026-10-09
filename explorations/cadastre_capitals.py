"""Andalusian-capital physical-stock profiles: municipal-grain era comparison.

Descriptive exploration only: property-weighted construction-era profiles,
record-date medians and surface proxies for Malaga, Granada and Cordoba
capitals from the municipal-grain BU pilot (scripts/fetch_cadastre_capitals.py),
with the Sevilla pilot as the benchmark. Same record-date proxy semantics
as explorations/cadastre_eras.py: earliest component construction year per
BU record weighted by declared housing properties. No causal claim.
Writes artifacts/cadastre_capitals.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

CAPITALS_DB = PROCESSED / "stock_capitals.duckdb"
SEVILLA_DB = PROCESSED / "stock.duckdb"
ARTIFACT = ROOT / "artifacts" / "cadastre_capitals.json"
ERAS = [
    (0, 1950, "Pre-1951"),
    (1951, 1970, "1951-1970"),
    (1971, 1990, "1971-1990"),
    (1991, 2010, "1991-2010"),
    (2011, 9999, "2011+"),
]


def era_of(year: int) -> str | None:
    for lo, hi, label in ERAS:
        if lo <= year <= hi:
            return label
    return None


def profile(rows: list[tuple]) -> dict:
    """rows: (year_start, dwelling_properties, gross_floor_m2)."""
    total = sum(p for _y, p, _f in rows)
    dated = [(y, p, f) for y, p, f in rows if y is not None]
    dated_props = sum(p for _y, p, _f in dated)
    era_counts = {label: 0 for _, _, label in ERAS}
    for y, p, _f in dated:
        era_counts[era_of(y)] += p
    years = sorted(y for y, p, _f in dated for _ in range(p))
    n = len(years)
    median = years[n // 2] if n % 2 else (years[n // 2 - 1] + years[n // 2]) / 2
    floors = [f for _y, _p, f in dated if f is not None]
    return {
        "n_records": len(rows),
        "total_properties": total,
        "dated_properties": dated_props,
        "missing_property_pct": round((total - dated_props) / total * 100, 2) if total else None,
        "median_year_property_weighted": median if n else None,
        "era_share_pct": {
            label: round(era_counts[label] / dated_props * 100, 1) for _, _, label in ERAS
        },
        "median_gross_floor_m2": sorted(floors)[len(floors) // 2] if floors else None,
    }


def main():
    for db in (CAPITALS_DB, SEVILLA_DB):
        if not db.is_file():
            raise SystemExit("Missing stock sidecars; run make fetch-stock first")
    con = duckdb.connect()
    con.execute(f"attach '{CAPITALS_DB}' as cap (read_only)")
    con.execute(f"attach '{SEVILLA_DB}' as sev (read_only)")
    cities = {
        r[0]: r[1]
        for r in con.execute("select ine_municipality, municipio from cap.municipios").fetchall()
    }
    results = {"eras": [label for _, _, label in ERAS], "cities": {}}
    for ine, name in sorted(cities.items()):
        rows = con.execute(
            "select year_start, dwelling_properties, gross_floor_m2 from cap.buildings "
            "where ine_municipality = ? and dwelling_properties > 0",
            [ine],
        ).fetchall()
        results["cities"][ine] = {"municipio": name, **profile(rows)}
    sev_rows = con.execute(
        "select year_start, dwelling_properties, gross_floor_m2 from sev.buildings "
        "where dwelling_properties > 0"
    ).fetchall()
    results["cities"]["41091"] = {"municipio": "Sevilla", **profile(sev_rows)}
    con.close()
    results["_meta"] = ols.model_meta(
        str(Path(__file__).resolve()),
        [
            str(CAPITALS_DB.relative_to(ROOT)),
            str(SEVILLA_DB.relative_to(ROOT)),
        ],
    )
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {ARTIFACT.relative_to(ROOT)}: {len(results['cities'])} cities")


if __name__ == "__main__":
    main()
