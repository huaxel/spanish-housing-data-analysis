"""Sevilla-province INSPIRE BU build: municipal-grain physical stock.

Downloads and parses the BU archives for all 106 Sevilla-province
municipalities into data/processed/stock_province.duckdb (separate from
stock.duckdb so no existing freshness key is touched).

The CAT->INE municipality map is derived at runtime from the pinned
province feed titles plus the municipal sidecar names, with strict
bijection assertions (unique normalized names on both sides, zero
unmatched entries on either side, explicit CAT/INE code-shape checks).
It is never guessed: any feed/sidecar drift fails loudly instead of
misassigning a city.

Municipal grain only (barrio_id NULL, match_status "municipal_only").
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _load_module(name: str, rel: str):
    import importlib.util

    path = Path(__file__).resolve().parent / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cap = _load_module("fetch_cadastre_capitals", "fetch_cadastre_capitals.py")
sev = _load_module("fetch_cadastre_stock", "fetch_cadastre_stock.py")

from spanish_housing import manifest  # noqa: E402
from spanish_housing import stock_geometry as geom  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

PROVINCE_FEED = RAW / "cadastre_sevilla_feed.xml"
DATABASE = PROCESSED / "stock_province.duckdb"


def norm(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(text.upper().replace("-", " ").split())


def uninvert(name: str) -> str:
    if "," in name:
        base, article = [part.strip() for part in name.split(",", 1)]
        return f"{article} {base}"
    return name


def municipality_map() -> list[dict]:
    """Derive the validated CAT->INE map from the pinned feed + sidecar."""
    root = ET.fromstring(PROVINCE_FEED.read_bytes())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    feed: dict[str, dict] = {}
    for entry in root.findall("a:entry", ns):
        title = (entry.findtext("a:title", namespaces=ns) or "").strip()
        code, rest = title.split("-", 1)
        name = rest[: -len(" buildings")].strip() if rest.endswith(" buildings") else rest.strip()
        if not code.strip().isdigit():
            raise ValueError(f"Non-numeric CAT code in feed title: {title}")
        key = norm(name)
        if key in feed:
            raise ValueError(f"Duplicated normalized feed name: {name}")
        feed[key] = {
            "cat": code.strip(),
            "name": name,
            "url": entry.find("a:link", ns).get("href"),
            "updated": (entry.findtext("a:updated", namespaces=ns) or "")[:10],
        }
    con = duckdb.connect(str(PROCESSED / "sevilla_2021.duckdb"), read_only=True)
    sidecar = con.execute("select codigo, municipio from perfiles").fetchall()
    con.close()
    seen, mapping = set(), []
    for ine, name in sidecar:
        if not ine.isdigit():
            raise ValueError(f"Non-numeric INE code in sidecar: {ine}")
        key = norm(uninvert(name))
        if key in seen:
            raise ValueError(f"Duplicated normalized sidecar name: {name}")
        seen.add(key)
        if key not in feed:
            raise ValueError(f"Sidecar municipality without feed entry: {ine} {name}")
        entry = feed[key]
        mapping.append(
            {
                "ine": ine,
                "ine_name": name,
                "cat": entry["cat"],
                "feed_name": entry["name"],
                "url": entry["url"],
                "updated": entry["updated"],
            }
        )
    used = {m["cat"] for m in mapping}
    orphan = sorted(code for code, e in ((v["cat"], v) for v in feed.values()) if code not in used)
    if orphan:
        raise ValueError(f"Feed entries without sidecar counterpart: {orphan}")
    return sorted(mapping, key=lambda m: m["ine"])


def paths(cat: str) -> dict[str, Path]:
    return {
        "zip": RAW / f"cadastre_prov_{cat}_buildings.zip",
        "parquet": RAW / "parquet" / f"cadastre_prov_{cat}_buildings.parquet",
    }


def crs_set(element) -> set[str]:
    """Collect the srsName values of a record's footprint surfaces."""
    found = set()
    for surface in element.findall(".//{*}Surface"):
        srs = surface.get("srsName")
        if srs is not None:
            found.add(srs)
    return found


CRS_25830 = "urn:ogc:def:crs:EPSG::25830"
CRS_25829 = "urn:ogc:def:crs:EPSG::25829"
NORMALIZED_REFCATS = 0


def attribute_record(element, snapshot: str, cat: str, ine: str) -> dict:
    """Scalar record fields without geometry measures (non-25830 CRS).

    Footprint area and centroid are planar measures that must not mix
    coordinate zones in one column; municipal-grain profiles use only the
    attribute fields, so geometry is recorded as NULL with an explicit CRS
    status instead of being silently mixed or reprojected without pyproj.
    """
    import math
    import re

    refcat = sev.text(element, ".//{*}localId")
    if not refcat or not re.fullmatch(r"[A-Z0-9]{14}", refcat):
        raise ValueError("Invalid cadastral parcel reference")
    gml_id = element.get("{http://www.opengis.net/gml/3.2}id")
    if gml_id != "ES.SDGC.BU." + refcat:
        raise ValueError("Building ID and cadastral reference disagree")
    start_raw = sev.text(element, "{*}dateOfConstruction/{*}DateOfEvent/{*}beginning")
    end_raw = sev.text(element, "{*}dateOfConstruction/{*}DateOfEvent/{*}end")
    start, start_quality = sev.construction_year(start_raw)
    end, end_quality = sev.construction_year(end_raw)
    quality = (
        "invalid"
        if "invalid" in (start_quality, end_quality)
        else "complete"
        if start is not None and end is not None
        else "missing"
        if start is None and end is None
        else "partial"
    )
    if start is not None and end is not None and start > end:
        raise ValueError("Construction date range reversed")
    floor_text = sev.text(element, "{*}officialArea/{*}OfficialArea/{*}value")
    floor = float(floor_text) if floor_text is not None else None
    if floor is not None:
        value = element.find("{*}officialArea/{*}OfficialArea/{*}value")
        reference = sev.text(element, "{*}officialArea/{*}OfficialArea/{*}officialAreaReference")
        if (
            reference != "grossFloorArea"
            or value.get("uom") != "m2"
            or not math.isfinite(floor)
            or floor < 0
        ):
            raise ValueError("Unexpected cadastral area definition/unit/value")
    return {
        "refcat": refcat,
        "cat_municipality": cat,
        "ine_municipality": ine,
        "snapshot_date": snapshot,
        "current_use": sev.text(element, "{*}currentUse"),
        "condition": sev.text(element, "{*}conditionOfConstruction"),
        "date_start_raw": start_raw,
        "date_end_raw": end_raw,
        "date_quality": quality,
        "year_start": start,
        "year_end": end,
        "dwelling_properties": sev.count_value(sev.text(element, "{*}numberOfDwellings")),
        "building_units": sev.count_value(sev.text(element, "{*}numberOfBuildingUnits")),
        "gross_floor_m2": floor,
        "footprint_m2": None,
        "centroid_x": None,
        "centroid_y": None,
        "barrio_id": None,
        "match_status": "municipal_only_25829",
    }


def record(element, snapshot: str, cat: str, ine: str) -> dict:
    import re

    global NORMALIZED_REFCATS
    local_id = element.find(".//{*}localId")
    raw = local_id.text if local_id is not None else None
    if raw is not None and not re.fullmatch(r"[A-Z0-9]{14}", raw):
        # Data quirk seen in the wild (e.g. Lantejuela '2968801UG0326n'):
        # same 14-char reference with a lowercase check character. Normalize
        # to canonical uppercase only when the gml:id agrees
        # case-insensitively; the duplicate-refcat check still guards
        # against case collisions, and the count is reported per build.
        gid = element.get("{http://www.opengis.net/gml/3.2}id")
        if re.fullmatch(r"[A-Za-z0-9]{14}", raw) and (
            gid is not None and gid.upper() == "ES.SDGC.BU." + raw.upper()
        ):
            local_id.text = raw.upper()
            element.set("{http://www.opengis.net/gml/3.2}id", "ES.SDGC.BU." + raw.upper())
            NORMALIZED_REFCATS += 1
    crs = crs_set(element)
    if crs - {CRS_25830}:
        if crs - {CRS_25830, CRS_25829}:
            raise ValueError(f"Unexpected building CRS: {sorted(crs)}")
        return attribute_record(element, snapshot, cat, ine)
    row = sev.building(element, snapshot, [])
    row["cat_municipality"] = cat
    row["ine_municipality"] = ine
    row["barrio_id"] = None
    row["match_status"] = "municipal_only"
    return row


def parse_archive(archive: Path, snapshot: str, cat: str, ine: str) -> list[dict]:
    rows, seen = [], set()
    with zipfile.ZipFile(archive) as zf:
        files = [f for f in zf.infolist() if f.filename.lower().endswith(".building.gml")]
        if len(files) != 1 or files[0].file_size > 400 * 1024 * 1024:
            raise ValueError("Missing, duplicated or oversized building GML")
        with zf.open(files[0]) as stream:
            if b"<!DOCTYPE" in stream.read(16384).upper():
                raise ValueError("DTD not permitted")
            stream.seek(0)
            events = ET.iterparse(stream, events=("start", "end"))
            _, root = next(events)
            for event, element in events:
                if (
                    event == "end"
                    and element.tag == "{http://www.opengis.net/gml/3.2}featureMember"
                ):
                    candidates = [c for c in element if c.tag.endswith("}Building")]
                    if len(candidates) != 1:
                        raise ValueError("Expected one Building per featureMember")
                    row = record(candidates[0], snapshot, cat, ine)
                    if row["refcat"] in seen:
                        raise ValueError("Duplicate cadastral parcel record")
                    seen.add(row["refcat"])
                    rows.append(row)
                    root.remove(element)
    if not rows:
        raise ValueError("No building records")
    return rows


def raw_pins(mapping: list[dict]) -> dict:
    pins = manifest.load()["sha256"]
    expected = {}
    rels = [str(PROVINCE_FEED.relative_to(ROOT))]
    rels += [str(paths(m["cat"])["zip"].relative_to(ROOT)) for m in mapping]
    for rel in rels:
        if rel not in pins:
            raise ValueError(f"Unpinned input {rel}; run fetch_cadastre_province.py")
        expected[rel] = pins[rel]
    missing, changed = manifest.check(expected)
    if missing or changed:
        raise ValueError(f"Province inputs missing={missing}, changed={changed}")
    return expected


def metadata(pins: dict, mapping: list[dict]) -> dict:
    import json

    return {
        "input_sha": json.dumps(pins, sort_keys=True),
        "municipalities": json.dumps(
            [{"ine": m["ine"], "cat": m["cat"], "updated": m["updated"]} for m in mapping],
            sort_keys=True,
        ),
        "script_sha": manifest.sha256(Path(__file__)),
        "parser_sha": manifest.sha256(Path(cap.__file__)),
        "geometry_sha": manifest.sha256(Path(geom.__file__)),
        "geometry_engine": geom.ENGINE_VERSION,
    }


def build_offline(mapping: list[dict]) -> dict:
    pins = raw_pins(mapping)
    tables = []
    for m in mapping:
        p = paths(m["cat"])
        rows = parse_archive(p["zip"], m["updated"], m["cat"], m["ine"])
        table = pa.Table.from_pylist(rows, schema=cap.sev.SCHEMA)
        p["parquet"].parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, p["parquet"])
        tables.append(table)
        print(f"province: {m['ine']} {m['ine_name']}: {len(rows)} records")
    global NORMALIZED_REFCATS
    print(f"province: case-normalized parcel references: {NORMALIZED_REFCATS}")
    combined = pa.concat_tables(tables)
    municipios = pa.Table.from_pylist(
        [
            {"cat_municipality": m["cat"], "ine_municipality": m["ine"], "municipio": m["ine_name"]}
            for m in mapping
        ]
    )
    tmp = DATABASE.with_suffix(".tmp.duckdb")
    with duckdb.connect(str(tmp)) as con:
        con.register("input_buildings", combined)
        con.execute("create or replace table buildings as select * from input_buildings")
        con.register("input_municipios", municipios)
        con.execute("create or replace table municipios as select * from input_municipios")
        con.execute("create or replace table stock_meta (key varchar, value varchar)")
        con.executemany(
            "insert into stock_meta values (?, ?)", list(metadata(pins, mapping).items())
        )
    tmp.replace(DATABASE)
    for m in mapping:
        manifest.record(
            str(paths(m["cat"])["parquet"].relative_to(ROOT)),
            {
                "publisher": "DGC INSPIRE",
                "accessed": date.today().isoformat(),
                "note": "Sevilla-province BU pilot, municipal grain",
            },
        )
    manifest.record(
        str(DATABASE.relative_to(ROOT)),
        {
            "publisher": "DGC INSPIRE",
            "accessed": date.today().isoformat(),
            "note": "Sevilla-province BU pilot, municipal grain",
        },
    )
    return metadata(pins, mapping)


def verify():
    mapping = municipality_map()
    pins = raw_pins(mapping)
    if not DATABASE.is_file():
        raise ValueError("Missing province sidecar; run fetch_cadastre_province.py --offline")
    for m in mapping:
        if not paths(m["cat"])["parquet"].is_file():
            raise ValueError(
                f"Missing {m['ine']} parquet; run fetch_cadastre_province.py --offline"
            )
    recorded = manifest.load()["sha256"]
    output_pins = {
        str(p.relative_to(ROOT)): recorded.get(str(p.relative_to(ROOT)), "")
        for p in [paths(m["cat"])["parquet"] for m in mapping] + [DATABASE]
    }
    missing, changed = manifest.check(output_pins)
    if missing or changed:
        raise ValueError(f"Province outputs missing={missing}, changed={changed}")
    expected = metadata(pins, mapping)
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        actual_meta = dict(con.execute("select key, value from stock_meta").fetchall())
        if actual_meta != expected:
            raise ValueError("Province derivation stale vs input/code; rebuild with --offline")
        n = con.execute("select count(*), sum(dwelling_properties) from buildings").fetchone()
    print(f"province: {n[0]} building/parcel records, {n[1]} properties; pins verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mapping = municipality_map()
    print(f"province: validated CAT->INE map for {len(mapping)} municipalities")
    if args.check:
        verify()
        return
    if not args.offline:
        for m in mapping:
            cap.sev.download(m["url"], paths(m["cat"])["zip"])
    build_offline(mapping)
    verify()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        raise SystemExit(f"province: {error}") from error
