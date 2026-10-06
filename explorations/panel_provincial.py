"""EXPLORATORY: absorption vs prices — provincial panel, 2002-2025.

`panel_adjusted.md` runs this design at CCAA grain (17 CCAA, IPV
outcome). The provincia grain was previously limited to 2002-2021
(population ended 2021); the Censo Anual extension
(`docs/explorations/censo_anual_probe.md`) carries the provincia mart to
2025, so the same absorption design can now run at 50 provinces with the
valor-tasado €/m² outcome (INE publishes no provincial IPV).

Design mirrors panel_adjusted: y = eur_m2 YoY % change; absorption =
d_viviendas / d_poblacion (excluded when d_pob <= 0); controls = mortgage
count growth, transaction count growth, tourist-dwelling growth (all
provincial); provincia + year FE; SEs clustered by provincia (CR1V).
Descriptive — supply/demand jointly determined.

Writes artifacts/panel_provincial.json.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

SEED = 20261006


def build_rows() -> list[dict]:
    con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)
    raw = con.execute(
        """
        SELECT cpro, provincia, anyo,
               eur_m2_libre, viviendas_total, poblacion,
               hip_viv_num, trx_total, viv_turisticas
        FROM mart_provincia_anual WHERE cpro != '51+52'
        ORDER BY cpro, anyo
        """
    ).fetchall()
    by: dict[str, list] = {}
    for cpro, _prov, anyo, eur, viv, pob, hip, trx, tur in raw:
        by.setdefault(cpro, []).append(
            {"anyo": anyo, "eur": eur, "viv": viv, "pob": pob, "hip": hip, "trx": trx, "tur": tur}
        )
    rows = []
    for cpro, rs in by.items():
        for prev, cur in zip(rs, rs[1:], strict=False):
            if cur["anyo"] != prev["anyo"] + 1:
                continue
            d_viv = cur["viv"] - prev["viv"]
            d_pob = cur["pob"] - prev["pob"]
            if cur["eur"] is None or prev["eur"] is None:
                continue
            row = {
                "prov": cpro,
                "anyo": cur["anyo"],
                "d_price": (cur["eur"] / prev["eur"] - 1) * 100,
                "absor": (d_viv / d_pob) if d_pob > 0 else None,
                "d_hip": (cur["hip"] / prev["hip"] - 1) * 100
                if cur["hip"] and prev["hip"]
                else None,
                "d_trx": (cur["trx"] / prev["trx"] - 1) * 100
                if cur["trx"] and prev["trx"]
                else None,
                "d_tur": (cur["tur"] / prev["tur"] - 1) * 100
                if cur["tur"] and prev["tur"]
                else None,
            }
            rows.append(row)
    return rows


def wild_p(
    x: list[list[float]], y: list[float], cl: list[str], coef_i: int, reps: int = 999
) -> float:
    """Null-imposed wild bootstrap-t on a clustered OLS coefficient."""
    base = ols.ols_cluster(x, y, cl)
    t_obs = base["beta"][coef_i] / base["se"][coef_i] if base["se"][coef_i] else 0.0
    # null-imposed residuals
    b = base["beta"]
    y_hat = [sum(b[j] * xr[j] for j in range(len(xr))) for xr in x]
    resid = [y[i] - y_hat[i] for i in range(len(y))]
    # cluster ids for re-sampling
    uniq = sorted(set(cl))
    cid = [uniq.index(c) for c in cl]
    rng = random.Random(SEED)
    t_star = []
    for _ in range(reps):
        w = {u: rng.choice([-1.0, 1.0]) for u in range(len(uniq))}
        y_star = [y_hat[i] + resid[i] * w[cid[i]] for i in range(len(y))]
        fit = ols.ols_cluster(x, y_star, cl)
        t_star.append(fit["beta"][coef_i] / fit["se"][coef_i] if fit["se"][coef_i] else 0.0)
    tail = sum(1 for t in t_star if abs(t) >= abs(t_obs))
    return tail / reps


def main() -> None:
    rows = build_rows()
    specs = {
        "s0_absorption_only": (["absor"], []),
        "s1_with_controls": (["absor"], ["d_hip", "d_trx", "d_tur"]),
    }
    out: dict = {}
    for name, (_base, ctrls) in specs.items():
        data = [o for o in rows if o["absor"] is not None and all(o[c] is not None for c in ctrls)]
        years = sorted({o["anyo"] for o in data})[1:]
        y, x, cl = [], [], []
        for o in data:
            y.append(o["d_price"])
            x.append(
                [o["absor"]]
                + [o[c] for c in ctrls]
                + [1.0]
                + [1.0 if o["anyo"] == t else 0.0 for t in years]
            )
            cl.append(o["prov"])
        fit = ols.ols_cluster(x, y, cl)
        coeffs = {}
        for i, name_i in enumerate(["absor"] + ctrls):
            se_i = fit["se"][i]
            coeffs[name_i] = {
                "b": round(fit["beta"][i], 3),
                "se": round(se_i, 3),
                "t": round(fit["beta"][i] / se_i, 2) if se_i else None,
                "wild_p": wild_p(x, y, cl, i),
            }
        out[name] = {
            "n": len(y),
            "clusters": len(set(cl)),
            "years": [min(o["anyo"] for o in data), max(o["anyo"] for o in data)],
            "r2": round(fit["r2"], 3),
            "coefs": coeffs,
        }
        print(
            f"{name}: n={len(y)} G={len(set(cl))} "
            f"absor b={coeffs['absor']['b']} se={coeffs['absor']['se']} "
            f"wild-p={coeffs['absor']['wild_p']:.3f}"
        )
    # window check: does the panel actually reach 2025?
    out["window"] = {
        "min": min(o["anyo"] for o in rows),
        "max": max(o["anyo"] for o in rows),
        "n_provinces": len({o["prov"] for o in rows}),
    }
    print("window:", out["window"])
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "panel_provincial.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
