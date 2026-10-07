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
    out = RAW / "parquet" / "serpavi_municipal.parquet"
    pq.write_table(pa.Table.from_pylist(rows), out)
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


if __name__ == "__main__":
    main()
