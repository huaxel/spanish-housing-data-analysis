"""Inventory the Sevilla-province INSPIRE Buildings feed (assessment only).

Reads the pinned province-41 ATOM feed, issues one HEAD request per
municipality entry to record archive sizes, and writes
artifacts/province_inventory.json. Network access required (like the fetch
scripts); not part of `make analysis`. Re-run to refresh the inventory.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

FEED = RAW / "cadastre_sevilla_feed.xml"
ARTIFACT = ROOT / "artifacts" / "province_inventory.json"


def main():
    if not FEED.is_file():
        raise SystemExit("Missing province feed; run make fetch first")
    root = ET.fromstring(FEED.read_bytes())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = []
    for entry in root.findall("a:entry", ns):
        title = (entry.findtext("a:title", namespaces=ns) or "").strip()
        link = entry.find("a:link", ns).get("href")
        updated = entry.findtext("a:updated", namespaces=ns)
        url = urllib.parse.quote(link, safe=":/?=&%+")
        req = urllib.request.Request(
            url, headers={"User-Agent": "housing-data-analysis/1.0"}, method="HEAD"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
                size = int(response.headers.get("Content-Length", 0))
        except Exception as error:
            raise SystemExit(f"inventory: HEAD failed for {title}: {error}") from error
        entries.append(
            {
                "title": title,
                "archive_url": link,
                "feed_updated": updated[:10] if updated else None,
                "archive_bytes": size,
            }
        )
        time.sleep(0.3)
    entries.sort(key=lambda e: -e["archive_bytes"])
    total = sum(e["archive_bytes"] for e in entries)
    results = {
        "method": "ATOM feed titles plus one HEAD per archive; sizes only, no downloads",
        "n_municipalities": len(entries),
        "total_archive_bytes": total,
        "municipalities": entries,
        "_meta": ols.model_meta(
            str(Path(__file__).resolve()),
            [str(FEED.relative_to(ROOT))],
        ),
    }
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}: {len(entries)} municipalities, "
        f"{total / 1e6:.1f} MB total"
    )


if __name__ == "__main__":
    main()
