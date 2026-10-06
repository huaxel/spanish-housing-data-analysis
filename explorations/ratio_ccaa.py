"""EXPLORATORY: the viv/1000 trajectory across CCAA, 2001-2025.

Question that started this: how does the national dwellings-per-1000 ratio
stay basically flat across 2001-2025 while population grew ~+20%? Answer
recorded here: it does not stay flat (+7.8% national), and the national
number hides a two-group split — the demand regions (Madrid, Cataluña,
Balears, Canarias) show a *falling* ratio (population ran ahead of stock),
while the interior/north-west (CyL, Asturias, Galicia, Extremadura) show a
+100 to +130 rise (the boom built for a shrinking population).

Also recorded: the cross-section of the ratio change (2007-25) with real
price change (IPV deflated by IPC, 2007-25). Sign is negative as the
overhang story predicts, but with n=17 CCAA it is not distinguishable from
zero (Pearson r=-0.385, t=-1.61). Directional, not conclusive.

Writes artifacts/ratio_ccaa.json.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)

# --- ratio 2001/2007/2021/2025 per CCAA (prov mart 2001-21 + ccaa mart 2025)
raw = con.execute(
    """
    WITH p AS (
      SELECT ccaa, anyo, SUM(viviendas_total) s, SUM(poblacion) p
      FROM mart_provincia_anual WHERE anyo IN (2001,2007,2021) GROUP BY ccaa, anyo
    ), c AS (
      SELECT ccaa, anyo, viviendas_total s, poblacion p
      FROM mart_ccaa_anual WHERE anyo IN (2025) AND ccaa != 'Nacional'
    )
    SELECT COALESCE(p.ccaa,c.ccaa) ccaa,
           p.anyo pa, p.s ps, p.p pp,
           c.anyo ca, c.s cs, c.p cp
    FROM p FULL OUTER JOIN c ON p.ccaa=c.ccaa
    """
).fetchall()

ratios: dict[str, dict] = {}
for ccaa, pa, ps, pp, ca, cs, cp in raw:
    d = ratios.setdefault(ccaa, {})
    if pa is not None:
        d[pa] = round(1000.0 * ps / pp, 1)
    if ca is not None:
        d[ca] = round(1000.0 * cs / cp, 1)
for ccaa, d in ratios.items():
    r01, r07, r21, r25 = d.get(2001), d.get(2007), d.get(2021), d.get(2025)
    ratios[ccaa] = {
        "r01": r01,
        "r07": r07,
        "r21": r21,
        "r25": r25,
        "d_07_25": round(r25 - r07, 1) if r25 is not None and r07 is not None else None,
    }

# --- real price change 2007-25 per CCAA (IPV index deflated by IPC levels)
price_rows = con.execute(
    """
    WITH ipv AS (
      SELECT ccaa, anyo, ipv_general FROM mart_ccaa_anual
      WHERE anyo IN (2007,2025) AND ccaa != 'Nacional'
    ), ipc AS (
      SELECT territorio, anyo, ipc FROM ipc_anual WHERE anyo IN (2007,2025)
    )
    SELECT ipv.ccaa,
      MAX(CASE WHEN ipv.anyo=2007 THEN ipv.ipv_general END) p07,
      MAX(CASE WHEN ipv.anyo=2025 THEN ipv.ipv_general END) p25,
      MAX(CASE WHEN ipc.anyo=2007 THEN ipc.ipc END) c07,
      MAX(CASE WHEN ipc.anyo=2025 THEN ipc.ipc END) c25
    FROM ipv LEFT JOIN ipc ON ipv.ccaa=ipc.territorio
    GROUP BY ipv.ccaa
    """
).fetchall()

prices: dict[str, float] = {}
for ccaa, p07, p25, c07, c25 in price_rows:
    if p07 and p25 and c07 and c25:
        prices[ccaa] = round((p25 / p07 / (c25 / c07) - 1) * 100, 1)

# --- correlation: ratio change vs real price change
xs = [ratios[k]["d_07_25"] for k in ratios if k in prices and ratios[k]["d_07_25"] is not None]
ys = [prices[k] for k in ratios if k in prices and ratios[k]["d_07_25"] is not None]
n = len(xs)
pearson = round(statistics.correlation(xs, ys), 3) if n > 2 else None
t = None
if n > 2:
    import math

    t = round(pearson * math.sqrt(n - 2) / math.sqrt(1 - pearson * pearson), 2)


def _rank(v: list[float]) -> list[float]:
    s = sorted(v)
    return [s.index(x) + 1 for x in v]


spearman = round(statistics.correlation(_rank(xs), _rank(ys)), 3) if n > 2 else None

# groups for the doc
scarcity = ["Madrid, Comunidad de", "Cataluña", "Balears, Illes", "Canarias"]
overstock = ["Asturias, Principado de", "Castilla y León", "Galicia", "Extremadura"]
out = {
    "national": {
        "r01": 511.6,
        "r07": 531.7,
        "r21": 563.9,
        "r25": 551.6,
        "stock_growth_01_25_pct": 28.8,
        "pop_growth_01_25_pct": 19.5,
    },
    "ccaa": ratios,
    "real_price_change_07_25": prices,
    "corr_ratio_vs_real_price": {
        "n": n,
        "pearson": pearson,
        "t": t,
        "spearman": spearman,
    },
    "groups": {
        "scarcity_falling": {k: ratios[k]["d_07_25"] for k in scarcity},
        "overstock_rising": {k: ratios[k]["d_07_25"] for k in overstock},
        "median_real_price": {
            "scarcity": round(statistics.median([prices[k] for k in scarcity]), 1),
            "overstock": round(statistics.median([prices[k] for k in overstock]), 1),
        },
    },
}
print(f"n={n} pearson={pearson} t={t} spearman={spearman}")
print("scarcity median real:", out["groups"]["median_real_price"]["scarcity"])
print("overstock median real:", out["groups"]["median_real_price"]["overstock"])

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "ratio_ccaa.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
