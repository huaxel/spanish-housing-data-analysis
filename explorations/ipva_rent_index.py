"""Compare municipal changes in INE's IPVA and MIVAU's SERPAVI tax-based rents.

Join official five-digit codes and use published positive observations at both
endpoints. Comparison of two statistics, not independent source validation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols, rank_stats  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

IPVA_PARQUET = RAW / "parquet" / "ipva_municipal.parquet"
MARTS = PROCESSED / "marts.duckdb"
ARTIFACT = ROOT / "artifacts/ipva_rent_index.json"
WINDOWS = [(2013, 2023), (2019, 2023), (2019, 2024)]


def by_code(rows):
    out = {}
    for code, year, value in rows:
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{5}", code):
            raise ValueError(f"Invalid municipality code {code!r}")
        years = out.setdefault(code, {})
        if year in years or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Duplicate or invalid observation for {(code, year)}")
        years[year] = Fraction(str(value))
    return out


def pair_ordering(codes, x, y) -> dict:
    """Compare faster-rising towns, within/across provinces on one common sample."""
    if len(set(codes)) != len(codes):
        raise ValueError("Pair ordering requires unique municipality codes")
    groups = [c[:2] for c in codes]
    sizes = Counter(groups)
    # Ranks preserve exact fractional changes and ties without doing rational
    # arithmetic for every pair. Both comparisons omit singleton provinces.
    rows = [
        (g, rx, ry)
        for g, rx, ry in zip(groups, rank_stats.midranks(x), rank_stats.midranks(y), strict=True)
        if sizes[g] >= 2
    ]
    per_province = {g: Counter() for g in sorted(sizes) if sizes[g] >= 2}
    per_province_pair = defaultdict(Counter)
    for (g, x1, y1), (h, x2, y2) in combinations(rows, 2):
        counts = per_province[g] if g == h else per_province_pair[(g, h) if g < h else (h, g)]
        if x1 == x2 or y1 == y2:
            counts["tied"] += 1
        elif (x1 < x2) == (y1 < y2):
            counts["agree"] += 1
        else:
            counts["disagree"] += 1

    def summarize(counts):
        n = counts["agree"] + counts["disagree"]
        return {
            "agreed": counts["agree"],
            "comparable": n,
            "tied": counts["tied"],
            "agreement_pct": round(100 * counts["agree"] / n, 2) if n else None,
        }

    def balanced(groups):
        # Average unrounded rates across provinces (or unordered province pairs).
        # An entirely tied group has no defined rate.
        rates = [
            c["agree"] / (c["agree"] + c["disagree"]) for c in groups if c["agree"] + c["disagree"]
        ]
        return len(rates), round(100 * statistics.mean(rates), 2) if rates else None

    n_provinces, within_balanced = balanced(per_province.values())
    n_province_pairs, between_balanced = balanced(per_province_pair.values())
    return {
        "municipalities": len(rows),
        "singletons_excluded": len(codes) - len(rows),
        "provinces_with_comparable_pairs": n_provinces,
        "comparable_province_pairs": n_province_pairs,
        "within": summarize(sum(per_province.values(), Counter())),
        "between": summarize(sum(per_province_pair.values(), Counter())),
        "equal_province_agreement_pct": within_balanced,
        "equal_province_pair_agreement_pct": between_balanced,
        "by_province": {
            g: {"municipalities": sizes[g], **summarize(c)} for g, c in per_province.items()
        },
    }


def build() -> dict:
    with duckdb.connect(str(MARTS), read_only=True) as con:
        ipva = by_code(
            con.execute(
                """select codigo_ine, anyo, valor from read_parquet(?)
               where nivel='municipio' and medida='indice'""",
                [str(IPVA_PARQUET)],
            ).fetchall()
        )
        rents = by_code(
            con.execute(
                """select codigo, anyo, valor from serpavi_municipal
               where medida='ALQM2_LV_M_VC'"""
            ).fetchall()
        )
    matched = ipva.keys() & rents.keys()
    windows = []
    for y0, y1 in WINDOWS:
        both = {c for c in ipva if y0 in ipva[c] and y1 in ipva[c]}
        codes = sorted(c for c in both & matched if y0 in rents[c] and y1 in rents[c])
        if len(codes) < 50:
            raise ValueError(f"IPVA: insufficient pairs for {y0}–{y1}: {len(codes)}")
        # Compute exact ratios from the stored decimal values so equal changes
        # receive equal ranks (and unrounded changes determine the quartiles).
        x = [100 * (ipva[c][y1] / ipva[c][y0] - 1) for c in codes]
        y = [100 * (rents[c][y1] / rents[c][y0] - 1) for c in codes]
        rho = rank_stats.spearman(x, y, digits=3)
        ipva_chg = list(map(float, x))
        serp_chg = list(map(float, y))
        gaps = sorted(a - b for a, b in zip(ipva_chg, serp_chg, strict=True))
        n = len(gaps)

        def quantile(values: list[float], p: float, size: int = n) -> float:
            return round(values[min(size - 1, int(p * size))], 2)

        # Stable code order breaks any ties at a quartile boundary.
        ordered = sorted(range(n), key=y.__getitem__)
        quartiles = []
        for i in range(4):
            chunk = ordered[i * n // 4 : (i + 1) * n // 4]
            quartiles.append(
                {
                    "quartile": i + 1,
                    "n": len(chunk),
                    "median_serpavi_pct": round(statistics.median(serp_chg[j] for j in chunk), 2),
                    "median_gap_pp": round(
                        statistics.median(ipva_chg[j] - serp_chg[j] for j in chunk), 2
                    ),
                }
            )

        windows.append(
            {
                "from": y0,
                "to": y1,
                "n": n,
                "ipva_at_both_endpoints": len(both),
                "ipva_median_pct": round(statistics.median(ipva_chg), 2),
                "serpavi_median_pct": round(statistics.median(serp_chg), 2),
                "pearson": round(statistics.correlation(ipva_chg, serp_chg), 3),
                "spearman": rho,
                "pair_ordering": pair_ordering(codes, x, y),
                "gap_pp": {
                    "p10": quantile(gaps, 0.10),
                    "median": round(statistics.median(gaps), 2),
                    "p90": quantile(gaps, 0.90),
                },
                "quartiles_by_serpavi_change": quartiles,
            }
        )

    return {
        "coverage": {
            "ipva_municipios": len(ipva),
            "matched": len(matched),
            "unmatched": len(ipva.keys() - matched),
            "unmatched_examples": sorted(ipva.keys() - matched)[:10],
        },
        "windows": windows,
        "_meta": ols.model_meta(
            __file__,
            [
                str(IPVA_PARQUET.relative_to(ROOT)),
                str(MARTS.relative_to(ROOT)),
                str(Path(rank_stats.__file__).relative_to(ROOT)),
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
            raise SystemExit("Stale artifacts/ipva_rent_index.json; re-run ipva_rent_index.py")
        print("ipva_rent_index: verified")
        return
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload)
    cov = data["coverage"]
    print(
        f"IPVA municipios {cov['ipva_municipios']}, "
        f"matched {cov['matched']} ({cov['unmatched']} unmatched)"
    )
    for w in data["windows"]:
        span = f"{w['from']}->{w['to']}"
        print(
            f"  {span}: n={w['n']} | IPVA {w['ipva_median_pct']:+.1f}% vs "
            f"SERPAVI {w['serpavi_median_pct']:+.1f}% | r={w['pearson']:+.3f} "
            f"rho={w['spearman']:+.3f} | gap median {w['gap_pp']['median']:+.1f} pp "
            f"({w['gap_pp']['p10']:+.1f} to {w['gap_pp']['p90']:+.1f})"
        )


if __name__ == "__main__":
    main()
