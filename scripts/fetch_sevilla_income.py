"""Separate SIM barrio net-family-income sidecar; no central mart changes."""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

LAYER = (
    "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/"
    + urllib.parse.quote("Cualificación_de_hogares_residentes_por_Renta_Neta_declarada")
    + "/FeatureServer/31"
)
URLS = {
    "query": LAYER
    + "/query?"
    + urllib.parse.urlencode(
        {"where": "1=1", "outFields": "*", "returnGeometry": "false", "f": "pjson"}
    ),
    "metadata": LAYER + "?f=pjson",
    "definition": "https://www.arcgis.com/sharing/rest/content/items/"
    "fe78eabad62b4e55a6531cb3e2249f1f/data?f=pjson",
}
INPUTS = {key: ROOT / f"data/raw/sevilla_income_{key}.json" for key in URLS}
DATABASE = PROCESSED / "income.duckdb"


def parse(query, metadata, definition):
    if query.get("error") or query.get("exceededTransferLimit"):
        raise ValueError("Income query failed or truncated")
    required = {"IDG", "ID_DIS", "ID_BAR", "BAR", "DIS", *[f"ING_FAM_{y}" for y in range(15, 21)]}
    fields = {f["name"]: f.get("type") for f in metadata.get("fields", [])}
    if not required <= fields.keys():
        raise ValueError("Income schema changed")
    numeric = {
        "esriFieldTypeInteger",
        "esriFieldTypeSmallInteger",
        "esriFieldTypeDouble",
        "esriFieldTypeSingle",
    }
    if any(fields[f"ING_FAM_{y}"] not in numeric for y in range(15, 21)):
        raise ValueError("Income numeric field types changed")
    if any(fields[k] != "esriFieldTypeString" for k in ["IDG", "BAR", "DIS"]):
        raise ValueError("Income label field types changed")
    if metadata.get("id") != 31 or "escala Barrio" not in metadata.get("name", ""):
        raise ValueError("Income layer is not the verified barrio layer")
    legend = definition.get("widgets", {}).get("widget_1389", {}).get("config", {}).get("text", "")
    if "Ingresos familiares declarados ejercicio AA (Renta media neta €)" not in legend:
        raise ValueError("Publisher income definition changed")
    features = query.get("features", [])
    if len(features) != 108:
        raise ValueError("Income barrio coverage changed")
    rows, seen = [], set()
    for feature in features:
        a = feature["attributes"]
        if not required <= a.keys():
            raise ValueError("Incomplete income attributes")
        idg = a["IDG"]
        if not isinstance(idg, str) or not idg.isdigit() or len(idg) != 5:
            raise ValueError("Invalid income key")
        if idg != str(a["ID_DIS"]).zfill(2) + str(a["ID_BAR"]).zfill(3) or idg in seen:
            raise ValueError("Duplicate or conflicting income key")
        if any(not isinstance(a[k], str) or not a[k].strip() for k in ["BAR", "DIS"]):
            raise ValueError("Invalid income geography labels")
        seen.add(idg)
        for year in range(15, 21):
            value = a[f"ING_FAM_{year}"]
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError("Income must be positive finite EUR or null")
            rows.append((idg, a["BAR"], a["DIS"], 2000 + year, value))
    return sorted(rows)


def inputs():
    man = manifest.load()
    paths = [str(p.relative_to(ROOT)) for p in INPUTS.values()]
    if any(p not in man.get("sha256", {}) for p in paths):
        raise ValueError("Unpinned income input; run scripts/fetch_sevilla_income.py")
    pins = {p: man["sha256"][p] for p in paths}
    missing, changed = manifest.check(pins)
    if missing or changed:
        raise ValueError("Missing or changed pinned income inputs")
    payloads = {k: json.loads(p.read_text()) for k, p in INPUTS.items()}
    rows = parse(payloads["query"], payloads["metadata"], payloads["definition"])
    meta = {**pins, "script_sha": manifest.sha256(Path(__file__)), "duckdb": duckdb.__version__}
    return rows, meta


def verify():
    rows, meta = inputs()
    if not DATABASE.is_file():
        raise ValueError("Missing income sidecar; rebuild with --offline")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        if dict(con.execute("select * from income_meta").fetchall()) != meta:
            raise ValueError("Stale income sidecar; rebuild with --offline")
        actual = con.execute("select * from barrios_income order by idg, anyo").fetchall()
    if actual != rows:
        raise ValueError("Income sidecar differs from pinned source")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        verify()
        print("income: source pins, definition and exact sidecar rows verified")
        return
    if not args.offline:
        downloaded = {}
        for key, url in URLS.items():
            with urllib.request.urlopen(url, timeout=40) as response:
                content = response.read(20 * 1024 * 1024 + 1)
            if len(content) > 20 * 1024 * 1024:
                raise ValueError("Income download exceeds size bound")
            downloaded[key] = content
        parse(*[json.loads(downloaded[k]) for k in ["query", "metadata", "definition"]])
        for key, content in downloaded.items():
            INPUTS[key].parent.mkdir(parents=True, exist_ok=True)
            INPUTS[key].write_bytes(content)
            manifest.record(
                str(INPUTS[key].relative_to(ROOT)),
                {
                    "url": URLS[key],
                    "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM",
                    "accessed": date.today().isoformat(),
                    "note": (
                        "Publisher-reported barrio net-family income; "
                        "aggregation weights undocumented"
                    ),
                },
            )
    rows, meta = inputs()
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATABASE.with_suffix(".tmp.duckdb")
    with duckdb.connect(str(tmp)) as con:
        con.execute(
            "create or replace table barrios_income (idg varchar, barrio varchar, "
            "distrito varchar, anyo integer, renta_neta_eur double)"
        )
        con.executemany("insert into barrios_income values (?,?,?,?,?)", rows)
        con.execute("create or replace table income_meta (key varchar, value varchar)")
        con.executemany("insert into income_meta values (?,?)", list(meta.items()))
    tmp.replace(DATABASE)
    verify()
    print(f"income: {len(rows)} barrio/year records built")


if __name__ == "__main__":
    main()
