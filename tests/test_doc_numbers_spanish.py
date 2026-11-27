"""Spanish thousands on the deficit page must stay tied to audited claims."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_doc_numbers as ad  # noqa: E402


def values(text):
    return [v for v, _, _ in ad.doc_numbers(ad.join_spanish_thousands(text))]


def test_spanish_thousands_read_as_integers():
    assert values("de 646.035 a 607.250, y 1.222.836.") == [646035, 607250, 1222836]


def test_decimals_and_urls_are_not_joined():
    assert values("0.4827 y 37,8 https://x.test/1.234") == [0.4827, 37.8]


def test_comma_fractions_below_one_keep_three_decimal_places():
    # Exhaust all three-digit fractional parts, including trailing zeros.
    for fraction in range(1000):
        for sign in ("+", "−"):
            comma = ad.doc_numbers(f"{sign}0,{fraction:03d}%")
            dot = ad.doc_numbers(f"{sign}0.{fraction:03d}%")
            assert len(comma) == len(dot) == 1
            assert comma[0][:2] == dot[0][:2]
    assert ad.doc_numbers("−0,825")[0][:2] == (-0.825, 0.0005)


def test_comma_thousands_are_not_mistaken_for_fractions():
    assert values("2,555; 10,825; 19,000,825; 19,000.825") == [2555, 10825, 19000825, 19000.825]


def test_current_deficit_results_are_not_allowlisted():
    allowed = {v for v, _ in ad.ALLOW["evidence/pages/deficit.md"]}
    assert not allowed & {607250, 754613, 607.25, 754.613}
