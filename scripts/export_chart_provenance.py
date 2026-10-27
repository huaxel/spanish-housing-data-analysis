"""Generate only the input metadata referenced by chart evidence panels.

Definitions stay beside charts; SQL and filtered rows come from Evidence's
own runtime Query. This is not a second claim/value registry. --check needs
only tracked files and fails on stale metadata or invalid panel declarations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "evidence/pages"
MANIFEST = ROOT / "data/input_manifest.json"
OUTPUT = ROOT / "evidence/components/provenance.generated.json"


def declarations(pages):
    panels = []
    ids = set()
    for page, text in pages.items():
        queries = set(re.findall(r"```sql (\w+)\n", text))
        for tag in re.findall(r"<EvidencePanel\b.*?/>", text, re.S):
            chart = re.search(r'\bchart="([a-z0-9-]+)"', tag)
            query = re.search(r"\bdata=\{(\w+)\}", tag)
            files = re.search(r"\bfiles=\{(\[.*?\])\}", tag, re.S)
            columns = re.search(r"\bcolumns=\{(\[.*?\])\}", tag, re.S)
            if not all((chart, query, files, columns)):
                raise ValueError(f"Incomplete evidence panel in {page}")
            chart = chart[1]
            if chart in ids or not chart.startswith(Path(page).stem + "-"):
                raise ValueError(f"Duplicate or misplaced evidence chart: {chart}")
            ids.add(chart)
            if query[1] not in queries:
                raise ValueError(f"Unknown evidence query {query[1]} in {page}")
            for field in ("definition", "coverage"):
                if not re.search(r"\b" + field + r'="[^"]+"', tag):
                    raise ValueError(f"Missing evidence {field}: {chart}")
            files, columns = json.loads(files[1]), json.loads(columns[1])
            for values in (files, columns):
                if (
                    not isinstance(values, list)
                    or not values
                    or not all(isinstance(v, str) and v for v in values)
                    or len(set(values)) != len(values)
                ):
                    raise ValueError(f"Invalid evidence file/column list: {chart}")
            if any(not f.startswith("data/raw/") or ".." in Path(f).parts for f in files):
                raise ValueError(f"Evidence file is not a public raw-input pin: {chart}")
            panels.append({"chart": chart, "query": query[1], "files": files, "columns": columns})
    if not panels:
        raise ValueError("No chart evidence panels found")
    return panels


def metadata(manifest, panels):
    sources = {}
    for path in sorted({path for panel in panels for path in panel["files"]}):
        sha = manifest.get("sha256", {}).get(path)
        if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError(f"Missing/invalid input pin: {path}")
        source = manifest.get("sources", {}).get(path, {})
        accessed = source.get("accessed")
        if accessed is not None:
            date.fromisoformat(accessed)
        url = source.get("url")
        api = source.get("api", "")
        if not url and re.fullmatch(r"wstempus/DATOS_TABLA/\d+", api):
            url = "https://servicios.ine.es/wstempus/js/ES/" + api.removeprefix("wstempus/")
        if url and (urlsplit(url).scheme != "https" or not urlsplit(url).hostname):
            raise ValueError(f"Non-HTTPS evidence origin: {path}")
        publisher = source.get("publisher") or (
            "INE · " + source["operation"] if source.get("operation") else Path(path).name
        )
        sources[path] = {"sha256": sha, "publisher": publisher, "accessed": accessed, "url": url}
    snapshot = manifest.get("snapshot_date")
    date.fromisoformat(snapshot)
    return {"snapshot_date": snapshot, "sources": sources}


def generate():
    pages = {str(p.relative_to(ROOT)): p.read_text() for p in sorted(PAGES.glob("*.md"))}
    panels = declarations(pages)
    contents = MANIFEST.read_bytes()
    payload = metadata(json.loads(contents), panels)
    payload["manifest_sha256"] = hashlib.sha256(contents).hexdigest()
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = generate()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != expected:
            raise ValueError("Chart provenance stale or missing; run make chart-provenance")
        print("chart provenance: panel declarations and tracked input pins verified")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(expected)
        print("wrote " + str(OUTPUT.relative_to(ROOT)))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"chart provenance: {error}") from error
