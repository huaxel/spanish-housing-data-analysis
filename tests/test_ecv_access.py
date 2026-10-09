"""Offline INE ECV 2025 housing-access parser and validation contracts."""

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_ecv_access as acc  # noqa: E402


def es(value):
    # JAXI one-decimal style: dot thousands, comma decimals ("41.873,1").
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def split_shares(rest):
    shares, remaining = [], 100.0
    for index in range(rest):
        if index == rest - 1:
            shares.append(remaining)
        else:
            shares.append(50.0 / (2**index))
            remaining -= shares[-1]
    return shares


def fixture(tpx=79621, groups=None, mutate=None):
    block, _, stub_keys, header_key, _, shape = acc.TABLES[tpx]
    stubs = [acc.STUB_HEADERS[key] for key in stub_keys]
    measures = acc.MEASURES[block] if shape == "full" else acc.MEASURES["reasons"]
    combos = (
        groups
        if groups is not None
        else list(itertools.product(*[acc.VOCAB[key] for key in stub_keys]))
    )
    lines = ["\t".join([*stubs, acc.MEASURE_HEADERS[header_key], "Total"])]
    for index, combo in enumerate(combos):
        pop = 1000.0 + index
        if shape == "full":
            values = [pop, 10.0, pop / 10, *split_shares(len(measures) - 3)]
            pairs = list(zip(measures, values, strict=True))
        else:
            pairs = list(zip(measures, split_shares(len(measures)), strict=True))
        for measure, value in pairs:
            lines.append("\t".join([*combo, measure, es(value)]))
    text = "\n".join(lines) + "\n"
    if mutate:
        text = mutate(text)
    return text


def rows(tpx, **kwargs):
    return acc.parse(fixture(tpx, **kwargs), tpx)


@pytest.mark.parametrize("tpx", acc.TABLES)
def test_all_tables_parse_to_pinned_shapes(tpx):
    block, breakdown, stub_keys, _, want_groups, shape = acc.TABLES[tpx]
    parsed = rows(tpx)
    measures = acc.MEASURES[block] if shape == "full" else acc.MEASURES["reasons"]
    assert len(parsed) == want_groups * len(measures)
    assert {row["block"] for row in parsed} == {block}
    assert {row["breakdown"] for row in parsed} == {breakdown}
    assert {row["survey_year"] for row in parsed} == {acc.SURVEY_YEAR}
    kinds = [row["kind"] for row in parsed[: len(measures)]]
    if shape == "full":
        assert kinds[:3] == ["count_thousands", "rate_pct", "count_thousands"]
        assert set(kinds[3:]) == {"share_pct"}
    else:
        assert set(kinds) == {"share_pct"}
    assert {row["status"] for row in parsed} == {""}


def test_spanish_thousands_and_decimal_separators():
    text = fixture(79622)
    text = text.replace("1.000,0", "41.873,1").replace("100,0", "4.187,3", 1)
    parsed = acc.parse(text, 79622)
    by_measure = {row["measure"]: row["value"] for row in parsed if row["group_label"] == "Total"}
    assert by_measure["Personas de 16 o más años (miles)"] == pytest.approx(41873.1)
    assert by_measure["Han cambiado de vivienda (miles)"] == pytest.approx(4187.3)


def test_suppressed_dot_cells_kept_null_without_sum_check():
    def blank(text):
        return text.replace("1.000,0", ".", 1)

    parsed = acc.parse(fixture(79636, mutate=blank), 79636)
    assert any(row["value"] is None for row in parsed)
    flagged = {row["group_label"] for row in parsed if row["status"] == "checks_skipped"}
    assert flagged == {"Total"}


def test_suppressed_reason_cell_flags_its_group():
    def blank(text):
        return text.replace("50,0", ".", 1)

    parsed = acc.parse(fixture(79622, mutate=blank), 79622)
    flagged = {row["group_label"] for row in parsed if row["status"] == "checks_skipped"}
    assert flagged == {"Total"}


def test_headline_identity_fails():
    def break_count(text):
        return text.replace("100,0", "200,0", 1)

    with pytest.raises(ValueError, match="identity"):
        acc.parse(fixture(79621, mutate=break_count), 79621)


def test_reason_sum_fails():
    def break_share(text):
        return text.replace("50,0", "40,0", 1)

    with pytest.raises(ValueError, match="sum"):
        acc.parse(fixture(79621, mutate=break_share), 79621)


def test_unknown_stub_value_fails():
    with pytest.raises(ValueError, match="unknown"):
        acc.parse(fixture(79622, groups=[("Total",), ("Narnia",)]), 79622)


def test_unknown_measure_sequence_fails():
    def rename(text):
        return text.replace("Motivos económicos", "Motivos misteriosos")

    with pytest.raises(ValueError, match="measure sequence"):
        acc.parse(fixture(79621, mutate=rename), 79621)


def test_wrong_group_count_fails():
    with pytest.raises(ValueError, match="groups"):
        acc.parse(fixture(79622, groups=[("Total",)]), 79622)


def test_ragged_row_fails():
    def ragged(text):
        lines = text.splitlines()
        lines[2] += "\textra"
        return "\n".join(lines) + "\n"

    with pytest.raises(ValueError, match="ragged"):
        acc.parse(fixture(79622, mutate=ragged), 79622)


def test_duplicate_cell_fails():
    def duplicate(text):
        lines = text.splitlines()
        return "\n".join(lines + [lines[1]]) + "\n"

    with pytest.raises(ValueError, match="duplicate"):
        acc.parse(fixture(79622, mutate=duplicate), 79622)


@pytest.mark.parametrize("bad", ["abc", "-5,0", "3.9", "1000", "1,00,0"])
def test_bad_number_format_fails(bad):
    # The strict Spanish-format guard fires before numeric parsing, so even
    # the negative case is rejected here rather than at the sign check.
    def inject(text):
        return text.replace("100,0", bad, 1)

    with pytest.raises(ValueError, match="number format"):
        acc.parse(fixture(79622, mutate=inject), 79622)


def test_share_above_100_fails():
    def inject(text):
        # Headline 10,0 -> 101,0 with a matching count keeps identity intact.
        text = text.replace("10,0", "101,0", 1)
        return text.replace("100,0", "1.010,0", 1)

    with pytest.raises(ValueError, match="bounds"):
        acc.parse(fixture(79622, mutate=inject), 79622)


def test_ccaa_geo_mapping():
    parsed = rows(79637)
    geos = {row["geo"] for row in parsed}
    assert geos == {"ES", *acc.VOCAB["CCAA"][1:]}
    assert {row["group_label"] for row in parsed} == {"TOTAL"}


def test_reasons_only_shape_has_no_headline():
    parsed = rows(79644)
    assert {row["kind"] for row in parsed} == {"share_pct"}
    totals = [row for row in parsed if row["group_label"] == "Total | Total"]
    assert abs(sum(row["value"] for row in totals) - 100) < 0.36


def test_no_observed_values_fails():
    def blank_all(text):
        lines = text.splitlines()
        return (
            "\n".join(
                line if i == 0 else line.rsplit("\t", 1)[0] + "\t." for i, line in enumerate(lines)
            )
            + "\n"
        )

    with pytest.raises(ValueError, match="no observed"):
        acc.parse(fixture(79622, mutate=blank_all), 79622)


def test_wrong_stub_header_fails():
    def rename(text):
        return text.replace("País de nacimiento", "País de nunca jamás", 1)

    with pytest.raises(ValueError, match="stub columns"):
        acc.parse(fixture(79622, mutate=rename), 79622)


def test_wrong_value_header_fails():
    def rename(text):
        return text.replace("\tTotal\n", "\tTotal_nacional\n", 1)

    with pytest.raises(ValueError, match="value columns"):
        acc.parse(fixture(79622, mutate=rename), 79622)


def headline_rows(block, value):
    def total_label(spec):
        if spec[1] == "ccaa":
            return "TOTAL"
        return " | ".join(acc.VOCAB[key][0] for key in spec[2])

    return [
        {
            "tpx": tpx,
            "block": block,
            "breakdown": acc.TABLES[tpx][1],
            "group_label": total_label(acc.TABLES[tpx]),
            "geo": "ES",
            "survey_year": 2025,
            "measure": acc.MEASURES[block][1],
            "kind": "rate_pct",
            "value": value,
            "status": "",
        }
        for tpx, spec in acc.TABLES.items()
        if spec[0] == block and tpx != 79644
    ]


def test_headline_agreement_and_disagreement():
    good = headline_rows("access_moves", 3.9)
    acc.validate_headlines(good)
    bad = headline_rows("access_moves", 3.9)
    bad[0]["value"] = 9.9
    with pytest.raises(ValueError, match="disagreement"):
        acc.validate_headlines(bad)


def test_single_headline_source_fails():
    with pytest.raises(ValueError, match="Single headline source"):
        acc.validate_headlines(headline_rows("access_moves", 3.9)[:1])
