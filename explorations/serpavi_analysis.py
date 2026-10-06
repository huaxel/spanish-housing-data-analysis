"""EXPLORATORY: SERPAVI rents — the rent-vs-sale wedge at municipal grain.

The repo's only municipal price coverage is Barcelona (DIBA sale €/m²
2013-) and Madrid (28 municipios). SERPAVI adds **rents** at municipal
grain nationwide (2,555 municipios at 2024). This script:

1. Validates SERPAVI rent against DIBA rent (muni_bcn.rent_month) on the
   overlapping municipios — a direct same-source-of-truth cross-check.
2. Computes the gross rental yield wedge = rent_month * 12 / sale_eur_m2
   for Barcelona municipios (both DIBA sale and SERPAVI rent).
3. Correlates municipal rents with the electricity-vacancy share
   (censo2021_intensidad) — the overstock hypothesis: high-vacancy
   municipios should carry lower rents.

Writes artifacts/serpavi_analysis.json.
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
    return pearson(ranks(xs), ranks(ys))


def ranks(vs: list[float]) -> list[float]:
    order = sorted(range(len(vs)), key=lambda i: vs[i])
    rk = [0.0] * len(vs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vs[order[j + 1]] == vs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            rk[order[k]] = avg
        i = j + 1
    return rk


# --- 1. SERPAVI vs DIBA rent cross-check (Barcelona municipios, 2023)
# Join by normalized name in Python (duckdb SQL cannot call Python funcs).
bcn_rent = con.execute(
    "SELECT municipio, rent_month FROM muni_bcn WHERE anyo = 2023 AND rent_month IS NOT NULL"
).fetchall()
serp = con.execute(
    "SELECT municipio, valor FROM serpavi_municipal WHERE anyo = 2023 AND medida = 'ALQM2_LV_M_VC'"
).fetchall()
bcn_by = {N(m): (m, d) for m, d in bcn_rent}
serp_by = {N(m): (m, e) for m, e in serp}
cross = []
for key in set(bcn_by) & set(serp_by):
    bm, d = bcn_by[key]
    _sm, e = serp_by[key]
    cross.append(
        {
            "municipio": bm,
            "diba_rent_month": d,
            "serpavi_eur_m2": e,
            "serpavi_implied_month": round(e * 80, 1),  # ~80 m2 typical contract
        }
    )
# correlation of DIBA rent (EUR/month) vs SERPAVI implied month (EUR/m2 * 80)
xs = [r["diba_rent_month"] for r in cross]
ys = [r["serpavi_implied_month"] for r in cross]
corr_rent = {"n": len(xs), "pearson": pearson(xs, ys), "spearman": spearman(xs, ys)}

# --- 2. Gross yield wedge: rent * 12 / sale, Barcelona municipios 2023
sale = con.execute(
    "SELECT municipio, sale_eur_m2 FROM muni_bcn WHERE anyo = 2023 AND sale_eur_m2 IS NOT NULL"
).fetchall()
sale_by = {N(m): (m, sv) for m, sv in sale}
wedges = []
for key in set(serp_by) & set(sale_by):
    sm, e = serp_by[key]
    _sm2, sv = sale_by[key]
    if sv:
        wedges.append(
            {
                "municipio": sm,
                "sale": sv,
                "rent_m2": e,
                "yield_pct": round(e * 12 / sv * 100, 2),
            }
        )
yields = [w["yield_pct"] for w in wedges]
yield_stats = {
    "n": len(yields),
    "median": round(statistics.median(yields), 2),
    "p25": round(sorted(yields)[len(yields) // 4], 2),
    "p75": round(sorted(yields)[3 * len(yields) // 4], 2),
}
bcn = next((w for w in wedges if w["municipio"] == "Barcelona"), None)

# --- 3. Municipal rents vs vacancy share (censo2021_intensidad), nationwide
vac = con.execute(
    """
    WITH v AS (
      SELECT i.codigo,
        SUM(CASE WHEN i.medida='Viviendas totales' THEN i.valor END) tot,
        SUM(CASE WHEN i.medida='Viviendas vacías' THEN i.valor END) vac
      FROM censo2021_intensidad i
      GROUP BY i.codigo
    )
    SELECT v.codigo, ROUND(100.0*v.vac/v.tot,2) vac_pct,
           s.valor rent_m2
    FROM v JOIN serpavi_municipal s
      ON s.codigo = v.codigo AND s.anyo = 2023
    WHERE s.medida = 'ALQM2_LV_M_VC'
    """
).fetchall()
rv = [(r[2], r[1]) for r in vac if r[2] is not None and r[1] is not None]
rent_vac = {
    "n": len(rv),
    "pearson": pearson([x for x, _ in rv], [y for _, y in rv]),
    "spearman": spearman([x for x, _ in rv], [y for _, y in rv]),
}

out = {
    "rent_cross_diba_2023": {
        "n": corr_rent["n"],
        "pearson": corr_rent["pearson"],
        "spearman": corr_rent["spearman"],
    },
    "gross_yield_bcn_2023": {"stats": yield_stats, "barcelona": bcn},
    "rent_vs_vacancy_2023": rent_vac,
    "coverage": {
        "serpavi_munis_2023_rent": len(set(r["municipio"] for r in cross)),
        "serpavi_munis_2024_rent": con.execute(
            "SELECT COUNT(DISTINCT codigo) FROM serpavi_municipal "
            "WHERE anyo=2024 AND medida='ALQM2_LV_M_VC'"
        ).fetchone()[0],
    },
}
print(f"cross DIBA-SERPAVI: n={corr_rent['n']} pearson={corr_rent['pearson']:.3f}")
print(f"yield bcn 2023: median={yield_stats['median']}%  barcelona={bcn}")
print(
    f"rent-vs-vacancy: n={rent_vac['n']} pearson={rent_vac['pearson']:.3f} "
    f"spearman={rent_vac['spearman']:.3f}"
)

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "serpavi_analysis.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
