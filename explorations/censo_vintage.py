"""Exploration: Censo 2021 housing stock by construction vintage and occupancy status.

Computes national and provincial breakdowns from censo2021_viviendas in marts.duckdb:
1. National stock by construction era band and principal vs non-principal status.
2. Decade-over-decade additions: 2001-2010 boom vs 2011-2020 post-bust tightening.
3. Provincial absorption of boom-era (2001-2010) construction.
4. Total provincial non-principal dwelling shares.

Descriptive findings only; no causal claims.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

MARTS = PROCESSED / "marts.duckdb"
ARTIFACT = ROOT / "artifacts" / "censo_vintage.json"

BANDS_ORDER = [
    "Antes de 1900",
    "De 1900 a 1920",
    "De 1921 a 1940",
    "De 1941 a 1950",
    "De 1951 a 1960",
    "De 1961 a 1970",
    "De 1971 a 1980",
    "De 1981 a 1990",
    "De 1991 a 2000",
    "De 2001 a 2010",
    "De 2011 a 2020",
    "No consta",
]


def main() -> None:
    if not MARTS.is_file():
        raise SystemExit("Missing marts.duckdb; run make build first")

    con = duckdb.connect(str(MARTS), read_only=True)

    # 1. National total
    tot_row = con.execute("""
        SELECT sum(case when tipo = 'Vivienda principal' then viviendas else 0 end),
               sum(case when tipo = 'Vivienda no principal' then viviendas else 0 end),
               sum(viviendas)
        FROM censo2021_viviendas
        WHERE tipo <> 'Total' AND banda = 'Total'
    """).fetchone()
    assert tot_row is not None
    n_principal, n_no_principal, n_total = tot_row

    nacional_total = {
        "viviendas_total": n_total,
        "viviendas_principal": n_principal,
        "viviendas_no_principal": n_no_principal,
        "pct_no_principal": round(100.0 * n_no_principal / n_total, 1),
    }

    # 2. National bands
    band_rows = con.execute("""
        SELECT banda,
               sum(case when tipo = 'Vivienda principal' then viviendas else 0 end) as principal,
               sum(case when tipo = 'Vivienda no principal' then viviendas else 0 end)
                   as no_principal,
               sum(viviendas) as total,
               round(100.0 * sum(viviendas) / (
                   SELECT sum(viviendas) FROM censo2021_viviendas
                   WHERE tipo <> 'Total' AND banda = 'Total'
               ), 1) as pct_stock,
               round(100.0 * sum(
                   case when tipo = 'Vivienda no principal' then viviendas else 0 end
               ) / nullif(sum(viviendas), 0), 1) as pct_no_principal
        FROM censo2021_viviendas
        WHERE tipo <> 'Total' AND banda <> 'Total'
        GROUP BY banda
    """).fetchall()

    bands_dict = {
        row[0]: {
            "banda": row[0],
            "principal": row[1],
            "no_principal": row[2],
            "total": row[3],
            "pct_stock": row[4],
            "pct_no_principal": row[5],
        }
        for row in band_rows
    }

    nacional_bandas = [bands_dict[b] for b in BANDS_ORDER if b in bands_dict]

    # 3. Boom vs post-boom comparison
    boom_dwellings = bands_dict["De 2001 a 2010"]["total"]
    post_boom_dwellings = bands_dict["De 2011 a 2020"]["total"]
    boom_vs_postboom = {
        "boom_2001_2010": boom_dwellings,
        "post_boom_2011_2020": post_boom_dwellings,
        "ratio_boom_to_post": round(boom_dwellings / post_boom_dwellings, 2),
    }

    # 4. Provincial boom construction absorption (2001-2010)
    boom_prov_rows = con.execute("""
        SELECT cpro, provincia,
               sum(case when tipo = 'Vivienda principal' then viviendas else 0 end) as principal,
               sum(case when tipo = 'Vivienda no principal' then viviendas else 0 end)
                   as no_principal,
               sum(viviendas) as total,
               round(100.0 * sum(
                   case when tipo = 'Vivienda no principal' then viviendas else 0 end
               ) / nullif(sum(viviendas), 0), 1) as pct_no_principal
        FROM censo2021_viviendas
        WHERE banda = 'De 2001 a 2010' AND tipo <> 'Total'
        GROUP BY cpro, provincia
        ORDER BY pct_no_principal DESC
    """).fetchall()

    boom_by_province = {
        row[0]: {
            "cpro": row[0],
            "provincia": row[1],
            "principal": row[2],
            "no_principal": row[3],
            "total": row[4],
            "pct_no_principal": row[5],
        }
        for row in boom_prov_rows
    }

    # 5. Total provincial stock non-principal shares
    total_prov_rows = con.execute("""
        SELECT cpro, provincia,
               sum(case when tipo = 'Vivienda principal' then viviendas else 0 end) as principal,
               sum(case when tipo = 'Vivienda no principal' then viviendas else 0 end)
                   as no_principal,
               sum(viviendas) as total,
               round(100.0 * sum(
                   case when tipo = 'Vivienda no principal' then viviendas else 0 end
               ) / nullif(sum(viviendas), 0), 1) as pct_no_principal
        FROM censo2021_viviendas
        WHERE banda = 'Total' AND tipo <> 'Total'
        GROUP BY cpro, provincia
        ORDER BY pct_no_principal DESC
    """).fetchall()

    total_by_province = {
        row[0]: {
            "cpro": row[0],
            "provincia": row[1],
            "principal": row[2],
            "no_principal": row[3],
            "total": row[4],
            "pct_no_principal": row[5],
        }
        for row in total_prov_rows
    }

    con.close()

    meta = ols.model_meta(
        str(Path(__file__).resolve()),
        [str(MARTS.relative_to(ROOT))],
    )

    out = {
        "nacional_total": nacional_total,
        "nacional_bandas": nacional_bandas,
        "boom_vs_postboom": boom_vs_postboom,
        "boom_by_province": boom_by_province,
        "total_by_province": total_by_province,
        "_meta": meta,
    }

    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(nacional_bandas)} bands and 52 provinces to {ARTIFACT}")


if __name__ == "__main__":
    main()
