"""EXPLORATORY: national municipal rents and vacancy from muni_all.

Descriptive only — no causal claim. muni_all merges all 52 DPOP municipal
tables with SERPAVI median rent and Censo 2011 vacancy. This script:

1. Rent geography 2024: median/P25/P75 across municipios with published
   rent (unweighted; SERPAVI publishes populated cells only).
2. Rent growth 2011→2024 on paired municipios: median growth + fastest.
3. Rent 2024 vs 2011 vacancy share: Pearson/Spearman (overhang geography).
4. Population growth 2011→2024 vs rent growth: demand co-movement.

Writes artifacts/municipios_nacional.json.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

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
    rx = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rx[order[k]] = (i + j) / 2 + 1
        i = j + 1
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    ry = [0.0] * len(ys)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and ys[order[j + 1]] == ys[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ry[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return pearson(rx, ry)


def pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, int(len(s) * q))]


# --- 1. Rent geography 2024 (populated SERPAVI cells only, unweighted)
r24 = con.execute(
    "SELECT municipio, provincia, rent_eur_m2 FROM muni_all "
    "WHERE anyo = 2024 AND rent_eur_m2 IS NOT NULL"
).fetchall()
rents = [r[2] for r in r24]
rent_geo = {
    "n": len(rents),
    "median": round(statistics.median(rents), 2),
    "p25": round(pct(rents, 0.25), 2),
    "p75": round(pct(rents, 0.75), 2),
    "max": {
        "municipio": max(r24, key=lambda r: r[2])[0],
        "provincia": max(r24, key=lambda r: r[2])[1],
        "rent": round(max(rents), 2),
    },
    "min": {
        "municipio": min(r24, key=lambda r: r[2])[0],
        "provincia": min(r24, key=lambda r: r[2])[1],
        "rent": round(min(rents), 2),
    },
}

# --- 2. Rent growth 2011→2024, paired municipios
pairs = con.execute(
    "SELECT a.municipio, a.provincia, a.rent_eur_m2, b.rent_eur_m2 "
    "FROM muni_all a JOIN muni_all b ON a.cpro = b.cpro AND a.municipio = b.municipio "
    "WHERE a.anyo = 2011 AND b.anyo = 2024 "
    "AND a.rent_eur_m2 IS NOT NULL AND b.rent_eur_m2 IS NOT NULL"
).fetchall()
growths = sorted(((b - a) / a * 100, m, p, a, b) for m, p, a, b in pairs if a > 0)
rent_growth = {
    "n": len(growths),
    "median_pct": round(statistics.median([g[0] for g in growths]), 1),
    "fastest": {
        "municipio": growths[-1][1],
        "provincia": growths[-1][2],
        "growth_pct": round(growths[-1][0], 1),
    },
}

# --- 3. Rent 2024 vs 2011 vacancy share (overhang geography)
rv = con.execute(
    "SELECT rent_eur_m2, 100.0 * vacant_2011 / dwellings_2011 "
    "FROM muni_all WHERE anyo = 2011 AND rent_eur_m2 IS NOT NULL "
    "AND dwellings_2011 IS NOT NULL AND dwellings_2011 > 0 AND vacant_2011 IS NOT NULL"
).fetchall()
# Rent is 2011 here (same-row constraint); pair 2024 rent with 2011 vacancy:
rv24 = con.execute(
    "SELECT b.rent_eur_m2, 100.0 * a.vacant_2011 / a.dwellings_2011 "
    "FROM muni_all a JOIN muni_all b ON a.cpro = b.cpro AND a.municipio = b.municipio "
    "WHERE a.anyo = 2011 AND b.anyo = 2024 AND b.rent_eur_m2 IS NOT NULL "
    "AND a.dwellings_2011 IS NOT NULL AND a.dwellings_2011 > 0 "
    "AND a.vacant_2011 IS NOT NULL"
).fetchall()
rent_vac = {
    "n": len(rv24),
    "pearson": pearson([x for x, _ in rv24], [y for _, y in rv24]),
    "spearman": spearman([x for x, _ in rv24], [y for _, y in rv24]),
}

# --- 4. Population growth 2011→2024 vs rent growth (demand co-movement)
pg = con.execute(
    "SELECT a.municipio, a.poblacion, b.poblacion, a.rent_eur_m2, b.rent_eur_m2 "
    "FROM muni_all a JOIN muni_all b ON a.cpro = b.cpro AND a.municipio = b.municipio "
    "WHERE a.anyo = 2011 AND b.anyo = 2024 AND a.poblacion > 0 "
    "AND a.rent_eur_m2 IS NOT NULL AND b.rent_eur_m2 IS NOT NULL"
).fetchall()
pop_rent = [((pb - pa) / pa * 100, (rb - ra) / ra * 100) for _, pa, pb, ra, rb in pg if ra > 0]
pop_rent_corr = {
    "n": len(pop_rent),
    "pearson": pearson([x for x, _ in pop_rent], [y for _, y in pop_rent]),
    "spearman": spearman([x for x, _ in pop_rent], [y for _, y in pop_rent]),
}

out = {
    "rent_geo_2024": rent_geo,
    "rent_growth_2011_2024": rent_growth,
    "rent_vs_vacancy": rent_vac,
    "pop_vs_rent_growth": pop_rent_corr,
    "coverage": {
        "municipios": con.execute(
            "SELECT COUNT(DISTINCT (cpro, municipio)) FROM muni_all"
        ).fetchone()[0],
    },
}
print(f"rent 2024: n={rent_geo['n']} median={rent_geo['median']} max={rent_geo['max']}")
print(f"rent growth: n={rent_growth['n']} median={rent_growth['median_pct']}%")
print(
    f"rent-vs-vacancy: n={rent_vac['n']} pearson={rent_vac['pearson']:.3f} "
    f"spearman={rent_vac['spearman']:.3f}"
)
print(
    f"pop-vs-rent growth: n={pop_rent_corr['n']} pearson={pop_rent_corr['pearson']:.3f} "
    f"spearman={pop_rent_corr['spearman']:.3f}"
)

out["_meta"] = ols.model_meta(__file__, ["data/processed/marts.duckdb"])
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "municipios_nacional.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
