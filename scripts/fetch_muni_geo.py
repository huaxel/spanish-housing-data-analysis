"""Fetch municipal polygons for the vacancy map (Eurostat GISCO LAU 2021).

Source: GISCO LAU 2021 TopoJSON, whole Europe (43 MB), EPSG:4326 —
  https://gisco-services.ec.europa.eu/distribution/v2/lau/topojson/LAU_RG_01M_2021_4326.json
LAU_ID for Spain is the 5-digit INE municipal code (verified: '10200'
Valdelacasa de Tajo), so the join key needs no name matching — it is
derived as GISCO_ID.split('_')[1] and stored as CODIGOINE.

Build (deterministic for pinned mapshaper + pinned raw bytes): keep only
CNTR_CODE == 'ES' (8,131 features), drop all properties but CODIGOINE,
Visvalingam-simplify to 7% with shapes kept (~3.8 MB), write
evidence/static/geo/municipios.geojson. Fails loudly when the feature
count drifts or fewer than 3,139 vacancy codigos join (46 'xx999' Resto
aggregates have no polygon by design).

Writes data/raw/geo/lau_2021.json (pinned) + evidence/static/geo/municipios.geojson.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://gisco-services.ec.europa.eu/distribution/v2/lau/topojson/LAU_RG_01M_2021_4326.json"
ACCESSED = "2026-10-06"
MAPSHAPER = "mapshaper@0.7.79"  # pinned: simplification must reproduce
EXPECTED_FEATURES = 8131
MIN_JOIN = 3139  # named vacancy municipios (46 Resto xx999 codes excluded)

ROOT = Path(__file__).resolve().parents[1]
RAW_GEO = RAW / "geo" / "lau_2021.json"
OUT = ROOT / "evidence" / "static" / "geo" / "municipios.geojson"


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)


def main() -> None:
    download(URL, RAW_GEO)
    manifest.record(
        "data/raw/geo/lau_2021.json",
        {"publisher": "Eurostat GISCO", "table": "LAU 2021 RG 01M 4326", "accessed": ACCESSED},
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "npx",
            "--yes",
            MAPSHAPER,
            str(RAW_GEO),
            "-filter",
            "CNTR_CODE === 'ES'",
            "-each",
            "CODIGOINE = GISCO_ID.split('_')[1]",
            "-filter-fields",
            "CODIGOINE",
            "-simplify",
            "7%",
            "keep-shapes",
            "-o",
            "format=geojson",
            str(OUT),
        ],
        check=True,
    )
    geo = json.loads(OUT.read_text(encoding="utf-8"))
    feats = geo["features"]
    if len(feats) != EXPECTED_FEATURES:
        raise SystemExit(f"municipal feature drift: {len(feats)} != {EXPECTED_FEATURES}")
    codes = {f["properties"]["CODIGOINE"] for f in feats}
    if len(codes) != EXPECTED_FEATURES or not all(len(c) == 5 for c in codes):
        raise SystemExit("CODIGOINE malformed or duplicated")
    import duckdb

    con = duckdb.connect(str(ROOT / "data" / "processed" / "marts.duckdb"), read_only=True)
    rows = con.execute("select distinct codigo from censo2021_intensidad").fetchall()
    ours = {r[0] for r in rows}
    named = {c for c in ours if not c.endswith("999")}
    if len(named & codes) < MIN_JOIN:
        raise SystemExit(f"vacancy join coverage {len(named & codes)} < {MIN_JOIN}")
    print(f"municipios.geojson: {len(feats)} features, vacancy join {len(named & codes)}")


if __name__ == "__main__":
    main()
