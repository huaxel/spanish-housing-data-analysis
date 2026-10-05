"""Hypothesis 01: dwellings built per additional inhabitant predicts price growth.

For each territory x time-window: X = d_viviendas / d_poblacion (absorption),
Y = % price change (IPV general at CCAA grain; valor-tasado EUR/m2 at
provincia grain, since INE publishes no provincial IPV).
Reports Pearson + Spearman per window and pooled. Windows with d_pob <= 0
are excluded from the ratio test (ratio undefined) and counted.
Correlation only — credit cycle etc. confound; see docs narrative.
Writes artifacts/hypothesis_01.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED  # noqa: E402

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


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    return pearson(ranks(xs), ranks(ys))


CCAA_WINDOWS = [(2007, 2011), (2011, 2015), (2015, 2019), (2019, 2021), (2021, 2025)]
PROV_WINDOWS = [(2007, 2011), (2011, 2015), (2015, 2019), (2019, 2021)]


def ccaa_pairs(y0: int, y1: int) -> list[dict]:
    q = """WITH a AS (SELECT * FROM mart_ccaa_anual WHERE anyo = ?),
                b AS (SELECT * FROM mart_ccaa_anual WHERE anyo = ?)
         SELECT b.ccaa, b.viviendas_total - a.viviendas_total AS d_viv,
                b.poblacion - a.poblacion AS d_pob,
                (b.ipv_general - a.ipv_general) / a.ipv_general * 100 AS d_ipv_pct,
                (b.eur_m2_libre - a.eur_m2_libre) / a.eur_m2_libre * 100 AS d_eur_pct
         FROM a JOIN b ON a.ccaa = b.ccaa WHERE b.ccaa != 'Nacional'"""
    out = []
    for ccaa, d_viv, d_pob, d_ipv, d_eur in con.execute(q, [y0, y1]).fetchall():
        if d_viv is None or d_pob is None or d_ipv is None:
            continue
        out.append(
            {
                "terr": ccaa,
                "ratio": (d_viv / d_pob) if d_pob > 0 else None,
                "d_price": d_ipv,
                "d_price_eur": d_eur,
            }
        )
    return out


def prov_pairs(y0: int, y1: int) -> list[dict]:
    q = """WITH a AS (SELECT * FROM mart_provincia_anual WHERE anyo = ?),
                b AS (SELECT * FROM mart_provincia_anual WHERE anyo = ?)
         SELECT b.provincia, b.viviendas_total - a.viviendas_total AS d_viv,
                b.poblacion - a.poblacion AS d_pob,
                (b.eur_m2_libre - a.eur_m2_libre) / a.eur_m2_libre * 100 AS d_eur_pct
         FROM a JOIN b ON a.cpro = b.cpro"""
    out = []
    for prov, d_viv, d_pob, d_eur in con.execute(q, [y0, y1]).fetchall():
        if d_viv is None or d_pob is None or d_eur is None:
            continue
        out.append(
            {
                "terr": prov,
                "ratio": (d_viv / d_pob) if d_pob > 0 else None,
                "d_price": d_eur,
                "d_price_eur": d_eur,
            }
        )
    return out


def summarize(pairs: list[dict]) -> dict:
    valid = [p for p in pairs if p["ratio"] is not None]
    xs = [p["ratio"] for p in valid]
    ys = [p["d_price"] for p in valid]
    return {
        "n": len(pairs),
        "n_valid": len(valid),
        "n_nonpositive_pop": len(pairs) - len(valid),
        "pearson": pearson(xs, ys),
        "spearman": spearman(xs, ys),
        "detail": sorted(
            pairs, key=lambda p: (p["ratio"] is None, p["ratio"] if p["ratio"] is not None else 0)
        ),
    }


results: dict = {"ccaa_windows": {}, "prov_windows": {}}
for y0, y1 in CCAA_WINDOWS:
    results["ccaa_windows"][f"{y0}-{y1}"] = summarize(ccaa_pairs(y0, y1))
for y0, y1 in PROV_WINDOWS:
    results["prov_windows"][f"{y0}-{y1}"] = summarize(prov_pairs(y0, y1))

# Pooled (all windows, rank-based; windows differ in credit regime — read with care).
pool_c = [
    p for w in results["ccaa_windows"].values() for p in w["detail"] if p["ratio"] is not None
]
pool_p = [
    p for w in results["prov_windows"].values() for p in w["detail"] if p["ratio"] is not None
]
results["pooled"] = {
    "ccaa": {
        "n": len(pool_c),
        "spearman": spearman([p["ratio"] for p in pool_c], [p["d_price"] for p in pool_c]),
    },
    "prov": {
        "n": len(pool_p),
        "spearman": spearman([p["ratio"] for p in pool_p], [p["d_price"] for p in pool_p]),
    },
}

from spanish_housing.data_paths import ROOT  # noqa: E402

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "hypothesis_01.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)

print("== CCAA (IPV %) ==")
for w, s in results["ccaa_windows"].items():
    print(
        f"{w}: n={s['n_valid']}/{s['n']} pearson={s['pearson']:+.2f} spearman={s['spearman']:+.2f}"
        if s["pearson"] is not None
        else f"{w}: n too small"
    )
print("== PROVINCIA (EUR/m2 %) ==")
for w, s in results["prov_windows"].items():
    print(
        f"{w}: n={s['n_valid']}/{s['n']} pearson={s['pearson']:+.2f} spearman={s['spearman']:+.2f}"
        if s["pearson"] is not None
        else f"{w}: n too small"
    )
print("== POOLED spearman ==", results["pooled"])
