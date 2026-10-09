"""Fetch Junta de Andalucía RMDVP table 01: solicitudes e inscripciones.

Source: Registro Municipal de Demandantes de Vivienda Protegida monthly
statistics (Consejería de Vivienda). Each month publishes table 01
("solicitudes y estado de inscripciones") as PDF plus an .xls twin with
the same figures at municipio grain: solicitudes, inscripciones total,
activas, canceladas por adjudicación, and caducadas y otros, with
province subtotal rows and a reconciling Andalucía total row.

Only the .xls twins are consumed (machine-readable, static hrefs in the
year archive pages). Monthly coverage with .xls twins runs 2020-12, then
2021-01 onward without gaps; earlier years (2015-2019) are PDF-only and
out of scope.

Semantics: end-of-month STOCK of registered demand (registrations and
their states as of the reference month), not a flow. The in-file date
filter ("Fecha de Solicitud está entre ... y <month-end>") bounds which
solicitudes are included. Only municipalities with listed rows are
stored; absent municipalities have no recorded solicitudes in the file
and are NOT zero-filled.

Writes data/raw/rmdvp/{yyyymm}_rmdvp01.xls (byte evidence) and
data/raw/parquet/rmdvp_inscripciones.parquet (parsed, all months).
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
import urllib.request
from pathlib import Path

import xlrd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

INDEX_URL = (
    "https://www.juntadeandalucia.es/organismos/"
    "viviendajuventudyordenaciondelterritorio/areas/vivienda-rehabilitacion/"
    "vivienda-protegida/paginas/rmdv-estadistica-mensual.html"
)
HOST = "https://www.juntadeandalucia.es"
RAW_DIR = RAW / "rmdvp"
RAW_PARQUET = RAW / "parquet" / "rmdvp_inscripciones.parquet"

# Uppercase publisher labels to INE cpro. The in-file province filter
# lists exactly these eight, comma-joined, in this order.
RMDVP_PROV_CPRO = {
    "ALMERÍA": "04",
    "CÁDIZ": "11",
    "CÓRDOBA": "14",
    "GRANADA": "18",
    "HUELVA": "21",
    "JAÉN": "23",
    "MÁLAGA": "29",
    "SEVILLA": "41",
}
EXPECTED_PROV_FILTER = "ALMERÍA, CÁDIZ, CÓRDOBA, GRANADA, HUELVA, JAÉN, MÁLAGA, SEVILLA"
# Cumulative solicitud window start seen in every file checked
# (2021-01 through 2026-08): 39814 == 2009-01-01. Pinned so a silent
# window change fails loudly instead of shifting the stock contents.
EXPECTED_WINDOW_START = 39814
TITLE_1 = "RMDVP solicitudes e inscripciones"
TITLE_2 = "Registros Municipales de Demandantes de Vivienda Protegida"
TABLE_SUBTITLE = "Solicitudes y estado de inscripciones"
HEADER_19 = {
    5: "Provincia",
    9: "Municipio",
    13: "Código INE",
    17: "Solicitudes",
    18: "Inscripciones",
}
HEADER_20 = {
    18: "Total",
    19: "Activas",
    21: "Canceladas por Adjudicación",
    23: "Caducadas y otros",
}
COUNT_COLS = (17, 18, 19, 21, 23)
USES = ("inscripciones", "activas", "canceladas", "caducadas")
# Excel serial epoch (1899-12-30) for binding filename months to the
# in-file filter/execution serials.
EXCEL_EPOCH = _dt.date(1899, 12, 30)


def _month_end_serial(yyyymm: str) -> int:
    year, month = int(yyyymm[:4]), int(yyyymm[4:])
    last = [
        31,
        29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ][month - 1]
    return (_dt.date(year, month, last) - EXCEL_EPOCH).days


def _text(value) -> str:
    return str(value).strip().strip("'")


def _count(value, where: str) -> int:
    raw = _text(value)
    if raw == "":
        raise SystemExit(f"rmdvp: empty count at {where}")
    try:
        number = float(raw.replace(",", "."))
    except ValueError:
        raise SystemExit(f"rmdvp: unparsable count {raw!r} at {where}") from None
    if number < 0 or number != int(number):
        raise SystemExit(f"rmdvp: non-integral/negative count {raw!r} at {where}")
    return int(number)


def parse_rmdvp_rows(cells: list[list], yyyymm: str) -> list[dict]:
    """Parse one month's table-01 cell grid to row dicts.

    `cells` is a row-major grid of raw xlrd values (or test doubles).
    Fails loudly on layout drift, month mismatch, unknown labels,
    count/identity mismatch, or aggregation mismatch.
    """
    ncols = max(len(r) for r in cells)
    if ncols != 24:
        raise SystemExit(f"rmdvp {yyyymm}: {ncols} columns, want 24")

    def get(r: int, c: int):
        return cells[r][c] if c < len(cells[r]) else ""

    for col, want in HEADER_19.items():
        if _text(get(19, col)) != want:
            raise SystemExit(f"rmdvp {yyyymm}: header drift at row 19 col {col}")
    for col, want in HEADER_20.items():
        if _text(get(20, col)) != want:
            raise SystemExit(f"rmdvp {yyyymm}: subheader drift at row 20 col {col}")
    if _text(get(6, 0)) != TITLE_1 or _text(get(7, 0)) != TITLE_2:
        raise SystemExit(f"rmdvp {yyyymm}: title drift")
    if _text(get(3, 11)) != TABLE_SUBTITLE:
        raise SystemExit(f"rmdvp {yyyymm}: subtitle drift")
    if _text(get(13, 3)) != "Provincias:" or _text(get(13, 7)) != EXPECTED_PROV_FILTER:
        raise SystemExit(f"rmdvp {yyyymm}: province filter drift")
    if _text(get(12, 4)) != "Fecha de Solicitud está entre:":
        raise SystemExit(f"rmdvp {yyyymm}: filter label drift")
    serials = set()
    for r in range(9, 15):
        for c in range(ncols):
            raw = _text(get(r, c))
            if re.fullmatch(r"\d{5}(\.0)?", raw):
                serials.add(int(float(raw)))
    if EXPECTED_WINDOW_START not in serials:
        raise SystemExit(f"rmdvp {yyyymm}: window start drift: {sorted(serials)}")
    month_end = _month_end_serial(yyyymm)
    if max(serials) != month_end:
        raise SystemExit(f"rmdvp {yyyymm}: filter end {max(serials)} != month end {month_end}")
    rows: list[dict] = []
    total_row = None
    r = 21
    while True:
        if r >= len(cells):
            raise SystemExit(f"rmdvp {yyyymm}: no Total row found")
        c5 = _text(get(r, 5))
        if c5 == "Total":
            vals = {
                u: _count(get(r, c), (yyyymm, "total", u))
                for u, c in zip(("solicitudes",) + USES, COUNT_COLS, strict=True)
            }
            total_row = {
                "yyyymm": yyyymm,
                "grano": "total_andalucia",
                "ine": None,
                "municipio": None,
                "provincia": None,
                "cpro": None,
                **vals,
            }
            break
        ine = _text(get(r, 13))
        if ine:
            if not re.fullmatch(r"\d{5}", ine) or ine[:2] not in set(RMDVP_PROV_CPRO.values()):
                raise SystemExit(f"rmdvp {yyyymm}: bad INE {ine!r} at row {r}")
            prov = _text(get(r, 6))
            if prov not in RMDVP_PROV_CPRO:
                raise SystemExit(f"rmdvp {yyyymm}: bad province {prov!r} at row {r}")
            if ine[:2] != RMDVP_PROV_CPRO[prov]:
                raise SystemExit(
                    f"rmdvp {yyyymm}: INE {ine} disagrees with province {prov} at row {r}"
                )
            muni = _text(get(r, 9))
            if not muni:
                raise SystemExit(f"rmdvp {yyyymm}: empty municipio at row {r}")
            vals = {
                u: _count(get(r, c), (yyyymm, ine, u))
                for u, c in zip(("solicitudes",) + USES, COUNT_COLS, strict=True)
            }
            rows.append(
                {
                    "yyyymm": yyyymm,
                    "grano": "municipio",
                    "ine": ine,
                    "municipio": muni,
                    "provincia": prov,
                    "cpro": RMDVP_PROV_CPRO[prov],
                    **vals,
                }
            )
        elif _text(get(r, 9)) == "Total" and c5 in RMDVP_PROV_CPRO:
            vals = {
                u: _count(get(r, c), (yyyymm, c5, u))
                for u, c in zip(("solicitudes",) + USES, COUNT_COLS, strict=True)
            }
            rows.append(
                {
                    "yyyymm": yyyymm,
                    "grano": "provincia",
                    "ine": None,
                    "municipio": None,
                    "provincia": c5,
                    "cpro": RMDVP_PROV_CPRO[c5],
                    **vals,
                }
            )
        else:
            raise SystemExit(f"rmdvp {yyyymm}: unclassifiable row {r}")
        r += 1
    r += 1
    while r < len(cells) and not any(_text(get(r, c)) for c in range(ncols)):
        r += 1  # publisher leaves a blank row between Total and footer
    if r >= len(cells):
        raise SystemExit(f"rmdvp {yyyymm}: no execution row found")
    exec_label = _text(get(r, 5))
    if not exec_label.startswith("Fecha de Ejecución del informe:"):
        raise SystemExit(f"rmdvp {yyyymm}: execution row drift")
    exec_serial_raw = _text(get(r, 10))
    if not re.fullmatch(r"\d{5}(\.\d+)?", exec_serial_raw):
        raise SystemExit(f"rmdvp {yyyymm}: non-numeric execution serial")
    if float(exec_serial_raw) <= month_end:
        raise SystemExit(f"rmdvp {yyyymm}: execution predates month end")
    munis = [x for x in rows if x["grano"] == "municipio"]
    if len({m["ine"] for m in munis}) != len(munis):
        raise SystemExit(f"rmdvp {yyyymm}: duplicate INE codes")
    if not munis:
        raise SystemExit(f"rmdvp {yyyymm}: no municipio rows")
    for row in rows + [total_row]:
        parts = row["activas"] + row["canceladas"] + row["caducadas"]
        if row["inscripciones"] != parts:
            key = row["ine"] or row["provincia"] or "total"
            raise SystemExit(f"rmdvp {yyyymm}: identity mismatch at {key}")
    by_prov = {x["provincia"]: x for x in rows if x["grano"] == "provincia"}
    if set(by_prov) != set(RMDVP_PROV_CPRO):
        drift = sorted(set(by_prov) ^ set(RMDVP_PROV_CPRO))
        raise SystemExit(f"rmdvp {yyyymm}: province subtotal drift: {drift}")
    for prov, cpro in RMDVP_PROV_CPRO.items():
        members = [m for m in munis if m["cpro"] == cpro]
        for use in ("solicitudes",) + USES:
            want = sum(m[use] for m in members)
            if by_prov[prov][use] != want:
                raise SystemExit(f"rmdvp {yyyymm}: {prov} subtotal disagrees on {use}")
    parts = [x for x in rows if x["grano"] in ("municipio",)]
    for use in ("solicitudes",) + USES:
        if sum(x[use] for x in parts) != total_row[use]:
            raise SystemExit(f"rmdvp {yyyymm}: Total disagrees with municipios on {use}")
    rows.append(total_row)
    return rows


# Known blind spot: if the publisher freezes the .xls twins and moves new
# data to .xlsx, discovery keeps finding the old files and fetch succeeds
# on stale data. Execution-date recency cannot catch it (stale files still
# postdate their own month-end). Re-check the archive pages by eye when a
# new reference month yields no new file within two publications.
def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def discover_months() -> dict[str, str]:
    """Scrape the index + year archive pages for table-01 .xls hrefs."""
    index = _get(INDEX_URL).decode("utf-8", errors="replace")
    year_pat = r'href="([^"]*rmdv-estadistica-mensual-\d{4}\.html)"'
    year_pages = sorted(set(re.findall(year_pat, index)))
    if not year_pages:
        raise SystemExit("rmdvp: no year archive pages found on index")
    months: dict[str, str] = {}
    pages = ["rmdv-estadistica-mensual.html"] + [p.split("/")[-1] for p in year_pages]
    area = "areas/vivienda-rehabilitacion/vivienda-protegida/paginas"
    base = f"{HOST}/organismos/viviendajuventudyordenaciondelterritorio/{area}"
    for page in pages:
        html = _get(f"{base}/{page}").decode("utf-8", errors="replace")
        pat = r'href="([^"]*?(\d{6})_rmdvp01[^"]*?\.xls)"'
        for path, yyyymm in set(re.findall(pat, html)):
            months[yyyymm] = path if path.startswith("http") else HOST + path
    if not months:
        raise SystemExit("rmdvp: no table-01 files discovered")
    ordered = sorted(months)
    if ordered[0] != "202012":
        raise SystemExit(f"rmdvp: series starts at {ordered[0]}, want 202012")
    prev = _dt.date(int(ordered[0][:4]), int(ordered[0][4:]), 1)
    for yyyymm in ordered[1:]:
        cur = _dt.date(int(yyyymm[:4]), int(yyyymm[4:]), 1)
        nxt = _dt.date(prev.year + (prev.month == 12), prev.month % 12 + 1, 1)
        if cur != nxt:
            raise SystemExit(f"rmdvp: month gap between {prev:%Y-%m} and {cur:%Y-%m}")
        prev = cur
    return months


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    months = discover_months()
    print(f"rmdvp: {len(months)} months {min(months)}..{max(months)}")
    all_rows: list[dict] = []
    for yyyymm in sorted(months):
        dest = RAW_DIR / f"{yyyymm}_rmdvp01.xls"
        blob = _get(months[yyyymm])
        dest.write_bytes(blob)
        sheet = xlrd.open_workbook(file_contents=blob).sheet_by_index(0)
        grid = [[sheet.cell(r, c).value for c in range(sheet.ncols)] for r in range(sheet.nrows)]
        rows = parse_rmdvp_rows(grid, yyyymm)
        munis = sum(1 for x in rows if x["grano"] == "municipio")
        total = next(x for x in rows if x["grano"] == "total_andalucia")
        print(f"rmdvp {yyyymm}: {munis} municipios, inscripciones={total['inscripciones']}")
        all_rows.extend(rows)
        manifest.record(
            f"data/raw/rmdvp/{yyyymm}_rmdvp01.xls",
            {"url": months[yyyymm], "publisher": "Junta de Andalucía", "operation": "RMDVP"},
        )
    n = csvx.write_parquet(all_rows, RAW_PARQUET)
    manifest.record(
        "data/raw/parquet/rmdvp_inscripciones.parquet",
        {
            "publisher": "Junta de Andalucía",
            "operation": "RMDVP",
            "months": f"{min(months)}..{max(months)}",
        },
    )
    print(f"rmdvp inscripciones: {n} rows -> {RAW_PARQUET}")


if __name__ == "__main__":
    main()
