"""Distributional first-round housing policy microsimulation on INE ECV 2025 microdata.

Uses the repo's verified INE ECV 2025 archive (data/raw/ine_ecv_2025.zip) and
official Eurostat housing-cost overburden rules (assess_ecv_benchmarks.py) to
simulate four Spanish rental-policy levers across equivalized-income quintiles
and age cohorts:

1. baseline: Observed ECV 2025 housing-cost overburden (>40% Eurostat, >30% effort)
2. bono_joven_0pt: Bono Alquiler Joven (250 €/mo, market renters with adult 18–35,
   HY020 <= 24,318 € [3x IPREM]), 0% landlord pass-through
3. bono_joven_50pt: Same policy with 50% landlord rent pass-through (net 125 €/mo)
4. renta_q1_q2: Income-targeted rental subsidy (250 €/mo for all Q1–Q2 market renters)
5. tope_5pct: Broad -5% market-rent reduction (calibrated to Phase 1 Catalonia range
   -3.8% to -6.2%), zero direct fiscal outlay
6. escudo_30pct: Progressive housing benefit covering housing cost above 30% of net
   income for Q1–Q2 market renters (capped at 400 €/mo)

Strict methodological boundaries:
- First-round static arithmetic on ECV 2025 (no behavioral supply/mobility response,
  except the explicit 50% pass-through sensitivity on Bono Joven).
- Never exports microdata rows; only aggregated cells with >=30 households and
  >=50 persons are released.

Outputs:
- artifacts/ecv_microsim.json
- data/processed/ecv_microsim.duckdb (tables: scenarios, by_quintile)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import assess_ecv_benchmarks as ecv  # noqa: E402
from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

ECV_ZIP = RAW / "ine_ecv_2025.zip"
ARTIFACT_OUT = ROOT / "artifacts/ecv_microsim.json"
DUCKDB_OUT = PROCESSED / "ecv_microsim.duckdb"

IPREM_3X_ANNUAL = 24_318.0  # Official 2024–2025 3× IPREM threshold (14 pagas)
BONO_MONTHLY = 250.0
ESCUDO_CAP_MONTHLY = 400.0
MIN_HOUSEHOLDS = 30
MIN_PERSONS = 50


def effort_ratio(monthly_cost: float, annual_income: float, gross_allowance: float) -> float:
    net_cost = 12.0 * monthly_cost - gross_allowance
    net_income = annual_income - gross_allowance
    if net_cost <= 0:
        return 0.0
    if net_income <= 0:
        return 9.99
    return net_cost / net_income


def load_households() -> list[dict]:
    if not ECV_ZIP.is_file():
        raise SystemExit(f"Missing pinned ECV microdata archive: {ECV_ZIP}")
    data = ecv.load_archive(ECV_ZIP, 2025)

    d_weights = {row["DB030"]: ecv.number(row["DB090"]) for row in data["d"]}
    persons_by_hh: dict[str, list[dict]] = defaultdict(list)
    for row in data["r"]:
        hh_id = row["RB030"][:-2]
        age = int(ecv.number(row["RB081"]))
        if age == -1:
            age = 0
        persons_by_hh[hh_id].append(
            {
                "age": age,
                "weight": ecv.number(row["RB050"]),
            }
        )

    households = []
    for row in data["h"]:
        hh_id = row["HB030"]
        if row["HH070_F"] == "-1" or row["HY020_F"] == "-1" or row["HH021_F"] == "-1":
            continue
        persons = persons_by_hh.get(hh_id)
        if not persons:
            continue
        hh_w = d_weights.get(hh_id, 0.0)
        if hh_w <= 0:
            continue
        hy020 = ecv.number(row["HY020"])
        hh070 = ecv.number(row["HH070"])
        hy070g = 0.0 if row["HY070G_F"] == "-1" else ecv.number(row["HY070G"])
        if hh070 < 0 or hy070g < 0:
            continue
        tenure = ecv.TENURES.get(row["HH021"])
        if tenure is None:
            continue

        # OECD-modified equivalence scale: 1.0 first adult + 0.5 other adults + 0.3 children (<14)
        adults = sum(1 for p in persons if p["age"] >= 14)
        children = len(persons) - adults
        eq_scale = 1.0 + 0.5 * max(0, adults - 1) + 0.3 * children
        eq_income = hy020 / eq_scale
        p_weight_sum = sum(p["weight"] for p in persons)
        has_young_adult = any(18 <= p["age"] <= 35 for p in persons)

        households.append(
            {
                "hh_id": hh_id,
                "tenure": tenure,
                "hh_weight": hh_w,
                "n_persons": len(persons),
                "person_weight": p_weight_sum,
                "hy020": hy020,
                "hh070": hh070,
                "hy070g": hy070g,
                "eq_income": eq_income,
                "has_young_adult": has_young_adult,
            }
        )

    # Assign person-weighted equivalized income quintiles Q1..Q5 across all valid households
    weighted_vals = [(h["eq_income"], h["person_weight"]) for h in households]
    cuts = [ecv.weighted_cut(weighted_vals, q) for q in (0.2, 0.4, 0.6, 0.8)]
    for h in households:
        ei = h["eq_income"]
        if ei <= cuts[0]:
            h["quintile"] = 1
        elif ei <= cuts[1]:
            h["quintile"] = 2
        elif ei <= cuts[2]:
            h["quintile"] = 3
        elif ei <= cuts[3]:
            h["quintile"] = 4
        else:
            h["quintile"] = 5
    return households


def simulate_policy(households: list[dict], scenario_id: str) -> tuple[dict, list[dict]]:
    """Evaluate a policy scenario on all households and market renters (RENT_MKT)."""
    # Baseline overburden flags on market renters for exact "lifted out" accounting
    tot_mkt_hh = 0.0
    tot_mkt_pers = 0.0
    tot_all_pers = 0.0
    over40_all_pers = 0.0
    over40_mkt_pers = 0.0
    over30_mkt_pers = 0.0
    base_over40_mkt_hh = 0.0
    post_over40_mkt_hh = 0.0
    elig_hh = 0.0
    elig_pers = 0.0
    fiscal_cost_eur = 0.0
    total_tenant_relief_eur = 0.0
    relief_q1_q2_eur = 0.0

    q_buckets: dict[int, dict] = {
        q: {
            "sample_hh": 0,
            "sample_pers": 0,
            "mkt_hh_w": 0.0,
            "mkt_pers_w": 0.0,
            "base_over40_w": 0.0,
            "post_over40_w": 0.0,
            "post_over30_w": 0.0,
            "relief_eur": 0.0,
            "fiscal_eur": 0.0,
        }
        for q in range(1, 6)
    }

    for h in households:
        pw = h["person_weight"]
        hw = h["hh_weight"]
        is_mkt = h["tenure"] == "RENT_MKT"
        base_ratio = effort_ratio(h["hh070"], h["hy020"], h["hy070g"])
        base_40 = base_ratio > 0.40

        # Policy transfer / cost adjustment (annualized for fiscal cost, monthly for cost relief)
        monthly_relief = 0.0
        annual_fiscal = 0.0
        eligible = False

        if is_mkt:
            if scenario_id == "bono_joven_0pt":
                if h["has_young_adult"] and h["hy020"] <= IPREM_3X_ANNUAL:
                    eligible = True
                    monthly_relief = min(BONO_MONTHLY, h["hh070"])
                    annual_fiscal = 12.0 * monthly_relief
            elif scenario_id == "bono_joven_50pt":
                if h["has_young_adult"] and h["hy020"] <= IPREM_3X_ANNUAL:
                    eligible = True
                    gross_sub = min(BONO_MONTHLY, h["hh070"])
                    annual_fiscal = 12.0 * gross_sub
                    monthly_relief = 0.5 * gross_sub  # 50% landlord pass-through
            elif scenario_id == "renta_q1_q2":
                if h["quintile"] in (1, 2):
                    eligible = True
                    monthly_relief = min(BONO_MONTHLY, h["hh070"])
                    annual_fiscal = 12.0 * monthly_relief
            elif scenario_id == "tope_5pct":
                eligible = True
                monthly_relief = 0.05 * h["hh070"]
                annual_fiscal = 0.0
            elif scenario_id == "escudo_30pct" and h["quintile"] in (1, 2):
                net_inc = max(0.0, h["hy020"] - h["hy070g"])
                net_cost = max(0.0, 12.0 * h["hh070"] - h["hy070g"])
                excess_annual = max(0.0, net_cost - 0.30 * net_inc)
                if excess_annual > 0:
                    eligible = True
                    monthly_relief = min(ESCUDO_CAP_MONTHLY, excess_annual / 12.0, h["hh070"])
                    annual_fiscal = 12.0 * monthly_relief

        new_cost = max(0.0, h["hh070"] - monthly_relief)
        new_ratio = effort_ratio(new_cost, h["hy020"], h["hy070g"])
        post_40 = new_ratio > 0.40
        post_30 = new_ratio > 0.30

        tot_all_pers += pw
        if post_40:
            over40_all_pers += pw

        if is_mkt:
            tot_mkt_hh += hw
            tot_mkt_pers += pw
            if base_40:
                base_over40_mkt_hh += hw
            if post_40:
                over40_mkt_pers += pw
                post_over40_mkt_hh += hw
            if post_30:
                over30_mkt_pers += pw
            if eligible:
                elig_hh += hw
                elig_pers += pw
                fiscal_cost_eur += annual_fiscal * hw
                total_tenant_relief_eur += (12.0 * monthly_relief) * hw
                if h["quintile"] in (1, 2):
                    relief_q1_q2_eur += (12.0 * monthly_relief) * hw

            qb = q_buckets[h["quintile"]]
            qb["sample_hh"] += 1
            qb["sample_pers"] += h["n_persons"]
            qb["mkt_hh_w"] += hw
            qb["mkt_pers_w"] += pw
            if base_40:
                qb["base_over40_w"] += pw
            if post_40:
                qb["post_over40_w"] += pw
            if post_30:
                qb["post_over30_w"] += pw
            qb["relief_eur"] += (12.0 * monthly_relief) * hw
            qb["fiscal_eur"] += annual_fiscal * hw

    lifted_hh = max(0.0, base_over40_mkt_hh - post_over40_mkt_hh)
    cost_per_lifted = (
        round(fiscal_cost_eur / lifted_hh, 0) if lifted_hh > 0 and fiscal_cost_eur > 0 else 0.0
    )
    q12_share = (
        round(100.0 * relief_q1_q2_eur / total_tenant_relief_eur, 1)
        if total_tenant_relief_eur > 0
        else None
    )

    labels = {
        "baseline": ("Situación base (ECV 2025)", "Sin intervención nueva; tasas observadas."),
        "bono_joven_0pt": (
            "Bono Alquiler Joven (0% traslación)",
            "250 €/mes a inquilinos de mercado con joven 18–35 y renta <= 24.318 € (3× IPREM).",
        ),
        "bono_joven_50pt": (
            "Bono Alquiler Joven (50% traslación)",
            "Misma elegibilidad, asumiendo que el 50% de la ayuda se traslada al alquiler.",
        ),
        "renta_q1_q2": (
            "Ayuda focalizada Q1–Q2 (250 €/mes)",
            "250 €/mes a todos los inquilinos de mercado en Q1–Q2, sin límite de edad.",
        ),
        "tope_5pct": (
            "Tope general al alquiler (−5%)",
            "Reducción del 5% en coste mensual (rango Cataluña), gasto fiscal directo 0 €.",
        ),
        "escudo_30pct": (
            "Escudo de esfuerzo 30% (Q1–Q2, tope 400 €)",
            "Prestación progresiva sobre el exceso del 30% de renta neta en Q1–Q2 (máx. 400 €).",
        ),
    }
    name, desc = labels[scenario_id]
    summary = {
        "scenario_id": scenario_id,
        "scenario_name": name,
        "description": desc,
        "eligible_hh": round(elig_hh),
        "eligible_persons": round(elig_pers),
        "fiscal_cost_meur": round(fiscal_cost_eur / 1e6, 1),
        "tenant_relief_meur": round(total_tenant_relief_eur / 1e6, 1),
        "relief_to_q1_q2_pct": q12_share,
        "overburden_40_all_pct": round(100.0 * over40_all_pers / tot_all_pers, 2),
        "overburden_40_mkt_pct": round(100.0 * over40_mkt_pers / tot_mkt_pers, 2),
        "effort_30_mkt_pct": round(100.0 * over30_mkt_pers / tot_mkt_pers, 2),
        "hh_lifted_out_40": round(lifted_hh),
        "fiscal_eur_per_hh_lifted": cost_per_lifted,
    }

    q_rows = []
    for q in range(1, 6):
        qb = q_buckets[q]
        if qb["sample_hh"] < MIN_HOUSEHOLDS or qb["sample_pers"] < MIN_PERSONS:
            raise ValueError(f"Quintile {q} below disclosure threshold")
        base_pct = round(100.0 * qb["base_over40_w"] / qb["mkt_pers_w"], 2)
        post_pct = round(100.0 * qb["post_over40_w"] / qb["mkt_pers_w"], 2)
        q_rows.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": name,
                "quintile": q,
                "quintile_label": f"Q{q}",
                "sample_hh": qb["sample_hh"],
                "mkt_persons": round(qb["mkt_pers_w"]),
                "base_over40_pct": base_pct,
                "post_over40_pct": post_pct,
                "delta_over40_pp": round(post_pct - base_pct, 2),
                "post_over30_pct": round(100.0 * qb["post_over30_w"] / qb["mkt_pers_w"], 2),
                "relief_meur": round(qb["relief_eur"] / 1e6, 1),
                "fiscal_meur": round(qb["fiscal_eur"] / 1e6, 1),
            }
        )
    return summary, q_rows


def run_microsim() -> dict:
    households = load_households()
    scenarios = []
    by_quintile = []
    for sid in (
        "baseline",
        "bono_joven_0pt",
        "bono_joven_50pt",
        "renta_q1_q2",
        "tope_5pct",
        "escudo_30pct",
    ):
        s_row, q_rows = simulate_policy(households, sid)
        scenarios.append(s_row)
        by_quintile.extend(q_rows)
    return {
        "meta": {
            "source_archive": str(ECV_ZIP.relative_to(ROOT)),
            "ecv_year": 2025,
            "valid_households": len(households),
            "valid_market_renter_hh": sum(1 for h in households if h["tenure"] == "RENT_MKT"),
            "iprem_3x_eur": IPREM_3X_ANNUAL,
            "static_first_round_only": True,
        },
        # Freshness key (audit_claims.MODEL_FRESHNESS): keyed to the pinned
        # archive bytes, so a re-pinned ECV release invalidates these cells.
        "_meta": ols.model_meta(__file__, [str(ECV_ZIP.relative_to(ROOT))]),
        "scenarios": scenarios,
        "by_quintile": by_quintile,
    }


def write_duckdb(data: dict) -> None:
    tmp = DUCKDB_OUT.with_suffix(".duckdb.tmp")
    if tmp.exists():
        tmp.unlink()
    con = duckdb.connect(str(tmp))
    con.register("s_tbl", pa.Table.from_pylist(data["scenarios"]))
    con.register("q_tbl", pa.Table.from_pylist(data["by_quintile"]))
    con.execute("CREATE TABLE scenarios AS SELECT * FROM s_tbl")
    con.execute("CREATE TABLE by_quintile AS SELECT * FROM q_tbl")
    con.close()
    tmp.replace(DUCKDB_OUT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify microsim outputs match ECV")
    args = parser.parse_args()

    data = run_microsim()
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not ARTIFACT_OUT.is_file() or ARTIFACT_OUT.read_text() != payload:
            raise SystemExit("Stale artifacts/ecv_microsim.json; re-run build_ecv_microsim.py")
        if not DUCKDB_OUT.is_file():
            raise SystemExit("Missing data/processed/ecv_microsim.duckdb")
        print(f"ecv_microsim: verified {len(data['scenarios'])} scenarios")
        return

    ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_OUT.write_text(payload)
    write_duckdb(data)

    print(
        f"ECV 2025 valid households: {data['meta']['valid_households']:,} "
        f"(market renters: {data['meta']['valid_market_renter_hh']:,})"
    )
    for s in data["scenarios"]:
        print(
            f"  {s['scenario_id']:16s} | over40_mkt={s['overburden_40_mkt_pct']:5.2f}% | "
            f"lifted={s['hh_lifted_out_40']:7,} hh | fiscal={s['fiscal_cost_meur']:7.1f} M€ | "
            f"€/lifted={s['fiscal_eur_per_hh_lifted']:8,.0f} | "
            f"Q1-Q2={s['relief_to_q1_q2_pct']}%"
        )


if __name__ == "__main__":
    main()
