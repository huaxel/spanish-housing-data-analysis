"""Quarterly credit-timing panel from pinned raw inputs (no new fetch).

y = QoQ % change of MIVAU valor tasado (vivienda libre, CCAA grain) on
QoQ % mortgage-count growth + 4 quarterly lags + national rate changes.
CCAA + year FE + quarter-season dummies; SEs clustered by CCAA (CR1V);
wild bootstrap-t for the headline credit lags. Complete quarters only
(all 3 months present for mortgages; both endpoints present for prices).

Caveats: appraisal smoothing delays and attenuates price responses (lag
structure is partly appraisal inertia); quarterly absorption is unobserved
(stock is annual), so this is credit timing, not supply. Descriptive only.
Writes artifacts/panel_quarterly.json.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_hipotecas import classify  # noqa: E402
from spanish_housing import ine_api, ols  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

N = ine_api.norm_name
# MIVAU writes 'Castilla-La Mancha' where INE writes 'Castilla - La Mancha'.
ALIAS = {"CASTILLA-LA MANCHA": "CASTILLA - LA MANCHA"}


def norm(ccaa: str) -> str:
    return ALIAS.get(N(ccaa), N(ccaa))


DROP_TERR = {"CEUTA", "MELILLA", "CEUTA Y MELILLA", "TOTAL NACIONAL"}
BOOT_REPS = 999


def quarterize(monthly: dict[tuple[int, int], float]) -> dict[tuple[int, int], float]:
    """Sum months into quarters; keep only quarters with all 3 months."""
    acc: dict[tuple[int, int], list[float]] = {}
    for (y, m), v in monthly.items():
        acc.setdefault((y, (m - 1) // 3 + 1), []).append(v)
    return {k: round(sum(v), 2) for k, v in acc.items() if len(v) == 3}


def load_valor() -> dict[tuple[str, int, int], float]:
    out = {}
    with (RAW / "valor_tasado.csv").open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["Régimen"] != "Libre" or not r["Valor"].strip():
                continue
            ccaa = norm(r["Comunidad_Autónoma"])
            if ccaa in DROP_TERR:
                continue
            out[(ccaa, int(r["Año"]), int(r["Trimestre"]))] = float(r["Valor"].replace(",", "."))
    return out


def load_hipotecas() -> tuple[dict, dict]:
    payload = json.loads((RAW / "hipotecas_ccaa.json").read_text(encoding="utf-8"))
    payload += json.loads((RAW / "hipotecas_rates.json").read_text(encoding="utf-8"))
    counts: dict[str, dict[tuple[int, int], float]] = {}
    rates: dict[tuple[int, int], list[float]] = {}
    for s in payload:
        cls = classify(s["Nombre"])
        if cls is None:
            continue
        kind, terr, medida = cls
        if kind == "rates":
            if medida != "Total":
                continue
            for x in s["Data"]:
                rates.setdefault((x["Anyo"], x["FK_Periodo"]), []).append(x["Valor"])
        elif medida == "Número de hipotecas":
            ccaa = norm(terr)
            if ccaa in DROP_TERR:
                continue
            for x in s["Data"]:
                counts.setdefault(ccaa, {})[(x["Anyo"], x["FK_Periodo"])] = x["Valor"]
    hq = {c: quarterize(m) for c, m in counts.items()}
    rq = {k: sum(v) / len(v) for k, v in rates.items() if len(v) == 1}
    return hq, rq


def qoq(prev: float | None, cur: float | None) -> float | None:
    if prev is None or cur is None or prev == 0:
        return None
    return (cur - prev) / prev * 100


def main() -> None:
    valor = load_valor()
    hq, rq = load_hipotecas()
    ccaas = sorted({c for c, _, _ in valor} & set(hq))
    quarters = sorted({(y, q) for _, y, q in valor} | {k for m in hq.values() for k in m})

    obs = []
    for c in ccaas:
        for i, (y, q) in enumerate(quarters):
            v, h = valor.get((c, y, q)), hq[c].get((y, q))
            py, pq_ = quarters[i - 1] if i else (None, None)
            pv = valor.get((c, py, pq_)) if py else None
            ph = hq[c].get((py, pq_)) if py else None
            r_now = rq.get((y, q))
            r_prev = rq.get((py, pq_)) if py else None
            # Mortgage growth in units of 10pp: QoQ count swings dwarf
            # appraisal-smoothed price moves, so per-pp coefs round to zero.
            hg = qoq(ph, h)
            row = {
                "ccaa": c,
                "yq": (y, q),
                "d_vt": qoq(pv, v),
                "h": hg / 10 if hg is not None else None,
                "dr": (r_now - r_prev) if r_now is not None and r_prev is not None else None,
            }
            for L in range(1, 5):
                jy, jq_ = quarters[i - L] if i >= L else (None, None)
                jh = hq[c].get((jy, jq_)) if jy else None
                jh1 = hq[c].get(quarters[i - L - 1]) if i >= L + 1 else None
                lag = qoq(jh1, jh)
                row[f"L{L}h"] = lag / 10 if lag is not None else None
            obs.append(row)

    spec = ["h", "L1h", "L2h", "L3h", "L4h", "dr"]
    rows = [o for o in obs if all(o[v] is not None for v in ["d_vt", *spec])]
    ux = sorted({o["ccaa"] for o in rows})
    uy = sorted({o["yq"][0] for o in rows})[1:]
    uq = [2, 3, 4]
    means: dict[str, dict[str, float]] = {c: {} for c in ux}
    for o in rows:
        for v in ["d_vt", *spec]:
            means[o["ccaa"]][v] = means[o["ccaa"]].get(v, 0.0) + o[v]
    n_c = {c: sum(1 for o in rows if o["ccaa"] == c) for c in ux}
    for c in ux:
        for v in means[c]:
            means[c][v] /= n_c[c]
    x, yv, cl = [], [], []
    for o in rows:
        m = means[o["ccaa"]]
        yv.append(o["d_vt"] - m["d_vt"])
        x.append(
            [o[v] - m[v] for v in spec]
            + [1.0 if o["yq"][0] == t else 0.0 for t in uy]
            + [1.0 if o["yq"][1] == t else 0.0 for t in uq]
        )
        cl.append(o["ccaa"])
    fit = ols.ols_cluster(x, yv, cl)
    coefs = {}
    for i, v in enumerate(spec):
        b, s = fit["beta"][i], fit["se"][i]
        coefs[v] = {
            "b": round(b, 6),
            "se": round(s, 6),
            "t": round(b / s, 2) if s > 0 else None,
            "ci95": [round(b - 1.96 * s, 6), round(b + 1.96 * s, 6)],
        }
    wb = {v: ols.wild_bootstrap_t(x, yv, cl, j=i, reps=BOOT_REPS) for i, v in enumerate(spec)}
    results = {
        "spec": spec,
        "n": fit["n"],
        "clusters": fit["clusters"],
        "coefs": coefs,
        "wild_bootstrap": wb,
        "ccaa": ux,
    }
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "panel_quarterly.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"== quarterly: n={fit['n']} G={fit['clusters']} R2={fit['r2']:.3f} ==")
    for v, c in coefs.items():
        line = f"  {v}: b={c['b']} se={c['se']} t={c['t']} ci95={c['ci95']}"
        if v in wb:
            line += f" wild-p={wb[v]['p']}"
        print(line)


if __name__ == "__main__":
    main()
