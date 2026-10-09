"""Cadastre construction-era profile: property-weighted era shares by barrio.

Uses the BU earliest-year proxy from the cadastre pilot: each building
record gets its earliest component construction year (year_start), and
every declared housing property (dwelling_properties) inherits that year.
This is a record-date proxy weighted by housing-property counts, not a
measured distribution of individual dwelling construction ages.
Writes artifacts/cadastre_eras.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

DATABASE = PROCESSED / "stock.duckdb"
ARTIFACT = ROOT / "artifacts" / "cadastre_eras.json"
ERAS = [
    (0, 1950, "Pre-1951"),
    (1951, 1970, "1951-1970"),
    (1971, 1990, "1971-1990"),
    (1991, 2010, "1991-2010"),
    (2011, 9999, "2011+"),
]


def era(year: int | None) -> str | None:
    if year is None:
        return None
    for lo, hi, label in ERAS:
        if lo <= year <= hi:
            return label
    return None


def main():
    if not DATABASE.is_file():
        raise SystemExit("Missing stock sidecar; run make stock-rent first")
    con = duckdb.connect(str(DATABASE), read_only=True)
    rows = con.execute(
        "SELECT b.barrio_id, br.barrio, br.distrito, "
        "b.year_start, b.dwelling_properties, b.match_status "
        "FROM buildings b "
        "JOIN barrios br ON b.barrio_id = br.idg "
        "ORDER BY br.barrio"
    ).fetchall()
    con.close()
    # Aggregate per barrio: property-weighted era shares, median year, missing
    barrios: dict[str, dict] = {}
    for row in rows:
        bid, barrio, distrito, year_start, props, status = row
        if props is None or props <= 0:
            continue
        if bid not in barrios:
            barrios[bid] = {
                "barrio": barrio,
                "distrito": distrito,
                "total_properties": 0,
                "dated_properties": 0,
                "years": [],
                "era_counts": {e[2]: 0 for e in ERAS},
            }
        b = barrios[bid]
        b["total_properties"] += props
        if year_start is not None:
            b["dated_properties"] += props
            e = era(year_start)
            if e:
                b["era_counts"][e] += props
            b["years"].extend([year_start] * props)
    # Compute per-barrio results
    results = {"eras": [e[2] for e in ERAS], "barrios": {}}
    for bid, b in barrios.items():
        if not b["years"]:
            continue
        b["years"].sort()
        n = len(b["years"])
        median = b["years"][n // 2] if n % 2 else (b["years"][n // 2 - 1] + b["years"][n // 2]) / 2
        dated = b["dated_properties"]
        era_pct = {e[2]: round(b["era_counts"][e[2]] / dated * 100, 1) for e in ERAS}
        results["barrios"][bid] = {
            "barrio": b["barrio"],
            "distrito": b["distrito"],
            "total_properties": b["total_properties"],
            "dated_properties": b["dated_properties"],
            "missing_property_pct": round(
                (b["total_properties"] - b["dated_properties"]) / b["total_properties"] * 100, 2
            ),
            "median_year": round(median, 1),
            **{e[2]: era_pct[e[2]] for e in ERAS},
        }
    # Global totals
    total_props = sum(b["total_properties"] for b in barrios.values())
    dated_props = sum(b["dated_properties"] for b in barrios.values())
    global_era = {e[2]: 0 for e in ERAS}
    for b in barrios.values():
        for e in ERAS:
            global_era[e[2]] += b["era_counts"][e[2]]
    results["global"] = {
        "n_barrios": len(barrios),
        "n_buildings": len(rows),
        "total_properties": total_props,
        "dated_properties": dated_props,
        "missing_property_pct": round((total_props - dated_props) / total_props * 100, 2),
        "era_pct": {e[2]: round(global_era[e[2]] / dated_props * 100, 1) for e in ERAS},
    }
    results["_meta"] = ols.model_meta(
        str(Path(__file__).resolve()),
        [str(DATABASE.relative_to(ROOT))],
    )
    (ROOT / "artifacts").mkdir(exist_ok=True)
    ARTIFACT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {ARTIFACT.relative_to(ROOT)}: {len(barrios)} barrios, {total_props} properties")


if __name__ == "__main__":
    main()
