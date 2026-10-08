"""Fetch CGPJ launch (desahucio) and mortgage-foreclosure series by province.

The CGPJ "efecto de la crisis" provincial series workbook consolidates
quarterly launches practiced by first-instance courts (exhaustive since
2013Q1, split by mortgage / LAU-rent / other causes) and mortgage
enforcement filings (Ejecuciones hipotecarias, since 2007Q1). Only quarterly
columns (YY-TQ) are parsed; annual 'Total YYYY' columns and the trailing
'Evolución' rate blocks are skipped (derived statistics, not levels).

Launches count every property whose handover is ordered (urban or rural,
dwelling or not) — a distress indicator, not a count of tenant evictions.
Service-common (servicios comunes) figures are never mixed in: the parsed
sheets are the exhaustive juzgados series. Ceuta/Melilla have no provincial
rows (50 provinces + national TOTAL, which is skipped).
"""

from __future__ import annotations

import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = (
    "https://www.poderjudicial.es/stfls/ESTADISTICA/FICHEROS/Crisis/"
    "Series%20-%20Efecto%20de%20la%20crisis%20en%20los%20organos%20judiciales%20"
    "por%20provincias%201T-2026_revisado.xlsx"
)
RAW_XLSX = RAW / "cgpj_crisis_provincias.xlsx"
RAW_PARQUET = RAW / "parquet" / "desahucios_provincia.parquet"
PUBLISHER = "CGPJ, Estadística Judicial (efecto de la crisis, series provinciales)"
SHEETS = {
    "Lanzamientos pract. Total prov": "lanz_total",
    "Lanzamientos E.hipotecaria prov": "lanz_hipoteca",
    "Lanzamientos L.A.U. prov": "lanz_lau",
    "Lanzamientos. Otros prov": "lanz_otros",
    " Ej.Hipot por provincias": "ej_hipotecarias",
}
QUARTER_RE = re.compile(r"^(\d{2})-T([1-4])$")
# CGPJ CAPS labels → mart provincia names (verified 2026-10-08; fail loudly on more).
PROVINCIAS = {
    "ALMERIA": "Almería",
    "CADIZ": "Cádiz",
    "CORDOBA": "Córdoba",
    "GRANADA": "Granada",
    "HUELVA": "Huelva",
    "JAEN": "Jaén",
    "MALAGA": "Málaga",
    "SEVILLA": "Sevilla",
    "HUESCA": "Huesca",
    "TERUEL": "Teruel",
    "ZARAGOZA": "Zaragoza",
    "ASTURIAS": "Asturias",
    "ILLES BALEARS": "Balears, Illes",
    "LAS PALMAS": "Palmas, Las",
    "SANTA CRUZ DE TENERIFE": "Santa Cruz de Tenerife",
    "CANTABRIA": "Cantabria",
    "AVILA": "Ávila",
    "BURGOS": "Burgos",
    "LEON": "León",
    "PALENCIA": "Palencia",
    "SALAMANCA": "Salamanca",
    "SEGOVIA": "Segovia",
    "SORIA": "Soria",
    "VALLADOLID": "Valladolid",
    "ZAMORA": "Zamora",
    "ALBACETE": "Albacete",
    "CIUDAD REAL": "Ciudad Real",
    "CUENCA": "Cuenca",
    "GUADALAJARA": "Guadalajara",
    "TOLEDO": "Toledo",
    "BARCELONA": "Barcelona",
    "GIRONA": "Girona",
    "LLEIDA": "Lleida",
    "TARRAGONA": "Tarragona",
    "ALICANTE": "Alicante/Alacant",
    "CASTELLON": "Castellón/Castelló",
    "VALENCIA": "Valencia/València",
    "BADAJOZ": "Badajoz",
    "CACERES": "Cáceres",
    "A CORUÑA": "Coruña, A",
    "LUGO": "Lugo",
    "OURENSE": "Ourense",
    "PONTEVEDRA": "Pontevedra",
    "MADRID": "Madrid",
    "MURCIA": "Murcia",
    "NAVARRA": "Navarra",
    "ARABA/ALAVA": "Araba/Álava",
    "GIPUZKOA": "Gipuzkoa",
    "BIZKAIA": "Bizkaia",
    "LA RIOJA": "Rioja, La",
}


def download() -> Path:
    req = urllib.request.Request(URL, headers={"User-Agent": "housing-data-analysis/1.0"})
    with urllib.request.urlopen(req, timeout=600) as response:  # noqa: S310 (pinned CGPJ host)
        contents = response.read()
    if not contents.startswith(b"PK"):
        raise SystemExit("desahucios: unexpected payload (not a ZIP/XLSX)")
    tmp = RAW_XLSX.with_suffix(RAW_XLSX.suffix + ".tmp")
    tmp.write_bytes(contents)
    tmp.replace(RAW_XLSX)
    manifest.record(
        str(RAW_XLSX.relative_to(Path.cwd())),
        {
            "url": URL,
            "publisher": PUBLISHER,
            "accessed": date.today().isoformat(),
            "note": (
                "consolidated provincial crisis series through 2026Q1; sheets pinned by fetcher"
            ),
        },
    )
    return RAW_XLSX


def main() -> None:
    path = download()
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    missing = [s for s in SHEETS if s not in book.sheetnames]
    if missing:
        raise SystemExit(f"desahucios: missing sheets {missing}")
    cells: dict[tuple[str, int, int], dict] = {}
    seen_labels: set[str] = set()
    for sheet, measure in SHEETS.items():
        rows = list(book[sheet].iter_rows(values_only=True))
        header_idx = next(
            i
            for i, r in enumerate(rows)
            if any(QUARTER_RE.match(str(c).strip()) for c in r[2:8] if c is not None)
        )
        header = rows[header_idx]
        quarters = []
        for cell in header[2:]:
            if cell is None:
                continue
            match = QUARTER_RE.match(str(cell).strip())
            if match:
                yy, quarter = int(match[1]), int(match[2])
                quarters.append((2000 + yy, quarter))
        if not quarters:
            raise SystemExit(f"desahucios: no quarter columns in {sheet!r}")
        for row in rows[header_idx + 1 :]:
            label = str(row[1]).strip() if row[1] is not None else ""
            if not label or label == "TOTAL":
                break
            if label not in PROVINCIAS:
                raise SystemExit(f"desahucios: unmapped province {label!r} in {sheet!r}")
            seen_labels.add(label)
            values = list(row[2 : 2 + len(quarters)])
            if len(values) != len(quarters):
                raise SystemExit(f"desahucios: short row {label} in {sheet!r}")
            for (year, quarter), value in zip(quarters, values, strict=True):
                key = (label, year, quarter)
                cell = cells.setdefault(key, {"cgpj": label, "anyo": year, "trimestre": quarter})
                if value is None or (isinstance(value, str) and not value.strip()):
                    cell[measure] = None
                else:
                    cell[measure] = int(value)
    if seen_labels != set(PROVINCIAS):
        raise SystemExit(f"desahucios: province set changed: {sorted(seen_labels)}")
    rows = []
    for (label, year, quarter), cell in sorted(cells.items()):
        row = {
            "provincia": PROVINCIAS[label],
            "anyo": year,
            "trimestre": quarter,
        }
        for measure in SHEETS.values():
            row[measure] = cell.get(measure)
        rows.append(row)
    launch_years = sorted({r["anyo"] for r in rows if r["lanz_total"] is not None})[::-1]
    print(f"desahucios: {len(rows)} province-quarters")
    print("launch years:", launch_years[0], "...", launch_years[-1])
    parquet = Path(str(RAW_PARQUET.relative_to(Path.cwd())))
    parquet.parent.mkdir(parents=True, exist_ok=True)
    tmp = parquet.with_suffix(parquet.suffix + ".tmp")
    pq.write_table(pa.Table.from_pylist(rows), tmp)
    tmp.replace(parquet)
    manifest.record(
        str(RAW_PARQUET.relative_to(Path.cwd())),
        {
            "url": URL,
            "publisher": PUBLISHER,
            "accessed": date.today().isoformat(),
            "note": "quarterly launches (2013Q1–) + foreclosure filings (2007Q1–); "
            "annual totals and Evolución blocks skipped; service-common figures excluded",
        },
    )
    print(
        "nulls:",
        {
            "lanz_total": sum(r["lanz_total"] is None for r in rows),
            "ej_hipotecarias": sum(r["ej_hipotecarias"] is None for r in rows),
        },
    )


if __name__ == "__main__":
    main()
