"""Descriptive overlap of tourist stock shares and annual rents, by INE code.

Compare SERPAVI levels and growth; for growth only, compare SERPAVI and IPVA
on identical municipal samples. August stock changes are also compared with
subsequent annual rent changes that share no calendar year. Descriptive only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from fractions import Fraction
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import ols, rank_stats  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

VUT = RAW / "parquet/vut_municipal.parquet"
IPVA = RAW / "parquet/ipva_municipal.parquet"
MARTS = PROCESSED / "marts.duckdb"
ARTIFACT = ROOT / "artifacts/vut_rent_overlap.json"
YEARS = tuple(range(2020, 2025))
MONTH = 8
END = 2024


def index(rows, *, strictly_positive=False):
    values = {}
    for year, code, value in rows:
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{5}", code):
            raise ValueError(f"Invalid municipality code {code!r}")
        key = (year, code)
        if key in values:
            raise ValueError(f"Duplicate municipality-year {key}")
        if not math.isfinite(value) or value < 0 or (strictly_positive and value == 0):
            raise ValueError(f"Invalid observation for {key}: {value}")
        values[key] = value
    return values


def endpoint_codes(series, start, end):
    return {c for y, c in series if y == start and (end, c) in series}


def growth_factor(series, code, start, end):
    return Fraction(str(series[end, code])) / Fraction(str(series[start, code]))


def census_bases(rows):
    """Named municipal totals only; a provincial remainder is never a town."""
    bases = {}
    for code, name, homes, andalucia in rows:
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{5}", code):
            raise ValueError(f"Invalid census code: {code!r}")
        if code.endswith("999") != name.startswith("Resto "):
            raise ValueError(f"Unexpected census remainder: {code} {name}")
        if code.endswith("999"):
            continue
        if not isinstance(andalucia, bool):
            raise ValueError(f"Unknown census region for {code}")
        if code in bases or type(homes) is not int or homes <= 0:
            raise ValueError(f"Duplicate or invalid census base: {code} {homes!r}")
        bases[code] = (homes, andalucia)
    return bases


def fixed_stock_change(stock, code, start, end, homes):
    if (start, code) not in stock or (end, code) not in stock:
        raise ValueError(f"Municipality without an endpoint count: {code}")
    old, new = stock[start, code], stock[end, code]
    if any(not math.isfinite(v) or v < 0 or int(v) != v for v in (old, new)):
        raise ValueError(f"Invalid tourist dwelling count for {code}")
    return Fraction(100 * (int(new) - int(old)), homes)


def net_change_summary(net, rent_factors):
    """Rank net changes before grouping; report medians of town-specific growth rates."""
    by_direction = {}
    for sign, name in [(-1, "decreased"), (0, "unchanged"), (1, "increased")]:
        idx = [i for i, change in enumerate(net) if (change > 0) - (change < 0) == sign]
        by_direction[name] = {
            "n": len(idx),
            "median_change_per_100": round(float(statistics.median(net[i] for i in idx)), 6)
            if idx
            else None,
            "median_rent_growth_pct": {
                label: round(float(statistics.median(100 * (values[i] - 1) for i in idx)), 6)
                if idx
                else None
                for label, values in rent_factors.items()
            },
        }
    return {
        "spearman": {
            label: rank_stats.spearman(net, values, digits=6)
            for label, values in rent_factors.items()
        },
        "by_direction": by_direction,
    }


def earlier_tourism_later_rents(rents, ipva, stock, bases, years):
    """Compare earlier one-year and net two-year stock changes on one fixed cohort."""
    observed = set(years)
    starts = sorted(y for y in observed if y + 1 in observed)
    pairs = [(s, r) for s in starts for r in starts if s + 1 < r]
    if not pairs:
        raise ValueError("No non-overlapping annual windows")
    stock_years = sorted({y for s, _ in pairs for y in (s, s + 1)})
    rent_years = sorted({y for _, r in pairs for y in (r, r + 1)})
    # Eligibility uses just the years required for each measure: a later
    # tourist-count revision cannot change the cohort or the exposures here.
    rent_codes = {
        c
        for y, c in rents
        if y == rent_years[0] and all((t, c) in rents and (t, c) in ipva for t in rent_years)
    }
    codes = sorted(
        c for c in rent_codes & bases.keys() if all((t, c) in stock for t in stock_years)
    )
    if len(codes) < 2:
        raise ValueError("Insufficient common towns for non-overlapping windows")
    comparisons, net_two_year = {}, {}
    for s, r in pairs:
        factors = {
            label: [growth_factor(series, c, r, r + 1) for c in codes]
            for label, series in (("serpavi", rents), ("ipva", ipva))
        }
        dx = [fixed_stock_change(stock, c, s, s + 1, bases[c][0]) for c in codes]
        comparisons[f"{s}_{s + 1}__{r}_{r + 1}"] = {
            label: rank_stats.spearman(dx, values, digits=6) for label, values in factors.items()
        }
        if (s + 1, r) in pairs:
            # Both adjacent changes precede the same rent window. Their middle
            # count cancels in the net exposure, not in their rank correlations.
            net = [fixed_stock_change(stock, c, s, s + 2, bases[c][0]) for c in codes]
            net_two_year[f"{s}_{s + 2}__{r}_{r + 1}"] = net_change_summary(net, factors)
    return {
        "stock_years": stock_years,
        "rent_years": rent_years,
        "rent_complete": len(rent_codes),
        "n": len(codes),
        "comparisons": comparisons,
        "net_two_year": net_two_year,
    }


def fixed_base_check(common, stock, shares, bases, start, end):
    """Re-rank both exposures and outcomes on exactly the same codes in each cut."""
    rows, outside_andalucia = [], []
    for c in sorted(common.keys() & bases.keys()):
        homes, andalucia = bases[c]
        fixed = fixed_stock_change(stock, c, start, end, homes)
        # Diagnostic only: census table 59531 is a fixed alternative, not an
        # assumption that the VTE denominator is identical in every town.
        dev = abs(Fraction(100 * int(stock[end, c]), homes) - Fraction(str(shares[end, c])))
        row = (*common[c], fixed, dev <= Fraction(1, 200))
        rows.append(row)
        if not andalucia:
            outside_andalucia.append(row)

    def summarize(sample):
        if not sample:
            raise ValueError("No fixed-base municipal observations for this geographic cut")
        reported, sr, ir, fixed, aligned = zip(*sample, strict=True)
        return {
            "n": len(sample),
            "end_shares_within_rounding": sum(aligned),
            "reported_serpavi": rank_stats.spearman(reported, sr, digits=6),
            "fixed_serpavi": rank_stats.spearman(fixed, sr, digits=6),
            "reported_ipva": rank_stats.spearman(reported, ir, digits=6),
            "fixed_ipva": rank_stats.spearman(fixed, ir, digits=6),
            "exposure_rank_agreement": rank_stats.spearman(reported, fixed, digits=6),
        }

    return {
        "missing_named_census_codes": sorted(common.keys() - bases.keys()),
        "all": summarize(rows),
        "outside_andalucia": summarize(outside_andalucia),
    }


def compare(rents, shares, stock, start, end, *, ipva=None, census=None):
    if census is not None and ipva is None:
        raise ValueError("Fixed-base comparison requires the common IPVA rent sample")
    if ipva is not None and start >= end:
        raise ValueError("Use IPVA only for changes between ordered endpoints, not rent levels")
    rent_codes = endpoint_codes(rents, start, end)
    share_codes = endpoint_codes(shares, start, end)
    keys = {c for y, c in stock if y == end}
    if share_codes - keys:
        raise ValueError("End-year tourist shares have no matching stock")
    codes = sorted(rent_codes & share_codes)
    if not codes:
        raise ValueError("No paired municipal observations")
    end_x = [shares[end, c] for c in codes]
    end_y = [rents[end, c] for c in codes]
    x, y = end_x, end_y
    if start != end:
        # Fractions preserve ties implied by the published decimals, such as
        # 0.35−0.30 and 0.15−0.10. Rank correlation ignores positive scale.
        x = [Fraction(str(shares[end, c])) - Fraction(str(shares[start, c])) for c in codes]
        y = [growth_factor(rents, c, start, end) for c in codes]
    national_stock = sum(stock[end, c] for c in sorted(keys))
    matched_stock = sum(stock[end, c] for c in codes)
    if national_stock <= 0:
        raise ValueError("No positive national tourist stock")
    result = {
        "n": len(codes),
        "rents_both_endpoints": len(rent_codes),
        "shares_both_endpoints": len(share_codes),
        "end_municipality_count": len(keys),
        "end_tourist_stock": int(national_stock),
        "end_matched_stock": int(matched_stock),
        "end_matched_stock_pct": round(100 * matched_stock / national_stock, 4),
        "end_matched_municipalities_pct": round(100 * len(codes) / len(keys), 4),
        "spearman": rank_stats.spearman(x, y, digits=6),
        "end_levels_spearman_on_same_sample": rank_stats.spearman(end_x, end_y, digits=6),
    }
    if ipva is not None:
        ipva_codes = endpoint_codes(ipva, start, end)
        # Select triples first, then rank each vector on this intersection.
        # Reusing ranks computed on the larger SERPAVI sample would be wrong.
        common = {
            c: (dx, sr, growth_factor(ipva, c, start, end))
            for c, dx, sr in zip(codes, x, y, strict=True)
            if c in ipva_codes
        }
        if not common:
            raise ValueError("No common VTE/SERPAVI/IPVA change observations")
        delta_share, rent_growth, index_growth = zip(*common.values(), strict=True)
        common_stock = int(sum(stock[end, c] for c in common))
        result["common_ipva_sample"] = {
            "n": len(common),
            "ipva_both_endpoints": len(ipva_codes),
            "end_matched_stock": common_stock,
            "end_matched_stock_pct": round(100 * common_stock / national_stock, 4),
            "tourism_serpavi_spearman": rank_stats.spearman(delta_share, rent_growth, digits=6),
            "tourism_ipva_spearman": rank_stats.spearman(delta_share, index_growth, digits=6),
            "serpavi_ipva_spearman": rank_stats.spearman(rent_growth, index_growth, digits=6),
        }
        if census is not None:
            result["fixed_2021_base"] = fixed_base_check(common, stock, shares, census, start, end)
    return result


def build():
    with duckdb.connect(str(MARTS), read_only=True) as con:
        census = census_bases(
            con.execute("""
                select codigo, municipio, valor, left(codigo, 2) in (
                    select cpro from dim_territorio where ccaa='Andalucía'
                ) from censo2021_intensidad where medida='Viviendas totales'
            """).fetchall()
        )
        ipva = index(
            con.execute(
                """select anyo, codigo_ine, valor from read_parquet(?)
                where nivel='municipio' and medida='indice' and anyo in (select unnest(?))""",
                [str(IPVA), list(YEARS)],
            ).fetchall(),
            strictly_positive=True,
        )
        tours = con.execute(
            """select anyo, codigo_ine, medida, valor from read_parquet(?)
            where nivel='municipio' and periodo=? and anyo in (select unnest(?))
              and medida in ('viviendas_turisticas', 'pct_censadas')""",
            [str(VUT), MONTH, list(YEARS)],
        ).fetchall()
        rents = index(
            con.execute(
                """select anyo, codigo, valor from serpavi_municipal
                where medida='ALQM2_LV_M_VC' and anyo in (select unnest(?))""",
                [list(YEARS)],
            ).fetchall(),
            strictly_positive=True,
        )
    shares = index((year, code, value) for year, code, m, value in tours if m == "pct_censadas")
    stock = index(
        (year, code, value) for year, code, m, value in tours if m == "viviendas_turisticas"
    )
    return {
        "tourist_month": MONTH,
        "tourist_measure": "published tourist dwellings as a share of census dwellings",
        "rent_measure": "annual SERPAVI collective dwelling median EUR/m²/month",
        "levels_2024": compare(rents, shares, stock, END, END),
        "alternate_rent_measure": "annual overall IPVA rent price index (changes only)",
        "changes_2022_2024": compare(rents, shares, stock, 2022, END, ipva=ipva, census=census),
        "changes_2020_2024": compare(rents, shares, stock, 2020, END, ipva=ipva, census=census),
        "earlier_tourism_later_rents": earlier_tourism_later_rents(
            rents, ipva, stock, census, YEARS
        ),
        "_meta": ols.model_meta(
            __file__,
            [str(p.relative_to(ROOT)) for p in (VUT, IPVA, MARTS, Path(rank_stats.__file__))],
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_text() != payload:
            raise SystemExit("Stale vut_rent_overlap.json; rerun vut_rent_overlap.py")
    else:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(payload)
    print("vut_rent_overlap: verified municipal levels, same-period changes and later rent growth")


if __name__ == "__main__":
    main()
