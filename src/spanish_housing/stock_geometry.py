"""Small planar geometry helpers for the EPSG:25830 cadastral pilot.

No reprojection, polygon overlays or proportional allocations. Rings must
be closed; holes are explicit. Boundary points count as covered and can
therefore produce ambiguous neighbourhood matches, never silently assigned.
"""

from __future__ import annotations

import math

from shapely import (
    Polygon,
    STRtree,
    __version__,
    geos_version_string,
    is_valid_reason,
    unary_union,
)
from shapely.geometry import mapping

ENGINE_VERSION = f"shapely={__version__};GEOS={geos_version_string}"


class InvalidTopology(ValueError):
    """Source polygon topology cannot support physical-area or location claims."""


def validated_components(polygons):
    """Validate each polygon, including self-intersections and hole topology."""
    if not polygons:
        raise ValueError("Empty polygon geometry")
    shapes = []
    for rings in polygons:
        if not rings:
            raise ValueError("Polygon without exterior")
        for ring in rings:
            validate_ring(ring)
        shape = Polygon(rings[0], rings[1:])
        if shape.is_empty or not shape.is_valid or shape.area <= 0:
            raise InvalidTopology(f"Invalid polygon topology: {is_valid_reason(shape)}")
        shapes.append(shape)
    return shapes


def validate_polygons(polygons):
    """Reject overlapping interiors; shared edges of GML Surface patches are OK."""
    shapes = validated_components(polygons)
    if len(shapes) > 1:
        tree = STRtree(shapes)
        for i, shape in enumerate(shapes):
            for j in tree.query(shape):
                if j > i and shape.relate_pattern(shapes[j], "T********"):
                    raise InvalidTopology("Overlapping polygon component interiors")


def dissolve_source_geojson(geometry):
    """Explicit SIM display-geometry policy: union valid same-feature components.

    Publisher MultiPolygon components can overlap. Return raw component area
    and union area to expose that correction. Invalid rings/holes fail; no
    buffer, make_valid, rounding or other topology repair is performed.
    """
    shapes = validated_components(raw_geojson_polygons(geometry))
    union = unary_union(shapes)
    if union.geom_type not in {"Polygon", "MultiPolygon"} or not union.is_valid:
        raise InvalidTopology("Invalid dissolved SIM display geometry")
    return mapping(union), math.fsum(shape.area for shape in shapes), union.area


def validate_ring(ring):
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError("Ring must have at least four coordinates and be closed")
    if any(len(p) != 2 or any(not math.isfinite(v) for v in p) for p in ring):
        raise ValueError("Nonfinite or non-2D polygon coordinate")


def ring_measure(ring):
    validate_ring(ring)
    ox, oy = ring[0]
    points = [(x - ox, y - oy) for x, y in ring]
    crosses = [a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:], strict=False)]
    twice_area = math.fsum(crosses)
    if abs(twice_area) < 1e-8:
        raise ValueError("Degenerate polygon ring")
    cx = math.fsum((a[0] + b[0]) * c for a, b, c in zip(points, points[1:], crosses, strict=False))
    cy = math.fsum((a[1] + b[1]) * c for a, b, c in zip(points, points[1:], crosses, strict=False))
    return abs(twice_area) / 2, (ox + cx / (3 * twice_area), oy + cy / (3 * twice_area))


def polygon_measure(polygons):
    """Area and centroid of nonoverlapping polygons with explicit interior rings."""
    validate_polygons(polygons)
    pieces = []
    for rings in polygons:
        if not rings:
            raise ValueError("Polygon without exterior")
        area, center = ring_measure(rings[0])
        pieces.append((area, center))
        for hole in rings[1:]:
            hole_area, hole_center = ring_measure(hole)
            area -= hole_area
            pieces.append((-hole_area, hole_center))
        if area <= 0:
            raise ValueError("Holes consume polygon area")
    total = math.fsum(a for a, _ in pieces)
    if total <= 0:
        raise ValueError("Empty polygon geometry")
    return total, (
        math.fsum(a * p[0] for a, p in pieces) / total,
        math.fsum(a * p[1] for a, p in pieces) / total,
    )


def ring_location(point, ring):
    """0 outside, 1 inside, 2 on boundary (metric tolerance below source precision)."""
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in zip(ring, ring[1:], strict=False):
        dx, dy = bx - ax, by - ay
        cross = (x - ax) * dy - (y - ay) * dx
        if (
            abs(cross) <= 1e-7 * max(1.0, math.hypot(dx, dy))
            and min(ax, bx) - 1e-7 <= x <= max(ax, bx) + 1e-7
            and min(ay, by) - 1e-7 <= y <= max(ay, by) + 1e-7
        ):
            return 2
        if (ay > y) != (by > y) and x < ax + (y - ay) * dx / dy:
            inside = not inside
    return int(inside)


def covers(point, polygons):
    for rings in polygons:
        outer = ring_location(point, rings[0])
        if not outer:
            continue
        holes = [ring_location(point, hole) for hole in rings[1:]]
        if outer == 2 or 2 in holes or not any(holes):
            return True
    return False


def bbox(polygons):
    points = [p for polygon in polygons for ring in polygon for p in ring]
    if not points:
        raise ValueError("Empty geometry")
    return (
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points),
    )


def raw_geojson_polygons(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError("Expected Polygon or MultiPolygon")


def geojson_polygons(geometry):
    polygons = raw_geojson_polygons(geometry)
    validate_polygons(polygons)
    return polygons


def spatial_match(point, neighbourhoods):
    hits = []
    for item in neighbourhoods:
        if not item["polygons"]:
            continue
        xmin, ymin, xmax, ymax = item["bbox"]
        if (
            xmin <= point[0] <= xmax
            and ymin <= point[1] <= ymax
            and covers(point, item["polygons"])
        ):
            hits.append(item["idg"])
    if len(hits) == 1:
        return hits[0], "matched"
    return None, "ambiguous" if hits else "outside_barrios"


def representative_point(polygon):
    """Find an interior point by scanline parity, including explicit holes.

    Prefer the area centroid when interior. Otherwise choose the midpoint
    of the widest interior interval on a scanline between vertex heights.
    This locates a record; it is not an area overlay or unit allocation.
    """
    _, center = polygon_measure([polygon])
    if covers(center, [polygon]) and all(ring_location(center, r) != 2 for r in polygon):
        return center
    heights = sorted({p[1] for ring in polygon for p in ring})
    gaps = sorted(
        zip(heights, heights[1:], strict=False), key=lambda pair: pair[1] - pair[0], reverse=True
    )
    for lower, upper in gaps:
        y = (lower + upper) / 2
        intersections = []
        for ring in polygon:
            for (ax, ay), (bx, by) in zip(ring, ring[1:], strict=False):
                if (ay <= y < by) or (by <= y < ay):
                    intersections.append(ax + (y - ay) * (bx - ax) / (by - ay))
        intersections.sort()
        if len(intersections) % 2:
            raise ValueError("Invalid polygon scanline topology")
        intervals = list(zip(intersections[::2], intersections[1::2], strict=True))
        if intervals:
            left, right = max(intervals, key=lambda pair: pair[1] - pair[0])
            point = ((left + right) / 2, y)
            if right > left and covers(point, [polygon]):
                return point
    raise ValueError("Cannot find interior footprint point")


def footprint_match(polygons, neighbourhoods):
    """All footprint components must locate uniquely in the same barrio."""
    validate_polygons(polygons)
    assignments = [
        spatial_match(representative_point(polygon), neighbourhoods) for polygon in polygons
    ]
    ids = {identifier for identifier, status in assignments if status == "matched"}
    if any(status == "ambiguous" for _, status in assignments):
        return None, "ambiguous"
    if len(ids) > 1:
        return None, "crosses_barrios"
    if any(status != "matched" for _, status in assignments):
        return None, "partly_outside_barrios" if ids else "outside_barrios"
    if len(ids) == 1:
        return next(iter(ids)), "matched"
    return None, "missing_geometry"
