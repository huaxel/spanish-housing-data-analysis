"""EXPLORATORY: tourist intensity vs rents — SERPAVI extends the test nationally.

`panel_tourist.md` found a null (tourist change → sale/rent growth) within
Barcelona municipios. Its stated external-validity question was Balears /
Canarias — untestable because rents existed only for Barcelona (DIBA).
SERPAVI now gives municipal rents nationwide. This extension:

1. **Replication with an independent rent source**: tourist intensity (DIBA
   `muni_bcn.tourist`, per-1,000) vs SERPAVI rent **level** (2023) and
   rent **growth** (2021→2024) across the 205 overlapping municipios —
   same cross-section the old panel called a null, now with SERPAVI rents
   instead of DIBA rents.
2. **National provincial cross-section**: INE turísticas (registered tourist
   dwellings per 1,000 pop, province grain) vs SERPAVI median municipal
   rent level (2023) and 2015–2024 growth by province — the Balears /
   Canarias test the old panel could not run.

Both are levels/cross-sections (not the within-FE panel); the panel's
within-variation null stands on its own. Writes artifacts/tourist_rents.json.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402
from spanish_housing.ine_api import norm_name as N  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    if not vx or not vy:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / (vx * vy)


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    rk = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            rk[order[k]] = avg
        i = j + 1
    return pearson(rk, [ys[x] for x in order])


# --- 1. Barcelona municipios: tourist intensity vs SERPAVI rent level/growth
tour = con.execute(
    "SELECT municipio, anyo, tourist, poblacion FROM muni_bcn "
    "WHERE tourist IS NOT NULL AND poblacion IS NOT NULL"
).fetchall()
tour_pc: dict[str, float] = {}
for m, a, t, p in tour:
    if p and t is not None:
        tour_pc.setdefault(m, []).append((a, t / p * 1000))
# 2019 tourist intensity (pre-regulatory peak), like the old panel
tour_base = {m: sorted(v)[-1][1] for m, v in tour_pc.items()}

serp = con.execute(
    "SELECT municipio, anyo, valor FROM serpavi_municipal "
    "WHERE medida = 'ALQM2_LV_M_VC' AND anyo IN (2021, 2024)"
).fetchall()
rent: dict[str, dict[int, float]] = {}
for m, a, v in serp:
    rent.setdefault(m, {})[a] = v

bcn_rows = []
for m, tp in tour_base.items():
    r = rent.get(m, {})
    if tp is None or 2021 not in r or 2024 not in r:
        continue
    bcn_rows.append(
        {
            "municipio": m,
            "tour_pc": round(tp, 2),
            "rent_2021": r[2021],
            "rent_2024": r[2024],
            "rent_growth_pct": round((r[2024] / r[2021] - 1) * 100, 2),
        }
    )

# --- 2. Provincial: INE turísticas intensity vs SERPAVI rent level/growth
tur = {
    (N(t), a): v
    for t, a, v in con.execute(
        "SELECT territorio, anyo, viv_turisticas FROM "
        "read_parquet('data/raw/parquet/turisticas_counts.parquet')"
    ).fetchall()
}
pob = {
    (N(t), a): v
    for t, a, v in con.execute(
        "SELECT provincia, anyo, poblacion FROM mart_provincia_anual WHERE anyo IN (2020, 2024)"
    ).fetchall()
}
prov_rent = con.execute(
    "SELECT provincia, anyo, valor FROM serpavi_municipal "
    "WHERE medida = 'ALQM2_LV_M_VC' AND anyo IN (2020, 2024)"
).fetchall()
pr: dict[str, dict[int, list[float]]] = {}
for p, a, v in prov_rent:
    pr.setdefault(p, {}).setdefault(a, []).append(v)

prov_rows = []
for prov, years in pr.items():
    if 2020 not in years or 2024 not in years or not years[2020] or not years[2024]:
        continue
    key = N(prov)
    tv = tur.get((key, 2020))
    pp = pob.get((key, 2020))
    if tv is None or not pp:
        continue
    r20 = statistics.median(years[2020])
    r24 = statistics.median(years[2024])
    prov_rows.append(
        {
            "provincia": prov,
            "tour_pc": round(tv / pp * 1000, 2),
            "rent_2020": round(r20, 2),
            "rent_2024": round(r24, 2),
            "rent_growth_pct": round((r24 / r20 - 1) * 100, 2),
        }
    )

out = {
    "bcn_municipal": {
        "n": len(bcn_rows),
        "corr_tour_vs_rent_level": {
            "pearson": pearson(
                [r["tour_pc"] for r in bcn_rows], [r["rent_2024"] for r in bcn_rows]
            ),
            "spearman": spearman(
                [r["tour_pc"] for r in bcn_rows], [r["rent_2024"] for r in bcn_rows]
            ),
        },
        "corr_tour_vs_rent_growth": {
            "pearson": pearson(
                [r["tour_pc"] for r in bcn_rows], [r["rent_growth_pct"] for r in bcn_rows]
            ),
            "spearman": spearman(
                [r["tour_pc"] for r in bcn_rows], [r["rent_growth_pct"] for r in bcn_rows]
            ),
        },
        "rows": bcn_rows,
    },
    "provincial": {
        "n": len(prov_rows),
        "corr_tour_vs_rent_level": {
            "pearson": pearson(
                [r["tour_pc"] for r in prov_rows], [r["rent_2024"] for r in prov_rows]
            ),
            "spearman": spearman(
                [r["tour_pc"] for r in prov_rows], [r["rent_2024"] for r in prov_rows]
            ),
        },
        "corr_tour_vs_rent_growth": {
            "pearson": pearson(
                [r["tour_pc"] for r in prov_rows], [r["rent_growth_pct"] for r in prov_rows]
            ),
            "spearman": spearman(
                [r["tour_pc"] for r in prov_rows], [r["rent_growth_pct"] for r in prov_rows]
            ),
        },
        "top_tourist": sorted(prov_rows, key=lambda r: -r["tour_pc"])[:5],
        "bottom_tourist": sorted(prov_rows, key=lambda r: r["tour_pc"])[:5],
    },
}
print(
    f"bcn: n={len(bcn_rows)} tour-vs-level "
    f"P={out['bcn_municipal']['corr_tour_vs_rent_level']['pearson']:.3f} "
    f"S={out['bcn_municipal']['corr_tour_vs_rent_level']['spearman']:.3f}"
)
print(
    f"     tour-vs-growth "
    f"P={out['bcn_municipal']['corr_tour_vs_rent_growth']['pearson']:.3f} "
    f"S={out['bcn_municipal']['corr_tour_vs_rent_growth']['spearman']:.3f}"
)
print(
    f"prov: n={len(prov_rows)} tour-vs-level "
    f"P={out['provincial']['corr_tour_vs_rent_level']['pearson']:.3f} "
    f"S={out['provincial']['corr_tour_vs_rent_level']['spearman']:.3f}"
)
print(
    f"      tour-vs-growth "
    f"P={out['provincial']['corr_tour_vs_rent_growth']['pearson']:.3f} "
    f"S={out['provincial']['corr_tour_vs_rent_growth']['spearman']:.3f}"
)
for r in out["provincial"]["top_tourist"]:
    print(
        f"  top: {r['provincia']:<26} tour={r['tour_pc']:>7}"
        f" rent24={r['rent_2024']:>6} g={r['rent_growth_pct']:>6}%"
    )

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "tourist_rents.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
