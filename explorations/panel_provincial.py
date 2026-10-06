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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

SEED = 20261006
BOOT_REPS = 999


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
    x: list[list[float]], y: list[float], cl: list[str], coef_i: int, reps: int = BOOT_REPS
) -> float:
    """Null-imposed wild cluster bootstrap-t (Rademacher) via ols helper."""
    return ols.wild_bootstrap_t(x, y, cl, j=coef_i, reps=reps, seed=SEED)["p"]


def main() -> None:
    rows = build_rows()
    specs = {
        "s0_absorption_only": (["absor"], []),
        "s1_with_controls": (["absor"], ["d_hip", "d_trx", "d_tur"]),
    }
    out: dict = {}
    for name, (_base, ctrls) in specs.items():
        data = [o for o in rows if o["absor"] is not None and all(o[c] is not None for c in ctrls)]
        # Correct two-way within: province-demean y, regressors AND the
        # year dummies (previously the province FE was missing entirely
        # and the bootstrap did not impose the null; fixed 2026-10-06).
        units = [o["prov"] for o in data]
        periods = [o["anyo"] for o in data]
        keys = ["d_price", "absor", *ctrls]
        series = {k: [o[k] for o in data] for k in keys}
        y, cols_dm, w, _kept = ols.two_way_within(
            units, periods, series["d_price"], [series[k] for k in ["absor", *ctrls]]
        )
        x = [[c[i] for c in cols_dm] + w[i] for i in range(len(data))]
        cl = list(units)
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
    out["_meta"] = ols.model_meta(__file__, ["data/processed/marts.duckdb"])
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "panel_provincial.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
