"""EXPLORATORY: rent-related launches per capita vs provincial rents.

Descriptive only — no causal claim. For each of the 50 provinces with CGPJ
launch data: 2024 LAU launches per 100,000 residents (population from
mart_provincia_anual) against the 2024 SERPAVI provincial collective-median
rent. Reports Pearson/Spearman, top/bottom provinces, and the national rate.

Caveats: launches count ordered property handovers (dwelling or not), not
tenant evictions; provincial rent medians are official aggregates; no
controls for contract density or court practice. Cross-section only.

Writes artifacts/desahucios_renta.json.
"""

from __future__ import annotations

import json
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


rows = con.execute(
    """
    SELECT d.provincia, SUM(d.lanz_lau) AS lau, MAX(p.poblacion) AS pop,
           MAX(s.valor) AS rent_m2
    FROM desahucios_provincia d
    JOIN mart_provincia_anual p
      ON p.provincia = d.provincia AND p.anyo = d.anyo
    JOIN serpavi_provincial s
      ON s.provincia = d.provincia AND s.anyo = d.anyo
     AND s.medida = 'ALQM2_LV_M_VC'
    WHERE d.anyo = 2024
    GROUP BY d.provincia
    """
).fetchall()

cells = [
    {
        "provincia": prov,
        "lau_2024": lau,
        "rent_m2_2024": round(rent, 2),
        "lau_per_100k": round(100000.0 * lau / pop, 1),
    }
    for prov, lau, pop, rent in rows
    if lau is not None and rent is not None and pop
]
cells.sort(key=lambda r: r["lau_per_100k"], reverse=True)
rents = [r["rent_m2_2024"] for r in cells]
rates = [r["lau_per_100k"] for r in cells]

out = {
    "year": 2024,
    "n": len(cells),
    "pearson": round(pearson(rents, rates), 3),
    "spearman": round(spearman(rents, rates), 3),
    "top": cells[0],
    "bottom": cells[-1],
    "top5": cells[:5],
    "bottom5": cells[-5:],
    "national_lau_per_100k": round(
        100000.0
        * sum(r["lau_2024"] for r in cells)
        / con.execute(
            "SELECT SUM(poblacion) FROM mart_provincia_anual "
            "WHERE anyo = 2024 AND provincia != 'Ceuta y Melilla'"
        ).fetchone()[0],
        1,
    ),
}
print(f"lau-vs-rent 2024: n={out['n']} pearson={out['pearson']} spearman={out['spearman']}")
top = cells[0]
print(f"top={top['provincia']} {top['lau_per_100k']} | national={out['national_lau_per_100k']}")

out["_meta"] = ols.model_meta(__file__, ["data/processed/marts.duckdb"])
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "desahucios_renta.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
