"""Cross-check cadastre era profiles with SIM building-condition scores per barrio.

Descriptive exploration only: joins the property-weighted construction-era
profile (same proxy as explorations/cadastre_eras.py) with SIM's
calidad_colectiva / calidad_unifamiliar scores and the rehabilitation
estimate, per Sevilla barrio, equal barrio weight. No causal claim, no
significance testing.

Central empirical caution: SIM's calidad_colectiva score correlates +0.87
with SIM's rehabilitation estimate across barrios, so the two SIM fields
are near-collinear (one is plausibly derived from the other). Whichever
direction the SIM scale runs, the two fields must not be treated as
independent confirmations of anything.
Writes artifacts/cadastre_era_quality.json.
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
ARTIFACT = ROOT / "artifacts" / "cadastre_era_quality.json"


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
        r[0]: {"calidad_col": r[1], "calidad_uni": r[2], "rehab_pct": r[3]}
        for r in con.execute(
            "select idg, calidad_colectiva, calidad_unifamiliar, "
            "rehabilitacion_estimada_pct from housing.sevilla_sim_vivienda"
        ).fetchall()
    }
    con.close()

    def joined_with(field: str) -> dict:
        return {
            bid: (profiles[bid], sim[bid])
            for bid in profiles
            if sim.get(bid, {}).get(field) is not None
        }

    jc = joined_with("calidad_col")
    ju = joined_with("calidad_uni")

    def corr_block(join: dict, field: str) -> dict:
        ids = sorted(join)
        return {
            "spearman": round(
                age_rent.spearman(
                    [join[b][0]["median_year"] for b in ids],
                    [float(join[b][1][field]) for b in ids],
                ),
                6,
            ),
            "pearson": round(
                age_rent.pearson(
                    [join[b][0]["median_year"] for b in ids],
                    [float(join[b][1][field]) for b in ids],
                ),
                6,
            ),
            "n": len(ids),
        }

    # SIM-internal collinearity: calidad_colectiva vs rehab (both non-null)
    both_ids = sorted(
        b
        for b in profiles
        if sim.get(b) and sim[b]["calidad_col"] is not None and sim[b]["rehab_pct"] is not None
    )
    col_vs_rehab = {
        "spearman": round(
            age_rent.spearman(
                [float(sim[b]["calidad_col"]) for b in both_ids],
                [float(sim[b]["rehab_pct"]) for b in both_ids],
            ),
            6,
        ),
        "pearson": round(
            age_rent.pearson(
                [float(sim[b]["calidad_col"]) for b in both_ids],
                [float(sim[b]["rehab_pct"]) for b in both_ids],
            ),
            6,
        ),
        "n": len(both_ids),
    }

    # Terziles of the collective score by median construction year
    ids_c = sorted(jc)
    by_age = sorted(ids_c, key=lambda b: jc[b][0]["median_year"])
    third = len(by_age) // 3
    terciles = []
    for name, group in (
        ("oldest_third", by_age[:third]),
        ("middle_third", by_age[third : len(by_age) - third]),
        ("newest_third", by_age[len(by_age) - third :]),
    ):
        vals = [float(jc[b][1]["calidad_col"]) for b in group]
        terciles.append(
            {
                "group": name,
                "n_barrios": len(group),
                "median_year_range": [
                    jc[group[0]][0]["median_year"],
                    jc[group[-1]][0]["median_year"],
                ]
                if group
                else None,
                "mean_calidad_col": round(sum(vals) / len(vals), 2),
            }
        )

    def extremes(reverse: bool, k: int = 5) -> list[dict]:
        return [
            {
                "barrio": jc[b][0]["barrio"],
                "distrito": jc[b][0]["distrito"],
                "calidad_colectiva": jc[b][1]["calidad_col"],
                "median_year": jc[b][0]["median_year"],
                "rehab_pct": jc[b][1]["rehab_pct"],
            }
            for b in sorted(ids_c, key=lambda b: float(jc[b][1]["calidad_col"]), reverse=reverse)[
                :k
            ]
        ]

    results = {
        "method": (
            "Descriptive cross-section, equal barrio weight; no causal claim, "
            "no significance testing"
        ),
        "calidad_definition": (
            "SIM calidad_colectiva / calidad_unifamiliar scores (published "
            "without documented derivation, direction or reference year). "
            "Empirically the collective score correlates +0.87 with SIM's "
            "rehabilitation estimate, so higher score tracks more estimated "
            "need; the two SIM fields are near-collinear, not independent"
        ),
        "age_definition": (
            "Property-weighted median earliest construction year of BU records "
            "per barrio; record-date proxy, not individual dwelling age"
        ),
        "coverage": {
            "era_barrios": len(profiles),
            "joined_calidad_colectiva": len(jc),
            "joined_calidad_unifamiliar": len(ju),
            "unifamiliar_null_barrios": sorted(
                f"{bid} {profiles[bid]['barrio']}" for bid in profiles if bid not in ju
            ),
        },
        "correlations": {
            "median_year_vs_calidad_colectiva": corr_block(jc, "calidad_col"),
            "median_year_vs_calidad_unifamiliar": corr_block(ju, "calidad_uni"),
            "calidad_colectiva_vs_rehab": col_vs_rehab,
        },
        "median_year_terciles_calidad": terciles,
        "lowest_score_barrios": extremes(False),
        "highest_score_barrios": extremes(True),
        "barrios": {
            bid: {
                "barrio": jc[bid][0]["barrio"],
                "distrito": jc[bid][0]["distrito"],
                "median_year": jc[bid][0]["median_year"],
                "calidad_colectiva": jc[bid][1]["calidad_col"],
                "calidad_unifamiliar": jc[bid][1]["calidad_uni"],
                "rehab_pct": jc[bid][1]["rehab_pct"],
            }
            for bid in ids_c
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
        f"wrote {ARTIFACT.relative_to(ROOT)}: {len(jc)}/{len(ju)} barrios "
        f"(colectiva/unifamiliar), calidad-vs-rehab spearman "
        f"{col_vs_rehab['spearman']}"
    )


if __name__ == "__main__":
    main()
