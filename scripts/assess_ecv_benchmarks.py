"""Benchmark-only ECV prototype; never exports microdata or triple-cross rates.

Official algorithm: LC-ILC 39-09 rev.1, housing-cost overburden section.
The historical algorithm and current layouts must be read together. Agreement
with rounded benchmarks is not certification of complex-sample inference.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import json
import math
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

AGES = ("TOTAL", "Y18-24", "Y25-29", "Y18-64", "Y_GE65")
TENURES = {"1": "OWN_NL", "2": "OWN_L", "3": "RENT_MKT", "4": "RENT_FR", "5": "RENT_FR"}
MAX_MEMBER = 128 * 1024 * 1024
REQUIRED_COLUMNS = {
    "d": {"DB010", "DB020", "DB030", "DB090", "DB090_F"},
    "h": {
        "HB010",
        "HB020",
        "HB030",
        "HX040",
        "HY020",
        "HY020_F",
        "HY070G",
        "HY070G_F",
        "HH070",
        "HH070_F",
        "HH021",
        "HH021_F",
    },
    "r": {"RB010", "RB020", "RB030", "RB050", "RB050_F", "RB081", "RB081_F", "RB090", "RB090_F"},
}
# The 2025 H CSV appends these modules beyond its base JSON register layout.
H_MODULE_COLUMNS = {
    "HC003A",
    "HC003A_F",
    "HC006",
    "HC006_F",
    "HEE01",
    "HEE01_F",
    "HEE07",
    "HEE07_F",
    "HEE09",
    "HEE09_F",
    "HEE11",
    "HEE11_F",
    "HEE12",
    "HEE12_F",
    "HEE13",
    "HEE13_F",
    "HEE14",
    "HEE14_F",
    "HS200",
    "HS200_F",
    "HS210",
    "HS210_F",
    "HS220",
    "HS220_F",
}


def number(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite numeric value")
    return result


def burden(monthly_cost: float, income: float, gross_allowance: float) -> bool:
    """Ordered official edge rules: nonpositive costs take precedence."""
    if not all(math.isfinite(x) for x in (monthly_cost, income, gross_allowance)):
        raise ValueError("Non-finite burden input")
    if monthly_cost < 0 or gross_allowance < 0:
        raise ValueError("Negative cost or allowance")
    net_cost = 12 * monthly_cost - gross_allowance
    net_income = income - gross_allowance
    if net_cost <= 0:
        return False
    if net_income <= 0:
        return True
    return net_cost > 0.4 * net_income


def weighted_cut(values: list[tuple[float, float]], fraction: float) -> float:
    """Historical official cut: first crossing, midpoint on exact cumulative equality."""
    if not values or not 0 < fraction < 1:
        raise ValueError("Invalid quantile request")
    if any(not math.isfinite(v) or not math.isfinite(w) or w <= 0 for v, w in values):
        raise ValueError("Invalid weighted values")
    target = math.fsum(w for _, w in values) * fraction
    accumulated = 0.0
    ordered = sorted(values)
    for index, (value, weight) in enumerate(ordered):
        accumulated += weight
        if accumulated == target and index + 1 < len(ordered):
            return (value + ordered[index + 1][0]) / 2
        if accumulated > target:
            return value
    return max(v for v, _ in values)


def age_groups(age: int) -> list[str]:
    # Born between income-year end and interview: official algorithm sets -1 to 0.
    if age == -1:
        age = 0
    if age < 0:
        raise ValueError("Unresolved negative reference age")
    result = ["TOTAL"]
    for code, lower, upper in (
        ("Y18-24", 18, 24),
        ("Y25-29", 25, 29),
        ("Y18-64", 18, 64),
        ("Y_GE65", 65, 999),
    ):
        if lower <= age <= upper:
            result.append(code)
    return result


def member(archive: zipfile.ZipFile, name: str) -> bytes:
    if len(archive.namelist()) != len(set(archive.namelist())):
        raise ValueError("Duplicate archive members")
    if archive.getinfo(name).file_size > MAX_MEMBER:
        raise ValueError("Archive member exceeds inspection bound")
    return archive.read(name)


def load_archive(path: Path, year: int) -> dict[str, list[dict]]:
    if year != 2025 or path.stat().st_size > MAX_MEMBER:
        raise ValueError("Unsupported year or oversized archive")
    result = {}
    with zipfile.ZipFile(path) as outer:
        with zipfile.ZipFile(
            io.BytesIO(member(outer, f"disreg_ecv{year % 100:02}.zip"))
        ) as layouts:
            for kind in ("d", "h", "r"):
                layout = json.loads(member(layouts, f"dr_ECV_SM_T{kind}_{year}.json"))
                with zipfile.ZipFile(io.BytesIO(member(outer, f"ECV_T{kind}_{year}.zip"))) as inner:
                    raw = member(inner, f"CSV/esudb{year % 100:02}{kind}.csv")
                    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
                    expected = [field["name"] for field in layout["layout"]]
                    actual = reader.fieldnames or []
                    extra = actual[len(expected) :]
                    allowed_extra = H_MODULE_COLUMNS if kind == "h" else set()
                    if (
                        actual[: len(expected)] != expected
                        or set(extra) != allowed_extra
                        or len(actual) != len(set(actual))
                    ):
                        raise ValueError("CSV differs from its base layout/module extension")
                    if not REQUIRED_COLUMNS[kind] <= set(actual):
                        raise ValueError("Required columns absent")
                    rows = []
                    for row in reader:
                        if None in row or None in row.values():
                            raise ValueError("Malformed CSV row")
                        rows.append(
                            {key: row[key] for key in actual if key in REQUIRED_COLUMNS[kind]}
                        )
                    result[kind] = rows
    return result


def prepare_population(tables: dict[str, list[dict]], year: int) -> dict:
    """Validated INTERNAL population; raw keys/rows must never be exported."""
    keyed = {}
    for kind, prefix in (("d", "DB"), ("h", "HB"), ("r", "RB")):
        keyed[kind] = {}
        for row in tables[kind]:
            if row[prefix + "010"] != str(year) or row[prefix + "020"] != "ES":
                raise ValueError("Unexpected survey year/country")
            identifier = int(row[prefix + "030"])
            if identifier <= 0 or identifier in keyed[kind]:
                raise ValueError("Invalid or duplicate key")
            keyed[kind][identifier] = row
    d, h, r = (keyed[k] for k in ("d", "h", "r"))
    if not d or not r or set(d) != set(h):
        raise ValueError("Household universes differ or are empty")
    counts = Counter(pid // 100 for pid in r)
    if set(counts) != set(h) or any(counts[k] != int(h[k]["HX040"]) for k in h):
        raise ValueError("Person linkage/member count mismatch")
    for rows, key in ((d, "DB090"), (r, "RB050")):
        if any(number(row[key]) <= 0 or row[key + "_F"] != "1" for row in rows.values()):
            raise ValueError("Invalid or incomplete weights")
    adults = Counter()
    children = Counter()
    for pid, p in r.items():
        if p["RB081_F"] != "1":
            raise ValueError("Missing reference age")
        if p["RB090_F"] != "1" or p["RB090"] not in {"1", "2"}:
            raise ValueError("Missing or unknown sex")
        age = int(p["RB081"])
        age_groups(age)
        (adults if age >= 14 else children)[pid // 100] += 1
    if any(adults[k] == 0 for k in h):
        raise ValueError("Equivalence convention for child-only household needs review")
    equivalents = {}
    income_flags = Counter()
    for hid, hh in h.items():
        if hh["HH021"] not in TENURES or hh["HH021_F"] != "1":
            raise ValueError("Unknown/incomplete tenure")
        # Current release: source 1/2/5; mode net=1, gross=5.
        for field, mode in (("HY020", "1"), ("HY070G", "5")):
            flag = hh[field + "_F"]
            if flag not in {source + mode for source in "125"}:
                raise ValueError("Income source/mode requires review")
            income_flags[field + ":" + flag] += 1
        if number(hh["HY070G"]) < 0:
            raise ValueError("Negative housing allowance")
        if hh["HH070_F"] not in {"1", "-1"}:
            raise ValueError("Unknown housing cost flag")
        scale = 1 + 0.5 * (adults[hid] - 1) + 0.3 * children[hid]
        equivalents[hid] = number(hh["HY020"]) / scale
    distribution = [(equivalents[pid // 100], number(p["RB050"])) for pid, p in r.items()]
    # National poverty threshold is inherited from the income-valid population.
    poverty_cut = 0.6 * weighted_cut(distribution, 0.5)
    return {
        "d": d,
        "h": h,
        "r": r,
        "equivalents": equivalents,
        "income_distribution": distribution,
        "poverty_cut": poverty_cut,
        "income_flags": income_flags,
    }


def calculate(tables: dict[str, list[dict]], year: int) -> dict:
    """Aggregate validation and candidate marginals; no individual output."""
    population = prepare_population(tables, year)
    d, h, r = (population[k] for k in ("d", "h", "r"))
    equivalents = population["equivalents"]
    distribution = population["income_distribution"]
    poverty_cut = population["poverty_cut"]
    income_flags = population["income_flags"]
    # DIAGNOSTIC CANDIDATE, not a confirmed official QPB convention:
    # LC-ILC 39-09 rev.1 excludes missing costs from housing rates, but its
    # QPB note does not unambiguously settle the ranking population. This
    # cost-eligible candidate matches rounded benchmarks; agreement is not proof.
    # No unavailable stratum-level calibration is claimed here.
    housing_distribution = [
        (equivalents[pid // 100], number(p["RB050"]))
        for pid, p in r.items()
        if h[pid // 100]["HH070_F"] == "1"
    ]
    quintile_cuts = [weighted_cut(housing_distribution, q / 5) for q in range(1, 5)]
    totals = defaultdict(lambda: [0.0, 0.0, 0])
    missing = 0
    missing_weight = 0.0
    nonpositive = 0
    for pid, p in r.items():
        hh = h[pid // 100]
        weight = number(p["RB050"])
        if hh["HH070_F"] == "-1":
            missing += 1
            missing_weight += weight
            continue
        if hh["HH070_F"] != "1":
            raise ValueError("Unknown housing cost flag")
        monthly, income, allowance = (number(hh[f]) for f in ("HH070", "HY020", "HY070G"))
        indicator = burden(monthly, income, allowance)
        nonpositive += income - allowance <= 0
        eq = equivalents[pid // 100]
        # Income classification uses disposable income BEFORE allowance subtraction.
        poverty = "B_60" if eq < poverty_cut else "A_60"
        groups = [
            ("tenure", "TOTAL"),
            ("tenure", TENURES[hh["HH021"]]),
            ("income", "TOTAL"),
            ("income", f"QU{bisect.bisect_left(quintile_cuts, eq) + 1}"),
        ]
        for age in age_groups(int(p["RB081"])):
            groups += [("age", age), ("age_poverty", age + ":" + poverty)]
        for key in groups:
            totals[key][0] += weight * indicator
            totals[key][1] += weight
            totals[key][2] += 1
    return {
        "survey_year": year,
        "publication_ready": False,
        "scope": "benchmark-only; no triple-cross rates or design-correct intervals",
        "quintile_methodology_status": "unresolved; cost-eligible ranking is diagnostic only",
        "counts": {
            "households": len(h),
            "persons": len(r),
            "poverty_reference_persons": len(distribution),
            "housing_quintile_reference_persons": len(housing_distribution),
            "newborn_reference_ages_mapped_to_zero": sum(int(p["RB081"]) == -1 for p in r.values()),
            "missing_cost_households": sum(hh["HH070_F"] == "-1" for hh in h.values()),
            "missing_cost_persons": missing,
            "missing_cost_person_weight": missing_weight,
            "known_cost_nonpositive_net_income_persons": nonpositive,
        },
        "classification_populations": {
            "poverty": "national income-valid persons, before housing-cost exclusions",
            "housing_quintiles": "housing-eligible persons, after housing-cost exclusions",
        },
        "income_flag_counts": dict(sorted(income_flags.items())),
        "conventions_pending_review": [
            "Current-release confirmation of historical algorithm and missing-value reweighting",
            "Official QPB ranking population unresolved: income-valid versus cost-eligible",
            "Current-release confirmation of historical quantile/tie conventions",
            "Public-file versus Eurostat release revisions; numeric agreement is rounded only",
        ],
        "cells": [
            {
                "breakdown": k[0],
                "group_code": k[1],
                "rate_pct": 100 * v[0] / v[1],
                "person_weight": v[1],
                "sample_persons": v[2],
            }
            for k, v in sorted(totals.items())
            if v[1] > 0
        ],
    }


def compare(report: dict, benchmarks: list[dict]) -> dict:
    computed = {(r["breakdown"], r["group_code"]): r for r in report["cells"]}
    comparisons = []
    for row in benchmarks:
        key = (row["breakdown"], row["group_code"])
        candidate = computed.get(key)
        observed = row["rate_pct"]
        match = (
            candidate is not None
            and observed is not None
            and abs(candidate["rate_pct"] - observed) <= 0.05 + 1e-9
        )
        comparisons.append(
            {
                "breakdown": key[0],
                "group_code": key[1],
                "published_rate_pct": observed,
                "published_status": row["status"],
                "candidate_rate_pct": candidate["rate_pct"] if candidate else None,
                "matches_rounding": match,
            }
        )
    report["comparisons"] = comparisons
    report["all_benchmarks_match_rounding"] = bool(comparisons) and all(
        r["matches_rounding"] for r in comparisons
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--benchmarks", required=True, type=Path)
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    import duckdb

    with duckdb.connect(str(args.benchmarks), read_only=True) as con:
        rows = con.execute(
            "SELECT breakdown, group_code, rate_pct, status FROM overburden "
            "WHERE survey_year = ? UNION ALL SELECT 'age_poverty', "
            "age_code || ':' || poverty_code, rate_pct, status "
            "FROM overburden_age_poverty WHERE survey_year = ?",
            [args.year, args.year],
        ).fetchall()
    expected = 16 + 2 * len(AGES)
    if len(rows) != expected or len({(r[0], r[1]) for r in rows}) != expected:
        raise ValueError("Incomplete or duplicate benchmark selection")
    benchmarks = [
        dict(zip(("breakdown", "group_code", "rate_pct", "status"), row, strict=True))
        for row in rows
    ]
    report = compare(calculate(load_archive(args.archive, args.year), args.year), benchmarks)
    report["input_sha256"] = {
        "archive": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        "benchmarks": hashlib.sha256(args.benchmarks.read_bytes()).hexdigest(),
    }
    report["prototype_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    # Emit diagnostics even on mismatch; never silently treat replication as passing.
    raise SystemExit(0 if report["all_benchmarks_match_rounding"] else 1)


if __name__ == "__main__":
    main()
