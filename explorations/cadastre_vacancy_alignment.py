"""Vacancy alignment: cadastre stock vs electric-consumption vacancy estimates.

Descriptive exploration only: cross-references housing-property counts from
the cadastre pilot with (a) the Censo 2021 electric-consumption dwelling
classes for Sevilla municipality (41091) and (b) SIM's per-barrio
deshabitadas counts evaluated against BOTH the SIM family-dwelling
denominator and the cadastre-property denominator. Vacancy figures are
reported as assumption-dependent rate ranges, never as measured rates:
stock declared != available housing, electric vacancy != available housing,
and the sources have different vintages and definitions.
Writes artifacts/cadastre_vacancy_alignment.json.
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
ARTIFACT = ROOT / "artifacts" / "cadastre_vacancy_alignment.json"
SEVILLA_MUNI = "41091"


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def main():
    ar = _load_module("cadastre_age_rent", "explorations/cadastre_age_rent.py")
    if not STOCK_DB.is_file() or not MARTS_DB.is_file():
        raise SystemExit("Missing stock or marts database; run make build first")
    con = duckdb.connect()
    con.execute(f"attach '{STOCK_DB}' as stock (read_only)")
    con.execute(f"attach '{MARTS_DB}' as housing (read_only)")

    cadastre_city_total = con.execute(
        "select sum(dwelling_properties) from stock.buildings where dwelling_properties > 0"
    ).fetchone()[0]
    cad_props = {
        r[0]: r[1]
        for r in con.execute(
            "select barrio_id, sum(dwelling_properties) from stock.buildings "
            "where dwelling_properties > 0 and barrio_id is not null group by barrio_id"
        ).fetchall()
    }
    unassigned_properties = con.execute(
        "select sum(dwelling_properties) from stock.buildings "
        "where dwelling_properties > 0 and barrio_id is null"
    ).fetchone()[0]
    measures = {
        r[0]: r[1]
        for r in con.execute(
            "select medida, valor from housing.censo2021_intensidad where codigo = ?",
            [SEVILLA_MUNI],
        ).fetchall()
    }
    sim = {
        r[0]: {"barrio": r[1], "familiares": r[2], "deshabitadas": r[3]}
        for r in con.execute(
            "select idg, barrio, viviendas_familiares, deshabitadas "
            "from housing.sevilla_sim_vivienda"
        ).fetchall()
    }
    con.close()

    total = measures.get("Viviendas totales")
    vacias = measures.get("Viviendas vacías")
    bajo = measures.get("Viviendas con bajo consumo")
    esporadico = measures.get("Viviendas de uso esporádico")
    upper_band = vacias + bajo + esporadico

    city = {
        "census_total_dwellings": total,
        "census_empty_dwellings": vacias,
        "census_low_consumption": bajo,
        "census_sporadic_use": esporadico,
        "upper_nonoccupied_band": upper_band,
        "cadastre_declared_properties": cadastre_city_total,
        "cadastre_to_census_ratio": round(cadastre_city_total / total, 6),
        "census_self_empty_rate_pct": round(vacias / total * 100, 2),
        "cadastre_denominated_empty_rate_pct": round(vacias / cadastre_city_total * 100, 2),
        "upper_band_census_rate_pct": round(upper_band / total * 100, 2),
        "upper_band_cadastre_rate_pct": round(upper_band / cadastre_city_total * 100, 2),
    }

    joined = {
        bid: (cad_props[bid], sim[bid])
        for bid in cad_props
        if sim.get(bid) and sim[bid]["deshabitadas"] is not None
    }
    no_rehab = sorted(
        f"{bid} {sim[bid]['barrio'] if bid in sim else '?'}"
        for bid in cad_props
        if bid not in joined
    )
    sim_only = sorted(b for b in sim if b not in cad_props)
    era_only = sorted(b for b in cad_props if b not in sim)
    coverage_extra = {"records_unassigned_to_barrio_properties": unassigned_properties}

    ids = sorted(joined)
    cp = [float(joined[b][0]) for b in ids]
    fam = [float(joined[b][1]["familiares"]) for b in ids]
    des = [float(joined[b][1]["deshabitadas"]) for b in ids]
    sim_rates = [d / f * 100 for d, f in zip(des, fam, strict=True)]
    cad_rates = [d / p * 100 for d, p in zip(des, cp, strict=True)]
    ratios = sorted(p / f for p, f in zip(cp, fam, strict=True))

    barrio_rows = {
        bid: {
            "barrio": joined[bid][1]["barrio"],
            "cadastre_properties": joined[bid][0],
            "sim_family_dwellings": joined[bid][1]["familiares"],
            "sim_deshabitadas": joined[bid][1]["deshabitadas"],
            "sim_own_rate_pct": round(sim_rates[i], 2),
            "cadastre_referenced_rate_pct": round(cad_rates[i], 2),
        }
        for i, bid in enumerate(ids)
    }
    results = {
        "method": (
            "Descriptive alignment; vacancy figures are assumption-dependent "
            "rate ranges, not measured rates; equal barrio weight for "
            "cross-barrio statistics"
        ),
        "city_41091": city,
        "coverage": {
            **coverage_extra,
            "era_barrios": len(cad_props),
            "sim_barrios": len(sim),
            "joined_with_deshabitadas": len(joined),
            "cadastre_barrios_without_deshabitadas": no_rehab,
            "sim_only_codes": sim_only,
            "cadastre_only_codes": era_only,
        },
        "denominator_consistency": {
            "spearman_cadastre_props_vs_sim_familiares": round(ar.spearman(cp, fam), 6),
            "joined_cadastre_properties": int(sum(cp)),
            "joined_sim_family_dwellings": int(sum(fam)),
            "joined_sim_deshabitadas": int(sum(des)),
            "denominator_ratio_median": round(ratios[len(ratios) // 2], 6),
            "denominator_ratio_min": round(ratios[0], 6),
            "denominator_ratio_max": round(ratios[-1], 6),
        },
        "rates": {
            "sim_own_rate_mean_pct": round(mean(sim_rates), 2),
            "sim_own_rate_min_pct": round(min(sim_rates), 2),
            "sim_own_rate_max_pct": round(max(sim_rates), 2),
            "cadastre_referenced_rate_mean_pct": round(mean(cad_rates), 2),
            "cadastre_referenced_rate_min_pct": round(min(cad_rates), 2),
            "cadastre_referenced_rate_max_pct": round(max(cad_rates), 2),
            "spearman_sim_rate_vs_cadastre_rate": round(ar.spearman(sim_rates, cad_rates), 6),
        },
        "barrios": barrio_rows,
        "_meta": ols.model_meta(
            str(Path(__file__).resolve()),
            [
                str(STOCK_DB.relative_to(ROOT)),
                str(MARTS_DB.relative_to(ROOT)),
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
        f"city empty rate {city['census_self_empty_rate_pct']}-"
        f"{city['cadastre_denominated_empty_rate_pct']} pct range"
    )


if __name__ == "__main__":
    main()
