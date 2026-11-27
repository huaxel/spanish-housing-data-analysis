"""Quasi-experimental evaluation of Catalonia's Ley 12/2023 rent-control zones (ZMRT).

Evaluates all three observable margins in INCASÒL administrative deposit records:
1. Habitual contractual rent: log(lloguer_eur)
2. Habitual contract flow: log(contractes) on active markets (and log(contractes + 1))
3. Seasonal contract substitution: temporada_share = temporada / (habitual + temporada),
   available 2023Q1–2026Q2.

Identification designs (all with municipality FE + quarter FE, CR1V SEs clustered by
municipality, plus Rademacher wild cluster bootstrap-t for headline DiD effects):
- Design A (Wave 1 vs Wave 2, 2019Q1–2024Q3): cleanest not-yet-treated comparison
  before Wave 2 took effect in 2024Q4.
- Design B (Wave 1 vs Never-treated active markets, 2019Q1–2026Q2): full 9-quarter
  post-treatment horizon (2024Q2–2026Q2).
- Design C (Wave 2 vs Never-treated active markets, 2019Q1–2026Q2): independent
  7-quarter replication (2024Q4–2026Q2) on smaller tensioned municipalities.
- Design D (Within-Comarca FE: municipality FE + comarca-by-quarter FE, 2019Q1–2026Q2):
  absorbs local comarca-level demand, tourism, and labor-market shocks.

Falsification:
- Event-study leads (k = -8..-2, reference k = -1) and placebo DiD shifted 4 quarters
  earlier (2023Q2) on strictly pre-treatment data (2019Q1–2024Q1).

Outputs:
- artifacts/catalonia_rent_control.json
- data/processed/policy_eval.duckdb (tables for Evidence /politica/ page)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

PARQUET = PROCESSED / "catalonia_rent_control.parquet"
ARTIFACT = ROOT / "artifacts/catalonia_rent_control.json"
DUCKDB_OUT = PROCESSED / "policy_eval.duckdb"

START_YEAR = 2019
W1_START_IDX = 2024 * 4 + 1  # 2024Q2 (first full quarter after 2024-03-16)
W2_START_IDX = 2024 * 4 + 3  # 2024Q4 (first full quarter after 2024-10-10)
PLACEBO_START_IDX = 2023 * 4 + 1  # 2023Q2 (placebo 4 quarters early)
WILD_REPS = 999
SEED = 20261127


def load_rows() -> list[dict]:
    if not PARQUET.is_file():
        raise SystemExit(
            f"Missing {PARQUET}; run `uv run python scripts/fetch_catalonia_rent_control.py`"
        )
    table = pq.read_table(PARQUET)
    return [r for r in table.to_pylist() if r["anyo"] >= START_YEAR]


def active_municipalities(rows: list[dict], min_pre_rent_quarters: int = 12) -> set[str]:
    """Municipalities with >= min_pre_rent_quarters published rent obs in 2019–2023."""
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if 2019 <= r["anyo"] <= 2023 and r["lloguer_eur"] is not None:
            counts[r["codi"]] += 1
    return {code for code, n in counts.items() if n >= min_pre_rent_quarters}


def two_way_demean(
    values: list[float],
    unit_ids: list[str],
    time_ids: list[str],
    max_iter: int = 60,
    tol: float = 1e-11,
) -> list[float]:
    """Alternating projections to absorb unit FE and time (or comarca×time) FE."""
    n = len(values)
    res = values[:]
    u_groups: dict[str, list[int]] = defaultdict(list)
    t_groups: dict[str, list[int]] = defaultdict(list)
    for i in range(n):
        u_groups[unit_ids[i]].append(i)
        t_groups[time_ids[i]].append(i)
    for _ in range(max_iter):
        max_shift = 0.0
        for idxs in u_groups.values():
            m = sum(res[i] for i in idxs) / len(idxs)
            if abs(m) > max_shift:
                max_shift = abs(m)
            for i in idxs:
                res[i] -= m
        for idxs in t_groups.values():
            m = sum(res[i] for i in idxs) / len(idxs)
            if abs(m) > max_shift:
                max_shift = abs(m)
            for i in idxs:
                res[i] -= m
        if max_shift < tol:
            break
    return res


def fit_did(
    obs: list[dict],
    y_fn,
    treat_fn,
    time_key_fn=lambda r: r["quarter_label"],
    run_wild: bool = True,
) -> dict:
    """Estimate TWFE DiD y_it = beta * D_it + alpha_i + gamma_t + e_it with CR1V & wild-p."""
    filtered = []
    for r in obs:
        y = y_fn(r)
        if y is None:
            continue
        filtered.append((r, float(y), float(treat_fn(r))))
    if len(filtered) < 20:
        return {"n": len(filtered), "error": "insufficient observations"}

    units = [r["codi"] for r, _, _ in filtered]
    times = [time_key_fn(r) for r, _, _ in filtered]
    y_raw = [y for _, y, _ in filtered]
    d_raw = [d for _, _, d in filtered]

    y_dm = two_way_demean(y_raw, units, times)
    d_dm = two_way_demean(d_raw, units, times)
    x = [[v] for v in d_dm]

    fit = ols.ols_cluster(x, y_dm, units)
    beta = fit["beta"][0]
    se = fit["se"][0]
    t_stat = beta / se if se > 1e-12 else 0.0
    n_clusters = len(set(units))
    n_treated = len({r["codi"] for r, _, d in filtered if d > 0.5})
    out = {
        "n_obs": len(filtered),
        "n_munis": n_clusters,
        "n_treated_munis": n_treated,
        "beta": round(beta, 5),
        "pct_approx": round((math.exp(beta) - 1.0) * 100.0, 2),
        "se_cr1v": round(se, 5),
        "t_cr1v": round(t_stat, 3),
        "ci95_low": round(beta - 1.96 * se, 5),
        "ci95_high": round(beta + 1.96 * se, 5),
    }
    if run_wild and n_clusters >= 10:
        # Null-imposed wild cluster bootstrap-t for a single demeaned regressor:
        # Under H0: beta = 0, restricted residuals are y_dm itself.
        import random

        rng = random.Random(SEED)
        groups: dict[str, list[int]] = defaultdict(list)
        for i, g in enumerate(units):
            groups[g].append(i)
        denom = sum(v * v for v in d_dm)
        if denom > 1e-12:
            g_list = list(groups.values())
            g_count = len(g_list)
            c_scale = (g_count / (g_count - 1)) * ((len(filtered) - 1) / (len(filtered) - 1))
            # Precompute cluster sums for fast exact Rademacher wild bootstrap-t
            s_g = [sum(d_dm[i] * y_dm[i] for i in idxs) for idxs in g_list]
            dd_g = [sum(d_dm[i] * d_dm[i] for i in idxs) for idxs in g_list]
            t_stars = []
            for _ in range(WILD_REPS):
                v = [1.0 if rng.random() < 0.5 else -1.0 for _ in range(g_count)]
                num_star = sum(v[idx] * s_g[idx] for idx in range(g_count))
                b_star = num_star / denom
                # Cluster score under fitted b_star: sum_i d_i (v_g y_i - b_star d_i)
                meat = sum((v[idx] * s_g[idx] - b_star * dd_g[idx]) ** 2 for idx in range(g_count))
                se_star = math.sqrt(c_scale * meat) / denom if meat > 0 else 0.0
                t_stars.append(b_star / se_star if se_star > 1e-12 else 0.0)
            extreme = sum(1 for ts in t_stars if abs(ts) >= abs(t_stat))
            out["wild_p"] = round((extreme + 1) / (WILD_REPS + 1), 4)
            out["wild_reps"] = WILD_REPS
    return out


def fit_event_study(
    obs: list[dict],
    y_fn,
    treated_wave: int,
    event_start_idx: int,
    k_min: int = -8,
    k_max: int = 8,
    time_key_fn=lambda r: r["quarter_label"],
) -> list[dict]:
    """Event study with municipality FE + time FE, reference k = -1."""
    filtered = []
    for r in obs:
        y = y_fn(r)
        if y is None:
            continue
        k = r["quarter_idx"] - event_start_idx if r["wave"] == treated_wave else None
        filtered.append((r, float(y), k))
    if len(filtered) < 50:
        return []

    ks = [k for k in range(k_min, k_max + 1) if k != -1]
    units = [r["codi"] for r, _, _ in filtered]
    times = [time_key_fn(r) for r, _, _ in filtered]
    y_dm = two_way_demean([y for _, y, _ in filtered], units, times)

    cols_dm = []
    active_ks = []
    for k_val in ks:
        if k_val == k_min:
            col = [1.0 if (k is not None and k <= k_min) else 0.0 for _, _, k in filtered]
        elif k_val == k_max:
            col = [1.0 if (k is not None and k >= k_max) else 0.0 for _, _, k in filtered]
        else:
            col = [1.0 if k == k_val else 0.0 for _, _, k in filtered]
        if sum(col) == 0:
            continue
        cols_dm.append(two_way_demean(col, units, times))
        active_ks.append(k_val)

    x = [[cols_dm[j][i] for j in range(len(active_ks))] for i in range(len(filtered))]
    fit = ols.ols_cluster(x, y_dm, units)

    results = [
        {
            "rel_q": -1,
            "beta": 0.0,
            "se": 0.0,
            "ci95_low": 0.0,
            "ci95_high": 0.0,
            "pct_approx": 0.0,
            "is_pre": True,
        }
    ]
    for idx, k_val in enumerate(active_ks):
        b = fit["beta"][idx]
        s = fit["se"][idx]
        results.append(
            {
                "rel_q": k_val,
                "beta": round(b, 5),
                "se": round(s, 5),
                "ci95_low": round(b - 1.96 * s, 5),
                "ci95_high": round(b + 1.96 * s, 5),
                "pct_approx": round((math.exp(b) - 1.0) * 100.0, 2),
                "is_pre": k_val < 0,
            }
        )
    results.sort(key=lambda r: r["rel_q"])
    return results


def build_group_series(rows: list[dict], active: set[str]) -> list[dict]:
    """Weighted mean rent, habitual contracts, and seasonal share by wave × quarter."""
    buckets: dict[tuple[int, str, int], dict] = {}
    for r in rows:
        key = (r["wave"], r["quarter_label"], r["quarter_idx"])
        b = buckets.setdefault(
            key,
            {
                "wave": r["wave"],
                "quarter_label": r["quarter_label"],
                "quarter_idx": r["quarter_idx"],
                "anyo": r["anyo"],
                "trimestre": r["trimestre"],
                "contractes_total": 0,
                "temporada_total": 0,
                "has_temporada": False,
                "rent_weighted_num": 0.0,
                "rent_weighted_den": 0,
                "active_rent_sum": 0.0,
                "active_rent_n": 0,
                "active_contracts_total": 0,
            },
        )
        c = r["contractes"] or 0
        b["contractes_total"] += c
        if r["temporada_contractes"] is not None:
            b["temporada_total"] += r["temporada_contractes"]
            b["has_temporada"] = True
        if r["lloguer_eur"] is not None and c > 0:
            b["rent_weighted_num"] += r["lloguer_eur"] * c
            b["rent_weighted_den"] += c
        if r["codi"] in active:
            b["active_contracts_total"] += c
            if r["lloguer_eur"] is not None:
                b["active_rent_sum"] += r["lloguer_eur"]
                b["active_rent_n"] += 1

    # Compute 2023Q4 = 100 index per wave for clean visual comparison
    wave_labels = {
        0: "No tensionados (677 mun.)",
        1: "Ola 1 · Mar 2024 (140 mun.)",
        2: "Ola 2 · Oct 2024 (131 mun.)",
    }
    raw_list = sorted(buckets.values(), key=lambda x: (x["wave"], x["quarter_idx"]))
    base_rent: dict[int, float] = {}
    base_contracts: dict[int, float] = {}
    # Use 2023 quarterly average as base=100 to smooth seasonality in the index chart
    for w in (0, 1, 2):
        w23 = [x for x in raw_list if x["wave"] == w and x["anyo"] == 2023]
        r_vals = [
            x["rent_weighted_num"] / x["rent_weighted_den"]
            for x in w23
            if x["rent_weighted_den"] > 0
        ]
        c_vals = [x["contractes_total"] for x in w23]
        base_rent[w] = sum(r_vals) / len(r_vals) if r_vals else 1.0
        base_contracts[w] = sum(c_vals) / len(c_vals) if c_vals else 1.0

    out = []
    for x in raw_list:
        w = x["wave"]
        w_rent = (
            round(x["rent_weighted_num"] / x["rent_weighted_den"], 2)
            if x["rent_weighted_den"] > 0
            else None
        )
        t_tot = x["temporada_total"] if x["has_temporada"] else None
        t_share_pct = (
            round(100.0 * t_tot / (x["contractes_total"] + t_tot), 2)
            if t_tot is not None and (x["contractes_total"] + t_tot) > 0
            else None
        )
        out.append(
            {
                "wave": w,
                "wave_label": wave_labels[w],
                "quarter_label": x["quarter_label"],
                "quarter_idx": x["quarter_idx"],
                "anyo": x["anyo"],
                "trimestre": x["trimestre"],
                "rent_weighted_eur": w_rent,
                "rent_idx_2023": round(100.0 * w_rent / base_rent[w], 2) if w_rent else None,
                "contractes_total": x["contractes_total"],
                "contracts_idx_2023": round(100.0 * x["contractes_total"] / base_contracts[w], 2),
                "temporada_total": t_tot,
                "temporada_share_pct": t_share_pct,
                "active_rent_munis": x["active_rent_n"],
            }
        )
    return out


def pretrend_summary(es_rows: list[dict]) -> dict:
    pre = [r for r in es_rows if r["is_pre"] and r["rel_q"] != -1]
    if not pre:
        return {"n_pre": 0, "max_abs_t": None, "sig_pre_leads": 0, "verdict": "unavailable"}
    ts = [abs(r["beta"] / r["se"]) if r["se"] > 1e-12 else 0.0 for r in pre]
    sig = sum(1 for t in ts if t >= 1.96)
    max_t = round(max(ts), 2)
    verdict = (
        "passes_pretrends" if sig == 0 else ("mixed_pretrends" if sig <= 1 else "fails_pretrends")
    )
    return {"n_pre": len(pre), "max_abs_t": max_t, "sig_pre_leads": sig, "verdict": verdict}


def run_analysis() -> dict:
    rows = load_rows()
    active = active_municipalities(rows, min_pre_rent_quarters=12)
    active_rows = [r for r in rows if r["codi"] in active]

    # Outcome extractors
    def y_log_rent(r):
        return math.log(r["lloguer_eur"]) if r["lloguer_eur"] and r["lloguer_eur"] > 0 else None

    def y_log_contracts(r):
        return math.log(r["contractes"]) if r["contractes"] and r["contractes"] > 0 else None

    def y_temp_share(r):
        return r["temporada_share"] if r["temporada_share"] is not None else None

    # Design subsets
    # A: Wave 1 vs Wave 2, 2019Q1–2024Q3 (clean not-yet-treated control)
    sub_a = [r for r in active_rows if r["wave"] in (1, 2) and r["quarter_idx"] < W2_START_IDX]
    sub_a_pre = [r for r in sub_a if r["quarter_idx"] < W1_START_IDX]
    # B: Wave 1 vs Never-treated active markets, 2019Q1–2026Q2
    sub_b = [r for r in active_rows if r["wave"] in (1, 0)]
    sub_b_pre = [r for r in sub_b if r["quarter_idx"] < W1_START_IDX]
    # C: Wave 2 vs Never-treated active markets, 2019Q1–2026Q2
    sub_c = [r for r in active_rows if r["wave"] in (2, 0)]
    sub_c_pre = [r for r in sub_c if r["quarter_idx"] < W2_START_IDX]
    # D: All active markets with Comarca × Quarter FE (staggered treatment indicator)
    sub_d = active_rows
    sub_d_pre = [r for r in active_rows if r["quarter_idx"] < W1_START_IDX]

    def d_w1(r):
        return 1 if (r["wave"] == 1 and r["quarter_idx"] >= W1_START_IDX) else 0

    def d_w2(r):
        return 1 if (r["wave"] == 2 and r["quarter_idx"] >= W2_START_IDX) else 0

    def d_staggered(r):
        if r["wave"] == 1 and r["quarter_idx"] >= W1_START_IDX:
            return 1
        if r["wave"] == 2 and r["quarter_idx"] >= W2_START_IDX:
            return 1
        return 0

    def d_placebo_w1(r):
        return 1 if (r["wave"] == 1 and r["quarter_idx"] >= PLACEBO_START_IDX) else 0

    def d_placebo_w2(r):
        return 1 if (r["wave"] == 2 and r["quarter_idx"] >= PLACEBO_START_IDX) else 0

    def comarca_q(r):
        return f"{r['comarca']}|{r['quarter_label']}"

    designs = []
    specs = [
        (
            "A_w1_vs_w2",
            "Ola 1 vs Ola 2 (no tratada aún, hasta 2024T3)",
            sub_a,
            sub_a_pre,
            d_w1,
            d_placebo_w1,
            lambda r: r["quarter_label"],
        ),
        (
            "B_w1_vs_never",
            "Ola 1 vs No tensionados activos (2019–2026T2)",
            sub_b,
            sub_b_pre,
            d_w1,
            d_placebo_w1,
            lambda r: r["quarter_label"],
        ),
        (
            "C_w2_vs_never",
            "Ola 2 vs No tensionados activos (2019–2026T2)",
            sub_c,
            sub_c_pre,
            d_w2,
            d_placebo_w2,
            lambda r: r["quarter_label"],
        ),
        (
            "D_within_comarca",
            "Intra-comarca (FE municipio + comarca×trimestre)",
            sub_d,
            sub_d_pre,
            d_staggered,
            d_placebo_w1,
            comarca_q,
        ),
    ]
    outcomes = [
        ("log_rent", "Alquiler medio contractual (log €/mes)", y_log_rent),
        ("log_contracts", "Contratos habituales firmados (log)", y_log_contracts),
        ("temporada_share", "Cuota de alquiler de temporada (pp, 2023–2026T2)", y_temp_share),
    ]

    for d_id, d_label, sub, sub_pre, d_fn, p_fn, t_fn in specs:
        for o_id, o_label, y_fn in outcomes:
            est = fit_did(sub, y_fn, d_fn, time_key_fn=t_fn, run_wild=True)
            # Placebo on pre-treatment only (only for outcomes with >= 2019 history)
            if o_id != "temporada_share":
                plac = fit_did(sub_pre, y_fn, p_fn, time_key_fn=t_fn, run_wild=False)
            else:
                plac = {"beta": None, "se_cr1v": None, "t_cr1v": None}
            row = {
                "design_id": d_id,
                "design_label": d_label,
                "outcome_id": o_id,
                "outcome_label": o_label,
                "n_obs": est.get("n_obs"),
                "n_munis": est.get("n_munis"),
                "n_treated_munis": est.get("n_treated_munis"),
                "beta": est.get("beta"),
                "effect_display": (
                    round(est["beta"] * 100.0, 2)
                    if o_id == "temporada_share" and est.get("beta") is not None
                    else est.get("pct_approx")
                ),
                "effect_unit": "pp" if o_id == "temporada_share" else "%",
                "se_cr1v": est.get("se_cr1v"),
                "t_cr1v": est.get("t_cr1v"),
                "wild_p": est.get("wild_p"),
                "placebo_beta": plac.get("beta"),
                "placebo_t": plac.get("t_cr1v"),
            }
            designs.append(row)

    # Event studies for the two main horizons:
    # 1. Design B (Wave 1 vs Never-treated active, k = -8..+8 around 2024Q2)
    # 2. Design A (Wave 1 vs Wave 2 not-yet-treated, k = -8..+1 around 2024Q2)
    # 3. Design C (Wave 2 vs Never-treated active, k = -8..+6 around 2024Q4)
    es_b_rent = fit_event_study(sub_b, y_log_rent, 1, W1_START_IDX, k_min=-8, k_max=8)
    es_b_contracts = fit_event_study(sub_b, y_log_contracts, 1, W1_START_IDX, k_min=-8, k_max=8)
    es_a_rent = fit_event_study(sub_a, y_log_rent, 1, W1_START_IDX, k_min=-8, k_max=1)
    es_a_contracts = fit_event_study(sub_a, y_log_contracts, 1, W1_START_IDX, k_min=-8, k_max=1)
    es_c_rent = fit_event_study(sub_c, y_log_rent, 2, W2_START_IDX, k_min=-8, k_max=6)
    es_c_contracts = fit_event_study(sub_c, y_log_contracts, 2, W2_START_IDX, k_min=-8, k_max=6)

    event_study_rows = []
    for tag, outcome, series in [
        ("B_w1_vs_never", "log_rent", es_b_rent),
        ("B_w1_vs_never", "log_contracts", es_b_contracts),
        ("A_w1_vs_w2", "log_rent", es_a_rent),
        ("A_w1_vs_w2", "log_contracts", es_a_contracts),
        ("C_w2_vs_never", "log_rent", es_c_rent),
        ("C_w2_vs_never", "log_contracts", es_c_contracts),
    ]:
        for item in series:
            event_study_rows.append({"design_id": tag, "outcome_id": outcome, **item})

    pretrends = {
        "A_w1_vs_w2_rent": pretrend_summary(es_a_rent),
        "A_w1_vs_w2_contracts": pretrend_summary(es_a_contracts),
        "B_w1_vs_never_rent": pretrend_summary(es_b_rent),
        "B_w1_vs_never_contracts": pretrend_summary(es_b_contracts),
        "C_w2_vs_never_rent": pretrend_summary(es_c_rent),
        "C_w2_vs_never_contracts": pretrend_summary(es_c_contracts),
    }

    group_series = build_group_series(rows, active)

    return {
        "meta": {
            "source_parquet": str(PARQUET.relative_to(ROOT)),
            "start_year": START_YEAR,
            "wave1_effective_quarter": "2024Q2",
            "wave2_effective_quarter": "2024Q4",
            "active_munis_total": len(active),
            "active_munis_by_wave": {
                str(w): len({r["codi"] for r in active_rows if r["wave"] == w}) for w in (0, 1, 2)
            },
            "wild_reps": WILD_REPS,
            "seed": SEED,
        },
        # Freshness key (audit_claims.MODEL_FRESHNESS): the fetch step rewrites
        # the parquet, so a new parquet hash means these DiD numbers are stale.
        "_meta": ols.model_meta(__file__, [str(PARQUET.relative_to(ROOT))]),
        "did_summary": designs,
        "pretrends": pretrends,
        "event_study": event_study_rows,
        "group_series": group_series,
    }


def write_duckdb(result: dict) -> None:
    tmp = DUCKDB_OUT.with_suffix(".duckdb.tmp")
    if tmp.exists():
        tmp.unlink()
    con = duckdb.connect(str(tmp))
    con.register("did_tbl", pa.Table.from_pylist(result["did_summary"]))
    con.register("es_tbl", pa.Table.from_pylist(result["event_study"]))
    con.register("grp_tbl", pa.Table.from_pylist(result["group_series"]))
    con.execute("CREATE TABLE cat_did_summary AS SELECT * FROM did_tbl")
    con.execute("CREATE TABLE cat_event_study AS SELECT * FROM es_tbl")
    con.execute("CREATE TABLE cat_group_series AS SELECT * FROM grp_tbl")
    con.close()
    tmp.replace(DUCKDB_OUT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify artifact and DuckDB match")
    args = parser.parse_args()

    result = run_analysis()
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_text() != payload:
            raise SystemExit(
                f"Stale {ARTIFACT.name}; re-run explorations/catalonia_rent_control.py"
            )
        if not DUCKDB_OUT.is_file():
            raise SystemExit(f"Missing {DUCKDB_OUT.name}")
        print("catalonia_rent_control analysis: verified")
        return

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload)
    write_duckdb(result)

    print(
        f"Active municipalities (>=12 pre rent quarters): {result['meta']['active_munis_by_wave']}"
    )
    print("\n=== DiD Summary ===")
    for r in result["did_summary"]:
        print(
            f"  {r['design_id']:17s} | {r['outcome_id']:15s} | "
            f"eff={r['effect_display']:+6.2f}{r['effect_unit']:2s} "
            f"(t={r['t_cr1v']:+6.2f}, wild_p={r['wild_p']}) | "
            f"placebo_t={r['placebo_t']} | n={r['n_obs']}"
        )
    print("\n=== Pre-trend checks ===")
    for k, v in result["pretrends"].items():
        print(f"  {k:28s}: {v}")


if __name__ == "__main__":
    main()
