"""Offline deficit-arithmetic contracts (pure helpers, no database)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "explorations"))
import deficit_vivienda as dv  # noqa: E402


def monthly(cpro="08", anyo=2021, mes=1, tipo="Libre", estado="Terminadas", valor=10):
    return {
        "cpro": cpro,
        "provincia": "Barcelona",
        "ccaa": "Cataluña",
        "anyo": anyo,
        "mes": mes,
        "tipo": tipo,
        "estado": estado,
        "viviendas": valor,
    }


def grid(cpros=("08", "28"), years=(2021, 2022), value=10):
    rows = []
    for cpro in cpros:
        for year in years:
            for month in range(1, 13):
                rows.append(monthly(cpro=cpro, anyo=year, mes=month, valor=value))
    return rows


def test_annual_flows_sum_both_regimes_and_list_missing():
    rows = grid()
    rows.append(monthly(cpro="08", anyo=2021, mes=1, tipo="Protegida", valor=5))
    rows[0] = monthly(cpro="08", anyo=2021, mes=1, valor=None)
    totals, missing = dv.annual_flows(rows, (2021, 2022))
    # 08/2021: 11 Libre months x10 + 1 Protegida x5 (missing Libre cell excluded).
    assert totals[("08", 2021)] == 11 * 10 + 5
    assert totals[("28", 2022)] == 12 * 10
    assert missing == [("08", 2021, 1)]
    # Other estados never enter totals.
    assert dv.annual_flows([monthly(estado="Iniciadas")], (2021,))[0] == {}


def test_creation_is_end_minus_start_and_requires_coverage():
    assert dv.creation({"a": 100, "b": 50}, {"a": 130, "b": 40}) == {"a": 30, "b": -10}
    with pytest.raises(ValueError, match="coverage"):
        dv.creation({"a": 100}, {"a": 130, "b": 40})


def test_ceuta_melilla_combine_and_partial_fails():
    values, names = dv.combine_ceuta_melilla(
        {"08": 10, "51": 1, "52": 2}, {"08": "Barcelona", "51": "Ceuta", "52": "Melilla"}
    )
    assert values == {"08": 10, "51+52": 3}
    assert names["51+52"] == "Ceuta y Melilla"
    with pytest.raises(ValueError, match="partial"):
        dv.combine_ceuta_melilla({"51": 1}, {"51": "Ceuta"})


def test_deficits_propagate_null_tourist_flow():
    rows = dv.deficits(
        {"a": 100, "b": 10, "c": 5},
        {"a": 60, "b": 20},
        {"a": 5, "b": None},
    )
    assert rows["a"]["deficit_v2"] == 40
    assert rows["a"]["deficit_v3p"] == 35
    assert rows["b"]["deficit_v2"] == -10
    assert rows["b"]["deficit_v3p"] is None
    assert rows["b"]["deficit_per_creation"] == -1.0
    assert rows["c"]["deficit_v2"] == 5  # missing completions read as zero flow
    assert rows["c"]["deficit_per_creation"] == 1.0


def test_deficit_per_creation_null_on_nonpositive_creation():
    rows = dv.deficits({"a": 0}, {"a": 0}, {"a": 0})
    assert rows["a"]["deficit_per_creation"] is None


def test_national_rollup_ranks_and_shares():
    rows = dv.deficits(
        {"m": 1000, "b": 500, "s": 10},
        {"m": 100, "b": 100, "s": 20},
        {"m": 0, "b": 0, "s": 0},
    )
    nat = dv.national(rows)
    assert nat["deficit_v2"] == 900 + 400 - 10
    assert nat["deficit_v3p"] == nat["deficit_v2"]
    assert nat["top5_keys"] == ["m", "b"]
    assert nat["top5_share"] == pytest.approx(1300 / 1300)
    assert nat["negative_keys"] == ["s"]


def test_national_v3p_null_if_any_province_missing_flow():
    rows = dv.deficits({"a": 100}, {"a": 60}, {"a": None})
    assert dv.national(rows)["deficit_v3p"] is None


def test_windows_and_benchmarks_pinned():
    assert set(dv.WINDOWS) == {"2021-2024", "2021-2025"}
    assert dv.WINDOWS["2021-2024"]["stock_end"] == 2025
    assert dv.WINDOWS["2021-2025"]["stock_end"] == 2026
    assert dv.BENCHMARKS["v2_2021-2024"] == 600000
    assert dv.BENCHMARKS["v2_2021-2025"] == 734000
