"""Malaga construction-era profile: property-weighted era shares by barrio.

Same proxy semantics as explorations/cadastre_eras.py applied to the
Malaga capital extract with the official Ayuntamiento barrio join:
each building record's earliest component construction year (year_start)
is assigned to every declared housing property (dwelling_properties).
Record-date proxy weighted by housing-property counts, not measured
dwelling ages. Only barrio-assigned records enter the profiles.
Writes artifacts/cadastre_malaga_barrios.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

DATABASE = PROCESSED / "stock_capitals.duckdb"
ARTIFACT = ROOT / "artifacts" / "cadastre_malaga_barrios.json"
ERAS = [
    (0, 1950, "Pre-1951"),
    (1951, 1970, "1951-1970"),
    (1971, 1990, "1971-1990"),
    (1991, 2010, "1991-2010"),
    (2011, 9999, "2011+"),
]
INE = "29067"


def era(year: int | None) -> str | None:
    if year is None:
        return None
    for lo, hi, label in ERAS:
        if lo <= year <= hi:
            return label
    return None


def main():
    if not DATABASE.is_file():
        raise SystemExit("Missing capitals sidecar; run make fetch-stock first")
    con = duckdb.connect(str(DATABASE), read_only=True)
    rows = con.execute(
        "SELECT b.barrio_id, br.barrio, b.year_start, b.dwelling_properties "
        "FROM buildings b JOIN barrios br ON b.barrio_id = br.idg "
        "WHERE b.ine_municipality = ? "
        "ORDER BY br.barrio",
        [INE],
    ).fetchall()
    statuses = con.execute(
        "SELECT match_status, count(*), sum(dwelling_properties) FROM buildings "
        "WHERE ine_municipality = ? GROUP BY match_status ORDER BY match_status",
        [INE],
    ).fetchall()
    con.close()
    barrios: dict[str, dict] = {}
    for bid, barrio, year_start, props in rows:
        if props is None or props <= 0:
            continue
        if bid not in barrios:
            barrios[bid] = {
                "barrio": barrio,
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
            "total_properties": b["total_properties"],
            "dated_properties": b["dated_properties"],
            "missing_property_pct": round(
                (b["total_properties"] - b["dated_properties"]) / b["total_properties"] * 100, 2
            ),
            "median_year": median,
            **{e[2]: era_pct[e[2]] for e in ERAS},
        }
    total_props = sum(b["total_properties"] for b in barrios.values())
    dated_props = sum(b["dated_properties"] for b in barrios.values())
    global_era = {e[2]: 0 for e in ERAS}
    for b in barrios.values():
        for e in ERAS:
            global_era[e[2]] += b["era_counts"][e[2]]
    results["global"] = {
        "n_barrios": len(barrios),
        "total_properties": total_props,
        "dated_properties": dated_props,
        "missing_property_pct": round((total_props - dated_props) / total_props * 100, 2),
        "era_pct": {e[2]: round(global_era[e[2]] / dated_props * 100, 1) for e in ERAS},
        "match_status": [{"status": s, "records": n, "properties": p} for s, n, p in statuses],
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
