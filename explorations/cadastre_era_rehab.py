"""Cross-check cadastre era profiles with SIM rehabilitation need per barrio.

Descriptive exploration only: joins the property-weighted construction-era
profile (same proxy as explorations/cadastre_eras.py) with SIM's estimated
rehabilitation need (rehabilitacion_estimada_pct, undated SIM layer) and
SIM's collective-housing construction-year reference, per Sevilla barrio,
equal barrio weight. No causal claim, no significance testing.

The SIM rehabilitation estimate's derivation is undocumented and may itself
be derived from SIM age and quality fields; correlations involving it are
possibly mechanical. Writes artifacts/cadastre_era_rehab.json.
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
ARTIFACT = ROOT / "artifacts" / "cadastre_era_rehab.json"


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    age_rent = _load_module("cadastre_age_rent", "explorations/cadastre_age_rent.py")
    if not STOCK_DB.is_file() or not MARTS_DB.is_file():
        raise SystemExit("Missing stock or marts database; run make build first")
    con = duckdb.connect()
    con.execute(f"attach '{STOCK_DB}' as stock (read_only)")
    con.execute(f"attach '{MARTS_DB}' as housing (read_only)")
    profiles = age_rent.era_profiles(con)
    sim = {
        r[0]: {"rehab_pct": r[1], "sim_ref_year": r[2]}
        for r in con.execute(
            "select idg, rehabilitacion_estimada_pct, antiguedad_colectiva_anos "
            "from housing.sevilla_sim_vivienda"
        ).fetchall()
    }
    con.close()

    joined = {
        bid: (profiles[bid], sim[bid])
        for bid in profiles
        if sim.get(bid, {}).get("rehab_pct") is not None
    }
    no_rehab = sorted(f"{bid} {profiles[bid]['barrio']}" for bid in profiles if bid not in joined)
    ids = sorted(joined)
    median_year = [joined[b][0]["median_year"] for b in ids]
    pre_1951 = [joined[b][0]["Pre-1951"] for b in ids]
    rehab = [float(joined[b][1]["rehab_pct"]) for b in ids]

    def both(a: list[float], b: list[float] | None) -> dict | None:
        if b is None or len(a) != len(b):
            pairs = [(x, y) for x, y in zip(a, b or [], strict=False) if y is not None]
            if len(pairs) < 3:
                return None
            a = [p[0] for p in pairs]
            b = [p[1] for p in pairs]
        return {
            "spearman": round(age_rent.spearman(a, b), 6),
            "pearson": round(age_rent.pearson(a, b), 6),
            "n": len(a),
        }

    # Median-year terciles of rehabilitation need
    by_age = sorted(ids, key=lambda b: joined[b][0]["median_year"])
    third = len(by_age) // 3
    terciles = []
    for name, group in (
        ("oldest_third", by_age[:third]),
        ("middle_third", by_age[third : len(by_age) - third]),
        ("newest_third", by_age[len(by_age) - third :]),
    ):
        terciles.append(
            {
                "group": name,
                "n_barrios": len(group),
                "median_year_range": [
                    joined[group[0]][0]["median_year"],
                    joined[group[-1]][0]["median_year"],
                ]
                if group
                else None,
                "mean_rehab_pct": round(
                    sum(float(joined[b][1]["rehab_pct"]) for b in group) / len(group), 2
                ),
                "median_rehab_pct": round(
                    sorted(float(joined[b][1]["rehab_pct"]) for b in group)[len(group) // 2],
                    2,
                )
                if group
                else None,
            }
        )

    top_rehab = [
        {
            "barrio": joined[b][0]["barrio"],
            "distrito": joined[b][0]["distrito"],
            "rehab_pct": joined[b][1]["rehab_pct"],
            "median_year": joined[b][0]["median_year"],
            "pre_1951_share": round(joined[b][0]["Pre-1951"], 1),
        }
        for b in sorted(ids, key=lambda b: (-float(joined[b][1]["rehab_pct"]), b))[:10]
    ]

    sim_ref_ids = [b for b in ids if joined[b][1]["sim_ref_year"] is not None]
    results = {
        "method": (
            "Descriptive cross-section, equal barrio weight; no causal claim, "
            "no significance testing"
        ),
        "rehab_definition": (
            "SIM rehabilitacion_estimada_pct: estimated share of dwellings in "
            "need of rehabilitation, undated SIM layer with undocumented "
            "derivation (possibly co-derived with SIM age/quality fields)"
        ),
        "age_definition": (
            "Property-weighted median earliest construction year of BU records "
            "per barrio; record-date proxy, not individual dwelling age"
        ),
        "sim_ref_definition": (
            "antiguedad_colectiva_anos: SIM year-like construction reference "
            "for collective housing, not elapsed age; snapshot year unknown"
        ),
        "coverage": {
            "era_barrios": len(profiles),
            "sim_barrios": len(sim),
            "joined_with_rehab": len(joined),
            "era_barrios_without_rehab": no_rehab,
        },
        "correlations": {
            "median_year_vs_rehab": both(median_year, rehab),
            "pre_1951_share_vs_rehab": both(pre_1951, rehab),
            "sim_ref_year_vs_rehab": both(
                [float(joined[b][1]["sim_ref_year"]) for b in sim_ref_ids],
                [float(joined[b][1]["rehab_pct"]) for b in sim_ref_ids],
            ),
            "median_year_vs_sim_ref_year": both(
                [joined[b][0]["median_year"] for b in sim_ref_ids],
                [float(joined[b][1]["sim_ref_year"]) for b in sim_ref_ids],
            ),
        },
        "median_year_terciles_rehab": terciles,
        "top_rehab_barrios": top_rehab,
        "barrios": {
            bid: {
                "barrio": joined[bid][0]["barrio"],
                "distrito": joined[bid][0]["distrito"],
                "median_year": joined[bid][0]["median_year"],
                "pre_1951_share": round(joined[bid][0]["Pre-1951"], 1),
                "rehab_pct": joined[bid][1]["rehab_pct"],
                "sim_ref_year": joined[bid][1]["sim_ref_year"],
            }
            for bid in ids
        },
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
        f"spearman median_year vs rehab "
        f"{results['correlations']['median_year_vs_rehab']['spearman']}"
    )


if __name__ == "__main__":
    main()
