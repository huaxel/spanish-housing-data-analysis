"""What INE's own household projection says about the repo's two-group pattern.

The repo's central finding is that a flat national dwellings-per-household ratio
hides two opposite regimes: metropolitan scarcity (Madrid, Cataluña falling or
flat) against interior overhang (rising). Until now the household side ended at
the last observed ECP year, so the question "does that split persist?" could
only be answered by extrapolation — or not at all.

INE's PROH (operation 70, table 54562) publishes households at 1 January for
2026–2040 by CCAA. This script uses it as an **external input about household
formation**, not as this project's forecast: we do not model prices, demand or
migration, we report what the official projection implies and how it lines up
with the stock the marts already measure.

Two things are computed:

1. The projected path: national and CCAA growth 2026→2040, and how concentrated
   it is (top-4 CCAA share).
2. The pairing with current stock: dwellings per household in 2025 against
   projected growth. If the two-group pattern were fading, the CCAA with the
   fattest stock per household would be the ones projected to grow; the sign of
   that relationship is the answer.

Dwellings implied by the projection are reported as an **identity** (projected
households × today's dwellings per household), never as a need estimate — the
same discipline the deficit explainer applies to household-minus-stock sums.

Outputs: artifacts/proh_households.json with an `_meta` freshness key.
Use --check to verify the artifact matches the pinned inputs.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402
from spanish_housing.ine_api import norm_name as N  # noqa: E402

PROH_PARQUET = RAW / "parquet" / "proh_hogares.parquet"
ECP_PARQUET = RAW / "parquet" / "ecp_hog_ccaa.parquet"
MARTS = PROCESSED / "marts.duckdb"
ARTIFACT = ROOT / "artifacts/proh_households.json"
FIRST_YEAR, LAST_YEAR = 2026, 2040


def load_projection() -> dict[str, dict[int, float]]:
    rows = pq.read_table(PROH_PARQUET).to_pylist()
    out: dict[str, dict[int, float]] = {}
    for r in rows:
        if r["medida"] != "Total":
            continue
        out.setdefault(r["territorio"], {})[r["anyo"]] = r["valor"]
    return out


def load_ecp_2026() -> float:
    """Observed ECP households at 1 Jan 2026, to sanity-check the projection base."""
    rows = pq.read_table(ECP_PARQUET).to_pylist()
    for r in rows:
        if (
            r["territorio"] == "Total Nacional"
            and r["tamano"] == "Total"
            and r["anyo"] == FIRST_YEAR
        ):
            return float(r["hogares"])
    raise SystemExit("PROH: ECP national total for 2026 not found — rerun make fetch")


def load_stock() -> dict[str, dict[str, float]]:
    con = duckdb.connect(str(MARTS), read_only=True)
    try:
        rows = con.execute(
            """
            select ccaa, anyo, viviendas_total, hogares
            from mart_ccaa_anual
            where ccaa != 'Nacional' and anyo = 2025
            """
        ).fetchall()
    finally:
        con.close()
    return {
        ccaa: {"viviendas_total": float(viv), "hogares": float(hog)}
        for ccaa, _anyo, viv, hog in rows
        if viv and hog
    }


def build() -> dict:
    proj = load_projection()
    stock = load_stock()

    national = proj["Total Nacional"]
    nat_first, nat_last = national[FIRST_YEAR], national[LAST_YEAR]
    national_block = {
        "first_year": FIRST_YEAR,
        "last_year": LAST_YEAR,
        "households_first": round(nat_first, 0),
        "households_last": round(nat_last, 0),
        "change": round(nat_last - nat_first, 0),
        "change_pct": round(100.0 * (nat_last / nat_first - 1.0), 2),
    }

    # Restrict to CCAA by matching INE names against the mart's CCAA dimension.
    by_norm = {N(ccaa): ccaa for ccaa in stock}
    ccaa_rows = []
    for terr, years in proj.items():
        if terr == "Total Nacional" or N(terr) not in by_norm:
            continue
        ccaa = by_norm[N(terr)]
        first, last = years.get(FIRST_YEAR), years.get(LAST_YEAR)
        if first is None or last is None:
            continue
        s = stock[ccaa]
        ratio = s["viviendas_total"] / s["hogares"]
        ccaa_rows.append(
            {
                "ccaa": ccaa,
                "households_2026": round(first, 0),
                "households_2040": round(last, 0),
                "change": round(last - first, 0),
                "change_pct": round(100.0 * (last / first - 1.0), 2),
                "dwellings_per_household_2025": round(ratio, 3),
                # Identity, not a need estimate: projected households × today's ratio.
                "dwellings_implied_2040": round(last * ratio, 0),
            }
        )
    ccaa_rows.sort(key=lambda r: -r["change"])

    total_growth = sum(r["change"] for r in ccaa_rows)
    top4 = sum(r["change"] for r in ccaa_rows[:4])
    ratios = [r["dwellings_per_household_2025"] for r in ccaa_rows]
    growth = [r["change_pct"] for r in ccaa_rows]
    pair = sorted(zip(ratios, growth, strict=True), key=lambda p: p[0])
    split = len(pair) // 2
    lean = [g for _r, g in pair[:split]]
    fat = [g for _r, g in pair[split:]]

    ecp_observed = load_ecp_2026()
    return {
        "ecp_check": {
            "observed_2026": ecp_observed,
            "projection_minus_observed": round(nat_first - ecp_observed, 0),
        },
        "source": {
            "operation_id": 70,
            "table_id": 54562,
            "url": "https://www.ine.es/jaxiT3/Tabla.htm?t=54562",
            "publisher": "INE · Proyección de Hogares (PROH)",
            "note": (
                "INE projection, not this project's forecast; base predates the latest ECP release"
            ),
        },
        "national": national_block,
        "concentration": {
            "top4_ccaa": [r["ccaa"] for r in ccaa_rows[:4]],
            "top4_change": round(top4, 0),
            "top4_share_pct": round(100.0 * top4 / total_growth, 2) if total_growth else None,
        },
        "stock_pairing": {
            "n_ccaa": len(ccaa_rows),
            "lean_stock_growth_median_pct": round(statistics.median(lean), 2),
            "fat_stock_growth_median_pct": round(statistics.median(fat), 2),
            "pearson_ratio_vs_growth": round(statistics.correlation(ratios, growth), 3),
        },
        "ccaa": ccaa_rows,
        "_meta": ols.model_meta(
            __file__,
            [
                str(PROH_PARQUET.relative_to(ROOT)),
                str(ECP_PARQUET.relative_to(ROOT)),
                str(MARTS.relative_to(ROOT)),
            ],
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify artifact matches inputs")
    args = parser.parse_args()

    data = build()
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_text() != payload:
            raise SystemExit("Stale artifacts/proh_households.json; re-run proh_households.py")
        print("proh_households: verified")
        return
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload)

    nat = data["national"]
    conc = data["concentration"]
    pair = data["stock_pairing"]
    print(
        f"national {nat['households_first']:,.0f} → {nat['households_last']:,.0f} "
        f"({nat['change']:+,.0f}, {nat['change_pct']:+.1f}%)"
    )
    names = ", ".join(conc["top4_ccaa"])
    print(f"  top-4 CCAA = {conc['top4_share_pct']}% of projected growth: {names}")
    print(
        f"  stock pairing: lean-stock CCAA median {pair['lean_stock_growth_median_pct']:+.1f}% vs "
        f"fat-stock {pair['fat_stock_growth_median_pct']:+.1f}% "
        f"(r = {pair['pearson_ratio_vs_growth']:+.3f}, n={pair['n_ccaa']})"
    )


if __name__ == "__main__":
    main()
