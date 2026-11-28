"""Quarter-date and stock-independent accounting contracts for ECP households."""

import sys
from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "explorations"))
import ecp_households as ecp  # noqa: E402

from spanish_housing.ecp import MADRID  # noqa: E402


def ecp_inputs_present():
    return all(
        p.is_file()
        for p in (
            ecp.SOURCE,
            ecp.PROVINCE_HOUSEHOLDS,
            ecp.FAMILY_POPULATION,
            ecp.STOCK,
            ecp.COMPLETIONS,
        )
    )


def series(*observations):
    return [
        {
            "Nombre": f"Total Nacional. {size}. Hogares en viviendas familiares. Número.",
            "Data": [
                {
                    "Fecha": int(datetime(year, month, 1, tzinfo=MADRID).timestamp() * 1000),
                    "Anyo": year,
                    "FK_Periodo": (month - 1) // 3 + 19,
                    "Valor": counts[i],
                    "Secreto": False,
                }
                for year, month, counts in observations
            ],
        }
        for i, size in enumerate(("Total", *ecp.SIZES))
    ]


def test_yoy_compares_same_reference_month_without_adding_missing_quarters():
    payload = series(
        (2026, 10, (145, 70, 45, 20, 10)),
        (2026, 7, (140, 67, 43, 19, 11)),
        (2025, 10, (100, 30, 40, 20, 10)),
        (2026, 1, (120, 55, 38, 17, 10)),
    )
    values = ecp.parse_territory(payload, ecp.NATIONAL)
    assert values[date(2026, 1, 1)]["Total"] == 120  # UTC timestamp lands on 31 Dec
    rows = ecp.summarize(values)
    assert [row["date"] for row in rows] == ["2025-10-01", "2026-01-01", "2026-07-01", "2026-10-01"]
    assert [row["yoy"] for row in rows[:-1]] == [None, None, None]
    yoy = rows[-1]["yoy"]
    assert yoy["small_change"] == yoy["total_change"] == 45
    assert yoy["small_share_of_net_change_pct"] == 100
    assert yoy["change_by_size"] == {"1": 40, "2": 5, "3": 0, "4 y más": 0}


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda p: p[0]["Data"][0].update(FK_Periodo=19), "Inconsistent ECP quarter"),
        (lambda p: p.append(p[0]), "Duplicate household series"),
        (lambda p: p.pop(), "Incomplete household sizes"),
        (lambda p: p[1]["Data"][0].update(Valor=2.3), "Invalid household count"),
        (lambda p: p[1]["Data"][0].update(Valor=3), "do not sum"),
    ],
)
def test_rejects_broken_date_and_accounting(mutate, error):
    payload = series((2026, 10, (9, 2, 3, 2, 2)))
    mutate(payload)
    with pytest.raises(ValueError, match=error):
        ecp.parse_territory(payload, ecp.NATIONAL)


def test_pinned_annual_quarters_match_existing_january_extraction():
    annual = ecp.RAW / "parquet/ecp_hog_ccaa.parquet"
    if not annual.is_file() or not (ecp_inputs_present()):
        pytest.skip("requires pinned local ECP inputs")
    with duckdb.connect() as con:
        independent = dict(
            con.execute(
                """
            select anyo, hogares from read_parquet(?)
            where territorio='Total Nacional' and tamano='Total'
        """,
                [str(annual)],
            ).fetchall()
        )
    rows = ecp.build()["quarters"]
    assert {
        int(r["date"][:4]): r["total"] for r in rows if r["date"].endswith("-01-01")
    } == independent


def test_october_aggregation_excludes_ties_and_allows_offsetting_size_changes():
    prior, latest = date(2025, 10, 1), date(2026, 10, 1)

    def dates(old, new):
        return {
            prior: dict(zip(("Total", *ecp.SIZES), old, strict=True)),
            latest: dict(zip(("Total", *ecp.SIZES), new, strict=True)),
        }

    territories = {str(i): dates((50, 10, 10, 20, 10), (60, 15, 10, 25, 10)) for i in range(4)}
    territories["other"] = dates((50, 10, 10, 20, 10), (52, 14, 10, 18, 10))
    national = dates((250, 50, 50, 100, 50), (292, 74, 50, 118, 50))
    result = ecp.regional_october(national, territories)["2026-10-01"]
    assert result["positive_net_growth"] == 5
    assert result["small_majority"] == 1  # one half is not a strict majority
    assert result["top4_change"] == 40 and result["rest_change"] == 2
    assert result["rest_small_share_pct"] == 200  # larger households fell
    with pytest.raises(ValueError, match="does not match Spain"):
        ecp.regional_october(national, {k: v for k, v in territories.items() if k != "other"})
    territories["other"].pop(prior)
    with pytest.raises(ValueError, match="does not cover the national reference dates"):
        ecp.regional_october(national, territories)


def test_pinned_regional_octobers_match_independent_source_pivot():
    from collections import defaultdict

    if not (ecp_inputs_present()):
        pytest.skip("requires pinned local ECP inputs")
    query = (Path(__file__).parent / "sql/ecp_regional_october.sql").read_text()
    with duckdb.connect() as con:
        observations = con.execute(query, [str(ecp.SOURCE)]).fetchall()
    groups = defaultdict(list)
    for year, name, total, small in observations:
        groups[f"{year}-10-01"].append((name, total, small))
    book = ecp.build()
    actual = book["regional_october"]
    assert actual.keys() == groups.keys()
    for key, ref in groups.items():
        out = actual[key]
        assert [
            (r["territory"], r["net_change"], r["small_change"]) for r in out["by_territory"]
        ] == ref
        assert out["small_majority"] == sum(
            total > 0 and small / total > 0.5 for _, total, small in ref
        )
        assert out["positive_net_growth"] == sum(total > 0 for _, total, _ in ref)
        assert out["top4_change"] == sum(t for _, t, _ in ref[:4])
        assert out["rest_change"] == sum(t for _, t, _ in ref[4:])
        assert out["rest_small_change"] == sum(s for _, _, s in ref[4:])
    assert book["regional_october_min_majority"] == min(
        v["small_majority"] for v in actual.values()
    )


@pytest.mark.parametrize(
    ("a_end", "b_end", "expected"),
    [
        ((30, 100), (80, 100), (5, 0, 1)),  # fixed geographic weights
        ((10, 50), (120, 150), (0, 15, 0)),  # fixed local small-household shares
    ],
)
def test_decomposition_separates_pure_changes_and_reverses_symmetrically(a_end, b_end, expected):
    start, end = date(2025, 10, 1), date(2026, 10, 1)

    def counts(small, total):
        return {"1": small, "2": 0, "Total": total}

    regions = {
        "a": {start: counts(20, 100), end: counts(*a_end)},
        "b": {start: counts(80, 100), end: counts(*b_end)},
    }
    national = {start: counts(100, 200), end: counts(a_end[0] + b_end[0], a_end[1] + b_end[1])}
    forward = ecp.small_share_decomposition(national, regions, start, end)
    backward = ecp.small_share_decomposition(national, regions, end, start)
    within, reweighting, rising = expected
    assert forward["total_shift_pp"] == within + reweighting
    assert forward["within_territories_pp"] == within
    assert forward["regional_reweighting_pp"] == reweighting
    assert forward["territories_with_rising_share"] == rising
    for k in ("total_shift_pp", "within_territories_pp", "regional_reweighting_pp"):
        assert backward[k] == -forward[k]


def test_pinned_small_share_decomposition_matches_crossed_weight_oracle():
    if not (ecp_inputs_present()):
        pytest.skip("requires pinned local ECP inputs")
    query = (Path(__file__).parent / "sql/ecp_small_share_shift.sql").read_text()
    with duckdb.connect() as con:
        source = {
            (a, b): values for a, b, *values in con.execute(query, [str(ecp.SOURCE)]).fetchall()
        }
    result = ecp.build()
    annual = [v["small_share_decomposition"] for v in result["regional_october"].values()]
    span = result["small_share_first_to_last_october"]
    assert len(annual) >= 1 and span is not None
    for r in [*annual, span]:
        key = (int(r["start"][:4]), int(r["end"][:4]))
        for field, value in zip(
            (
                "start_share_pct",
                "end_share_pct",
                "total_shift_pp",
                "within_territories_pp",
                "regional_reweighting_pp",
                "territories_with_rising_share",
            ),
            source[key],
            strict=True,
        ):
            assert r[field] == round(value, 6)


@pytest.mark.parametrize(
    ("p0", "p1", "h0", "h1", "population", "size"),
    [(100, 120, 50, 60, 10, 0), (100, 100, 40, 60, 0, 20), (100, 200, 50, 50, 37.5, -37.5)],
)
def test_accounting_changes_one_factor_at_a_time_or_offsets_both(p0, p1, h0, h1, population, size):
    outcome = ecp.household_growth_components(p0, p1, h0, h1)
    assert outcome["population_component_households"] == population
    assert outcome["household_size_component_households"] == size
    assert outcome["net_household_change"] == population + size
    if h1 == h0:
        assert outcome["household_size_component_pct"] is None


def test_family_population_requires_matching_dates_and_feasible_membership():
    ref = date(2026, 10, 1)
    sample = {ref: {"Total": 4, "1": 1, "2": 1, "3": 1, "4 y más": 1}}
    with pytest.raises(ValueError, match="reference dates do not match"):
        ecp.population_accounting(sample, {date(2026, 7, 1): 10})
    with pytest.raises(ValueError, match="below minimum household membership"):
        ecp.population_accounting(sample, {ref: 9})
    assert (
        ecp.population_accounting(sample, {ref: 10})["quarters"][0]["people_per_household"] == 2.5
    )


def test_pinned_family_growth_components_match_crossed_endpoint_oracle():
    if not (ecp_inputs_present()):
        pytest.skip("requires pinned local ECP inputs")
    query = (Path(__file__).parent / "sql/ecp_family_growth.sql").read_text()
    with duckdb.connect() as con:
        rows = con.execute(query, [str(ecp.FAMILY_POPULATION), str(ecp.SOURCE)]).fetchall()
    ref = {(a, b): (diff, pop, size) for a, b, diff, pop, size in rows}
    accounting = ecp.build()["population_accounting"]
    for r in [*accounting["october_yoy"].values(), accounting["first_to_last_october"]]:
        dif, pop, size = ref[int(r["start"][:4]), int(r["end"][:4])]
        assert r["net_household_change"] == dif
        assert r["population_component_households"] == round(pop, 6)
        assert r["household_size_component_households"] == round(size, 6)
        if dif > 0:
            assert r["household_size_component_pct"] == round(100 * size / dif, 6)


def test_pinned_local_family_growth_agrees_for_every_october_pair():
    if not ecp_inputs_present():
        pytest.skip("requires pinned local ECP inputs")
    query = (Path(__file__).parent / "sql/ecp_local_family_growth.sql").read_text()
    with duckdb.connect() as con:
        reference = con.execute(
            query, [str(ecp.PROVINCE_HOUSEHOLDS), str(ecp.FAMILY_POPULATION)]
        ).fetchall()
    results = ecp.build()["local_family_accounting"]
    for period in [*results["october_yoy"].values(), results["first_to_last_october"]]:
        start, end = int(period["start"][:4]), int(period["end"][:4])
        expect = {
            place: (hh, people, smaller)
            for a, b, place, hh, people, smaller in reference
            if (a, b) == (start, end)
        }
        assert period["territories"] == len(expect) == 52
        assert period["territories_with_smaller_households"] == sum(r[2] for r in expect.values())
        assert period["households_rose_population_fell"] == sorted(
            p for p, (hh, n, _) in expect.items() if hh > 0 > n
        )
        assert {
            p: (
                r["net_household_change"],
                r["family_population_change"],
                r["people_per_household_fell"],
            )
            for p, r in period["by_territory"].items()
        } == expect


def test_pinned_stock_comparison_matches_existing_deficit_windows_and_sql_benchmark():
    sidecar = ecp.ROOT / "data/processed/deficit.duckdb"
    stock_csv = ecp.RAW / "parque_viviendas.csv"
    if not ecp_inputs_present() or not sidecar.is_file() or not stock_csv.is_file():
        pytest.skip("requires pinned local ECP, MIVAU and deficit comparison inputs")
    query = (Path(__file__).parent / "sql/ecp_aligned_stock.sql").read_text()
    with duckdb.connect(str(sidecar), read_only=True) as con:
        ref = con.execute(
            query,
            {
                "people": str(ecp.FAMILY_POPULATION),
                "households": str(ecp.PROVINCE_HOUSEHOLDS),
                "stock_csv": str(stock_csv),
            },
        ).fetchall()
    data = ecp.build()
    out = data["aligned_stock_comparison"]
    for years, bridge in data["annual_gap_change"].items():
        start, end = years.split("-")
        a, b = [{r[1]: r for r in ref if r[0] == year} for year in (start, end)]
        assert a.keys() == b.keys()
        local = {name: b[name][6] - a[name][6] for name in a}
        if years == "2024-2025":
            assert [n for n, v in local.items() if v == max(local.values())] == ["Madrid"]
        # SQL supplies each area's stock change and fixed-size gap; adding
        # those reconstructs household growth at fixed size before differencing.
        pop = sum((b[n][7] + b[n][5]) - (a[n][7] + a[n][5]) for n in a)
        assert bridge == {
            "observed_gap_change": sum(local.values()),
            "stock_contribution": sum(a[n][5] - b[n][5] for n in a),
            "population_at_starting_size_contribution": round(pop),
            "household_size_residual_contribution": round(sum(b[n][4] - a[n][4] for n in a) - pop),
            "territories_with_wider_gap": sum(v > 0 for v in local.values()),
            "by_territory": local,
        }
    assert len(ref) == sum(w["territories"] for w in out.values()) == 357
    for end_year in (2024, 2025):
        cumulative = out[f"2021-{end_year}"]["spain"]
        for field in ("household_change", "stock_change", "observed_gap"):
            assert cumulative[field] == sum(
                out[str(year)]["spain"][field] for year in range(2021, end_year + 1)
            )
    for window, name, code, people, hh, stock, gap, fixed, *_ in ref:
        row = out[window]["by_territory"][name]
        assert row == {
            "cpro": code,
            "resident_change": people,
            "household_change": hh,
            "stock_change": stock,
            "observed_gap": gap,
            "fixed_size_gap": round(fixed, 6),
            "fixed_size_gap_positive": fixed > 0,
        }
    for window, values in out.items():
        rows = [r for r in ref if r[0] == window]
        assert values["observed_gap_positive"] == sum(r[6] > 0 for r in rows)
        assert values["fixed_size_gap_positive"] == sum(r[7] > 0 for r in rows)
        assert values["fewer_residents"] == sum(r[3] < 0 for r in rows)
        assert values["fewer_residents_but_household_growth_exceeds_stock"] == sum(
            people < 0 and hh > 0 and gap > 0 for _, _, _, people, hh, _, gap, *_ in rows
        )
        observed, local, national = rows[0][-3:]
        assert values["spain"] == {
            "household_change": sum(r[4] for r in rows),
            "stock_change": sum(r[5] for r in rows),
            "observed_gap": observed,
            "fixed_local_size_gap": round(local, 6),
            "fixed_national_size_gap": round(national, 6),
            "observed_minus_fixed_local": round(observed - local, 6),
        }
        # Calculate concentration on the observed cohort, with negative gaps excluded.
        top = sorted(rows, key=lambda r: (-r[6], r[1]))[:4]
        names = [r[1] for r in top]
        if "-" in window:
            assert set(names) == {"Madrid", "Barcelona", "Valencia/València", "Alicante/Alacant"}
        concentration = values["positive_gap_concentration"]
        assert concentration["observed_top_four"] == names
        assert concentration["same_provinces_at_fixed_size"] == (
            set(names) == {r[1] for r in sorted(rows, key=lambda r: (-r[7], r[1]))[:4]}
        )
        for label, column in [("observed", 6), ("fixed_local_size", 7)]:
            total = sum(r[column] for r in rows if r[column] > 0)
            group = sum(r[column] for r in top if r[column] > 0)
            assert concentration[label] == {
                "positive_gap_total": round(total, 6),
                "group_positive_gap": round(group, 6),
                "share_pct": round(100 * group / total, 6),
            }


def test_concentration_fixes_group_and_does_not_net_negative_areas():
    observed = dict(a=90, b=40, c=30, d=20, e=10, f=-100)
    fixed = dict(a=10, b=20, c=-20, d=10, e=60, f=0)
    result = ecp.positive_gap_concentration(observed, fixed)
    assert result["observed_top_four"] == ["a", "b", "c", "d"]
    assert not result["same_provinces_at_fixed_size"]
    assert result["observed"]["positive_gap_total"] == 190
    assert result["fixed_local_size"]["positive_gap_total"] == 100
    assert result["fixed_local_size"]["share_pct"] == 40
    assert (
        ecp.positive_gap_concentration(observed, dict.fromkeys(fixed, 0))["fixed_local_size"][
            "share_pct"
        ]
        is None
    )


def test_completion_comparison_counts_zero_and_never_calls_incomplete_totals_exact():
    aligned = {
        str(y): {
            "spain": {"household_change": 100, "observed_gap": 50},
            "by_territory": {
                "Ceuta y Melilla": {
                    "cpro": "51+52",
                    "household_change": 100,
                    "observed_gap": 50,
                    "stock_change": 50,
                }
            },
        }
        for y in (2024, 2025)
    }
    rows = [
        (y, f"{p:02d}", m, kind, 0)
        for y in (2024, 2025)
        for p in range(1, 53)
        for m in range(1, 13)
        for kind in ("Libre", "Protegida")
    ]
    complete = ecp.completion_crosscheck(aligned, rows, (2024, 2025))
    assert complete["by_year"]["2025"]["completions"] == 0
    assert complete["completion_gap_change"] == 0
    assert complete["local"]["areas_with_matching_direction"] == 1  # both unchanged
    for incomplete_rows in (rows[:-1], [*rows[:-1], (*rows[-1][:-1], None)]):
        incomplete = ecp.completion_crosscheck(aligned, incomplete_rows, (2024, 2025))
        assert incomplete["by_year"]["2025"]["completion_cells_missing"] == 1
        assert incomplete["by_year"]["2025"]["households_minus_completions"] is None
        assert incomplete["completion_gap_change"] is None
        assert incomplete["local"]["areas_with_paired_completion_gaps"] == 0
        assert incomplete["local"]["areas_with_end_completion_gap"] == 0
    with pytest.raises(ValueError, match="duplicate MIVAU completion cell"):
        ecp.completion_crosscheck(aligned, [*rows, rows[-1]], (2024, 2025))


def test_pinned_completion_totals_match_public_csvs():
    paths = [ecp.RAW / f for f in ("mivau_iniciadas_terminadas.csv", "mivau_calificaciones.csv")]
    if not ecp_inputs_present() or not all(p.is_file() for p in paths):
        pytest.skip("requires pinned local ECP and MIVAU publisher inputs")
    with duckdb.connect() as con:
        rows = con.execute(
            """
            with all_cells as (
                select ANIO, COD_PROV, MES, 'free' regime, NUM_VIVIENDAS units
                from read_csv(?, delim=';', all_varchar=true)
                where ESTADO_CONSTRUCCION='Terminada' and REGIMEN_VIVIENDA in ('Libre','Libres')
                union all
                select ANIO, COD_PROV, MES, 'protected', NUM_VIVIENDAS
                from read_csv(?, delim=';', all_varchar=true)
                where TIPO_VIVIENDA='Protegida' and TIPO_TRAMITE='Calificación'
                  and ESTADO_TRAMITACION='Definitiva'
            ), mapped as (
                select *, case when COD_PROV in ('51','52') then '51+52'
                               else lpad(COD_PROV, 2, '0') end area
                from all_cells where ANIO in ('2024','2025')
            )
            select ANIO, sum(units::bigint), count(units), count(distinct (COD_PROV, MES, regime)),
                   area
            from mapped group by grouping sets ((ANIO), (ANIO, area)) order by ANIO
        """,
            [str(p) for p in paths],
        ).fetchall()
    data = ecp.build()
    result = data["completion_crosscheck_2024_2025"]
    national = [row for row in rows if row[-1] is None]
    assert len(national) == 2
    for year, total, observed, keys, _ in national:
        assert observed == keys == 52 * 12 * 2
        assert result["by_year"][year]["completions"] == total
        households = data["aligned_stock_comparison"][year]["spain"]["household_change"]
        assert result["by_year"][year]["households_minus_completions"] == households - total
    assert result["completion_gap_change"] == (
        data["aligned_stock_comparison"]["2025"]["spain"]["household_change"]
        - data["aligned_stock_comparison"]["2024"]["spain"]["household_change"]
        - (national[1][1] - national[0][1])
    )
    local = {(year, code): total for year, total, _, _, code in rows if code is not None}
    assert len(local) == 102
    computed = result["local"]
    assert (
        computed["areas_with_paired_completion_gaps"]
        == computed["areas_with_end_completion_gap"]
        == 51
    )
    before = data["aligned_stock_comparison"]["2024"]["by_territory"]
    after = data["aligned_stock_comparison"]["2025"]["by_territory"]
    verified = {}
    for place, row in after.items():
        code = row["cpro"]
        cg0 = before[place]["household_change"] - local["2024", code]
        cg1 = row["household_change"] - local["2025", code]
        sg0, sg1 = before[place]["observed_gap"], row["observed_gap"]
        verified[place] = {
            "completion_gap_end": cg1,
            "completion_gap_change": cg1 - cg0,
            "stock_gap_end": sg1,
            "stock_gap_change": sg1 - sg0,
            "completion_flow_change": local["2025", code] - local["2024", code],
            "net_stock_growth_change": row["stock_change"] - before[place]["stock_change"],
        }
    assert computed["by_territory"] == verified
    assert (
        sum(v["completion_gap_change"] for v in verified.values())
        == result["completion_gap_change"]
    )
    assert computed["areas_with_both_gaps_widening"] == sum(
        min(v["completion_gap_change"], v["stock_gap_change"]) > 0 for v in verified.values()
    )
    assert computed["areas_with_matching_direction"] == sum(
        v["completion_gap_change"] * v["stock_gap_change"] > 0
        or v["completion_gap_change"] == v["stock_gap_change"] == 0
        for v in verified.values()
    )

    def matched(a, b):
        return a * b > 0 or a == b == 0

    mismatched_supply = [
        name
        for name, row in verified.items()
        if not matched(row["completion_flow_change"], row["net_stock_growth_change"])
    ]
    assert mismatched_supply == ["Toledo"]
    assert computed["areas_with_matching_supply_direction"] == len(verified) - len(
        mismatched_supply
    )
    assert computed["areas_with_different_end_signs"] == sum(
        v["completion_gap_end"] * v["stock_gap_end"] <= 0
        and v["completion_gap_end"] != v["stock_gap_end"]
        for v in verified.values()
    )
