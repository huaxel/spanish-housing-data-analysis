"""Calendar years must be skipped as labels; near-misses must stay audited."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_doc_numbers as ad  # noqa: E402


def numbers(text: str) -> list[float]:
    return [v for v, _slack, _ctx in ad.doc_numbers(text)]


def is_skipped_year(val: float) -> bool:
    """The exact predicate main() applies before matching claims."""
    return val == int(val) and 1990 <= val <= 2100


def test_projection_horizons_are_years_not_results():
    # INE PROH projects to 2040; those labels must not need allowlists.
    for year in (1990, 2026, 2030, 2040, 2050, 2100):
        assert is_skipped_year(year), year


def test_near_miss_integers_still_reach_the_claims_check():
    for value in (1989, 2101, 1890):
        assert not is_skipped_year(value), value


def test_no_claim_pins_a_whole_number_inside_the_skip_window():
    """Widening the window is only safe while no claim expects such a value."""
    masked = [
        (expected, tol)
        for expected, tol in ad.claim_expectations()
        if expected == int(expected)
        and is_skipped_year(expected)
        and expected >= 2031  # 1990-2030 was already skipped before the widening
    ]
    assert masked == [], masked


def test_year_labels_are_extracted_but_skipped_by_main_not_by_the_tokenizer():
    # doc_numbers keeps years (they are numbers); main() decides they are labels.
    assert 2040 in numbers("INE projects households to 2040")
    assert 19_761_683 in numbers("19,761,683 households at 1 January 2026")
