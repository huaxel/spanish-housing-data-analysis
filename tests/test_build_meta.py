"""Offline build-meta contracts: descriptions, social cards, tag injection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fix_build_meta as fb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8" />\n'
    '<meta property="og:title" content="Alquiler e ingresos">\n'
    '<meta name="twitter:card" content="summary_large_image">\n'
    '<meta name="twitter:site" content="@evidence_dev"></head></html>'
)


def test_descriptions_cover_every_page():
    pages = {p.stem for p in (ROOT / "evidence/pages").glob("*.md") if not p.stem.startswith("_")}
    described = {
        (Path(rel).parent.name if rel != "index.html" else "index") for rel in fb.DESCRIPTIONS
    }
    assert pages - described == set(), f"pages without meta description: {pages - described}"


def test_card_for_routes_to_existing_assets():
    assert fb.card_for("renta-ingresos/index.html").endswith("/social/renta-ingresos.png")
    assert fb.card_for("acceso/index.html").endswith("/social/default.png")
    assert fb.card_for("index.html").endswith("/social/default.png")


def test_fix_page_injects_social_tags_and_drops_wrong_handle(tmp_path):
    build = tmp_path / "build"
    page = build / "renta-ingresos" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(SAMPLE, encoding="utf-8")
    real_build = fb.BUILD
    fb.BUILD = build
    try:
        assert fb.fix_page(page, "Test description.")
        html = page.read_text(encoding="utf-8")
        # Idempotent: second run changes nothing.
        assert not fb.fix_page(page, "Test description.")
    finally:
        fb.BUILD = real_build
    html = page.read_text(encoding="utf-8")
    assert '<html lang="es">' in html
    assert '<meta name="description" content="Test description." />' in html
    assert '<meta property="og:description" content="Test description." />' in html
    assert '<meta name="twitter:description" content="Test description." />' in html
    assert "og:image" in html and "/social/renta-ingresos.png" in html
    assert "@evidence_dev" not in html
