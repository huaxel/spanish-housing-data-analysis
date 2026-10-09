"""Offline census-section indicator tests. No network, no data/ dependency."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_censo_secciones import INDICATORS, KEYS, parse_secciones  # noqa: E402

HEADER = ",".join(KEYS + INDICATORS)

FULL = {
    "ccaa": "01",
    "cpro": "04",
    "cmun": "001",
    "dist": "01",
    "secc": "001",
    "t1_1": "1260",
    "t2_1": "0.4857",
    "t2_2": "0.5143",
    "t3_1": "49.4994",
    "t4_1": "0.1048",
    "t4_2": "0.6008",
    "t4_3": "0.2944",
    "t5_1": "0.0984",
    "t6_1": "0.0984",
    "t7_1": "0.0833",
    "t8_1": "0.0762",
    "t9_1": "0.2163",
    "t10_1": "0.1951",
    "t11_1": "0.3768",
    "t12_1": "0.4681",
    "t13_1": "0.0363",
    "t14_1": "0.2899",
    "t15_1": "0.1507",
    "t16_1": "0.0629",
    "t17_1": "0.3921",
    "t17_2": "0.4524",
    "t17_3": "0.0770",
    "t17_4": "0.0246",
    "t17_5": "0.0540",
    "t18_1": "1076",
    "t19_1": "568",
    "t19_2": "508",
    "t20_1": "394",
    "t20_2": "80",
    "t20_3": "94",
    "t21_1": "568",
    "t22_1": "199",
    "t22_2": "182",
    "t22_3": "90",
    "t22_4": "73",
    "t22_5": "24",
}
SUPPRESSED = {"ccaa": "01", "cpro": "04", "cmun": "001", "dist": "01", "secc": "002", "t1_1": "900"}


def line(values):
    return ",".join(values.get(c, "") for c in KEYS + INDICATORS)


def fixture_text():
    return HEADER + "\n" + line(FULL) + "\n" + line(SUPPRESSED) + "\n"


def test_parses_full_and_suppressed_rows():
    rows = parse_secciones(fixture_text(), expect_rows=2)
    assert len(rows) == 2
    full, supp = rows
    assert full["seccion"] == "010400101001"
    assert full["t18_1"] == 1076
    assert full["t3_1"] == pytest.approx(49.4994)
    assert full["suprimido"] is False
    assert supp["suprimido"] is True
    assert supp["t1_1"] == 900
    assert supp["t18_1"] is None


def test_header_and_count_drift_fail():
    with pytest.raises(SystemExit, match="header drift"):
        parse_secciones("a,b,c\n1,2,3\n", expect_rows=1)
    with pytest.raises(SystemExit, match="want 3"):
        parse_secciones(fixture_text(), expect_rows=3)


def test_key_format_and_duplicates_fail():
    bad = dict(FULL, cmun="1")
    with pytest.raises(SystemExit, match="bad cmun"):
        parse_secciones(HEADER + "\n" + line(bad) + "\n", expect_rows=1)
    dup = HEADER + "\n" + line(FULL) + "\n" + line(FULL) + "\n"
    with pytest.raises(SystemExit, match="duplicate section"):
        parse_secciones(dup, expect_rows=2)


def test_partial_suppression_fails():
    partial = dict(SUPPRESSED, t18_1="100")
    text = HEADER + "\n" + line(FULL) + "\n" + line(partial) + "\n"
    with pytest.raises(SystemExit, match="partial suppression"):
        parse_secciones(text, expect_rows=2)


def test_split_consistency_fails():
    bad19 = dict(FULL, t19_2="509")
    with pytest.raises(SystemExit, match="type split breaks total"):
        parse_secciones(HEADER + "\n" + line(bad19) + "\n", expect_rows=1)
    bad22 = dict(FULL, t22_5="25")
    with pytest.raises(SystemExit, match="size split breaks households"):
        parse_secciones(HEADER + "\n" + line(bad22) + "\n", expect_rows=1)
    bad20 = dict(FULL, t20_1="2000")
    with pytest.raises(SystemExit, match="tenure split exceeds principales"):
        parse_secciones(HEADER + "\n" + line(bad20) + "\n", expect_rows=1)


def test_unparsable_cells_fail():
    bad = dict(FULL, t18_1="1.07x")
    with pytest.raises(SystemExit, match="unparsable count"):
        parse_secciones(HEADER + "\n" + line(bad) + "\n", expect_rows=1)


def test_suppression_counts_are_pinned():
    import fetch_censo_secciones as mod

    assert mod.KEYS == ["ccaa", "cpro", "cmun", "dist", "secc"]
    assert len(mod.COUNTS) == 13
    assert len(mod.SHARES) == 23


def test_negative_and_nonfinite_shares_fail():
    bad = dict(FULL, t2_1="-0.1")
    with pytest.raises(SystemExit, match="non-finite or negative share"):
        parse_secciones(HEADER + "\n" + line(bad) + "\n", expect_rows=1)


def test_zero_denominator_fails():
    bad = dict(
        FULL,
        t18_1="0",
        t19_1="0",
        t19_2="0",
        t21_1="0",
        t22_1="0",
        t22_2="0",
        t22_3="0",
        t22_4="0",
        t22_5="0",
        t20_1="0",
        t20_2="0",
        t20_3="0",
    )
    with pytest.raises(SystemExit, match="non-positive usable denominator"):
        parse_secciones(HEADER + "\n" + line(bad) + "\n", expect_rows=1)


def test_section_ratios_recompute_from_counts():
    from build_marts import section_ratios  # noqa: E402

    got = section_ratios({"t1_1": 1260, "t18_1": 1076, "t21_1": 568, "t20_2": 80, "t19_1": 568})
    assert got["personas_por_vivienda"] == pytest.approx(1260 / 1076)
    assert got["hogares_por_vivienda"] == pytest.approx(568 / 1076)
    assert got["alquiler_share"] == pytest.approx(80 / 568)


def test_section_table_stays_quarantined():
    root = Path(__file__).resolve().parents[1]
    consumers = []
    for base in ("scripts", "explorations", "evidence"):
        for pattern in ("*.py", "*.md", "*.sql"):
            for path in (root / base).rglob(pattern):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if "censo2021_secciones" in text:
                    consumers.append(str(path.relative_to(root)))
    allowed = {
        "scripts/build_marts.py",
        "scripts/audit_claims.py",
        "scripts/fetch_censo_secciones.py",
        "tests/test_censo_secciones.py",
        "docs/sources.md",
        "docs/methods.md",
        "docs/occupancy_availability.md",
    }
    assert set(consumers) <= allowed, f"new consumers: {set(consumers) - allowed}"
