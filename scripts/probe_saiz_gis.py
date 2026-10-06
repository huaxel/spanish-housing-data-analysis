"""Feasibility probe: Saiz-style undevelopable-land share at provincia grain.

Deliberately a PROBE, not the production pipeline. It answers one question:
can Copernicus DEM 30 m + a free province boundary set yield a
geographically sane developable-share series for all 52 provincias, with
the tooling and bandwidth available here? Verdict in
`docs/explorations/saiz_gis_probe.md`.

Method (Saiz 2010, QJE 125(3)), as closely as the data allow:
  undevelopable = (slope > 15% grade) | (water)
  15% grade == arctan(0.15) == 8.53 degrees -- NOT 15 degrees.
  slope = max rise/run to the four orthogonal neighbours (Saiz uses max
  slope to adjacent quadrants, not a central-difference gradient).

Resolution: the DEM is block-averaged to 90 m by default, matching Saiz's
90 m USGS DEM. This matters: Copernicus GLO-30 is a DSM (buildings and
canopy included), so at native 30 m a building edge alone can clear the
15% threshold. On rolling Extremadura terrain the steep share falls
0.290 -> 0.248 -> 0.192 at 30/90/180 m; on genuinely steep Pyrenees
tiles it barely moves (0.880 -> 0.876 -> 0.853). Ranking is robust to
resolution, the level is not -- so the level must be pinned.

Longitude handling: slope is computed on the native EPSG:4326 grid with an
analytic cos(lat) correction, because east-west cell width shrinks with
latitude. A constant-spacing gradient understates the >15% share by ~24%
in relative terms at 40N. Do not use it.

Usage:
  uv run --with rasterio --with numpy python scripts/probe_saiz_gis.py [provincia ...]
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize

CACHE = Path("/tmp/saizprobe/tiles")
NUTS_URL = (
    "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/"
    "NUTS_RG_01M_2021_4326_LEVL_3.geojson"
)
DEM_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_{hemi}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
)

SLOPE_GRADE_THRESHOLD = 15.0  # percent; arctan(0.15) = 8.53 degrees
FACTOR = 3  # 30 m -> 90 m, matching Saiz
M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON_EQ = 111320.0

CANARY_LAS_PALMAS = {"Fuerteventura", "Gran Canaria", "Lanzarote", "La Graciosa"}
CANARY_SC_TENERIFE = {"El Hierro", "La Gomera", "La Palma", "Tenerife"}
BALEARES = {"Eivissa y Formentera", "Mallorca", "Menorca"}

PROVINCIA_OF = {n: "Las Palmas" for n in CANARY_LAS_PALMAS}
PROVINCIA_OF.update({n: "Santa Cruz de Tenerife" for n in CANARY_SC_TENERIFE})
PROVINCIA_OF.update({n: "Illes Balears" for n in BALEARES})

# Saiz-style reference: undevelopable share must be high in alpine provinces
# and low in the Meseta/Guadalquivir basins. Used only as a read-out check.


def tile_key(lat: int, lon: int) -> str:
    hemi = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{hemi}{abs(lat):02d}{ew}{abs(lon):03d}"


def tile_name(kind: str, lat: int, lon: int) -> str:
    hemi = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"Copernicus_DSM_COG_10_{hemi}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_{kind}.tif"


def dem_url(lat: int, lon: int, kind: str) -> str:
    hemi = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    stem = f"Copernicus_DSM_COG_10_{hemi}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00"
    prefix = "" if kind == "DEM" else "AUXFILES/"
    return f"{DEM_URL.format(hemi=hemi, lat=lat, ew=ew, lon=abs(lon))}{prefix}{stem}_{kind}.tif"


def fetch(url: str, dest: Path) -> Path | None:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=180) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 22):
                f.write(chunk)
        tmp.rename(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        return None
    return dest


def load_provinces() -> dict[str, list]:
    g = CACHE.parent / "nuts3.geojson"
    if not g.exists():
        fetch(NUTS_URL, g)
    data = json.loads(g.read_text())
    out: dict[str, list] = {}
    for f in data["features"]:
        p = f["properties"]
        if not p.get("NUTS_ID", "").startswith("ES"):
            continue
        name = p["NAME_LATN"]
        prov = PROVINCIA_OF.get(name, name)
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        out.setdefault(prov, []).extend(polys)
    return out


def geom_bbox(polys: list) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for poly in polys:
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return min(xs), max(xs), min(ys), max(ys)


def block_mean(a: np.ndarray, factor: int) -> np.ndarray:
    h, w = a.shape
    h2, w2 = h // factor * factor, w // factor * factor
    return a[:h2, :w2].reshape(h2 // factor, factor, w2 // factor, factor).mean(axis=(1, 3))


def max_neighbour_slope_grade(a: np.ndarray, transform) -> np.ndarray:
    """Max rise/run to 4 orthogonal neighbours, percent grade, cos(lat)-corrected."""
    h, _ = a.shape
    dlat = abs(transform.e)
    dlon = abs(transform.a)
    lat_rows = transform.f - dlat * (np.arange(h) + 0.5)
    dx_m = dlon * M_PER_DEG_LON_EQ * np.cos(np.radians(lat_rows))
    dy_m = dlat * M_PER_DEG_LAT

    out = np.zeros_like(a, dtype="float32")
    slope = np.abs(np.diff(a, axis=1)) / dx_m[:, None]
    out[:, :-1] = np.maximum(out[:, :-1], slope)
    out[:, 1:] = np.maximum(out[:, 1:], slope)
    slope = np.abs(np.diff(a, axis=0)) / dy_m
    out[:-1, :] = np.maximum(out[:-1, :], slope)
    out[1:, :] = np.maximum(out[1:, :], slope)
    return out * 100.0


def tiles_for(polys: list) -> list[tuple[int, int]]:
    lo_x, hi_x, lo_y, hi_y = geom_bbox(polys)
    return [
        (la, lo)
        for la in range(math.floor(lo_y), math.ceil(hi_y))
        for lo in range(math.floor(lo_x), math.ceil(hi_x))
    ]


def tile_paths(lat: int, lon: int) -> tuple[Path, Path]:
    key = tile_key(lat, lon)
    return CACHE / f"{key}_DEM.tif", CACHE / f"{key}_WBM.tif"


def province_stats(name: str, polys: list) -> dict | None:
    dev_px = und_px = steep_px = water_px = 0
    used = 0
    for lat, lon in tiles_for(polys):
        dem, wbm = tile_paths(lat, lon)
        if not dem.exists():
            continue
        with rasterio.open(dem) as ds:
            a = ds.read(1).astype("float32")
            nd = ds.nodata
            transform = ds.transform
        if nd is not None:
            a = np.where(a == nd, np.nan, a)

        h, w = a.shape
        coarse_shape = (h // FACTOR, w // FACTOR)
        coarse_transform = rasterio.Affine(
            transform.a * FACTOR,
            transform.b,
            transform.c,
            transform.d,
            transform.e * FACTOR,
            transform.f,
        )
        mask = rasterize(
            [({"type": "Polygon", "coordinates": p}, 1) for p in polys],
            out_shape=coarse_shape,
            transform=coarse_transform,
            fill=0,
            dtype="uint8",
        ).astype(bool)
        if mask.sum() == 0:
            continue

        a_filled = np.where(np.isnan(a), np.nanmean(a), a)
        a90 = block_mean(a_filled, FACTOR)
        if wbm.exists():
            with rasterio.open(wbm) as ws:
                wt = block_mean(ws.read(1).astype("float32"), FACTOR)
            water = (wt > 0.5) & mask
        else:
            water = np.zeros_like(mask)

        slope = max_neighbour_slope_grade(a90, coarse_transform)
        steep = (slope > SLOPE_GRADE_THRESHOLD) & mask
        und = steep | water

        # Cell AREA needs the same cos(lat) correction as the gradient: on an
        # EPSG:4326 grid cells are ~92 m N-S but only ~71 m E-W at 40N. A
        # scalar 90x90 m^2 overstates Spanish land area by ~24%.
        dlat = abs(coarse_transform.e)
        dlon = abs(coarse_transform.a)
        nrows = coarse_shape[0]
        lat_rows = coarse_transform.f - dlat * (np.arange(nrows) + 0.5)
        row_area = (dlat * M_PER_DEG_LAT) * (dlon * M_PER_DEG_LON_EQ * np.cos(np.radians(lat_rows)))
        wgt = np.broadcast_to(row_area[:, None], mask.shape)

        dev_px += float(((mask & ~und) * wgt).sum())
        und_px += float((und * wgt).sum())
        steep_px += float((steep * wgt).sum())
        water_px += float((water * wgt).sum())
        used += 1

    total = dev_px + und_px
    if total == 0:
        return None
    return {
        "provincia": name,
        "tiles": used,
        "land_km2": round(total / 1e6, 2),
        "undevelopable_share": round(und_px / total, 4),
        "steep_share": round(steep_px / total, 4),
        "water_share": round(water_px / total, 4),
    }


def sensitivity_report() -> None:
    """Resolution sensitivity of the steep share, for the committed table.

    Rolling Extremadura vs genuinely steep Pyrenees: the ranking survives
    the choice of resolution, the level does not. Written to JSON so the
    probe doc's numbers are auditable rather than remembered.
    """
    tiles = {"extremadura_rolling": "N38W006", "pyrenees_steep": "N42E000"}
    out: dict[str, dict[str, float]] = {}
    for label, key in tiles.items():
        lat = int(key[1:3])
        lon = int(key[4:]) * (-1 if key[3] == "W" else 1)
        dem_path, _ = tile_paths(lat, lon)
        fetch(dem_url(lat, lon, "DEM"), dem_path)
        with rasterio.open(dem_path) as ds:
            a = ds.read(1).astype("float32")
            tr = ds.transform
        row: dict[str, float] = {}
        for factor in (1, 3, 6):
            b = a if factor == 1 else block_mean(a, factor)
            t = rasterio.Affine(tr.a * factor, tr.b, tr.c, tr.d, tr.e * factor, tr.f)
            s = max_neighbour_slope_grade(b, t)[1:-1, 1:-1]
            row[f"{factor * 30}m"] = round(float((s > SLOPE_GRADE_THRESHOLD).mean()), 4)
        out[label] = row
        print(label, row)
    (CACHE.parent / "sensitivity.json").write_text(json.dumps(out, indent=2))


def municipal_report(prefix: str, out_name: str) -> None:
    """Terrain terrain series per LAU (municipio) for one provincia code.

    Processes whole 1x1 degree tiles and labels every municipio in the tile
    at once (rasterize + bincount), rather than one pass per municipio. Much
    faster and it keeps the cos(lat) area weighting identical to the
    provincial run.

    Validates computed land area against GISCO's own AREA_KM2 per municipio,
    which is a per-row external check the provincial run could not offer.
    """
    lau = CACHE.parent / "lau.geojson"
    if not lau.exists():
        fetch(
            "https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/"
            "LAU_RG_01M_2021_4326.geojson",
            lau,
        )
    data = json.loads(lau.read_text())
    units = []
    for f in data["features"]:
        p = f["properties"]
        if p.get("CNTR_CODE") != "ES" or not p.get("LAU_ID", "").startswith(prefix):
            continue
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        units.append(
            {"id": p["LAU_ID"], "name": p["LAU_NAME"], "lau_km2": p["AREA_KM2"], "polys": polys}
        )
    if not units:
        raise SystemExit(f"no LAU units for prefix {prefix!r}")
    print(f"LAU units: {len(units)}")

    needed: set[tuple[int, int]] = set()
    for u in units:
        needed.update(tiles_for(u["polys"]))

    def dl(t):
        lat, lon = t
        dem, wbm = tile_paths(lat, lon)
        if not dem.exists():
            fetch(dem_url(lat, lon, "DEM"), dem)
        if not wbm.exists():
            fetch(dem_url(lat, lon, "WBM"), wbm)

    with ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(dl, sorted(needed)))

    n = len(units)
    tot = np.zeros(n + 1)
    und = np.zeros(n + 1)
    steep_t = np.zeros(n + 1)
    water_t = np.zeros(n + 1)
    for lat, lon in sorted(needed):
        dem, wbm = tile_paths(lat, lon)
        if not dem.exists():
            continue
        with rasterio.open(dem) as ds:
            a = ds.read(1).astype("float32")
            nd = ds.nodata
            transform = ds.transform
        if nd is not None:
            a = np.where(a == nd, np.nan, a)
        h, w = a.shape
        coarse_shape = (h // FACTOR, w // FACTOR)
        coarse_transform = rasterio.Affine(
            transform.a * FACTOR,
            transform.b,
            transform.c,
            transform.d,
            transform.e * FACTOR,
            transform.f,
        )
        shapes = []
        for i, u in enumerate(units, start=1):
            for p in u["polys"]:
                shapes.append(({"type": "Polygon", "coordinates": p}, i))
        labels = rasterize(
            shapes,
            out_shape=coarse_shape,
            transform=coarse_transform,
            fill=0,
            dtype="int32",
        )
        if not labels.any():
            continue
        a90 = block_mean(np.where(np.isnan(a), np.nanmean(a), a), FACTOR)
        if wbm.exists():
            with rasterio.open(wbm) as ws:
                wt = block_mean(ws.read(1).astype("float32"), FACTOR)
            water = wt > 0.5
        else:
            water = np.zeros_like(labels, dtype=bool)
        slope = max_neighbour_slope_grade(a90, coarse_transform)
        steep = slope > SLOPE_GRADE_THRESHOLD
        un = steep | water

        dlat = abs(coarse_transform.e)
        dlon = abs(coarse_transform.a)
        lat_rows = coarse_transform.f - dlat * (np.arange(coarse_shape[0]) + 0.5)
        row_area = (dlat * M_PER_DEG_LAT) * (dlon * M_PER_DEG_LON_EQ * np.cos(np.radians(lat_rows)))
        wgt = np.broadcast_to(row_area[:, None], labels.shape)
        lab = labels.ravel()
        wt_flat = wgt.ravel()

        tot += np.bincount(lab, weights=wt_flat, minlength=n + 1)
        und += np.bincount(lab, weights=(wt_flat * un.ravel()), minlength=n + 1)
        steep_t += np.bincount(lab, weights=(wt_flat * steep.ravel()), minlength=n + 1)
        water_t += np.bincount(lab, weights=(wt_flat * water.ravel()), minlength=n + 1)

    rows = []
    worst = 0.0
    for i, u in enumerate(units, start=1):
        if tot[i] <= 0:
            continue
        km2 = tot[i] / 1e6
        err = abs(km2 - u["lau_km2"]) / u["lau_km2"] if u["lau_km2"] else 0.0
        worst = max(worst, err)
        rows.append(
            {
                "lau_id": u["id"],
                "municipio": u["name"],
                "lau_km2": round(u["lau_km2"], 3),
                "land_km2": round(km2, 3),
                "area_err_pct": round(err * 100, 2),
                "undevelopable_share": round(und[i] / tot[i], 4),
                "steep_share": round(steep_t[i] / tot[i], 4),
                "water_share": round(water_t[i] / tot[i], 4),
            }
        )
    rows.sort(key=lambda r: r["undevelopable_share"])
    (CACHE.parent / "municipal.json").write_text(json.dumps(rows, indent=2))
    tot_km2 = sum(r["land_km2"] for r in rows)
    print(f"municipios: {len(rows)}  total {tot_km2:.0f} km2  worst area err {worst * 100:.1f}%")

    def _fmt(rs):
        return ", ".join(f"{r['municipio']} {r['undevelopable_share']:.2f}" for r in rs)

    print("least:", _fmt(rows[:4]))
    print(
        "most: ", ", ".join(f"{r['municipio']} {r['undevelopable_share']:.2f}" for r in rows[-4:])
    )


def main() -> None:
    if sys.argv[1:2] == ["--sensitivity"]:
        sensitivity_report()
        return
    if sys.argv[1:2] == ["--municipal"]:
        municipal_report(sys.argv[2] if len(sys.argv) > 2 else "08", "municipal.json")
        return
    provinces = load_provinces()
    wanted = sys.argv[1:] or sorted(provinces)
    unknown = [w for w in wanted if w not in provinces]
    if unknown:
        raise SystemExit(f"unknown provincia: {unknown}")
    print(f"provincias: {len(provinces)} (crosswalk from {len(PROVINCIA_OF)} merged NUTS-3)")

    needed: set[tuple[int, int]] = set()
    for name in wanted:
        needed.update(tiles_for(provinces[name]))
    print(f"tiles needed: {len(needed)}")

    def dl(t: tuple[int, int]):
        lat, lon = t
        dem, wbm = tile_paths(lat, lon)
        if not dem.exists():
            fetch(dem_url(lat, lon, "DEM"), dem)
        if not wbm.exists():
            fetch(dem_url(lat, lon, "WBM"), wbm)

    with ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(dl, sorted(needed)))
    have = sum(1 for t in needed if tile_paths(*t)[0].exists())
    print(f"tiles on disk: {have}/{len(needed)}")

    rows = []
    for name in wanted:
        stats = province_stats(name, provinces[name])
        if stats:
            rows.append(stats)
            print(
                f"{name:<28} undevelopable={stats['undevelopable_share']:.3f} "
                f"(steep={stats['steep_share']:.3f} water={stats['water_share']:.3f})"
            )

    rows.sort(key=lambda r: r["undevelopable_share"])
    (CACHE.parent / "probe_results.json").write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {len(rows)} provincias to probe_results.json")
    print(
        "least constrained:",
        ", ".join(f"{r['provincia']} {r['undevelopable_share']:.2f}" for r in rows[:5]),
    )
    print(
        "most constrained: ",
        ", ".join(f"{r['provincia']} {r['undevelopable_share']:.2f}" for r in rows[-5:]),
    )


if __name__ == "__main__":
    main()
