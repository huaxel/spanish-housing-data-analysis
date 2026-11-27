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


def test_current_deficit_results_are_not_allowlisted():
    allowed = {v for v, _ in ad.ALLOW["evidence/pages/deficit.md"]}
    assert not allowed & {607250, 754613, 607.25, 754.613}
