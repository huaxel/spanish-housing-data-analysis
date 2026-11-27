"""Every cartesian chart takes the shared narrow-screen defaults."""

import re
from pathlib import Path

PAGES = sorted((Path(__file__).resolve().parents[1] / "evidence/pages").glob("*.md"))
OPENING = re.compile(
    r"^[ \t]*<(LineChart|BarChart|AreaChart|ScatterPlot|BubbleChart|BoxPlot|Histogram|Chart)\b",
    re.M,
)


def chart_tags(text: str):
    for match in OPENING.finditer(text):
        end = r"^[ \t]*</Chart>" if match[1] == "Chart" else r"/>[ \t]*$"
        closing = re.compile(end, re.M).search(text, match.end())
        assert closing, f"unterminated <{match[1]}>"
        yield text[match.start() : closing.end()]


def test_every_chart_uses_the_shared_options():
    total = 0
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        tags = list(chart_tags(text))
        total += len(tags)
        for tag in tags:
            # A plain echartsOptions object would silently drop the defaults.
            assert "echartsOptions={ajusteGrafico(" in tag, f"{page.name}: {tag[:80]}"
            assert tag.count("echartsOptions=") == 1, f"{page.name}: {tag[:80]}"
        if tags:
            path = "../components" if page.stem == "index" else "../../components"
            assert f"import {{ ajusteGrafico }} from '{path}/chartOptions.js';" in text, page.name
    assert total >= 79, "chart tags were no longer detected"
