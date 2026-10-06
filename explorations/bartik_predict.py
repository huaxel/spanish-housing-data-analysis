"""Construct shift-share predicted inflows (mechanical values only).

pred[p,t] = sum_o share[p,o,1998] * surge[o,t], normalized per 1,000
1998 inhabitants. Shares and surges come from pinned marts via the
tested bartik constructor (leave-one-out). Mechanical asserts only
(shares sum to 1, no NaNs, full coverage) — NO first stage, NO reduced
form, NO 2SLS. Those need commissioning + independent read.
Writes artifacts/bartik_predicted.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import bartik  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)

rows = con.execute("""
    SELECT cpro, nacionalidad, anyo, SUM(personas) AS stock
    FROM padron_extranjeros_origen
    WHERE sexo = 'Ambos sexos' AND cpro != '00'
    GROUP BY cpro, nacionalidad, anyo
""").fetchall()

stocks: dict[tuple[str, str, int], float] = {}
for cpro, nac, anyo, stock in rows:
    stocks[(cpro, nac, anyo)] = float(stock)

units = sorted({u for (u, _o, _a) in stocks})
origins = sorted({o for (_u, o, _a) in stocks if not o.isupper() and o != "TOTAL EXTRANJEROS"})
years = sorted({a for (_u, _o, a) in stocks if a > 1998})

# NOTE: total (natives + foreign) 1998 pop comes from raw padron below.
tot98 = {}
praw = duckdb.connect(":memory:")
praw.execute("CREATE TABLE p AS SELECT * FROM 'data/raw/parquet/padron_provincia.parquet'")
for r in praw.execute(
    "SELECT territorio, poblacion FROM p WHERE sexo = 'Total' AND anyo = 1998"
).fetchall():
    tot98[r[0]] = r[1]

# Map raw padrón names to cpro via the mart dim table.
dim = {r[0]: r[1] for r in con.execute("SELECT provincia, cpro FROM dim_territorio").fetchall()}
pop_by_cpro: dict[str, int] = {}
for terr, pop in tot98.items():
    match = [c for p, c in dim.items() if p == terr or terr in p or p in terr]
    if len(match) == 1:
        pop_by_cpro[match[0]] = pop
pop_by_cpro["51+52"] = tot98.get("Ceuta", 0) + tot98.get("Melilla", 0)

# Predicted inflow LEVELS: base-year origin levels x national growth.
# (bartik.shares normalizes over foreigners; here levels carry the scale.)
base98 = {(u, o): stocks.get((u, o, 1998), 0.0) for u in units for o in origins}
pred: dict[str, dict[int, float]] = {}
for u in units:
    pred[u] = {}
    for t in years:
        g = bartik.national_growth(stocks, origins, units, 1998, t, leave_out=u)
        pred[u][t] = sum(base98[(u, o)] * g[o] for o in origins)

# Mechanical asserts (no estimation).
assert set(pred) == set(units) and all(len(pred[u]) == len(years) for u in units)
assert all(v == v and abs(v) != float("inf") for u in units for v in pred[u].values())
s98 = bartik.shares(stocks, units, origins, 1998)
assert all(abs(sum(s98[(u, o)] for o in origins) - 1.0) < 1e-9 for u in units)

per_1000 = {
    u: {t: (pred[u][t] / pop_by_cpro[u] * 1000 if pop_by_cpro.get(u) else None) for t in years}
    for u in units
}

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "bartik_predicted.json").write_text(
    json.dumps({"pred_inflow_rate_per_1000_1998pop": per_1000}, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
print(f"bartik predicted: {len(units)} units x {len(years)} years; asserts hold")
print("example Madrid 2008:", round(per_1000.get("28", {}).get(2008, 0.0), 2), "per 1000")
