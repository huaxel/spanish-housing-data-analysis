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
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import manifest  # noqa: E402
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


def record(element, snapshot: str, cat: str, ine: str) -> dict:
    """Same record semantics as the Sevilla pilot, without a barrio join."""
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
                    candidates = [child for child in element if child.tag.endswith("}Building")]
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


def raw_pins() -> dict:
    pins = manifest.load()["sha256"]
    expected = {}
    for slug, _cat, _ine, _name, _prov in CITIES:
        for key in ("zip", "feed"):
            rel = str(paths(slug)[key].relative_to(ROOT))
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
    for slug, cat, ine, name, _prov in CITIES:
        p = paths(slug)
        snapshots[slug] = snapshot_for(p["feed"], f"{cat}-{name} buildings")
        rows = parse_archive(p["zip"], snapshots[slug], cat, ine)
        tables[slug] = pa.Table.from_pylist(rows, schema=sev.SCHEMA)
        p["parquet"].parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(tables[slug], p["parquet"])
    combined = pa.concat_tables([tables[s] for s, _, _, _, _ in CITIES])
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
                "note": "Andalusian-capital BU pilot, municipal grain; see cadastre_capitals.md",
            },
        )
    manifest.record(
        str(DATABASE.relative_to(ROOT)),
        {
            "publisher": "DGC INSPIRE",
            "accessed": date.today().isoformat(),
            "note": "Andalusian-capital BU pilot, municipal grain; see cadastre_capitals.md",
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
    build_offline()
    verify()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        raise SystemExit(f"capitals: {error}") from error
