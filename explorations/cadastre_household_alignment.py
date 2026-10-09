"""Household alignment: cadastre stock vs census/SIM households per barrio.

Descriptive exploration only: cross-references declared housing-property
counts from the cadastre pilot with (a) the official Censo 2021 household
count for Sevilla municipality (INE 59543 via the municipal sidecar) and
(b) SIM's per-barrio household series (latest year 2021). Coverage ratios
properties-per-household are documented as definitional comparisons, not
occupancy rates: cadastral properties, census dwellings and households are
different units, with different vintages and reference dates.
Writes artifacts/cadastre_household_alignment.json.
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
MARTS_DB = PROCESSED / "marts.duckdb"
MUNI_DB = PROCESSED / "sevilla_2021.duckdb"
ARTIFACT = ROOT / "artifacts" / "cadastre_household_alignment.json"
SEVILLA_MUNI = "41091"
SIM_YEAR = 2021


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def main():
    ar = _load_module("cadastre_age_rent", "explorations/cadastre_age_rent.py")
    for db in (STOCK_DB, MARTS_DB, MUNI_DB):
        if not db.is_file():
            raise SystemExit("Missing sidecar; run make build first")
    con = duckdb.connect()
    con.execute(f"attach '{STOCK_DB}' as stock (read_only)")
    con.execute(f"attach '{MARTS_DB}' as housing (read_only)")
    con.execute(f"attach '{MUNI_DB}' as muni (read_only)")

    census_hh = con.execute(
        "select hogares from muni.perfiles where codigo = ?", [SEVILLA_MUNI]
    ).fetchone()[0]
    cad_props = {
        r[0]: r[1]
        for r in con.execute(
            "select barrio_id, sum(dwelling_properties) from stock.buildings "
            "where dwelling_properties > 0 and barrio_id is not null group by barrio_id"
        ).fetchall()
    }
    cad_city = con.execute(
        "select sum(dwelling_properties) from stock.buildings where dwelling_properties > 0"
    ).fetchone()[0]
    sim_hh = {
        r[0]: (r[1], r[2])
        for r in con.execute(
            "select idg, barrio, hogares from housing.sevilla_sim_poblacion_hogares where anyo = ?",
            [SIM_YEAR],
        ).fetchall()
    }
    con.close()

    joined = {bid: (cad_props[bid], sim_hh[bid]) for bid in cad_props if bid in sim_hh}
    sim_only = sorted(b for b in sim_hh if b not in cad_props)
    cad_only = sorted(b for b in cad_props if b not in sim_hh)

    ids = sorted(joined)
    cp = [float(joined[b][0]) for b in ids]
    hh = [float(joined[b][1][1]) for b in ids]
    hog_per_prop = [h / p for h, p in zip(hh, cp, strict=True)]
    srt = sorted(hog_per_prop)

    def extremes(reverse: bool, k: int = 5) -> list[dict]:
        return [
            {
                "barrio": joined[b][1][0],
                "cadastre_properties": joined[b][0],
                "sim_households_2021": joined[b][1][1],
                "households_per_property": round(joined[b][1][1] / joined[b][0], 4),
            }
            for b in sorted(ids, key=lambda b: joined[b][1][1] / joined[b][0], reverse=reverse)[:k]
        ]

    results = {
        "method": (
            "Descriptive definitional comparison; coverage ratios, not "
            "occupancy rates; equal barrio weight for cross-barrio statistics"
        ),
        "definitions": {
            "cadastre_properties": "Declared housing property units (BU records), cadastre extract",
            "census_households": "INE 59543 municipal households, 1 January 2021",
            "sim_households": "SIM municipal household series per barrio, latest 2021",
        },
        "city": {
            "census_households_2021": census_hh,
            "cadastre_properties_barrio_assigned": sum(cp),
            "cadastre_properties_full_extract": cad_city,
            "sim_households_joined": int(sum(hh)),
            "properties_per_census_household": round(cad_city / census_hh, 4),
            "properties_per_sim_household": round(sum(cp) / sum(hh), 4),
        },
        "coverage": {
            "cadastre_barrios": len(cad_props),
            "sim_barrios": len(sim_hh),
            "joined": len(joined),
            "sim_only_codes": sim_only,
            "cadastre_only_codes": cad_only,
        },
        "alignment": {
            "spearman_properties_vs_households": round(ar.spearman(cp, hh), 6),
            "households_per_property_median": round(srt[len(srt) // 2], 4),
            "households_per_property_min": round(srt[0], 4),
            "households_per_property_max": round(srt[-1], 4),
        },
        "lowest_households_per_property": extremes(False),
        "highest_households_per_property": extremes(True),
        "barrios": {
            bid: {
                "barrio": joined[bid][1][0],
                "cadastre_properties": joined[bid][0],
                "sim_households_2021": joined[bid][1][1],
                "households_per_property": round(joined[bid][1][1] / joined[bid][0], 4),
            }
            for bid in ids
        },
        "_meta": ols.model_meta(
            str(Path(__file__).resolve()),
            [
                str(STOCK_DB.relative_to(ROOT)),
                str(MARTS_DB.relative_to(ROOT)),
                str(MUNI_DB.relative_to(ROOT)),
            ],
        ),
    }
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}: {len(joined)} barrios, "
        f"{results['city']['properties_per_census_household']} properties per census household"
    )


if __name__ == "__main__":
    main()
