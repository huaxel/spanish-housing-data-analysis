"""ECP household composition and a separate aligned year-end stock comparison."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ecp, ols  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402
from spanish_housing.ine_api import split_nombre  # noqa: E402

SOURCE = RAW / "ecp_hog_ccaa.json"
PROVINCE_HOUSEHOLDS = RAW / "ecp_hog_prov.json"
FAMILY_POPULATION = RAW / ecp.FAMILY_FILE
STOCK = RAW / "parquet/parque_viviendas.parquet"
COMPLETIONS = RAW / "parquet/mivau_terminadas.parquet"
COMPLETION_YEARS = (2024, 2025)
STOCK_WINDOWS = {
    "2021-2024": (2021, 2024),
    "2021-2025": (2021, 2025),
    **{str(year): (year, year) for year in range(2021, 2026)},
}
STOCK_YEARS = frozenset(yr for start, end in STOCK_WINDOWS.values() for yr in (start - 1, end))
ARTIFACT = ROOT / "artifacts/ecp_households.json"
SIZES = ("1", "2", "3", "4 y más")
NATIONAL = "Total Nacional"
REGIONS = {
    "Andalucía",
    "Aragón",
    "Asturias, Principado de",
    "Balears, Illes",
    "Canarias",
    "Cantabria",
    "Castilla y León",
    "Castilla - La Mancha",
    "Cataluña",
    "Comunitat Valenciana",
    "Extremadura",
    "Galicia",
    "Madrid, Comunidad de",
    "Murcia, Región de",
    "Navarra, Comunidad Foral de",
    "País Vasco",
    "Rioja, La",
    "Ceuta",
    "Melilla",
}


def parse_territory(payload, territory):
    """Index one territory by Spanish civil reference date and published size."""
    by_date = {}
    seen = set()
    for series in payload:
        parts = split_nombre(series["Nombre"])
        if not parts or parts[0] != territory:
            continue
        if (
            len(parts) != 4
            or parts[2:] != ["Hogares en viviendas familiares", "Número"]
            or parts[1] not in ("Total", *SIZES)
        ):
            raise ValueError(f"Unexpected ECP series: {series['Nombre']}")
        size = parts[1]
        if size in seen:
            raise ValueError(f"Duplicate household series: {territory} {size}")
        seen.add(size)
        for item in series["Data"]:
            ref = ecp.reference_date(item)
            values = by_date.setdefault(ref, {})
            if size in values:
                raise ValueError(f"Duplicate household cell: {territory} {ref} {size}")
            n = item["Valor"]
            if (
                item["Secreto"]
                or type(n) not in (int, float)
                or not math.isfinite(n)
                or n < 0
                or int(n) != n
            ):
                raise ValueError(f"Invalid household count: {territory} {ref} {size} {n}")
            values[size] = int(n)
    if not by_date:
        raise ValueError(f"Missing household observations: {territory}")
    for ref, values in by_date.items():
        if values.keys() != {"Total", *SIZES}:
            raise ValueError(f"Incomplete household sizes: {territory} {ref}")
        if values["Total"] <= 0 or sum(values[s] for s in SIZES) != values["Total"]:
            raise ValueError(f"Household sizes do not sum to a positive total: {territory} {ref}")
    return by_date


def summarize(by_date):
    rows = []
    for ref, counts in sorted(by_date.items()):
        small = counts["1"] + counts["2"]
        previous = by_date.get(ref.replace(year=ref.year - 1))
        row = {
            "date": ref.isoformat(),
            "total": counts["Total"],
            "by_size": {s: counts[s] for s in SIZES},
            "small_households_pct": round(100 * small / counts["Total"], 6),
            "yoy": None,
        }
        if previous is not None:
            changes = {s: counts[s] - previous[s] for s in SIZES}
            total = counts["Total"] - previous["Total"]
            small_change = changes["1"] + changes["2"]
            row["yoy"] = {
                "total_change": total,
                "total_pct": round(100 * total / previous["Total"], 6),
                "change_by_size": changes,
                "small_change": small_change,
                "small_share_of_net_change_pct": round(100 * small_change / total, 6)
                if total > 0
                else None,
            }
        rows.append(row)
    return rows


def reconcile_regions(national, regions):
    for region, by_date in regions.items():
        if by_date.keys() != national.keys():
            raise ValueError(f"ECP region does not cover the national reference dates: {region}")
    for ref, national_counts in national.items():
        for size, count in national_counts.items():
            if sum(by_date[ref][size] for by_date in regions.values()) != count:
                raise ValueError(f"ECP regional sum does not match Spain: {ref}, size {size}")


def small_share_decomposition(national, regions, start, end):
    """Split the national share change with symmetric endpoint weights (not causal)."""

    def small_share(counts):
        return Fraction(counts["1"] + counts["2"], counts["Total"])

    within, reweighting, rising = 0, 0, 0
    for by_date in regions.values():
        s0, s1 = (small_share(by_date[d]) for d in (start, end))
        w0, w1 = (Fraction(by_date[d]["Total"], national[d]["Total"]) for d in (start, end))
        within += (w0 + w1) * (s1 - s0) / 2
        reweighting += (s0 + s1) * (w1 - w0) / 2
        rising += s1 > s0
    share0, share1 = (small_share(national[d]) for d in (start, end))
    if within + reweighting != share1 - share0:
        raise ValueError(f"ECP share decomposition does not reconcile: {start} to {end}")
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "start_share_pct": round(float(100 * share0), 6),
        "end_share_pct": round(float(100 * share1), 6),
        "total_shift_pp": round(float(100 * (share1 - share0)), 6),
        "within_territories_pp": round(float(100 * within), 6),
        "regional_reweighting_pp": round(float(100 * reweighting), 6),
        "territories_with_rising_share": rising,
    }


def regional_october(national, regions):
    """Compare fixed calendar months; rank by absolute net change, not growth rate."""
    reconcile_regions(national, regions)
    out = {}
    for end in sorted(ref for ref in national if ref.month == 10):
        start = end.replace(year=end.year - 1)
        if start not in national:
            continue
        rows = []
        for region, by_date in regions.items():
            before, after = by_date[start], by_date[end]
            total = after["Total"] - before["Total"]
            small = sum(after[s] - before[s] for s in ("1", "2"))
            rows.append(
                {
                    "territory": region,
                    "net_change": total,
                    "small_change": small,
                    "larger_change": total - small,
                }
            )
        rows.sort(key=lambda r: (-r["net_change"], r["territory"]))
        national_change = national[end]["Total"] - national[start]["Total"]
        top4 = sum(r["net_change"] for r in rows[:4])
        remaining = national_change - top4
        remaining_small = sum(r["small_change"] for r in rows[4:])
        out[end.isoformat()] = {
            "territories": len(rows),
            "positive_net_growth": sum(r["net_change"] > 0 for r in rows),
            "small_majority": sum(2 * r["small_change"] > r["net_change"] > 0 for r in rows),
            "top4_change": top4,
            "top4_share_pct": round(100 * top4 / national_change, 6)
            if national_change > 0
            else None,
            "rest_change": remaining,
            "rest_small_change": remaining_small,
            "rest_small_share_pct": round(100 * remaining_small / remaining, 6)
            if remaining > 0
            else None,
            "by_territory": rows,
            "small_share_decomposition": small_share_decomposition(national, regions, start, end),
        }
    return out


def household_growth_components(p0, p1, h0, h1):
    """Apply the midpoint product rule to H = P × (households per resident)."""
    r0, r1 = Fraction(h0, p0), Fraction(h1, p1)
    population = (p1 - p0) * (r0 + r1) / 2
    smaller_size = (r1 - r0) * (p0 + p1) / 2
    change = h1 - h0
    return {
        "net_household_change": change,
        "population_component_households": round(float(population), 6),
        "household_size_component_households": round(float(smaller_size), 6),
        "household_size_component_pct": round(float(100 * smaller_size / change), 6)
        if change > 0
        else None,
    }


def validate_family_coverage(households, people):
    if households.keys() != people.keys():
        raise ValueError("ECP household/family-population reference dates do not match")
    for ref, counts in households.items():
        minimum_residents = sum(i * counts[size] for i, size in enumerate(SIZES, start=1))
        if people[ref] < minimum_residents:
            raise ValueError(
                f"ECP family population falls below minimum household membership: {ref}"
            )


def population_accounting(national, people):
    validate_family_coverage(national, people)
    quarters = []
    for ref, n in sorted(people.items()):
        counts = national[ref]
        quarters.append(
            {
                "date": ref.isoformat(),
                "family_population": n,
                "households": counts["Total"],
                "people_per_household": round(n / counts["Total"], 6),
            }
        )

    def compare(start, end):
        p0, p1 = people[start], people[end]
        h0, h1 = national[start]["Total"], national[end]["Total"]
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "start_people_per_household": round(p0 / h0, 6),
            "end_people_per_household": round(p1 / h1, 6),
            **household_growth_components(p0, p1, h0, h1),
        }

    october_dates = sorted(ref for ref in people if ref.month == 10)
    return {
        "source_url": ecp.FAMILY_TABLE,
        "quarters": quarters,
        "october_yoy": {
            end.isoformat(): compare(start, end)
            for end in october_dates
            if (start := end.replace(year=end.year - 1)) in people
        },
        "first_to_last_october": compare(october_dates[0], october_dates[-1])
        if len(october_dates) >= 2
        else None,
    }


def validated_local_households(national, province_payload, people):
    """Use identical publisher territories; reconcile both endpoints to Spain."""
    places = sorted(people.keys() - {NATIONAL})
    if {split_nombre(s["Nombre"])[0] for s in province_payload} != people.keys():
        raise ValueError("ECP provincial household and family-population territories do not match")
    if parse_territory(province_payload, NATIONAL) != national:
        raise ValueError("ECP national households disagree between tables 60131 and 60133")
    households = {place: parse_territory(province_payload, place) for place in places}
    reconcile_regions(national, households)
    for place in places:
        validate_family_coverage(households[place], people[place])
    for ref, count in people[NATIONAL].items():
        if sum(people[place][ref] for place in places) != count:
            raise ValueError(f"ECP provincial family population does not sum to Spain: {ref}")
    return households


def local_family_accounting(households, people):
    places = sorted(households)

    def compare(start, end):
        rows = {}
        for place in places:
            p0, p1 = people[place][start], people[place][end]
            h0, h1 = households[place][start]["Total"], households[place][end]["Total"]
            rows[place] = {
                "family_population_change": p1 - p0,
                "people_per_household_fell": p1 * h0 < p0 * h1,
                **household_growth_components(p0, p1, h0, h1),
            }
        diverging = [
            place
            for place, row in rows.items()
            if row["net_household_change"] > 0 > row["family_population_change"]
        ]
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "territories": len(rows),
            "territories_with_smaller_households": sum(
                r["people_per_household_fell"] for r in rows.values()
            ),
            "households_rose_population_fell": diverging,
            "households_rose_population_fell_count": len(diverging),
            "by_territory": rows,
        }

    dates = sorted(ref for ref in people[NATIONAL] if ref.month == 10)
    return {
        "household_source_url": "https://www.ine.es/jaxiT3/Tabla.htm?t=60133",
        "october_yoy": {
            end.isoformat(): compare(start, end)
            for end in dates
            if (start := end.replace(year=end.year - 1)) in people[NATIONAL]
        },
        "first_to_last_october": compare(dates[0], dates[-1]) if len(dates) >= 2 else None,
    }


def positive_gap_concentration(observed, fixed):
    """Hold the observed top-four group fixed; denominator is positive gaps only."""

    def top_four(gaps):
        return sorted((n for n in gaps if gaps[n] > 0), key=lambda n: (-gaps[n], n))[:4]

    top = top_four(observed)

    def measure(gaps):
        positive_total = sum(v for v in gaps.values() if v > 0)
        group_total = sum(max(gaps[n], 0) for n in top)
        return {
            "positive_gap_total": round(float(positive_total), 6),
            "group_positive_gap": round(float(group_total), 6),
            "share_pct": round(float(100 * Fraction(group_total, positive_total)), 6)
            if positive_total
            else None,
        }

    return {
        "observed_top_four": top,
        "same_provinces_at_fixed_size": set(top) == set(top_four(fixed)),
        "observed": measure(observed),
        "fixed_local_size": measure(fixed),
    }


def align_stock_windows(households, people, stock_rows):
    """Keep the start-year households-per-resident rate fixed in the benchmark."""
    # The published stock series only provides a joint total for the two cities.
    groups = {name: (name,) for name in households if name not in ("Ceuta", "Melilla")}
    groups["Ceuta y Melilla"] = ("Ceuta", "Melilla")
    stock = {}
    codes = {}
    for raw_code, raw_name, yr, count in stock_rows:
        code, name = (raw_code.zfill(2), raw_name) if raw_code else ("51+52", "Ceuta y Melilla")
        key = (name, yr)
        if key in stock or (name in codes and codes[name] != code) or count is None or count <= 0:
            raise ValueError(f"Invalid or duplicate MIVAU stock endpoint: {key}")
        stock[key] = count
        codes[name] = code
    if (
        set(codes) != groups.keys()
        or set(codes.values()) != {*(f"{n:02d}" for n in range(1, 51)), "51+52"}
        or len(codes) != 51
    ):
        raise ValueError("ECP and MIVAU province coverage differs")
    expected = {(name, yr) for name in groups for yr in STOCK_YEARS}
    if stock.keys() != expected:
        raise ValueError("Missing or extra MIVAU year-end stock endpoints")
    out = {}
    for key, (start_year, end_year) in STOCK_WINDOWS.items():
        start, end = date(start_year, 1, 1), date(end_year + 1, 1, 1)
        rows = {}
        fixed_gaps = {}
        initial_households = initial_residents = 0
        for name, members in sorted(groups.items()):
            h0, h1 = (sum(households[p][d]["Total"] for p in members) for d in (start, end))
            p0, p1 = (sum(people[p][d] for p in members) for d in (start, end))
            net_stock = stock[name, end_year] - stock[name, start_year - 1]
            observed_gap = h1 - h0 - net_stock
            fixed_gap = Fraction((p1 - p0) * h0, p0) - net_stock
            fixed_gaps[name] = fixed_gap
            initial_households += h0
            initial_residents += p0
            rows[name] = {
                "cpro": codes[name],
                "resident_change": p1 - p0,
                "household_change": h1 - h0,
                "stock_change": net_stock,
                "observed_gap": observed_gap,
                "fixed_size_gap": round(float(fixed_gap), 6),
                "fixed_size_gap_positive": fixed_gap > 0,
            }
        fewer_residents = [name for name, row in rows.items() if row["resident_change"] < 0]
        total_stock_change = sum(row["stock_change"] for row in rows.values())
        total_household_change = sum(row["household_change"] for row in rows.values())
        resident_change = sum(row["resident_change"] for row in rows.values())
        observed_total = total_household_change - total_stock_change
        fixed_local_total = sum(fixed_gaps.values())
        fixed_national = (
            Fraction(resident_change * initial_households, initial_residents) - total_stock_change
        )
        out[key] = {
            "household_start": start.isoformat(),
            "household_end": end.isoformat(),
            "stock_start_year": start_year - 1,
            "stock_end_year": end_year,
            "territories": len(rows),
            "observed_gap_positive": sum(row["observed_gap"] > 0 for row in rows.values()),
            "fixed_size_gap_positive": sum(row["fixed_size_gap_positive"] for row in rows.values()),
            "fewer_residents": len(fewer_residents),
            "fewer_residents_but_household_growth_exceeds_stock": sum(
                rows[n]["household_change"] > 0 and rows[n]["observed_gap"] > 0
                for n in fewer_residents
            ),
            "by_territory": rows,
            "positive_gap_concentration": positive_gap_concentration(
                {name: row["observed_gap"] for name, row in rows.items()}, fixed_gaps
            ),
            "spain": {
                "household_change": total_household_change,
                "stock_change": total_stock_change,
                "observed_gap": observed_total,
                "fixed_local_size_gap": round(float(fixed_local_total), 6),
                "fixed_national_size_gap": round(float(fixed_national), 6),
                "observed_minus_fixed_local": round(float(observed_total - fixed_local_total), 6),
            },
        }
    return out


def annual_gap_change(before, after):
    """Compare annual gaps using each year's own starting-size benchmark."""
    a, b = before["spain"], after["spain"]
    stock = a["stock_change"] - b["stock_change"]
    gap = b["observed_gap"] - a["observed_gap"]
    # The input artifact stores counterfactual gaps to six decimals. Report
    # differences to the nearest whole unit, without intermediate float subtraction.
    fixed_change = Decimal(str(b["fixed_local_size_gap"])) - Decimal(str(a["fixed_local_size_gap"]))
    by_territory = {
        name: row["observed_gap"] - before["by_territory"][name]["observed_gap"]
        for name, row in after["by_territory"].items()
    }
    return {
        "observed_gap_change": gap,
        "stock_contribution": stock,
        "population_at_starting_size_contribution": round(fixed_change - stock),
        "household_size_residual_contribution": round(gap - fixed_change),
        "territories_with_wider_gap": sum(v > 0 for v in by_territory.values()),
        "by_territory": by_territory,
    }


def local_completion_crosscheck(aligned, by_year, expected, years):
    start, end = years
    before, after = (aligned[str(y)]["by_territory"] for y in years)
    if before.keys() != after.keys():
        raise ValueError("Territory coverage changed between annual stock windows")

    def sign(value):
        return (value > 0) - (value < 0)

    local = {}
    for name, row in after.items():
        code = row["cpro"]
        if before[name]["cpro"] != code:
            raise ValueError(f"Stock territory code changed for {name}")
        provinces = code.split("+")
        keys = [key for key in expected if key[0] in provinces]
        if not keys:
            raise ValueError(f"Unknown completion territory {code}")
        values = {y: [by_year[y].get(key) for key in keys] for y in years}
        finished = {y: None if None in cells else sum(cells) for y, cells in values.items()}
        completion_end = finished[end]
        completion_start = finished[start]
        end_gap = row["household_change"] - completion_end if completion_end is not None else None
        change = (
            end_gap - (before[name]["household_change"] - completion_start)
            if end_gap is not None and completion_start is not None
            else None
        )
        stock_change = row["observed_gap"] - before[name]["observed_gap"]
        local[name] = {
            "completion_gap_end": end_gap,
            "stock_gap_end": row["observed_gap"],
            "completion_gap_change": change,
            "stock_gap_change": stock_change,
            "completion_flow_change": completion_end - completion_start
            if completion_end is not None and completion_start is not None
            else None,
            "net_stock_growth_change": row["stock_change"] - before[name]["stock_change"],
        }
    paired = {name: r for name, r in local.items() if r["completion_gap_change"] is not None}
    end_complete = {name: r for name, r in local.items() if r["completion_gap_end"] is not None}
    return {
        "areas_with_paired_completion_gaps": len(paired),
        "areas_with_both_gaps_widening": sum(
            r["completion_gap_change"] > 0 and r["stock_gap_change"] > 0 for r in paired.values()
        ),
        "areas_with_matching_direction": sum(
            sign(r["completion_gap_change"]) == sign(r["stock_gap_change"]) for r in paired.values()
        ),
        "areas_with_matching_supply_direction": sum(
            sign(r["completion_flow_change"]) == sign(r["net_stock_growth_change"])
            for r in paired.values()
        ),
        "areas_with_end_completion_gap": len(end_complete),
        "areas_with_different_end_signs": sum(
            sign(r["completion_gap_end"]) != sign(r["stock_gap_end"]) for r in end_complete.values()
        ),
        "by_territory": local,
    }


def completion_crosscheck(aligned, rows, years):
    """Compare flows without treating a missing completion cell as zero."""
    expected = {
        (f"{p:02d}", m, regime)
        for p in range(1, 53)
        for m in range(1, 13)
        for regime in ("Libre", "Protegida")
    }
    by_year = {year: {} for year in years}
    for year, province, month, regime, value in rows:
        cells = by_year[year]
        key = (province, month, regime)
        if key not in expected or key in cells or (value is not None and value < 0):
            raise ValueError(f"Invalid or duplicate MIVAU completion cell: {year} {key}")
        cells[key] = value
    levels = {}
    for year, cells in by_year.items():
        observed = [value for value in cells.values() if value is not None]
        missing = len(expected) - len(observed)
        completions = sum(observed) if not missing else None
        stock = aligned[str(year)]["spain"]
        levels[str(year)] = {
            "completion_cells_missing": missing,
            "completions": completions,
            "households_minus_completions": stock["household_change"] - completions
            if completions is not None
            else None,
            "households_minus_net_stock_growth": stock["observed_gap"],
        }
    a, b = (levels[str(year)] for year in years)
    return {
        "by_year": levels,
        "local": local_completion_crosscheck(aligned, by_year, expected, years),
        "completion_gap_change": b["households_minus_completions"]
        - a["households_minus_completions"]
        if not (a["completion_cells_missing"] or b["completion_cells_missing"])
        else None,
        "net_stock_gap_change": b["households_minus_net_stock_growth"]
        - a["households_minus_net_stock_growth"],
    }


def build():
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    national = parse_territory(payload, NATIONAL)
    observed = {split_nombre(s["Nombre"])[0] for s in payload} - {NATIONAL}
    if observed != REGIONS:
        raise ValueError(f"ECP regional coverage changed: {sorted(observed ^ REGIONS)}")
    regions = {region: parse_territory(payload, region) for region in sorted(REGIONS)}
    people = ecp.parse_family_population(json.loads(FAMILY_POPULATION.read_bytes()))
    local_households = validated_local_households(
        national, json.loads(PROVINCE_HOUSEHOLDS.read_bytes()), people
    )
    with duckdb.connect() as con:
        stock = con.execute(
            """
            select CPRO, Provincia, "Año"::int, Valor::bigint
            from read_parquet(?) where Tipo_Vivienda='Viviendas_Totales'
              and "Año" in (select unnest(?))
        """,
            [str(STOCK), [str(yr) for yr in sorted(STOCK_YEARS)]],
        ).fetchall()
        completions = con.execute(
            """
            select anyo, cpro, mes, tipo, viviendas from read_parquet(?)
            where estado='Terminadas' and anyo in (select unnest(?))
        """,
            [str(COMPLETIONS), list(COMPLETION_YEARS)],
        ).fetchall()
    rows = summarize(national)
    octobers = regional_october(national, regions)
    october_dates = sorted(d for d in national if d.month == 10)
    span = (
        small_share_decomposition(national, regions, october_dates[0], october_dates[-1])
        if len(october_dates) >= 2
        else None
    )
    aligned = align_stock_windows(local_households, people, stock)
    annual_years = sorted(start for start, end in STOCK_WINDOWS.values() if start == end)
    return {
        "source_url": "https://www.ine.es/jaxiT3/Tabla.htm?t=60131",
        "quarters": rows,
        "latest": rows[-1],
        "regional_october": octobers,
        "small_share_first_to_last_october": span,
        "regional_october_min_majority": min(
            (v["small_majority"] for v in octobers.values()), default=None
        ),
        "population_accounting": population_accounting(national, people[NATIONAL]),
        "local_family_accounting": local_family_accounting(local_households, people),
        "aligned_stock_comparison": aligned,
        "completion_crosscheck_2024_2025": completion_crosscheck(
            aligned, completions, COMPLETION_YEARS
        ),
        "annual_gap_change": {
            f"{start}-{end}": annual_gap_change(aligned[str(start)], aligned[str(end)])
            for start, end in zip(annual_years[:-1], annual_years[1:], strict=True)
            if end == start + 1
        },
        "_meta": ols.model_meta(
            __file__,
            [
                str(SOURCE.relative_to(ROOT)),
                str(PROVINCE_HOUSEHOLDS.relative_to(ROOT)),
                str(FAMILY_POPULATION.relative_to(ROOT)),
                str(STOCK.relative_to(ROOT)),
                str(COMPLETIONS.relative_to(ROOT)),
                str(Path(ecp.__file__).relative_to(ROOT)),
            ],
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    if args.check:
        if not ARTIFACT.is_file() or json.loads(ARTIFACT.read_text(encoding="utf-8")) != result:
            raise SystemExit(
                "ECP households: missing or stale artifact; rerun explorations/ecp_households.py"
            )
    else:
        ARTIFACT.parent.mkdir(exist_ok=True)
        ARTIFACT.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"ECP households: {len(result['quarters'])} quarters through {result['latest']['date']}")


if __name__ == "__main__":
    main()
