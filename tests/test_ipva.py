"""Municipal identity and measurement contracts for the IPVA–SERPAVI cross-check."""

from __future__ import annotations

import itertools
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "explorations"))

import ipva_rent_index as ipva  # noqa: E402

import fetch_ipva  # noqa: E402
from spanish_housing import rank_stats  # noqa: E402


def csv_bytes(*rows):
    return ("Municipio;Tipo de dato;Periodo;Total\r\n" + "\r\n".join(rows)).encode("utf-8-sig")


def test_csv_separates_aggregates_and_preserves_codes_even_on_homonyms():
    rows = fetch_ipva.parse(
        csv_bytes(
            "Total Nacional;Índice;2023;100,5",
            "Resto Valencia/València;Índice;2023;100,2",
            "46250 Valencia;Índice;2023;120,1",
            "01001 Valencia;Índice;2023;102,5",
            "01001 Valencia;Variación anual;2023;-1,2",
            "01001 Valencia;Variación anual;2022;0",
            "01001 Valencia;Índice;2022;..",
            "01001 Valencia;Índice;2021;",
        )
    )
    assert [r["nivel"] for r in rows[:2]] == ["nacional", "resto_provincia"]
    assert all(r["codigo_ine"] is None for r in rows[:2])
    indices = ipva.by_code(
        (r["codigo_ine"], r["anyo"], r["valor"])
        for r in rows
        if r["nivel"] == "municipio" and r["medida"] == "indice"
    )
    assert indices == {"01001": {2023: Fraction("102.5")}, "46250": {2023: Fraction("120.1")}}
    assert [r["valor"] for r in rows if r["medida"] == "variacion"] == [-1.2, 0]


@pytest.mark.parametrize(
    ("row", "error"),
    [
        ("1001 Madrid;Índice;2023;110", "unknown geography"),
        ("01001 A;Índice;2023T1;110", "annual period"),
        ("01001 A;Índice;2023;-1", "nonpositive index"),
        ("01001 A;Índice;2023;1.23", "invalid value"),
        ("01001 A;Índice;2023;100;extra", "malformed row"),
    ],
)
def test_invalid_cells_fail_closed(row, error):
    with pytest.raises(ValueError, match=error):
        fetch_ipva.parse(csv_bytes(row))


def test_one_observation_per_code_year_even_if_a_label_changes():
    with pytest.raises(ValueError, match="duplicate observation"):
        fetch_ipva.parse(csv_bytes("01001 Old;Índice;2020;..", "01001 New;Índice;2020;100"))
    with pytest.raises(ValueError, match="Duplicate"):
        ipva.by_code([("01001", 2020, 3.5), ("01001", 2020, 4.2)])


def test_rank_agreement_for_monotone_transforms_exhaustive_over_ties():
    # The former last-rank/no-ties-variance formula returned 0.5 on [1,1,2]
    # correlated with itself. Exercise every tie pattern on this small domain.
    for x in itertools.product(range(3), repeat=4):
        if len(set(x)) == 1:
            assert rank_stats.spearman(x, x, digits=6) is None
        else:
            for sign in (-1, 1):
                assert rank_stats.spearman(x, [sign * (v + 1) ** 2 for v in x], digits=6) == sign


def test_matched_samples_and_quartile_accounting():
    if not ipva.MARTS.exists() or not ipva.IPVA_PARQUET.exists():
        pytest.skip("requires pinned local data")
    data = ipva.build()
    cov = data["coverage"]
    assert cov["matched"] + cov["unmatched"] == cov["ipva_municipios"]
    for window in data["windows"]:
        assert window["n"] <= window["ipva_at_both_endpoints"] <= cov["ipva_municipios"]
        parts = window["quartiles_by_serpavi_change"]
        assert sum(part["n"] for part in parts) == window["n"]
        assert [part["quartile"] for part in parts] == [1, 2, 3, 4]
        medians = [part["median_serpavi_pct"] for part in parts]
        assert medians == sorted(medians)
        gaps = window["gap_pp"]
        assert gaps["p10"] <= gaps["median"] <= gaps["p90"]


def test_local_order_and_geographic_separation_are_distinct():
    # In one province the order is reversed; in another, all three pairs agree.
    # The singleton must not enter either contrast, even in cross-province pairs.
    codes = ["01001", "01002", "02001", "02002", "02003", "03001"]
    result = ipva.pair_ordering(codes, [1, 2, 3, 4, 5, -100], [2, 1, 3, 4, 5, 100])
    assert result["municipalities"] == 5 and result["singletons_excluded"] == 1
    assert result["within"] == {"agreed": 3, "comparable": 4, "tied": 0, "agreement_pct": 75.0}
    assert result["between"] == {"agreed": 6, "comparable": 6, "tied": 0, "agreement_pct": 100.0}
    assert result["equal_province_agreement_pct"] == 50


def test_each_unordered_province_pair_gets_one_vote_in_the_balanced_contrast():
    # AB and AC agree; BC disagrees. Group sizes 2/3/4 imply 6/8/12 pairs.
    r = ipva.pair_ordering(
        ["01001", "01002", "02001", "02002", "02003", "03001", "03002", "03003", "03004"],
        list(range(9)),
        [0, 1, 6, 7, 8, 2, 3, 4, 5],
    )
    assert r["between"]["agreement_pct"] == round(100 * 14 / 26, 2)
    assert r["comparable_province_pairs"] == 3
    assert r["equal_province_pair_agreement_pct"] == 66.67


def test_all_tied_and_singleton_provinces_have_no_local_rate():
    codes = ["01001", "01002", "02001", "02002", "03001"]
    r = ipva.pair_ordering(codes, [1, 1, 3, 4, 0], [2, 3, 10, 10, 0])
    assert r["within"] == {"agreed": 0, "comparable": 0, "tied": 2, "agreement_pct": None}
    assert r["provinces_with_comparable_pairs"] == 0
    assert r["equal_province_agreement_pct"] is None
    assert r["between"]["agreement_pct"] == 100
    assert (
        ipva.pair_ordering(["01001", "02001"], [1, 2], [1, 2])["between"]["agreement_pct"] is None
    )


def test_pair_partition_conserves_all_pairs_under_ties_and_reversal():
    codes = ["01001", "02002", "01002", "02001"]
    x = [0, 1, 0, 2]
    for y in itertools.product(range(3), repeat=4):
        r = ipva.pair_ordering(codes, x, y)
        reversed_order = ipva.pair_ordering(codes, x, [-v for v in y])
        assert r == ipva.pair_ordering(codes[::-1], x[::-1], y[::-1])
        for key, expected in [("within", 2), ("between", 4)]:
            p, q = r[key], reversed_order[key]
            assert p["tied"] == q["tied"]
            assert p["comparable"] + p["tied"] == expected
            assert p["agreed"] + q["agreed"] == p["comparable"]
