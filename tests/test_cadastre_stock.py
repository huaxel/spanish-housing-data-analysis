"""Offline physical-stock contracts, with no network or production-data dependency."""

import importlib.util
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import duckdb
import pyarrow as pa
import pytest

from spanish_housing import stock_geometry as geom

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "cadastre_stock", ROOT / "scripts/fetch_cadastre_stock.py"
)
stock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock)
PAGE = (ROOT / "evidence/pages/stock.md").read_text()
SQL = dict(re.findall(r"```sql (\w+)\n(.*?)\n```", PAGE, re.DOTALL))


def expand_sql(sql):
    for _ in range(20):
        updated = re.sub(r"\$\{(\w+)\}", lambda m: "(" + SQL[m[1]] + ")", sql)
        if updated == sql:
            return sql
        sql = updated
    raise AssertionError("Cyclic page query references")


def rectangle(x=0, y=0, width=10, height=10):
    return [[x, y], [x + width, y], [x + width, y + height], [x, y + height], [x, y]]


def neighbourhood(identifier, polygon):
    return {"idg": identifier, "polygons": [polygon], "bbox": geom.bbox([polygon])}


def element():
    return ET.fromstring("""
    <Building xmlns="urn:bu" xmlns:gml="http://www.opengis.net/gml/3.2"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      gml:id="ES.SDGC.BU.000200600TG33D">
      <inspireId><Identifier><localId>000200600TG33D</localId></Identifier></inspireId>
      <dateOfConstruction><DateOfEvent><beginning>1960-01-01T00:00:00</beginning>
        <end>2000-01-01T00:00:00</end></DateOfEvent></dateOfConstruction>
      <currentUse>4_2_retail</currentUse><conditionOfConstruction>functional</conditionOfConstruction>
      <numberOfDwellings>3</numberOfDwellings><numberOfBuildingUnits>5</numberOfBuildingUnits>
      <officialArea><OfficialArea><officialAreaReference>grossFloorArea</officialAreaReference>
        <value uom="m2">500</value></OfficialArea></officialArea>
      <geometry><BuildingGeometry><geometry>
        <gml:Surface srsName="urn:ogc:def:crs:EPSG::25830"><gml:patches><gml:PolygonPatch>
          <gml:exterior><gml:LinearRing><gml:posList srsDimension="2">
            0 0 10 0 10 10 0 10 0 0
          </gml:posList></gml:LinearRing></gml:exterior>
        </gml:PolygonPatch></gml:patches></gml:Surface>
      </geometry><horizontalGeometryReference>footPrint</horizontalGeometryReference>
      </BuildingGeometry></geometry>
    </Building>""")


def record():
    return stock.building(
        element(), "2026-08-21", [neighbourhood("A", [rectangle(-1, -1, 12, 12)])]
    )


def test_metric_area_centroid_holes_orientation_and_large_coordinates():
    exterior, hole = rectangle(), rectangle(4, 4, 2, 2)
    area, center = geom.polygon_measure([[exterior, hole]])
    assert area == 96 and center == (5, 5)
    assert geom.polygon_measure([[exterior[::-1], hole[::-1]]]) == (area, center)
    shifted = [[[x + 236000, y + 4130000] for x, y in ring] for ring in [exterior, hole]]
    a, c = geom.polygon_measure([shifted])
    assert a == 96 and c == pytest.approx((236005, 4130005))
    assert not geom.covers(center, [[exterior, hole]])
    assert geom.covers((4, 5), [[exterior, hole]])  # polygon boundary is covered
    anchor = geom.representative_point([exterior, hole])
    assert geom.covers(anchor, [[exterior, hole]])
    assert all(geom.ring_location(anchor, ring) != 2 for ring in [exterior, hole])


def test_concave_footprint_uses_an_interior_anchor():
    ring = [[0, 0], [4, 0], [4, 1], [1, 1], [1, 3], [4, 3], [4, 4], [0, 4], [0, 0]]
    _, center = geom.polygon_measure([[ring]])
    assert not geom.covers(center, [[ring]])
    anchor = geom.representative_point([ring])
    assert geom.ring_location(anchor, ring) == 1


def test_multipart_never_assigns_across_different_barrios_or_missing_components():
    a, b = [rectangle()], [rectangle(20)]
    barrios = [
        neighbourhood("A", [rectangle(-1, -1, 12, 12)]),
        neighbourhood("B", [rectangle(19, -1, 12, 12)]),
    ]
    assert geom.footprint_match([a, b], barrios) == (None, "crosses_barrios")
    assert geom.footprint_match([a, b], barrios[:1]) == (None, "partly_outside_barrios")
    assert geom.footprint_match([b], barrios[:1]) == (None, "outside_barrios")
    assert geom.footprint_match([a], barrios) == ("A", "matched")
    assert geom.footprint_match([a], [barrios[0], barrios[0]]) == (None, "ambiguous")


@pytest.mark.parametrize(
    "ring",
    [
        [],
        [[0, 0]] * 4,
        [[0, 0], [1, 0], [1, 1], [0, 1]],
        [[0, 0], [float("nan"), 0], [1, 1], [0, 0]],
    ],
)
def test_invalid_geometry_fails_instead_of_publishing_density(ring):
    with pytest.raises(ValueError):
        geom.polygon_measure([[ring]])


def test_source_units_date_ranges_and_mixed_use_are_not_reinterpreted():
    row = record()
    assert row["cat_municipality"] == "41900" and row["ine_municipality"] == "41091"
    assert row["year_start"] == 1960 and row["year_end"] == 2000
    assert row["date_quality"] == "complete" and row["current_use"] == "4_2_retail"
    assert row["dwelling_properties"] == 3 and row["building_units"] == 5
    assert row["footprint_m2"] == 100 and row["gross_floor_m2"] == 500
    assert row["barrio_id"] == "A" and row["match_status"] == "matched"


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, (None, "missing")),
        ("--01-01T00:00:00", (None, "missing")),
        ("206-01-01T00:00:00", (None, "invalid")),
        ("0000-01-01T00:00:00", (None, "invalid")),
        ("2000-02-31T00:00:00", (None, "invalid")),
        ("1023-01-01T00:00:00", (1023, "valid")),
    ],
)
def test_missing_malformed_and_historical_dates(value, expected):
    assert stock.construction_year(value) == expected


def test_raw_malformed_date_preserved_and_nil_count_not_zero():
    e = element()
    e.find(".//{*}beginning").text = "206-01-01T00:00:00"
    count = e.find("{*}numberOfDwellings")
    count.set("{http://www.w3.org/2001/XMLSchema-instance}nil", "true")
    row = stock.building(e, "2026-08-21", [])
    assert row["date_start_raw"] == "206-01-01T00:00:00"
    assert row["year_start"] is None and row["date_quality"] == "invalid"
    assert row["dwelling_properties"] is None


@pytest.mark.parametrize(
    "path,attribute,value",
    [
        (".//{*}Surface", "srsName", "urn:ogc:def:crs:EPSG::4326"),
        (".//{*}OfficialArea/{*}value", "uom", "ha"),
        (".//{*}officialAreaReference", None, "netFloorArea"),
        (".//{*}OfficialArea/{*}value", None, "nan"),
        (".//{*}numberOfDwellings", None, "-1"),
        (".//{*}beginning", None, "2001-01-01T00:00:00"),
    ],
)
def test_changed_schema_or_inconsistent_source_fails(path, attribute, value):
    e = element()
    target = e.find(path)
    if attribute:
        target.set(attribute, value)
    else:
        target.text = value
    with pytest.raises(ValueError):
        stock.building(e, "2026-08-21", [])


def test_duplicate_parcel_records_in_archive_rejected(tmp_path, monkeypatch):
    p = tmp_path / "buildings.zip"
    member = ET.Element("{http://www.opengis.net/gml/3.2}featureMember")
    member.append(element())
    root = ET.Element("{http://www.opengis.net/gml/3.2}FeatureCollection")
    root.append(member)
    root.append(ET.fromstring(ET.tostring(member)))
    with zipfile.ZipFile(p, "w") as archive:
        archive.writestr("test.building.gml", ET.tostring(root))
    monkeypatch.setattr(stock, "ARCHIVE", p)
    with pytest.raises(ValueError, match="Duplicate"):
        stock.parse_archive("2026-08-21", [])


@pytest.fixture
def database():
    with duckdb.connect() as con:
        con.execute("create schema stock; create schema housing")
        rows = [
            record(),
            {
                **record(),
                "refcat": "second",
                "barrio_id": None,
                "match_status": "outside_barrios",
                "dwelling_properties": 7,
                "year_start": None,
                "date_quality": "missing",
            },
        ]
        con.register("records", pa.Table.from_pylist(rows, schema=stock.SCHEMA))
        con.execute("create table stock.buildings as select * from records")
        con.execute("create table stock.snapshot as select '2026-08-21' as snapshot_date")
        con.execute("""create table stock.barrios as select 'A' as idg, 'Alpha' as barrio,
                       'District' as distrito, 0.5 as area_km2 union all
                       select 'B', 'Beta', 'District', 1.0""")
        con.execute("alter table stock.barrios add column geometry_quality varchar default 'valid'")
        con.execute("alter table stock.barrios add column source_overlap_m2 double default 0")
        con.execute("""create table housing.sevilla_sim_poblacion_hogares as
                       select 'A' as idg, 2015 as anyo, 2 as hogares union all
                       select 'A', 2021, 4""")
        con.execute("""create table housing.barrios_sevilla as
                       select 'A' as idg, 'Alpha' as barrio, 'District' as distrito,
                              2022 as anyo, 7.0 as ipra_eur_m2 union all
                       select 'B', 'Beta', 'District', 2022, 8.0""")
        con.execute("create schema income")
        con.execute("""create table income.barrios_income as
                       select 'A' as idg, 'Alpha' as barrio, 'District' as distrito,
                              2019 as anyo, 30000.0 as renta_neta_eur""")
        yield con


def test_dashboard_queries_keep_units_unmatched_rows_and_missing_density(database):
    for sql in SQL.values():
        sql = expand_sql(sql)
        database.execute(sql).fetchall()  # every query parses against an offline schema
    coverage = database.execute(SQL["cobertura_stock"]).fetchall()
    assert sum(row[3] for row in coverage) == 10
    barrios = database.execute(SQL["stock_barrios"]).fetchall()
    assert barrios[0][4:9] == (1, 3, 6, 0.01, 0.0005)
    assert barrios[1][4] == 0 and barrios[1][5] is None and barrios[1][6] is None
    cohorts = database.execute(SQL["cohortes_stock"]).fetchall()
    assert sum(row[2] for row in cohorts) == 2  # includes unmatched; each record gets equal weight
    demand = database.execute(
        SQL["demanda_stock"].replace("${stock_barrios}", f"({SQL['stock_barrios']})")
    ).fetchall()
    assert demand[0] == ("Alpha", 3, 2, 4, 2)  # no fabricated contemporaneous ratio
    assert demand[1][2:] == (None, None, None)


def test_page_contract_explains_nonavailability_and_spatial_approximation():
    assert "geoId='IDG'" in PAGE and "areaCol=idg" in PAGE
    assert "no una intersección exacta" in PAGE
    assert "tamaño medio de vivienda" in PAGE and "registros sin asignación" in PAGE
    assert "no son hogares, viviendas ocupadas" in PAGE
    assert "stock.duckdb" in (ROOT / "evidence/sources/stock/connection.yaml").read_text()


@pytest.fixture
def geography_inputs(tmp_path, monkeypatch):
    import json

    projected, mapping, context = [], [], []
    for i in range(108):
        properties = {
            "IDG": f"{i:05d}",
            "ID_DIS": "01",
            "DIS": "District",
            "ID_BAR": str(i),
            "BAR": f"Barrio {i}",
        }
        projected.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {"type": "Polygon", "coordinates": [rectangle(236000, 4130000)]},
            }
        )
        mapping.append(
            {
                "type": "Feature",
                "properties": dict(properties),
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [rectangle(-5.99, 37.38, 0.001, 0.001)],
                },
            }
        )
        context.append({"attributes": dict(properties)})
    paths = {}
    for name, value in [
        ("PROJECTED", {"crs": {"properties": {"name": "EPSG:25830"}}, "features": projected}),
        ("MAP_INPUT", {"crs": {"properties": {"name": "EPSG:4326"}}, "features": mapping}),
        ("CONTEXT", {"query": {"features": context}}),
    ]:
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(value))
        monkeypatch.setattr(stock, name, path)
        paths[name] = path
    return paths


def test_polygon_keys_labels_and_units_match_pinned_context(geography_inputs):
    barrios, mapping = stock.neighbourhoods()
    assert len(barrios) == len(mapping["features"]) == 108
    assert barrios[0]["area_km2"] == pytest.approx(0.0001)
    assert barrios[0]["idg"] == "00000"


def test_same_id_different_barrio_name_cannot_join_demand(geography_inputs):
    import json

    path = geography_inputs["CONTEXT"]
    payload = json.loads(path.read_text())
    payload["query"]["features"][0]["attributes"]["BAR"] = "Different geography"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="keys/labels differ"):
        stock.neighbourhoods()


def test_projected_coordinates_mislabeled_as_longitude_latitude_fail(geography_inputs):
    import json

    path = geography_inputs["MAP_INPUT"]
    payload = json.loads(path.read_text())
    payload["features"][0]["geometry"]["coordinates"] = [rectangle(236000, 4130000)]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="longitude/latitude"):
        stock.neighbourhoods()


@pytest.mark.parametrize(
    "value",
    [
        "2000-01-01Tgarbage",
        "2000-01-01T99:99:99",
        "2000-01-01T00:00:00junk",
        "2000-01-01T00:00:00+01:60",
        "2000-01-01T00:00:00+15:00",
        "--01-01Tgarbage",
    ],
)
def test_complete_malformed_datetime_is_flagged(value):
    assert stock.construction_year(value) == (None, "invalid")


@pytest.mark.parametrize(
    "value", ["2000-01-01T00:00:00", "2000-01-01T00:00:00.123Z", "2000-01-01T00:00:00+02:00"]
)
def test_complete_valid_datetime_preserves_local_construction_year(value):
    assert stock.construction_year(value) == (2000, "valid")


@pytest.mark.parametrize(
    "polygons",
    [
        [[[[0, 0], [4, 4], [0, 4], [4, 0], [5, 0], [0, 0]]]],
        [[rectangle(), rectangle(20, 20, 2, 2)]],
        [[rectangle(), rectangle(2, 2, 4, 4), rectangle(4, 4, 4, 4)]],
        [[rectangle()], [rectangle(5)]],
        [[rectangle()], [rectangle(2, 2, 2, 2)]],
    ],
)
def test_invalid_topology_fails_before_measurement_or_assignment(polygons):
    with pytest.raises(geom.InvalidTopology):
        geom.polygon_measure(polygons)
    with pytest.raises(geom.InvalidTopology):
        geom.footprint_match(polygons, [])


def test_adjacent_surface_patches_do_not_double_count_or_require_repair():
    area, center = geom.polygon_measure([[rectangle()], [rectangle(10)]])
    assert area == 200 and center == (10, 5)


def test_sim_display_overlap_is_explicit_union_not_hidden_area_double_count():
    geometry = {"type": "MultiPolygon", "coordinates": [[rectangle()], [rectangle(5)]]}
    normalized, source_area, union_area = geom.dissolve_source_geojson(geometry)
    assert source_area == 200 and union_area == 150
    assert geom.polygon_measure(geom.geojson_polygons(normalized))[0] == 150
    invalid = {"type": "Polygon", "coordinates": [rectangle(), rectangle(20, 20, 2, 2)]}
    with pytest.raises(geom.InvalidTopology):
        geom.dissolve_source_geojson(invalid)  # no make_valid/buffer repair


@pytest.mark.parametrize(
    "change",
    [
        "unknown_only",
        "mixed_unknown",
        "triangle_patch",
        "bad_reference",
        "missing_reference",
        "bad_count",
    ],
)
def test_unsupported_or_partial_gml_cannot_publish_a_supported_subset(change):
    e = element()
    geometry = e.find("{*}geometry/{*}BuildingGeometry/{*}geometry")
    if change == "unknown_only":
        geometry.clear()
        ET.SubElement(geometry, stock.GML + "MultiSurface")
    elif change == "mixed_unknown":
        ET.SubElement(geometry, stock.GML + "MultiSurface")
    elif change == "triangle_patch":
        ET.SubElement(geometry.find("{*}Surface/{*}patches"), stock.GML + "Triangle")
    elif change == "bad_reference":
        e.find(".//{*}horizontalGeometryReference").text = "roofEdge"
    elif change == "missing_reference":
        e.find(".//{*}BuildingGeometry").remove(e.find(".//{*}horizontalGeometryReference"))
    else:
        e.find(".//{*}posList").set("count", "99")
    with pytest.raises(ValueError):
        stock.building(e, "2026-08-21", [])


def test_absent_nil_and_empty_unsupported_geometry_are_distinct():
    e = element()
    prop = e.find("{*}geometry")
    e.remove(prop)
    assert stock.building(e, "2026-08-21", [])["match_status"] == "missing_geometry"
    prop.clear()
    e.append(prop)
    with pytest.raises(ValueError, match="wrapper"):
        stock.building(e, "2026-08-21", [])
    prop.set(stock.NIL, "true")
    row = stock.building(e, "2026-08-21", [])
    assert row["match_status"] == "missing_geometry" and row["footprint_m2"] is None


def test_mixed_nil_and_present_geometry_cannot_claim_complete_footprint():
    e = element()
    prop = ET.SubElement(e, "{urn:bu}geometry", {stock.NIL: "true"})
    assert len(prop) == 0
    with pytest.raises(ValueError, match="Incomplete footprint"):
        stock.building(e, "2026-08-21", [])


def test_invalid_barrio_quarantined_not_repaired_or_removed_from_context(geography_inputs):
    import json

    path = geography_inputs["PROJECTED"]
    payload = json.loads(path.read_text())
    payload["features"][0]["geometry"]["coordinates"].append(rectangle(236020, 4130020, 2, 2))
    path.write_text(json.dumps(payload))
    barrios, mapping = stock.neighbourhoods()
    assert len(barrios) == 108 and len(mapping["features"]) == 107
    assert barrios[0]["geometry_quality"] == "invalid_topology"
    assert barrios[0]["area_km2"] is None and barrios[0]["polygons"] == []
    assert barrios[0]["source_overlap_m2"] is None


def test_source_overlap_quality_and_correction_are_exposed(geography_inputs):
    import json

    path = geography_inputs["PROJECTED"]
    payload = json.loads(path.read_text())
    payload["features"][0]["geometry"] = {
        "type": "MultiPolygon",
        "coordinates": [[rectangle(236000, 4130000)], [rectangle(236005, 4130000)]],
    }
    path.write_text(json.dumps(payload))
    barrios, _ = stock.neighbourhoods()
    assert barrios[0]["geometry_quality"] == "overlapping_components_dissolved"
    assert barrios[0]["source_overlap_m2"] == 50
    assert barrios[0]["area_km2"] == pytest.approx(0.00015)
    assert barrios[0]["source_component_area_km2"] == pytest.approx(0.0002)


def test_engine_version_is_part_of_freshness_metadata():
    meta = stock.metadata({}, "2026-08-21")
    assert meta["geometry_engine"] == geom.ENGINE_VERSION
    assert "shapely=" in meta["geometry_engine"] and "GEOS=" in meta["geometry_engine"]


def test_map_only_invalid_topology_quarantines_the_paired_barrio(geography_inputs):
    import json

    path = geography_inputs["MAP_INPUT"]
    payload = json.loads(path.read_text())
    payload["features"][0]["geometry"]["coordinates"].append(rectangle(-5.97, 37.40, 0.001, 0.001))
    path.write_text(json.dumps(payload))
    barrios, mapping = stock.neighbourhoods()
    assert barrios[0]["geometry_quality"] == "invalid_topology"
    assert barrios[0]["area_km2"] is None and barrios[0]["polygons"] == []
    assert len(mapping["features"]) == 107


def test_page_sql_keeps_quarantined_household_context_without_stock_or_density(database):
    database.execute(
        "update stock.barrios set area_km2=null, geometry_quality='invalid_topology' where idg='B'"
    )
    database.execute(
        "insert into housing.sevilla_sim_poblacion_hogares values ('B',2015,7),('B',2021,9)"
    )
    rows = database.execute(SQL["stock_barrios"]).fetchall()
    assert rows[1][3] is None and rows[1][5] is None and rows[1][6] is None
    assert rows[1][-1] == "invalid_topology"
    demand = database.execute(
        SQL["demanda_stock"].replace("${stock_barrios}", f"({SQL['stock_barrios']})")
    ).fetchall()
    assert demand[1] == ("Beta", None, 7, 9, 2)
