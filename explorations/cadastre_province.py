"""Sevilla-province physical-stock profiles per municipality.

Descriptive exploration only: property-weighted construction-era profiles,
record-date medians and surface proxies for all 106 province municipalities
from stock_province.duckdb, joined to the municipal sidecar (census
households, dwellings, rent context). Same record-date proxy semantics as
the Sevilla pilot. No causal claim.
Writes artifacts/cadastre_province.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

PROV_DB = PROCESSED / "stock_province.duckdb"
MUNI_DB = PROCESSED / "sevilla_2021.duckdb"
ARTIFACT = ROOT / "artifacts" / "cadastre_province.json"
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
    total = sum(p for _y, p, _f in rows)
    dated = [(y, p, f) for y, p, f in rows if y is not None]
    dated_props = sum(p for _y, p, _f in dated)
    if not dated:
        return {
            "n_records": len(rows),
            "total_properties": total,
            "dated_properties": 0,
            "missing_property_pct": None,
            "median_year_property_weighted": None,
            "era_share_pct": {label: None for _, _, label in ERAS},
            "median_m2_per_property": None,
        }
    era_counts = {label: 0 for _, _, label in ERAS}
    for y, p, _f in dated:
        era_counts[era_of(y)] += p
    years = sorted(y for y, p, _f in dated for _ in range(p))
    n = len(years)
    median = years[n // 2] if n % 2 else (years[n // 2 - 1] + years[n // 2]) / 2
    m2 = sorted(f / p for _y, p, f in dated if f is not None and p > 0)
    return {
        "n_records": len(rows),
        "total_properties": total,
        "dated_properties": dated_props,
        "missing_property_pct": round((total - dated_props) / total * 100, 2) if total else None,
        "median_year_property_weighted": median if n else None,
        "era_share_pct": {
            label: round(era_counts[label] / dated_props * 100, 1) for _, _, label in ERAS
        },
        "median_m2_per_property": round(m2[len(m2) // 2], 1) if m2 else None,
    }


def main():
    for db in (PROV_DB, MUNI_DB):
        if not db.is_file():
            raise SystemExit("Missing province or municipal sidecar; run make fetch-stock")
    con = duckdb.connect()
    con.execute(f"attach '{PROV_DB}' as prov (read_only)")
    con.execute(f"attach '{MUNI_DB}' as muni (read_only)")
    munis = {
        r[0]: {"municipio": r[1], "hogares": r[2], "viviendas": r[3], "completo": r[4]}
        for r in con.execute(
            "select codigo, municipio, hogares, viviendas, perfil_completo from muni.perfiles"
        ).fetchall()
    }
    statuses = {
        r[0]: r[1]
        for r in con.execute(
            "select ine_municipality, string_agg(distinct match_status, '+' order by match_status) "
            "from prov.buildings group by ine_municipality"
        ).fetchall()
    }
    results = {"eras": [label for _, _, label in ERAS], "municipalities": {}}
    for ine in sorted(munis):
        rows = con.execute(
            "select year_start, dwelling_properties, gross_floor_m2 from prov.buildings "
            "where ine_municipality = ? and dwelling_properties > 0",
            [ine],
        ).fetchall()
        entry = {"municipio": munis[ine]["municipio"], **profile(rows)}
        entry["crs_status"] = statuses.get(ine)
        entry["census_hogares_2021"] = munis[ine]["hogares"]
        entry["census_viviendas_2021"] = munis[ine]["viviendas"]
        if munis[ine]["hogares"]:
            entry["properties_per_household"] = round(
                entry["total_properties"] / munis[ine]["hogares"], 4
            )
        results["municipalities"][ine] = entry
    con.close()
    dated_total = sum(m["dated_properties"] for m in results["municipalities"].values())
    prov_era = {
        label: round(
            sum(
                m["era_share_pct"][label] * m["dated_properties"]
                for m in results["municipalities"].values()
            )
            / dated_total,
            1,
        )
        for _, _, label in ERAS
    }
    rest_meds = sorted(
        m["median_year_property_weighted"]
        for i, m in results["municipalities"].items()
        if i != "41091"
    )
    results["province"] = {
        "n_municipalities": len(results["municipalities"]),
        "total_records": sum(m["n_records"] for m in results["municipalities"].values()),
        "total_properties": sum(m["total_properties"] for m in results["municipalities"].values()),
        "era_share_pct": prov_era,
        "sevilla_city_property_share_pct": round(
            results["municipalities"]["41091"]["total_properties"]
            / sum(m["total_properties"] for m in results["municipalities"].values())
            * 100,
            1,
        ),
        "rest_median_of_median_years": rest_meds[len(rest_meds) // 2],
    }
    results["_meta"] = ols.model_meta(
        str(Path(__file__).resolve()),
        [
            str(PROV_DB.relative_to(ROOT)),
            str(MUNI_DB.relative_to(ROOT)),
        ],
    )
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {ARTIFACT.relative_to(ROOT)}: {len(results['municipalities'])} municipalities")


if __name__ == "__main__":
    main()
