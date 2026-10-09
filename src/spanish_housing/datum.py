"""ED50/UTM30 to ETRS89/UTM30 for the Granada district polygons (pure stdlib).

The Ayuntamiento de Granada district layer is published in ED50/UTM zone
30N. The cadastre pilot works in ETRS89/UTM 30N (EPSG:25830). The official
NTv2 grid (PENR2009.gsb) needs binary grid support, so this module uses
the published 7-parameter Position Vector transformation EPSG:1632
("ED50 to ETRS89 (7)", CNIG-Esp, for mainland Spain except the northwest;
stated accuracy 1.5 m -- ample for assigning records to km-scale
districts, where only a thin edge band is sensitive at all):

    T = (-131.0, -100.3, -163.4) m
    R = (-1.244, -0.02, -1.144) arcseconds (Position Vector convention)
    D = +9.39 ppm

Pipeline: UTM inverse (Hayford 1924 ellipsoid) -> geocentric ->
Helmert -> geocentric (GRS80) -> geodetic (Bowring) -> UTM forward
(GRS80, zone 30N). Angles in radians internally.
"""

from __future__ import annotations

import math

# Ellipsoids: (semi-major axis m, inverse flattening).
HAYFORD = (6378388.0, 297.0)
GRS80 = (6378137.0, 298.257222101)

# EPSG:1632 ED50 -> ETRS89, Position Vector convention.
_TX, _TY, _TZ = -131.0, -100.3, -163.4
_ARCSEC = math.pi / (180.0 * 3600.0)
_RX, _RY, _RZ = -1.244 * _ARCSEC, -0.02 * _ARCSEC, -1.144 * _ARCSEC
_SCALE = 9.39e-6

_UTM_K0 = 0.9996
_UTM_LON0 = math.radians(-3.0)
_UTM_E0 = 500000.0


def _utm_inverse(x: float, y: float, ellipsoid) -> tuple[float, float]:
    """UTM zone 30N inverse: easting/northing -> (lat, lon) radians."""
    a, rf = ellipsoid
    f = 1.0 / rf
    e2 = 2 * f - f * f
    ep2 = e2 / (1 - e2)
    m = y / _UTM_K0
    mu = m / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
    )
    n1 = a / math.sqrt(1 - e2 * math.sin(phi1) ** 2)
    t1 = math.tan(phi1) ** 2
    c1 = ep2 * math.cos(phi1) ** 2
    r1 = a * (1 - e2) / (1 - e2 * math.sin(phi1) ** 2) ** 1.5
    d = (x - _UTM_E0) / (n1 * _UTM_K0)
    lat = phi1 - (n1 * math.tan(phi1) / r1) * (
        d**2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1**2) * d**4 / 24
    )
    lon = _UTM_LON0 + (
        d - (1 + 2 * t1 + c1) * d**3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1**2) * d**5 / 120
    ) / math.cos(phi1)
    return lat, lon


def _utm_forward(lat: float, lon: float, ellipsoid) -> tuple[float, float]:
    """UTM zone 30N forward: (lat, lon) radians -> easting/northing."""
    a, rf = ellipsoid
    f = 1.0 / rf
    e2 = 2 * f - f * f
    ep2 = e2 / (1 - e2)
    n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    t = math.tan(lat) ** 2
    c = ep2 * math.cos(lat) ** 2
    lam = (lon - _UTM_LON0) * math.cos(lat)
    m = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat)
        - (35 * e2**3 / 3072) * math.sin(6 * lat)
    )
    x = _UTM_E0 + _UTM_K0 * n * (
        lam + (1 - t + c) * lam**3 / 6 + (5 - 18 * t + t**2 + 72 * c) * lam**5 / 120
    )
    y = _UTM_K0 * (m + n * math.tan(lat) * (lam**2 / 2 + (5 - t + 9 * c + 4 * c**2) * lam**4 / 24))
    return x, y


def _to_geocentric(lat: float, lon: float, ellipsoid) -> tuple[float, float, float]:
    a, rf = ellipsoid
    f = 1.0 / rf
    e2 = 2 * f - f * f
    n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    return (
        n * math.cos(lat) * math.cos(lon),
        n * math.cos(lat) * math.sin(lon),
        n * (1 - e2) * math.sin(lat),
    )


def _to_geodetic(x: float, y: float, z: float, ellipsoid) -> tuple[float, float]:
    a, rf = ellipsoid
    f = 1.0 / rf
    e2 = 2 * f - f * f
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - e2))
    for _ in range(5):
        n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        lat = math.atan2(z + e2 * n * math.sin(lat), p)
    return lat, lon


def ed50_utm30_to_etrs89_utm30(x: float, y: float) -> tuple[float, float]:
    """Transform one ED50/UTM30 point to ETRS89/UTM30 (EPSG:1632, ~1.5 m)."""
    lat, lon = _utm_inverse(x, y, HAYFORD)
    gx, gy, gz = _to_geocentric(lat, lon, HAYFORD)
    s = 1 + _SCALE
    hx = _TX + s * (gx - _RZ * gy + _RY * gz)
    hy = _TY + s * (_RZ * gx + gy - _RX * gz)
    hz = _TZ + s * (-_RY * gx + _RX * gy + gz)
    lat2, lon2 = _to_geodetic(hx, hy, hz, GRS80)
    return _utm_forward(lat2, lon2, GRS80)
