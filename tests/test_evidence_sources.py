"""Every housing table referenced by an explorer page needs a source export."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "evidence"


def test_page_housing_references_have_source_exports():
    sources = {p.name for p in (ROOT / "sources").iterdir() if p.is_dir()}
    pattern = rf"\b({'|'.join(sorted(sources))})\.(\w+)"
    referenced = set()
    for page in (ROOT / "pages").glob("*.md"):
        referenced.update(re.findall(pattern, page.read_text()))
    exported = {(source.parent.name, source.stem) for source in (ROOT / "sources").glob("*/*.sql")}
    assert referenced - exported == set(), f"Missing source exports: {referenced - exported}"
