"""Andalusian-capital INSPIRE BU pilot: municipal-grain physical stock.

Fetches the DGC INSPIRE Buildings archives for Malaga, Granada and Cordoba
capitals (CAT codes 29900/18900/14900), parses the same GML record format as
the Sevilla pilot (scripts/fetch_cadastre_stock.py, whose record helpers are
reused verbatim) and writes data/processed/stock_capitals.duckdb.

Municipal grain only: no barrio/district geometry layer is attempted for
these cities, so barrio_id is NULL and match_status is "municipal_only"
(the footprint area and centroid are still measured). A per-city barrio join
needs official local geometries and is tracked separately.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import (  # noqa: E402
    datum,
    manifest,
    shapefile,
)
from spanish_housing import stock_geometry as geom  # noqa: E402


def _load_sevilla():
    import importlib.util

    path = Path(__file__).resolve().parent / "fetch_cadastre_stock.py"
    spec = importlib.util.spec_from_file_location("fetch_cadastre_stock", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sev = _load_sevilla()

from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

CITIES = [
    # (slug, CAT code, INE code, display name, province code)
    ("malaga", "29900", "29067", "MALAGA", "29"),
    ("granada", "18900", "18087", "GRANADA", "18"),
    ("cordoba", "14900", "14021", "CORDOBA", "14"),
]

DATABASE = PROCESSED / "stock_capitals.duckdb"
MLG_BARRIOS = RAW / "cadastre_malaga_barrios_25830.geojson"
MLG_BARRIOS_URL = (
    "https://datosabiertos.malaga.eu/recursos/urbanismoEInfraestructura/"
    "planimetria/callejero/da_cartografiaBarrio-25830.geojson"
)
GRA_DISTRITOS_URL = (
    "https://opendata.granada.org/dataset/cf4dab5c-6e37-4cb2-996f-d72576e71f14/"
    "resource/e3487eb6-2543-4165-8252-3fa00597579a/download/"
    "101_distritos_municipales_20230101.zip"
)
GRA_DISTRITOS = RAW / "cadastre_granada_distritos_20230101.zip"


def paths(slug: str) -> dict[str, Path]:
    return {
        "zip": RAW / f"cadastre_{slug}_buildings.zip",
        "feed": RAW / f"cadastre_{slug}_feed.xml",
        "parquet": RAW / "parquet" / f"cadastre_{slug}_buildings.parquet",
    }


def zip_url(cat: str, name: str, province: str) -> str:
    return (
        "https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/"
        f"{province}/{cat}-{name}/A.ES.SDGC.BU.{cat}.zip"
    )


def feed_url(province: str) -> str:
    return (
        "https://www.catastro.hacienda.gob.es/INSPIRE/buildings/"
        f"{province}/ES.SDGC.bu.atom_{province}.xml"
    )


def snapshot_for(feed: Path, title: str) -> str:
    root = ET.fromstring(feed.read_bytes())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("a:entry", ns):
        if (entry.findtext("a:title", namespaces=ns) or "").strip() == title:
            updated = entry.findtext("a:updated", namespaces=ns)
            if not updated:
                raise ValueError(f"No updated timestamp for {title}")
            return updated[:10]
    raise ValueError(f"Feed entry missing: {title}")


def record(element, snapshot: str, cat: str, ine: str, barrios=()) -> dict:
    """Sevilla record semantics; barrio join only where polygons are given."""
    row = sev.building(element, snapshot, list(barrios))
    row["cat_municipality"] = cat
    row["ine_municipality"] = ine
    if not barrios:
        row["barrio_id"] = None
        row["match_status"] = "municipal_only"
    return row


def parse_archive(archive: Path, snapshot: str, cat: str, ine: str, barrios=()) -> list[dict]:
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
                    candidates = [child for child in element if child.tag.endswith("}Building")]
                    if len(candidates) != 1:
                        raise ValueError("Expected one Building per featureMember")
                    row = record(candidates[0], snapshot, cat, ine, barrios)
                    if row["refcat"] in seen:
                        raise ValueError("Duplicate cadastral parcel record")
                    seen.add(row["refcat"])
                    rows.append(row)
                    root.remove(element)
    if not rows:
        raise ValueError("No building records")
    return rows


def strip_z(geometry: dict) -> dict:
    """Drop near-zero Z ordinates from the Malaga 25830 polygons.

    Every ordinate must be 2D or carry |z| < 1 cm (observed max 0.2 mm,
    elevation noise); anything larger fails rather than being silently
    flattened, since Z could otherwise hide a genuinely 3D dataset.
    """

    def walk(coords):
        if isinstance(coords, list) and coords and isinstance(coords[0], (int, float)):
            if len(coords) > 2:
                if any(abs(v) >= 0.01 for v in coords[2:]):
                    raise ValueError("Non-negligible Z ordinate in Malaga barrio geometry")
                return coords[:2]
            return coords
        return [walk(part) for part in coords]

    return {**geometry, "coordinates": walk(geometry["coordinates"])}


def malaga_barrios() -> list[dict]:
    """Load and validate the official Malaga barrio polygons (EPSG:25830)."""
    payload = json.loads(MLG_BARRIOS.read_bytes())
    if payload.get("crs", {}).get("properties", {}).get("name") != "urn:ogc:def:crs:EPSG::25830":
        raise ValueError("Unexpected Malaga barrio coordinate system, expected EPSG:25830")
    features = payload.get("features", [])
    if len(features) != 419:
        raise ValueError("Expected 419 official Malaga barrios")
    numbers = [f["properties"]["NUMBARRIO"] for f in features]
    names = [str(f["properties"]["NOMBARRIO"]).strip() for f in features]
    if len(set(numbers)) != 419 or len(set(names)) != 419:
        raise ValueError("Malaga barrio keys or names are not unique")
    items = []
    for feature, number, name in zip(features, numbers, names, strict=True):
        geometry = strip_z(feature["geometry"])
        raw = geom.raw_geojson_polygons(geometry)
        for polygon in raw:
            for ring in polygon:
                geom.validate_ring(ring)
        box = geom.bbox(raw)
        if not (355000 < box[0] < box[2] < 390000 and 4050000 < box[1] < box[3] < 4085000):
            raise ValueError("Malaga barrio coordinates do not match the metric CRS")
        area = component_area = overlap = None
        polygons = []
        quality, note = "invalid_topology", ""
        try:
            normalized, component_area, area = geom.dissolve_source_geojson(geometry)
            polygons = geom.geojson_polygons(normalized)
            overlap = component_area - area
            if abs(overlap) < 1e-6:
                overlap = 0.0
            quality = "overlapping_components_dissolved" if overlap > 0 else "valid"
        except geom.InvalidTopology as error:
            note = str(error)
        items.append(
            {
                "idg": f"29067-{number}",
                "barrio": name,
                "distrito": None,
                "area_km2": area / 1e6 if area is not None else None,
                "source_overlap_m2": overlap,
                "geometry_quality": quality,
                "geometry_note": note,
                "polygons": polygons,
                "bbox": box,
            }
        )
    return items


def granada_districts() -> list[dict]:
    """Load Granada districts from the vendored SHP, reprojected to ETRS89.

    The layer is published in ED50/UTM zone 30N (.prj asserts it); every
    ordinate is transformed to ETRS89/UTM 30N via EPSG:1632 (~1.5 m) before
    any join, so no ED50 numbers ever enter the metric pipeline.
    """
    import zipfile

    with zipfile.ZipFile(GRA_DISTRITOS) as zf:
        names = zf.namelist()
        base = "101_Distritos_Municipales_20230101"
        prj = [n for n in names if n == base + ".prj"]
        if len(prj) != 1:
            raise ValueError("Expected one Granada district .prj")
        wkt = zf.read(prj[0]).decode("utf-8", "replace")
        if "ED_1950" not in wkt or "UTM_Zone_30N" not in wkt:
            raise ValueError("Granada districts are not ED50/UTM zone 30N")
        tmpdir = RAW / "tmp_gra_distritos"
        tmpdir.mkdir(exist_ok=True)
        for suffix in (".shp", ".shx", ".dbf"):
            (tmpdir / (base + suffix)).write_bytes(zf.read(base + suffix))
    pairs = shapefile.read_shapes(tmpdir / base)
    names_seen = [attrs["DISTRITO"].strip() for attrs, _parts in pairs]
    if len(pairs) != 8 or len(set(names_seen)) != 8:
        raise ValueError("Expected 8 uniquely named Granada districts")
    items = []
    for attrs, parts in pairs:
        name = attrs["DISTRITO"].strip()
        rings = []
        for ring in parts:
            rings.append([list(datum.ed50_utm30_to_etrs89_utm30(x, y)) for x, y in ring])
        polys = [[ring] for ring in rings]
        for poly in polys:
            for ring in poly:
                geom.validate_ring([list(p) for p in ring])
        box = geom.bbox(polys)
        if not (435000 < box[0] < box[2] < 460000 and 4105000 < box[1] < box[3] < 4125000):
            raise ValueError("Granada district coordinates out of expected range")
        area = component_area = overlap = None
        polygons = []
        quality, note = "invalid_topology", ""
        try:
            normalized, component_area, area = geom.dissolve_source_geojson(
                {"type": "MultiPolygon", "coordinates": polys}
            )
            polygons = geom.geojson_polygons(normalized)
            overlap = component_area - area
            if abs(overlap) < 1e-6:
                overlap = 0.0
            quality = "overlapping_components_dissolved" if overlap > 0 else "valid"
        except geom.InvalidTopology as error:
            note = str(error)
        items.append(
            {
                "idg": f"18087-{name}",
                "barrio": name,
                "distrito": name,
                "area_km2": area / 1e6 if area is not None else None,
                "source_overlap_m2": overlap,
                "geometry_quality": quality,
                "geometry_note": note,
                "polygons": polygons,
                "bbox": box,
            }
        )
    return items


def raw_pins() -> dict:
    pins = manifest.load()["sha256"]
    expected = {}
    rels = [str(MLG_BARRIOS.relative_to(ROOT)), str(GRA_DISTRITOS.relative_to(ROOT))]
    for slug, _cat, _ine, _name, _prov in CITIES:
        for key in ("zip", "feed"):
            rels.append(str(paths(slug)[key].relative_to(ROOT)))
    for rel in rels:
        if rel not in pins:
            raise ValueError(f"Unpinned input {rel}; run fetch_cadastre_capitals.py")
        expected[rel] = pins[rel]
    missing, changed = manifest.check(expected)
    if missing or changed:
        raise ValueError(f"Capital inputs missing={missing}, changed={changed}")
    return expected


def metadata(pins: dict, snapshots: dict) -> dict:
    return {
        "input_sha": json_dumps(pins),
        "snapshots": json_dumps(snapshots),
        "script_sha": manifest.sha256(Path(__file__)),
        "barrios_sha": manifest.sha256(MLG_BARRIOS),
        "distritos_sha": manifest.sha256(GRA_DISTRITOS),
        "datum_sha": manifest.sha256(Path(datum.__file__)),
        "shapefile_sha": manifest.sha256(Path(shapefile.__file__)),
        "parser_sha": manifest.sha256(Path(sev.__file__)),
        "geometry_sha": manifest.sha256(Path(geom.__file__)),
        "geometry_engine": geom.ENGINE_VERSION,
    }


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj, sort_keys=True)


def build_offline() -> dict:
    pins = raw_pins()
    snapshots, tables = {}, {}
    barrios_malaga = malaga_barrios()
    barrios_granada = granada_districts()
    for slug, cat, ine, name, _prov in CITIES:
        p = paths(slug)
        snapshots[slug] = snapshot_for(p["feed"], f"{cat}-{name} buildings")
        sub = barrios_malaga if slug == "malaga" else barrios_granada if slug == "granada" else ()
        rows = parse_archive(p["zip"], snapshots[slug], cat, ine, sub)
        tables[slug] = pa.Table.from_pylist(rows, schema=sev.SCHEMA)
        p["parquet"].parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(tables[slug], p["parquet"])
    combined = pa.concat_tables([tables[s] for s, _, _, _, _ in CITIES])
    barrios_table = pa.Table.from_pylist(
        [
            {k: item[k] for k in ["idg", "barrio", "distrito", "area_km2", "geometry_quality"]}
            | {"ine_municipality": "29067"}
            for item in barrios_malaga
        ]
        + [
            {k: item[k] for k in ["idg", "barrio", "distrito", "area_km2", "geometry_quality"]}
            | {"ine_municipality": "18087"}
            for item in barrios_granada
        ]
    )
    municipios = pa.Table.from_pylist(
        [
            {"cat_municipality": cat, "ine_municipality": ine, "municipio": name.title()}
            for _, cat, ine, name, _ in CITIES
        ]
    )
    tmp = DATABASE.with_suffix(".tmp.duckdb")
    with duckdb.connect(str(tmp)) as con:
        con.register("input_buildings", combined)
        con.execute("create or replace table buildings as select * from input_buildings")
        con.register("input_municipios", municipios)
        con.execute("create or replace table municipios as select * from input_municipios")
        con.register("input_barrios", barrios_table)
        con.execute("create or replace table barrios as select * from input_barrios")
        con.execute("create or replace table stock_meta (key varchar, value varchar)")
        con.executemany(
            "insert into stock_meta values (?, ?)", list(metadata(pins, snapshots).items())
        )
    tmp.replace(DATABASE)
    for slug, _cat, _ine, _name, _prov in CITIES:
        manifest.record(
            str(paths(slug)["parquet"].relative_to(ROOT)),
            {
                "publisher": "DGC INSPIRE",
                "accessed": date.today().isoformat(),
                "note": "Capital BU pilot; Malaga barrio join, rest municipal grain",
            },
        )
    manifest.record(
        str(DATABASE.relative_to(ROOT)),
        {
            "publisher": "DGC INSPIRE",
            "accessed": date.today().isoformat(),
            "note": "Capital BU pilot; Malaga barrio join, rest municipal grain",
        },
    )
    return metadata(pins, snapshots)


def verify():
    pins = raw_pins()
    if not DATABASE.is_file():
        raise ValueError("Missing capitals sidecar; run fetch_cadastre_capitals.py --offline")
    for slug, _cat, _ine, _name, _prov in CITIES:
        if not paths(slug)["parquet"].is_file():
            raise ValueError(f"Missing {slug} parquet; run fetch_cadastre_capitals.py --offline")
    recorded = manifest.load()["sha256"]
    output_pins = {
        str(p.relative_to(ROOT)): recorded.get(str(p.relative_to(ROOT)), "")
        for p in [paths(s)[key] for s, _, _, _, _ in CITIES for key in ("parquet",)] + [DATABASE]
    }
    missing, changed = manifest.check(output_pins)
    if missing or changed:
        raise ValueError(f"Capital outputs missing={missing}, changed={changed}")
    snapshots = {
        slug: snapshot_for(paths(slug)["feed"], f"{cat}-{name} buildings")
        for slug, cat, _ine, name, _prov in CITIES
    }
    expected = metadata(pins, snapshots)
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        actual_meta = dict(con.execute("select key, value from stock_meta").fetchall())
        if actual_meta != expected:
            raise ValueError("Capital derivation stale vs input/code; rebuild with --offline")
        rows = con.execute("select * from buildings order by refcat").to_arrow_table().to_pylist()
    raw_rows = []
    for slug, _cat, _ine, _name, _prov in CITIES:
        raw_rows.extend(pq.read_table(paths(slug)["parquet"]).to_pylist())
    raw_rows = sorted(raw_rows, key=lambda r: r["refcat"])
    if rows != raw_rows:
        raise ValueError("Capital parquet and database differ")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        print(
            con.execute(
                "select ine_municipality, count(*), sum(dwelling_properties) "
                "from buildings group by ine_municipality order by ine_municipality"
            ).fetchall()
        )
    print(f"capitals: {len(rows)} building/parcel records; pins and derivation verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        verify()
        return
    if not args.offline:
        for slug, cat, _ine, name, province in CITIES:
            p = paths(slug)
            sev.download(feed_url(province), p["feed"], 10 * 1024 * 1024)
            snapshot_for(p["feed"], f"{cat}-{name} buildings")
            sev.download(zip_url(cat, name, province), p["zip"])
        sev.download(
            MLG_BARRIOS_URL,
            MLG_BARRIOS,
            10 * 1024 * 1024,
        )
        sev.download(
            GRA_DISTRITOS_URL,
            GRA_DISTRITOS,
            10 * 1024 * 1024,
        )
        manifest.record(
            str(MLG_BARRIOS.relative_to(ROOT)),
            {
                "url": MLG_BARRIOS_URL,
                "publisher": "Ayuntamiento de Malaga (datosabiertos.malaga.eu)",
                "accessed": date.today().isoformat(),
                "note": "Official barrio polygons CC BY-SA 4.0; share-alike applies to derivatives",
            },
        )
        manifest.record(
            str(GRA_DISTRITOS.relative_to(ROOT)),
            {
                "url": GRA_DISTRITOS_URL,
                "publisher": "Ayuntamiento de Granada (opendata.granada.org)",
                "accessed": date.today().isoformat(),
                "note": "District polygons CC-BY, ED50/UTM30 reprojected via EPSG:1632",
            },
        )
    build_offline()
    verify()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        raise SystemExit(f"capitals: {error}") from error
