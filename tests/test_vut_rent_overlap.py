"""Matched-sample accounting in the tourist-stock/rent comparison."""

import math
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "explorations"))
import vut_rent_overlap as vr  # noqa: E402


def test_average_ranks_and_constant_series():
    assert vr.rank_stats.midranks([3, 1, 1, 2]) == [4, 1.5, 1.5, 3]
    assert vr.rank_stats.spearman([1, 1, 2], [3, 2, 1], digits=6) == pytest.approx(
        -math.sqrt(3) / 2, abs=1e-6
    )
    assert vr.rank_stats.spearman([1, 1, 1], [3, 2, 1], digits=6) is None


def test_index_preserves_zero_shares_and_rejects_duplicate_or_malformed_codes():
    assert vr.index([(2024, "01001", 0)]) == {(2024, "01001"): 0}
    with pytest.raises(ValueError, match="Duplicate municipality-year"):
        vr.index([(2024, "01001", 0), (2024, "01001", 1)])
    with pytest.raises(ValueError, match="Invalid municipality code"):
        vr.index([(2024, "1001", 1)])
    with pytest.raises(ValueError, match="Invalid observation"):
        vr.index([(2024, "01001", 0)], strictly_positive=True)


def test_missing_baseline_is_excluded_but_zero_baseline_is_a_real_observation():
    a, b, c = "01001", "01002", "01003"
    rents = {(2022, a): 10, (2024, a): 20, (2022, b): 10, (2024, b): 11, (2024, c): 5}
    shares = {(2022, a): 0, (2024, a): 2, (2022, b): 1, (2024, b): 0, (2024, c): 4}
    stock = {(2024, a): 50, (2024, b): 0, (2024, c): 30}
    levels = vr.compare(rents, shares, stock, 2024, 2024)
    changes = vr.compare(rents, shares, stock, 2022, 2024)
    assert levels["n"] == 3 and levels["end_matched_stock_pct"] == 100
    assert changes["n"] == 2 and changes["end_matched_stock_pct"] == 62.5
    assert changes["spearman"] == 1


def test_decimal_changes_that_are_equal_get_equal_ranks():
    a, b = "01001", "01002"
    shares = {(2022, a): 0.10, (2024, a): 0.15, (2022, b): 0.30, (2024, b): 0.35}
    rents = {(2022, a): 10, (2024, a): 20, (2022, b): 5, (2024, b): 8}
    result = vr.compare(rents, shares, {(2024, a): 10, (2024, b): 5}, 2022, 2024)
    assert result["spearman"] is None
    assert result["end_levels_spearman_on_same_sample"] == -1


def test_index_check_reranks_both_outcomes_on_complete_triples():
    # d/e have only one IPVA endpoint each; f lacks a baseline tourist share;
    # g lacks baseline SERPAVI rent. The later IPVA rows alone are insufficient.
    codes = tuple(f"0100{i}" for i in range(1, 8))

    def series(before, after):
        return {
            (year, code): value
            for year, vals in [(2020, before), (2024, after)]
            for code, value in zip(codes, vals, strict=True)
            if value is not None
        }

    # The excluded e falls between b and c in tourist-share growth only.
    # Keeping full-sample ranks for the triple would no longer yield +1.
    shares = series([0, 1, 2, 0, 1, None, 0], [1, 3, 5, 4, 3.5, 1, 1])
    rents = series([10, 10, 10, 10, 10, 10, None], [11, 12, 13, 1, 8, 6, 7])
    ipva = series([100, 100, 100, None, 100, 100, 100], [130, 120, 110, 160, None, 50, 90])
    stock = {(2024, code): i for i, code in enumerate(codes, 1)}
    out = vr.compare(rents, shares, stock, 2020, 2024, ipva=ipva)
    common = out["common_ipva_sample"]
    assert out["n"] == 5 and out["spearman"] < 0
    assert common["n"] == 3 and common["ipva_both_endpoints"] == 5
    assert common["end_matched_stock"] == 6
    assert common["end_matched_stock_pct"] == round(100 * 6 / 28, 4)
    assert common["tourism_serpavi_spearman"] == 1
    assert common["tourism_ipva_spearman"] == common["serpavi_ipva_spearman"] == -1


def test_index_check_uses_relative_growth_not_index_levels_or_point_differences():
    # Rebasing each town independently changes index levels and point changes,
    # but must leave both correlations involving IPVA (including ties) intact.
    codes = ["01001", "01002", "01003", "01004"]
    shares = {(y, c): (i if y == 2024 else 0) for y in (2020, 2024) for i, c in enumerate(codes)}
    rents = {
        (y, c): 10 + (i if y == 2024 else 0) for y in (2020, 2024) for i, c in enumerate(codes)
    }
    ipva = {
        (y, c): (v if y == 2024 else 100)
        for y in (2020, 2024)
        for c, v in zip(codes, [110, 110, 120, 130], strict=True)
    }
    stock = {(2024, c): 1 for c in codes}

    def result(values):
        return vr.compare(rents, shares, stock, 2020, 2024, ipva=values)["common_ipva_sample"]

    expected = result(ipva)
    assert expected["tourism_ipva_spearman"] == pytest.approx(math.sqrt(0.9), abs=1e-6)
    for factors in [(3, 2, 1, 1), (1, 1, 1, 7), (91, 32, 5, 1)]:
        scales = dict(zip(codes, factors, strict=True))
        assert result({(y, c): v * scales[c] for (y, c), v in reversed(ipva.items())}) == expected


def test_no_index_level_comparison_or_silent_empty_overlap():
    data = {(2020, "01001"): 1, (2024, "01001"): 2}
    with pytest.raises(ValueError, match="not rent levels"):
        vr.compare(data, data, data, 2024, 2024, ipva=data)
    with pytest.raises(ValueError, match="No common"):
        vr.compare(data, data, data, 2020, 2024, ipva={(2024, "01001"): 100})


def test_census_denominator_excludes_remainders_and_rejects_ambiguous_bases():
    rows = [("04001", "Abla", 1076, True), ("04999", "Resto de Almería", 21017, True)]
    assert vr.census_bases(rows) == {"04001": (1076, True)}
    with pytest.raises(ValueError, match="Unexpected census remainder"):
        vr.census_bases([("04001", "Resto de Almería", 21017, True)])
    for extra in [rows[0], ("04002", "Other", 0, True)]:
        with pytest.raises(ValueError, match="Duplicate or invalid"):
            vr.census_bases([rows[0], extra])


def test_fixed_base_holds_towns_fixed_and_reranks_after_regional_exclusion():
    a, b, c, d, e = codes = ["01001", "02001", "03001", "04001", "05001"]
    common = {k: (i, i, -i) for i, k in enumerate(codes, 1)}
    bases = {a: (20, False), b: (200, False), c: (200, False), d: (100, True)}
    stock = {(2020, k): old for k, old in zip(codes, [0, 1, 2, 3, 4], strict=True)}
    stock.update({(2024, k): new for k, new in zip(codes, [1, 3, 1, 10, 5], strict=True)})
    shares = {(2024, k): v for k, v in zip(codes, [5, 1.505, 0.51, 10, 0.25], strict=True)}

    def check():
        return vr.fixed_base_check(common, stock, shares, bases, 2020, 2024)

    out = check()
    assert out["missing_named_census_codes"] == [e]
    assert out["all"]["n"] == 4 and out["all"]["fixed_serpavi"] == 0.2
    outside = out["outside_andalucia"]
    assert outside["n"] == 3 and outside["end_shares_within_rounding"] == 2
    assert outside["reported_serpavi"] == 1 and outside["fixed_serpavi"] == -1
    assert outside["reported_ipva"] == -1 and outside["fixed_ipva"] == 1
    # Multiplying a town's counts AND housing base by the same positive
    # integer cannot change any fixed share (or the rounding diagnostic).
    for scale in (2, 3, 7):
        bases[a] = (bases[a][0] * scale, False)
        for y in (2020, 2024):
            stock[y, a] *= scale
        assert check() == out
    del stock[2020, b]
    with pytest.raises(ValueError, match="without an endpoint count"):
        check()
    stock[2020, b] = 1.5
    with pytest.raises(ValueError, match="Invalid tourist dwelling count"):
        check()


def test_later_rents_use_one_cohort_and_only_the_years_needed_by_each_measure():
    codes = tuple(f"0100{i}" for i in range(1, 7))

    def observations(years, columns):
        return {
            (yr, c): v
            for c, column in zip(codes, columns, strict=True)
            for yr, v in zip(years, column, strict=True)
            if v is not None
        }

    # D lacks a 2020 count, E a 2022 index, F a named census base. None
    # should enter even a row whose own endpoints could be computed for it.
    stock = observations(
        range(2020, 2023),
        [(0, 0, 20), (0, 10, 20), (0, 20, 20), (None, 8, 6), (9, 3, 1), (8, 50, 0)],
    )
    rents = observations(
        range(2022, 2025),
        [(10, 10, 30), (10, 11, 22), (10, 12, 12), (1, 99, 1), (5, 2, 13), (5, 2, 1)],
    )
    ipva = observations(
        range(2022, 2025),
        [(10, 12, 12), (10, 11, 22), (10, 10, 30), (5, 1, 222), (None, 2, 11), (5, 2, 1)],
    )
    bases = {c: (100, False) for c in codes[:-1]}
    result = vr.earlier_tourism_later_rents(rents, ipva, stock, bases, vr.YEARS)
    assert result["n"] == 3 and result["rent_complete"] == 5
    assert result["stock_years"] == [2020, 2021, 2022]
    assert result["rent_years"] == [2022, 2023, 2024]
    assert result["comparisons"] == {
        "2020_2021__2022_2023": {"serpavi": 1, "ipva": -1},
        "2020_2021__2023_2024": {"serpavi": -1, "ipva": 1},
        "2021_2022__2023_2024": {"serpavi": 1, "ipva": -1},
    }
    # A 2024 tourist-count revision or unrelated early rent cells must not
    # alter either cohort selection or the estimate in any row.
    for y in (2023, 2024):
        for c in codes:
            stock[y, c] = 999
    rents[2020, codes[0]] = ipva[2021, codes[1]] = 123
    assert result == vr.earlier_tourism_later_rents(rents, ipva, stock, bases, reversed(vr.YEARS))
    for middle_count in (10, 100, 1000):
        stock[2021, codes[0]] = middle_count
        revised = vr.earlier_tourism_later_rents(rents, ipva, stock, bases, vr.YEARS)
        assert revised["comparisons"] != result["comparisons"]
        assert revised["net_two_year"] == result["net_two_year"]


@pytest.mark.parametrize("years", [(2020, 2021, 2022), (2020, 2022, 2023)])
def test_timing_never_uses_a_shared_endpoint_or_bridges_a_missing_year(years):
    with pytest.raises(ValueError, match="No non-overlapping"):
        vr.earlier_tourism_later_rents({}, {}, {}, {}, years)


def test_pinned_timing_matches_independent_raw_source_query():
    import duckdb

    sources = [
        vr.RAW / rel
        for rel in (
            "censo2021_intensidad.csv",
            "vut_municipal_39363.csv",
            "ipva_municipal_59060.csv",
            "parquet/serpavi_municipal.parquet",
        )
    ]
    if not all(p.is_file() for p in [*sources, vr.VUT, vr.IPVA, vr.MARTS]):
        pytest.skip("requires pinned local source files and marts")
    query = (Path(__file__).parent / "sql/vut_rent_timing.sql").read_text()
    with duckdb.connect() as con:
        reference = con.execute(query, [str(p) for p in sources]).fetchall()
    actual = vr.build()["earlier_tourism_later_rents"]
    assert len(reference) == 4
    assert all(n == actual["n"] for *_, n, _, _ in reference)
    one = [row for row in reference if row[2] == 1]
    assert actual["comparisons"] == {
        f"{s}_{s + 1}__{r}_{r + 1}": {"serpavi": sr, "ipva": ir} for s, r, _, _, sr, ir in one
    }
    two = [row for row in reference if row[2] == 2]
    ((s, r, _, n, sr, ir),) = two
    net = actual["net_two_year"][f"{s}_{s + 2}__{r}_{r + 1}"]
    assert net["spearman"] == {"serpavi": sr, "ipva": ir}
    # Independent grouping: medians of town-level growth, not of endpoint levels.
    query = (Path(__file__).parent / "sql/vut_rent_timing.sql").read_text()
    grouped = (
        query.split("), ranks as (")[0]
        + """) select sign(dn), count(*), median(100.0*dn/dwellings),
        median(100*(s1/s0-1)), median(100*(i1/i0-1)) from endpoints
        where span=2 and s=? and r=? group by sign(dn) order by 1"""
    )
    with duckdb.connect() as con:
        groups = con.execute(grouped, [*map(str, sources), s, r]).fetchall()
    names = {-1: "decreased", 0: "unchanged", 1: "increased"}
    assert {
        names[sign]: {
            "n": count,
            "median_change_per_100": round(float(change), 6),
            "median_rent_growth_pct": {
                "serpavi": round(float(ser), 6),
                "ipva": round(float(ipv), 6),
            },
        }
        for sign, count, change, ser, ipv in groups
    } == net["by_direction"]


def test_net_change_reports_town_growth_medians_and_keeps_signs_distinct():
    net = [Fraction(-2), Fraction(0), Fraction(1), Fraction(4)]
    factors = {
        "a": [Fraction(11, 10), Fraction(10, 10), Fraction(21, 20), Fraction(12, 10)],
        "b": [Fraction(9, 10), Fraction(10, 10), Fraction(11, 10), Fraction(14, 10)],
    }
    out = vr.net_change_summary(net, factors)
    assert out["by_direction"]["decreased"] == {
        "n": 1,
        "median_change_per_100": -2.0,
        "median_rent_growth_pct": {"a": 10.0, "b": -10.0},
    }
    assert out["by_direction"]["unchanged"]["median_rent_growth_pct"] == {"a": 0.0, "b": 0.0}
    assert out["by_direction"]["increased"]["n"] == 2
    assert out["by_direction"]["increased"]["median_rent_growth_pct"] == {"a": 12.5, "b": 25.0}
    assert out["spearman"] == {"a": 0.4, "b": 1}
    assert (
        vr.net_change_summary([Fraction(-1), Fraction(-2)], {k: v[:2] for k, v in factors.items()})[
            "by_direction"
        ]["increased"]["n"]
        == 0
    )
