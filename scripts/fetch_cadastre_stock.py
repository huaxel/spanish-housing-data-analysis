"""Sevilla INSPIRE BU physical-stock pilot, separate from central housing marts.

CAT municipality 41900 corresponds to INE 41091. BU records group the
constructions of a cadastral parcel. Dwelling counts are cadastral housing
properties, not observed occupancy. Footprint-component interior-point joins
are conservative and expose ambiguous, crossing and outside records explicitly.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import manifest  # noqa: E402
from spanish_housing import stock_geometry as geom
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

ZIP_URL = (
    "https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/41/41900-SEVILLA/A.ES.SDGC.BU.41900.zip"
)
FEED_URL = "https://www.catastro.hacienda.gob.es/INSPIRE/buildings/41/ES.SDGC.bu.atom_41.xml"
BAR_URL = (
    "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/"
    "Evolución_reciente_de_población_residente/FeatureServer/26/query"
)
ARCHIVE = RAW / "cadastre_sevilla_buildings.zip"
FEED = RAW / "cadastre_sevilla_feed.xml"
PROJECTED = RAW / "sevilla_barrios_25830.geojson"
MAP_INPUT = RAW / "sevilla_barrios_4326.geojson"
CONTEXT = RAW / "sevilla_sim_poblacion.json"
PARQUET = RAW / "parquet" / "cadastre_sevilla_buildings.parquet"
DATABASE = PROCESSED / "stock.duckdb"
MAP = ROOT / "evidence/static/geo/sevilla_barrios.geojson"
INPUTS = [ARCHIVE, FEED, PROJECTED, MAP_INPUT, CONTEXT]
SCHEMA = pa.schema(
    [
        ("refcat", pa.string()),
        ("cat_municipality", pa.string()),
        ("ine_municipality", pa.string()),
        ("snapshot_date", pa.string()),
        ("current_use", pa.string()),
        ("condition", pa.string()),
        ("date_start_raw", pa.string()),
        ("date_end_raw", pa.string()),
        ("date_quality", pa.string()),
        ("year_start", pa.int64()),
        ("year_end", pa.int64()),
        ("dwelling_properties", pa.int64()),
        ("building_units", pa.int64()),
        ("gross_floor_m2", pa.float64()),
        ("footprint_m2", pa.float64()),
        ("centroid_x", pa.float64()),
        ("centroid_y", pa.float64()),
        ("barrio_id", pa.string()),
        ("match_status", pa.string()),
    ]
)


def download(url, path, limit=100 * 1024 * 1024):
    url = urllib.parse.quote(url, safe=":/?=&%+")
    req = urllib.request.Request(url, headers={"User-Agent": "housing-data-analysis/1.0"})
    with urllib.request.urlopen(req, timeout=180) as response:  # noqa: S310
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Download exceeds size bound: {path.name}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    manifest.record(
        str(path.relative_to(ROOT)),
        {
            "url": url,
            "publisher": "DGC INSPIRE" if "catastro" in url else "Ayuntamiento/EMVISESA SIM",
            "accessed": date.today().isoformat(),
            "note": "Sevilla physical-stock pilot; no protected ownership data",
        },
    )


def raw_pins():
    pins = manifest.load()["sha256"]
    expected = {}
    for path in INPUTS:
        rel = str(path.relative_to(ROOT))
        if rel not in pins:
            raise ValueError(f"Unpinned input {rel}; run fetch_cadastre_stock.py")
        expected[rel] = pins[rel]
    missing, changed = manifest.check(expected)
    if missing or changed:
        raise ValueError(f"Stock inputs missing={missing}, changed={changed}")
    return expected


def snapshot_date():
    root = ET.fromstring(FEED.read_bytes())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = [
        e
        for e in root.findall("a:entry", ns)
        if (e.findtext("a:title", namespaces=ns) or "").strip() == "41900-SEVILLA buildings"
    ]
    if len(entries) != 1:
        raise ValueError(
            "Expected exact Sevilla cadastral entry, not INE code or Cuervo de Sevilla"
        )
    links = [link.get("href") for link in entries[0].findall("a:link", ns)]
    if ZIP_URL not in links:
        raise ValueError("Sevilla archive URL changed")
    return date.fromisoformat(entries[0].findtext("a:updated", namespaces=ns)[:10]).isoformat()


def neighbourhoods():
    projected = json.loads(PROJECTED.read_text())
    map_payload = json.loads(MAP_INPUT.read_text())
    for payload, epsg in [(projected, "EPSG:25830"), (map_payload, "EPSG:4326")]:
        if payload.get("crs", {}).get("properties", {}).get("name") != epsg:
            raise ValueError(f"Unexpected barrio coordinate system, expected {epsg}")
        if len(payload.get("features", [])) != 108:
            raise ValueError("Expected complete SIM barrio coverage")
    context = json.loads(CONTEXT.read_text())
    context_rows = [feature["attributes"] for feature in context["query"]["features"]]
    keys = ["IDG", "ID_DIS", "DIS", "ID_BAR", "BAR"]

    def geography(rows):
        return {str(row["IDG"]): tuple(str(row[key]) for key in keys) for row in rows}

    expected = geography(context_rows)
    if (
        len(context_rows) != 108
        or len(expected) != 108
        or geography([f["properties"] for f in projected["features"]]) != expected
        or geography([f["properties"] for f in map_payload["features"]]) != expected
    ):
        raise ValueError("Stock polygon keys/labels differ from pinned SIM household context")
    mapped = {str(f["properties"]["IDG"]): f for f in map_payload["features"]}
    items, valid_features = [], []
    for feature in projected["features"]:
        properties = feature["properties"]
        identifier = str(properties["IDG"])
        map_feature = mapped[identifier]
        raw_polygons = geom.raw_geojson_polygons(feature["geometry"])
        raw_map_polygons = geom.raw_geojson_polygons(map_feature["geometry"])
        for polygons in [raw_polygons, raw_map_polygons]:
            for polygon in polygons:
                for ring in polygon:
                    geom.validate_ring(ring)
        box = geom.bbox(raw_polygons)
        map_box = geom.bbox(raw_map_polygons)
        if not (100000 < box[0] < box[2] < 500000 and 4000000 < box[1] < box[3] < 4300000):
            raise ValueError("Barrio coordinates do not match the Sevilla metric CRS")
        if not (-7 < map_box[0] < map_box[2] < -5 and 36 < map_box[1] < map_box[3] < 38):
            raise ValueError("Map coordinates do not match Sevilla longitude/latitude")
        area = component_area = overlap = None
        polygons = []
        quality, note = "invalid_topology", ""
        try:
            normalized, component_area, area = geom.dissolve_source_geojson(feature["geometry"])
            normalized_map, _, _ = geom.dissolve_source_geojson(map_feature["geometry"])
            polygons = geom.geojson_polygons(normalized)
            geom.geojson_polygons(normalized_map)
            overlap = component_area - area
            if abs(overlap) < 1e-6:
                overlap = 0.0
            quality = "overlapping_components_dissolved" if overlap > 0 else "valid"
            valid_features.append({**map_feature, "geometry": normalized_map})
        except geom.InvalidTopology as error:
            # Explicit quarantine of the whole barrio, not a repaired or partial polygon.
            area = component_area = overlap = None
            polygons = []
            note = str(error)
        items.append(
            {
                "idg": identifier,
                "barrio": properties["BAR"],
                "distrito": properties["DIS"],
                "area_km2": area / 1e6 if area is not None else None,
                "source_component_area_km2": component_area / 1e6
                if component_area is not None
                else None,
                "source_overlap_m2": overlap,
                "geometry_quality": quality,
                "geometry_note": note,
                "polygons": polygons,
                "bbox": box,
            }
        )
    return items, {"type": "FeatureCollection", "features": valid_features}


def text(element, path):
    found = element.find(path)
    if found is None or found.get("{http://www.w3.org/2001/XMLSchema-instance}nil") == "true":
        return None
    return found.text.strip() if found.text and found.text.strip() else None


def count_value(value):
    if value is None:
        return None
    number = int(value)
    if number < 0:
        raise ValueError("Negative cadastral count")
    return number


def construction_year(value):
    if value is None or value == "--01-01T00:00:00":
        return None, "missing"
    pattern = (
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
        r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)?"
    )
    if not re.fullmatch(pattern, value):
        return None, "invalid"
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return None, "invalid"
    offset = timestamp.utcoffset()
    if timestamp.year > 2100 or (offset is not None and abs(offset.total_seconds()) > 14 * 3600):
        return None, "invalid"
    return timestamp.year, "valid"


GML = "{http://www.opengis.net/gml/3.2}"
NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"


def nil_geometry(element):
    if element.get(NIL) == "true":
        if len(element) or (element.text and element.text.strip()):
            raise ValueError("Nil geometry has content")
        return True
    return False


def building_polygons(element):
    """Consume the entire supported DGC footprint profile, never a subset."""
    properties = element.findall("{*}geometry")
    polygons, missing = [], False
    for prop in properties:
        if nil_geometry(prop):
            missing = True
            continue
        wrappers = list(prop)
        if len(wrappers) != 1 or wrappers[0].tag.rsplit("}", 1)[-1] != "BuildingGeometry":
            raise ValueError("Unsupported building geometry wrapper")
        wrapper = wrappers[0]
        allowed = {
            "geometry",
            "horizontalGeometryEstimatedAccuracy",
            "horizontalGeometryReference",
            "referenceGeometry",
        }
        if any(child.tag.rsplit("}", 1)[-1] not in allowed for child in wrapper):
            raise ValueError("Unsupported BuildingGeometry component")
        references = wrapper.findall("{*}horizontalGeometryReference")
        geometries = wrapper.findall("{*}geometry")
        if len(geometries) != 1:
            raise ValueError("Expected one complete footprint geometry property")
        geometry = geometries[0]
        if nil_geometry(geometry):
            missing = True
            continue
        if len(references) != 1 or (references[0].text or "").strip().lower() != "footprint":
            raise ValueError("Building horizontal geometry reference is not footprint")
        surfaces = list(geometry)
        if not surfaces or any(surface.tag != GML + "Surface" for surface in surfaces):
            raise ValueError("Unsupported building geometry type")
        for surface in surfaces:
            if surface.get("srsName") != "urn:ogc:def:crs:EPSG::25830":
                raise ValueError("Building geometry is not EPSG:25830")
            patches_properties = list(surface)
            if len(patches_properties) != 1 or patches_properties[0].tag != GML + "patches":
                raise ValueError("Unsupported Surface component")
            patches = list(patches_properties[0])
            if not patches or any(patch.tag != GML + "PolygonPatch" for patch in patches):
                raise ValueError("Unsupported or empty Surface patches")
            for patch in patches:
                boundaries = list(patch)
                exteriors = [
                    boundary for boundary in boundaries if boundary.tag == GML + "exterior"
                ]
                interiors = [
                    boundary for boundary in boundaries if boundary.tag == GML + "interior"
                ]
                if len(exteriors) != 1 or len(exteriors) + len(interiors) != len(boundaries):
                    raise ValueError("Unsupported PolygonPatch boundary")
                rings = []
                for boundary in exteriors + interiors:
                    ring_elements = list(boundary)
                    if len(ring_elements) != 1 or ring_elements[0].tag != GML + "LinearRing":
                        raise ValueError("Unsupported polygon ring")
                    positions_elements = list(ring_elements[0])
                    if len(positions_elements) != 1 or positions_elements[0].tag != GML + "posList":
                        raise ValueError("Unsupported ring coordinate representation")
                    positions = positions_elements[0]
                    if positions.get("srsDimension", "2") != "2":
                        raise ValueError("Expected 2D building footprint")
                    coordinates = [float(v) for v in (positions.text or "").split()]
                    if len(coordinates) % 2:
                        raise ValueError("Odd coordinate count")
                    ring = [
                        [coordinates[i], coordinates[i + 1]] for i in range(0, len(coordinates), 2)
                    ]
                    if positions.get("count") is not None and int(positions.get("count")) != len(
                        ring
                    ):
                        raise ValueError("Coordinate count differs from GML declaration")
                    geom.validate_ring(ring)
                    rings.append(ring)
                polygons.append(rings)
    if missing and polygons:
        raise ValueError("Incomplete footprint geometry; cannot publish a supported subset")
    return polygons


def building(element, snapshot, barrios):
    refcat = text(element, ".//{*}localId")
    if not refcat or not re.fullmatch(r"[A-Z0-9]{14}", refcat):
        raise ValueError("Invalid cadastral parcel reference")
    gml_id = element.get("{http://www.opengis.net/gml/3.2}id")
    if gml_id != "ES.SDGC.BU." + refcat:
        raise ValueError("Building ID and cadastral reference disagree")
    start_raw = text(element, "{*}dateOfConstruction/{*}DateOfEvent/{*}beginning")
    end_raw = text(element, "{*}dateOfConstruction/{*}DateOfEvent/{*}end")
    start, start_quality = construction_year(start_raw)
    end, end_quality = construction_year(end_raw)
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
    floor_text = text(element, "{*}officialArea/{*}OfficialArea/{*}value")
    floor = float(floor_text) if floor_text is not None else None
    if floor is not None:
        value = element.find("{*}officialArea/{*}OfficialArea/{*}value")
        reference = text(element, "{*}officialArea/{*}OfficialArea/{*}officialAreaReference")
        if (
            reference != "grossFloorArea"
            or value.get("uom") != "m2"
            or not math.isfinite(floor)
            or floor < 0
        ):
            raise ValueError("Unexpected cadastral area definition/unit/value")
    polygons = building_polygons(element)
    area = cx = cy = barrio_id = None
    status = "missing_geometry"
    if polygons:
        area, (cx, cy) = geom.polygon_measure(polygons)
        barrio_id, status = geom.footprint_match(polygons, barrios)
    return {
        "refcat": refcat,
        "cat_municipality": "41900",
        "ine_municipality": "41091",
        "snapshot_date": snapshot,
        "current_use": text(element, "{*}currentUse"),
        "condition": text(element, "{*}conditionOfConstruction"),
        "date_start_raw": start_raw,
        "date_end_raw": end_raw,
        "date_quality": quality,
        "year_start": start,
        "year_end": end,
        "dwelling_properties": count_value(text(element, "{*}numberOfDwellings")),
        "building_units": count_value(text(element, "{*}numberOfBuildingUnits")),
        "gross_floor_m2": floor,
        "footprint_m2": area,
        "centroid_x": cx,
        "centroid_y": cy,
        "barrio_id": barrio_id,
        "match_status": status,
    }


def parse_archive(snapshot, barrios):
    rows, seen = [], set()
    with zipfile.ZipFile(ARCHIVE) as archive:
        files = [f for f in archive.infolist() if f.filename.lower().endswith(".building.gml")]
        if len(files) != 1 or files[0].file_size > 400 * 1024 * 1024:
            raise ValueError("Missing, duplicated or oversized building GML")
        with archive.open(files[0]) as stream:
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
                    candidates = [child for child in element if child.tag.endswith("}Building")]
                    if len(candidates) != 1:
                        raise ValueError("Expected one Building per featureMember")
                    row = building(candidates[0], snapshot, barrios)
                    if row["refcat"] in seen:
                        raise ValueError("Duplicate cadastral parcel record")
                    seen.add(row["refcat"])
                    rows.append(row)
                    root.remove(element)
    if not rows:
        raise ValueError("No building records")
    return rows


def metadata(pins, snapshot):
    return {
        "input_sha": json.dumps(pins, sort_keys=True),
        "snapshot_date": snapshot,
        "script_sha": manifest.sha256(Path(__file__)),
        "geometry_sha": manifest.sha256(Path(geom.__file__)),
        "geometry_engine": geom.ENGINE_VERSION,
    }


def verify():
    pins = raw_pins()
    expected = metadata(pins, snapshot_date())
    if not DATABASE.is_file() or not PARQUET.is_file() or not MAP.is_file():
        raise ValueError("Missing stock sidecar or map; run fetch_cadastre_stock.py --offline")
    recorded = manifest.load()["sha256"]
    output_pins = {
        str(p.relative_to(ROOT)): recorded.get(str(p.relative_to(ROOT)), "")
        for p in [PARQUET, DATABASE, MAP]
    }
    missing, changed = manifest.check(output_pins)
    if missing or changed:
        raise ValueError(f"Stock outputs missing={missing}, changed={changed}")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        actual_meta = dict(con.execute("select key, value from stock_meta").fetchall())
        if actual_meta != expected:
            raise ValueError("Stock derivation stale vs input/code; rebuild with --offline")
        rows = con.execute("select * from buildings order by refcat").to_arrow_table().to_pylist()
    raw_rows = sorted(pq.read_table(PARQUET).to_pylist(), key=lambda r: r["refcat"])
    if rows != raw_rows:
        raise ValueError("Stock parquet and database differ")
    print(f"stock: {len(rows)} building/parcel records; pins and derivation metadata verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        verify()
        return
    if not args.offline:
        download(FEED_URL, FEED, 10 * 1024 * 1024)
        snapshot_date()  # fail on feed mismatch before requesting the large archive
        download(ZIP_URL, ARCHIVE)
        for sr, path in [(25830, PROJECTED), (4326, MAP_INPUT)]:
            params = urllib.parse.urlencode(
                {
                    "where": "1=1",
                    "outFields": "IDG,ID_DIS,DIS,ID_BAR,BAR",
                    "returnGeometry": "true",
                    "outSR": sr,
                    "f": "geojson",
                }
            )
            download(BAR_URL + "?" + params, path, 10 * 1024 * 1024)
    pins = raw_pins()
    snapshot = snapshot_date()
    barrios, mapping = neighbourhoods()
    rows = parse_archive(snapshot, barrios)
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, PARQUET)
    map_copy = {"type": "FeatureCollection", "features": mapping["features"]}
    MAP.write_text(json.dumps(map_copy, ensure_ascii=False, separators=(",", ":")) + "\n")
    tmp = DATABASE.with_suffix(".tmp.duckdb")
    with duckdb.connect(str(tmp)) as con:
        con.register("input_buildings", table)
        con.execute("create or replace table buildings as select * from input_buildings")
        base = [
            {
                k: item[k]
                for k in [
                    "idg",
                    "barrio",
                    "distrito",
                    "area_km2",
                    "source_component_area_km2",
                    "source_overlap_m2",
                    "geometry_quality",
                    "geometry_note",
                ]
            }
            for item in barrios
        ]
        con.register("input_barrios", pa.Table.from_pylist(base))
        con.execute("create or replace table barrios as select * from input_barrios")
        con.execute("create or replace table stock_meta (key varchar, value varchar)")
        con.executemany(
            "insert into stock_meta values (?, ?)", list(metadata(pins, snapshot).items())
        )
    tmp.replace(DATABASE)
    for path in [PARQUET, DATABASE, MAP]:
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "publisher": "DGC INSPIRE + Ayuntamiento/EMVISESA SIM",
                "accessed": date.today().isoformat(),
                "note": (
                    "Physical-stock pilot; all-component interior-point joins; "
                    "see cadastre_stock.md"
                ),
            },
        )
    verify()
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        print(
            con.execute(
                "select match_status,count(*),sum(dwelling_properties) from buildings "
                "group by match_status order by match_status"
            ).fetchall()
        )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        raise SystemExit(f"stock: {error}") from error
