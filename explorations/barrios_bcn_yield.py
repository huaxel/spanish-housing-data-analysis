"""EXPLORATORY: Barcelona barrio gross rental yields, 2024.

Descriptive only — no causal claim. Joins the two Barcelona barrio marts on
barrio code: INCASÒL mean contractual rent (flow, new contracts, €/m²/month)
and Registradores mean registered sale price (€/m² built). Gross yield =
rent × 12 / sale price.

Caveats carried in the output: rents are new-contract means (upper-biased
vs sitting-tenant stock in a rising market); sales average all registered
transactions; thin cells (few transactions) are flagged, not dropped.

Writes artifacts/barrios_bcn_yield.json.
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

YEAR = 2024
THIN_TRX = 15

rows = con.execute(
    """
    SELECT s.nom, r.lloguer_m2 AS rent_m2, s.sale_m2, s.trx
    FROM (
        SELECT codi, nom, AVG(eur_m2_total) AS sale_m2, SUM(trx_total) AS trx
        FROM barrios_bcn_compraventes
        WHERE ambit = 'barri' AND anyo = $YEAR AND eur_m2_total IS NOT NULL
        GROUP BY codi, nom
    ) s
    JOIN (
        SELECT codi, lloguer_m2
        FROM barrios_bcn_lloguer_anual
        WHERE ambit = 'barri' AND anyo = $YEAR AND lloguer_m2 IS NOT NULL
    ) r ON r.codi = s.codi
    """.replace("$YEAR", str(YEAR))
).fetchall()

yields = [
    {
        "barrio": nom,
        "rent_m2": rent,
        "sale_m2": sale,
        "transactions": trx,
        "yield_pct": round(100 * rent * 12 / sale, 2),
        "thin": trx < THIN_TRX,
    }
    for nom, rent, sale, trx in rows
    if sale and sale > 0
]
yields.sort(key=lambda r: r["yield_pct"], reverse=True)
solid = [r for r in yields if not r["thin"]]
all_y = sorted(r["yield_pct"] for r in yields)


def pct(xs: list[float], q: float) -> float:
    return xs[min(len(xs) - 1, int(len(xs) * q))]


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


out = {
    "year": YEAR,
    "n": len(yields),
    "n_thin": len(yields) - len(solid),
    "median_yield": round(pct(all_y, 0.5), 2),
    "p25_yield": round(pct(all_y, 0.25), 2),
    "p75_yield": round(pct(all_y, 0.75), 2),
    "top": yields[0],
    "bottom": yields[-1],
    "rent_vs_sale_pearson": round(
        pearson([r["rent_m2"] for r in yields], [r["sale_m2"] for r in yields]), 3
    ),
    "top5": yields[:5],
    "bottom5": yields[-5:],
}
print(f"yields {YEAR}: n={out['n']} thin={out['n_thin']} median={out['median_yield']}%")
top, bottom = yields[0], yields[-1]
print(f"top={top['barrio']} {top['yield_pct']}% | bottom={bottom['barrio']} {bottom['yield_pct']}%")
print(f"rent-vs-sale pearson={out['rent_vs_sale_pearson']}")

out["_meta"] = ols.model_meta(__file__, ["data/processed/marts.duckdb"])
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "barrios_bcn_yield.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
