"""Fetch SERPAVI (MIVAU) municipal rents — tax-exploitation of rental deposits.

Sistema Estatal de Referencia del Precio del Alquiler de Vivienda: the
official rent statistics built from ~37M rental-deposit observations.
This fetch keeps the **Municipios** sheet (8,894 rows — every municipio
is named, small villages included) melted to long form.

Source: 71 MB Excel, single static download:
  https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx

Sheet layout (wide): 4 id cols + 280 data cols = 20 measures × 14 years
(2011-2024). Measures (VC = vivienda colectiva, VU = unifamiliar, M/25/75 =
mediana/P25/P75): ALQM2_LV_* (EUR/m2/month rent), ALQTBID12_* (EUR/month),
SLVM2_* (surface m2), BI_ALVHEPCO_* (contract counts). Only populated
cells are kept (716,889; blanks are statistical suppression).

Verified 2026-10-06: Barcelona 2024 median 13.68 EUR/m2 ~ 1,147 EUR/mo
vs DIBA muni_bcn.rent_month 2024 (1,147) — consistent. Coverage: 2,555
municipios with 2024 median rent (29% of all; contract counts cover
~6,500). See docs/explorations/serpavi_probe.md.

Writes data/raw/serpavi_municipal.parquet (long: municipio x anyo x medida)
"""

from __future__ import annotations

import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = (
    "https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/"
    "2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx"
)
ACCESSED = date.today().isoformat()
# Validated anchors (probe doc): Barcelona city 2024 median, collective.
BARCELONA_2024 = 13.680434782608694
# Madrid distrito 04 (Salamanca) 2024 collective median, district-sheet anchor.
SALAMANCA_2024 = 18.30985915492958
YEAR_RE = re.compile(r"_(\d{2})$")


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)


def parse_municipios(xlsx: Path) -> tuple[list[dict], dict]:
    """Read the Municipios sheet; melt populated cells to long form."""
    import openpyxl  # deferred: only this fetch needs it

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb["Municipios"]
    hdr = [str(c) for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    if hdr[:4] != ["CPRO", "NPRO", "CUMUN", "NMUN"]:
        raise SystemExit(f"serpavi: unexpected header {hdr[:4]}")
    measures: list[tuple[int, str, int]] = []  # (col, measure_root, year)
    for i, h in enumerate(hdr[4:]):
        m = YEAR_RE.search(h)
        if not m:
            raise SystemExit(f"serpavi: non-year column {h}")
        yy = int(m.group(1))
        # Suffix is the last two digits of the year (11 -> 2011 ... 24 -> 2024).
        anyo = 2000 + yy if yy >= 11 else 2000 + yy + 100
        measures.append((4 + i, h[: m.start()], anyo))
    rows: list[dict] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        cpro, npro, cumun, nmun = row[:4]
        if cpro is None or cumun is None:
            continue
        for col, root, year in measures:
            v = row[col]
            if v is None or v == "":
                continue
            rows.append(
                {
                    "cpro": str(cpro).zfill(2),
                    "provincia": str(npro),
                    "codigo": str(cumun).zfill(5),
                    "municipio": str(nmun),
                    "anyo": year,
                    "medida": root,
                    "valor": float(v),
                }
            )
    bcn = [r for r in rows if r["codigo"] == "08019" and r["anyo"] == 2024]
    anchors: dict[str, object] = {}
    for root in ("ALQM2_LV_M_VC", "ALQM2_LV_25_VC", "ALQM2_LV_75_VC"):
        hit = [r["valor"] for r in bcn if r["medida"] == root]
        anchors[root] = hit[0] if hit else None
    return rows, anchors


def parse_distritos(xlsx: Path) -> list[dict]:
    """Read the Distritos sheet; melt populated cells to long form.

    Same 20 measures x 14 years as Municipios, keyed by 7-digit CUDIS district
    code (province+municipio+district). District names are not published in
    the workbook — only codes. Secciones censales (36,294 rows) are skipped:
    census-vintage geometry makes them unstable across years.
    """
    import openpyxl  # deferred: only this fetch needs it

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb["Distritos"]
    hdr = [str(c) for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    if hdr[:5] != ["CPRO", "LITPRO", "CUMUN", "LITMUN", "CUDIS"]:
        raise SystemExit(f"serpavi: unexpected district header {hdr[:5]}")
    measures: list[tuple[int, str, int]] = []
    for i, h in enumerate(hdr[5:]):
        m = YEAR_RE.search(h)
        if not m:
            raise SystemExit(f"serpavi: non-year district column {h}")
        yy = int(m.group(1))
        anyo = 2000 + yy if yy >= 11 else 2000 + yy + 100
        measures.append((5 + i, h[: m.start()], anyo))
    rows: list[dict] = []
    n_districts = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None or row[4] is None:
            continue
        n_districts += 1
        cudis = str(row[4]).zfill(7)
        for col, root, year in measures:
            v = row[col]
            if v is None or v == "":
                continue
            rows.append(
                {
                    "cpro": str(row[0]).zfill(2),
                    "provincia": str(row[1]),
                    "codigo": str(row[2]).zfill(5),
                    "municipio": str(row[3]),
                    "distrito": cudis,
                    "anyo": year,
                    "medida": root,
                    "valor": float(v),
                }
            )
    if n_districts != 10511:
        raise SystemExit(f"serpavi: district rows {n_districts} != 10511 — drift")
    return rows


def parse_provincial(xlsx: Path) -> list[dict]:
    """Read the Provincias sheet; melt populated cells to long form.

    Same 20 measures x 14 years, keyed by 2-digit CPRO. LITPRO names must
    match the mart provincia set (Ceuta/Melilla aggregate included here).
    """
    import openpyxl  # deferred: only this fetch needs it

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb["Provincias"]
    hdr = [str(c) for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    if hdr[:2] != ["CPRO", "LITPRO"]:
        raise SystemExit(f"serpavi: unexpected provincial header {hdr[:2]}")
    measures: list[tuple[int, str, int]] = []
    for i, h in enumerate(hdr[2:]):
        m = YEAR_RE.search(h)
        if not m:
            raise SystemExit(f"serpavi: non-year provincial column {h}")
        yy = int(m.group(1))
        anyo = 2000 + yy if yy >= 11 else 2000 + yy + 100
        measures.append((2 + i, h[: m.start()], anyo))
    # The provincial sheet does not reuse the municipal sheet's labels for
    # Alicante/Valencia (verified 2026-10-08; fail loudly on anything new).
    PROV_ALIAS = {
        "Alicante": "Alicante/Alacant",
        "Valencia/Valéncia": "Valencia/València",
    }
    rows: list[dict] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        name = PROV_ALIAS.get(str(row[1]), str(row[1]))
        for col, root, year in measures:
            v = row[col]
            if v is None or v == "":
                continue
            rows.append(
                {
                    "cpro": str(row[0]).zfill(2),
                    "provincia": name,
                    "anyo": year,
                    "medida": root,
                    "valor": float(v),
                }
            )
    return rows


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    xlsx = RAW / "serpavi_bd.xlsx"
    download(URL, xlsx)
    manifest.record(
        "data/raw/serpavi_bd.xlsx",
        {
            "url": URL,
            "operation": "SERPAVI alquiler municipal (MIVAU, fianzas)",
            "accessed": ACCESSED,
            "note": "71 MB Excel; Municipios sheet 8,894 rows x 280 cols",
        },
    )
    rows, anchors = parse_municipios(xlsx)
    if not rows:
        raise SystemExit("serpavi: zero rows — format changed?")
    # Guard: Barcelona 2024 median must match the probe's validated value.
    med = anchors.get("ALQM2_LV_M_VC")
    if med is None or abs(med - BARCELONA_2024) > 0.01:
        raise SystemExit(f"serpavi: Barcelona 2024 median {med} != {BARCELONA_2024} — drift")
    dist_rows = parse_distritos(xlsx)
    if not dist_rows:
        raise SystemExit("serpavi: zero district rows — format changed?")
    salamanca = [
        r["valor"]
        for r in dist_rows
        if r["distrito"] == "2807904" and r["anyo"] == 2024 and r["medida"] == "ALQM2_LV_M_VC"
    ]
    if not salamanca or abs(salamanca[0] - SALAMANCA_2024) > 0.01:
        got = salamanca[0] if salamanca else None
        raise SystemExit(f"serpavi: Salamanca 2024 median {got} != {SALAMANCA_2024} — drift")
    out = RAW / "parquet" / "serpavi_municipal.parquet"
    prov_rows = parse_provincial(xlsx)
    if not prov_rows:
        raise SystemExit("serpavi: zero provincial rows — format changed?")
    dist_out = RAW / "parquet" / "serpavi_distritos.parquet"
    prov_out = RAW / "parquet" / "serpavi_provincial.parquet"
    pq.write_table(pa.Table.from_pylist(rows), out)
    pq.write_table(pa.Table.from_pylist(dist_rows), dist_out)
    pq.write_table(pa.Table.from_pylist(prov_rows), prov_out)
    manifest.record(
        "data/raw/parquet/serpavi_provincial.parquet",
        {
            "url": URL,
            "operation": "SERPAVI alquiler provincial (MIVAU, fianzas)",
            "accessed": ACCESSED,
            "note": "long melt: provincia x anyo x medida; populated cells only",
        },
    )
    manifest.record(
        "data/raw/parquet/serpavi_distritos.parquet",
        {
            "url": URL,
            "operation": "SERPAVI alquiler por distrito censal (MIVAU, fianzas)",
            "accessed": ACCESSED,
            "note": "long melt: distrito x anyo x medida; populated cells only; "
            "district names unpublished (codes only); secciones skipped",
        },
    )
    manifest.record(
        "data/raw/parquet/serpavi_municipal.parquet",
        {
            "url": URL,
            "operation": "SERPAVI alquiler municipal (MIVAU, fianzas)",
            "accessed": ACCESSED,
            "note": "long melt: municipio x anyo x medida; populated cells only",
        },
    )
    print(
        f"serpavi: {len(rows)} cells, {len({r['codigo'] for r in rows})} municipios, "
        f"Barcelona2024 median={med:.2f}"
    )
    print(
        f"serpavi distritos: {len(dist_rows)} cells, "
        f"{len({r['distrito'] for r in dist_rows})} districts, "
        f"Salamanca2024 median={salamanca[0]:.2f}"
    )
    print(f"serpavi provincial: {len(prov_rows)} cells")


if __name__ == "__main__":
    main()
