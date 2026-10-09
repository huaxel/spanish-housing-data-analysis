"""Minimal strict ESRI Shapefile reader (Polygon-only, pure stdlib).

Supports exactly what the Granada district layer needs: shape type 5
(Polygon) with 2D finite coordinates, plus dBase III attribute tables
with C/N field types. Anything else -- Z/M coordinates, other shape
types, memo fields, missing .shx index agreement -- fails loudly instead
of being silently coerced. Attribute text is decoded as Windows-1252
(the usual Spanish-administration encoding for these files); names that
do not round-trip are a loud error at join time, not here.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path


def read_dbf(path: str | Path) -> tuple[list[str], list[dict]]:
    raw = Path(path).read_bytes()
    if raw[0] != 0x03:
        raise ValueError("DBF version is not dBase III")
    nrec = struct.unpack("<I", raw[4:8])[0]
    hdrlen = struct.unpack("<H", raw[8:10])[0]
    reclen = struct.unpack("<H", raw[10:12])[0]
    fields = []
    pos = 32
    while raw[pos] != 0x0D:
        name = raw[pos : pos + 11].split(b"\x00")[0].decode("ascii")
        kind = chr(raw[pos + 11])
        length, decimals = raw[pos + 16], raw[pos + 17]
        if kind not in ("C", "N"):
            raise ValueError(f"Unsupported DBF field type: {kind}")
        if not name:
            raise ValueError("Empty DBF field name")
        fields.append((name, kind, length, decimals))
        pos += 32
    if pos + 1 != hdrlen:
        raise ValueError("DBF header length disagrees with field descriptors")
    names = [f[0] for f in fields]
    if len(set(names)) != len(names):
        raise ValueError("Duplicated DBF field names")
    widths = [f[2] for f in fields]
    if 1 + sum(widths) != reclen:
        raise ValueError("DBF record length disagrees with field widths")
    records = []
    body = pos + 1
    for i in range(nrec):
        rec = raw[body + i * reclen : body + (i + 1) * reclen]
        if len(rec) != reclen:
            raise ValueError("Truncated DBF record")
        values = {}
        at = 1
        for name, kind, length, _decimals in fields:
            token = rec[at : at + length].decode("windows-1252")
            at += length
            if kind == "C":
                values[name] = token.strip()
            else:
                token = token.strip()
                values[name] = None if token in ("", "*") else float(token)
        records.append(values)
    return names, records


def read_shp_polygons(path: str | Path) -> list[list[list[list[float]]]]:
    """Read Polygon shapes as lists of parts, each a list of linear rings."""
    raw = Path(path).read_bytes()
    if struct.unpack(">i", raw[0:4])[0] != 9994:
        raise ValueError("SHP file code is not 9994")
    if struct.unpack("<i", raw[28:32])[0] != 1000:
        raise ValueError("SHP version is not 1000")
    if struct.unpack("<i", raw[32:36])[0] != 5:
        raise ValueError("SHP shape type is not Polygon")
    shapes = []
    pos = 100
    while pos < len(raw):
        reclen_words = struct.unpack(">i", raw[pos + 4 : pos + 8])[0]
        content = raw[pos + 8 : pos + 8 + reclen_words * 2]
        if len(content) != reclen_words * 2:
            raise ValueError("Truncated SHP record")
        shape_type = struct.unpack("<i", content[0:4])[0]
        if shape_type == 0:
            shapes.append([])
            pos += 8 + reclen_words * 2
            continue
        if shape_type != 5:
            raise ValueError(f"Non-Polygon SHP record: {shape_type}")
        nparts, npoints = struct.unpack("<ii", content[36:44])
        starts = struct.unpack(f"<{nparts}i", content[44 : 44 + 4 * nparts])
        coords = struct.unpack(f"<{2 * npoints}d", content[44 + 4 * nparts :])
        points = [(coords[2 * i], coords[2 * i + 1]) for i in range(npoints)]
        for x, y in points:
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError("Nonfinite SHP coordinate")
        parts = []
        for k, start in enumerate(starts):
            end = starts[k + 1] if k + 1 < nparts else npoints
            ring = [list(p) for p in points[start:end]]
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError("Unclosed SHP ring")
            parts.append(ring)
        shapes.append(parts)
        pos += 8 + reclen_words * 2
    return shapes


def read_shapes(base: str | Path) -> list[tuple[dict, list]]:
    """Join .shp geometries with .dbf attributes by record order."""
    base = str(base)
    shapes = read_shp_polygons(base + ".shp")
    _names, records = read_dbf(base + ".dbf")
    if len(shapes) != len(records):
        raise ValueError("SHP/DBF record count mismatch")
    return list(zip(records, shapes, strict=True))
