"""Fetch AEAT dwellings declared in IRPF, by use (CCAA + provincia).

Source: AEAT Estadística de viviendas declaradas en el IRPF, table
"Valor catastral y uso de las viviendas clasificadas por Comunidad
autónoma y provincia" (static server-rendered HTML, no JS needed).
Each dwelling with cadastral value is classified by use over the tax
year: habitual, rented at any point, or at the owners' disposal
(generally a second home, possibly an empty dwelling with no use).

Coverage is the common fiscal territory ONLY: no País Vasco, Navarra,
Ceuta or Melilla rows exist in these tables — their absence is asserted,
never filled. Do not mix this split with SERPAVI's: AEAT prioritises
habitual use, MIVAU prioritises rental use for dual-use dwellings.

Writes data/raw/aeat_viviendas_uso_{year}.html (byte evidence) and
data/raw/parquet/aeat_viviendas_uso.parquet (parsed, both years).
"""

from __future__ import annotations

import re
import sys
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLE_PATHS = {
    2023: "jrubik19cd43289fdbce9fbcbd2391abc7741113e371d8.html",
    2024: "jrubik61a05e3830ecee0fbb552daa3b8d60a57826ffd9.html",
}
BASE = (
    "https://sede.agenciatributaria.gob.es/AEAT/Contenidos_Comunes/"
    "La_Agencia_Tributaria/Estadisticas/Publicaciones/sites/irpfvivienda"
)
URLS = {year: f"{BASE}/{year}/{path}" for year, path in TABLE_PATHS.items()}
RAW_HTML = {year: RAW / f"aeat_viviendas_uso_{year}.html" for year in URLS}
RAW_PARQUET = RAW / "parquet" / "aeat_viviendas_uso.parquet"

# The 15 CCAA rows in these tables. País Vasco, Navarra, Ceuta and Melilla
# are outside the common fiscal territory and have no rows: their absence
# below is the foral-exclusion assertion, not an omission to repair.
EXPECTED_CCAA = {
    "Andalucía",
    "Aragón",
    "Asturias, Principado de",
    "Balears, Illes",
    "Canarias",
    "Cantabria",
    "Castilla y León",
    "Castilla - La Mancha",
    "Cataluña",
    "Comunitat Valenciana",
    "Extremadura",
    "Galicia",
    "Madrid, Comunidad de",
    "Murcia, Región de",
    "Rioja, La",
}
# Single-province CCAA resolve through their CCAA row (no province rows).
AEAT_SINGLES = {
    "Asturias, Principado de": "33",
    "Balears, Illes": "07",
    "Cantabria": "39",
    "Madrid, Comunidad de": "28",
    "Murcia, Región de": "30",
    "Rioja, La": "26",
}
# AEAT short labels to INE cpro. Stable codes; each target must be a real
# mart cpro (cross-checked in tests). Nothing consumes the parquet yet —
# the first downstream join must assert full cpro coverage.
AEAT_PROV_CPRO = {
    "Almería": "04",
    "Cádiz": "11",
    "Córdoba": "14",
    "Granada": "18",
    "Huelva": "21",
    "Jaén": "23",
    "Málaga": "29",
    "Sevilla": "41",
    "Huesca": "22",
    "Teruel": "44",
    "Zaragoza": "50",
    "Las Palmas": "35",
    "S. C. Tenerife": "38",
    "Ávila": "05",
    "Burgos": "09",
    "León": "24",
    "Palencia": "34",
    "Salamanca": "37",
    "Segovia": "40",
    "Soria": "42",
    "Valladolid": "47",
    "Zamora": "49",
    "Albacete": "02",
    "Ciudad Real": "13",
    "Cuenca": "16",
    "Guadalajara": "19",
    "Toledo": "45",
    "Barcelona": "08",
    "Girona": "17",
    "Lleida": "25",
    "Tarragona": "43",
    "Alicante": "03",
    "Castellón": "12",
    "Valencia": "46",
    "Badajoz": "06",
    "Cáceres": "10",
    "A Coruña": "15",
    "Lugo": "27",
    "Ourense": "32",
    "Pontevedra": "36",
}
# Published % columns are shares of the row total, 2 decimals.
PCT_TOL = 0.015
# Publisher defect, measured 2026-10-09 on both live tables: their Total
# rows exceed the CCAA sums by exactly these dwellings (2023: 0.46%,
# 2024: 0.19% on n_total), unexplained anywhere in-page — possibly
# dwellings with no Spanish CCAA assignment (e.g. foreign-located),
# unverified. Gap composition is disposición-light both years (hab/alq/dis
# 47/47/5 in 2023, 69/18/13 in 2024), which sits uneasily with that story:
# open question, not evidence. Provinces and CCAA rows are internally
# consistent
# (shares, CCAA sums), so only the aggregate rows are affected. On an
# exact match the Total row is dropped from parsed output (the raw HTML
# keeps it); if AEAT revises either file the figures stop matching and
# the build fails loudly for re-investigation.
NACIONAL_KNOWN_GAPS = {
    2023: {"n_total": 82740, "n_habitual": 39225, "n_arrendadas": 39097, "n_disposicion": 4418},
    2024: {"n_total": 35476, "n_habitual": 24448, "n_arrendadas": 6432, "n_disposicion": 4596},
}


class _TableParser(HTMLParser):
    """Extract table01 data rows: (depth, label, 11 cells)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_table = self.in_th = self.in_td = False
        self.depth = None
        self.label = ""
        self.cells: list[str] = []
        self.rows: list[tuple[str, str, list[str]]] = []
        self.headers: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and attrs.get("id") == "table01":
            self.in_table = True
            return
        if not self.in_table:
            return
        if tag == "tr" and "class" in attrs:
            match = re.match(r"depth_(\d)", attrs["class"])
            if match:
                self.depth = match.group(1)
                self.label = ""
                self.cells = []
        elif tag == "th":
            self.in_th = True
            self.label = ""
        elif tag == "td":
            self.in_td = True
            self.cells.append("")

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        if not self.in_table and tag == "table":
            return
        if tag == "th":
            self.in_th = False
            text = " ".join(self.label.split())
            if self.depth is None:
                self.headers.append(text)
        elif tag == "td":
            self.in_td = False
        elif tag == "tr" and self.depth is not None:
            self.rows.append((self.depth, " ".join(self.label.split()), list(self.cells)))
            self.depth = None

    def handle_data(self, data):
        if self.in_th:
            self.label += data
        elif self.in_td and self.cells:
            self.cells[-1] += data


def _int(raw: str, where: str) -> int:
    raw = (raw or "").strip()
    if not re.fullmatch(r"\d{1,3}(\.\d{3})*", raw):
        raise SystemExit(f"aeat: unparsable count {raw!r} at {where}")
    return int(raw.replace(".", ""))


def _pct(raw: str, where: str) -> float:
    raw = (raw or "").strip()
    if not re.fullmatch(r"\d{1,3}(,\d+)?", raw):
        raise SystemExit(f"aeat: unparsable share {raw!r} at {where}")
    return float(raw.replace(",", "."))


def parse_aeat_table(html: str, year: int) -> list[dict]:
    """Parse one yearly use-split table to row dicts (raw labels kept).

    Fails loudly on year drift, header drift, row-count drift, unknown
    labels, share/count inconsistency, or CCAA/total aggregation mismatch.
    """
    if f"IRPF: {year}:" not in html:
        raise SystemExit(f"aeat: title year drift for {year}")
    ejercicios = set(re.findall(r"Ejercicio (\d{4})", html))
    if ejercicios != {str(year)}:
        raise SystemExit(f"aeat: ejercicio marker drift for {year}: {sorted(ejercicios)}")
    parser = _TableParser()
    parser.feed(html)
    # Header presence AND order: the cell-index mapping below assigns
    # cells[2,3,4]=habitual, [5,6,7]=arrendadas, [8,9,10]=disposición, so a
    # permuted use-block order must fail here, not parse silently.
    if "Localización de la vivienda" not in parser.headers:
        raise SystemExit(f"aeat: header drift for {year}, missing location header")
    order = [h for h in parser.headers if h in ("Vivienda habitual", "Arrendadas", "A disposición")]
    if order != ["Vivienda habitual", "Arrendadas", "A disposición"]:
        raise SystemExit(f"aeat: header order drift for {year}: {order}")
    if len(parser.rows) != 56:
        raise SystemExit(f"aeat: {len(parser.rows)} rows for {year}, want 56")
    depth0 = [r for r in parser.rows if r[0] == "0"]
    if len(depth0) != 1 or depth0[0][1] != "Total":
        raise SystemExit(f"aeat: first row is not Total for {year}")
    ccaa_labels = {label for depth, label, _ in parser.rows if depth == "1"}
    if ccaa_labels != EXPECTED_CCAA:
        raise SystemExit(f"aeat: CCAA drift for {year}: {sorted(ccaa_labels ^ EXPECTED_CCAA)}")
    prov_labels = [label for depth, label, _ in parser.rows if depth == "2"]
    if len(prov_labels) != 40:
        raise SystemExit(f"aeat: {len(prov_labels)} province rows for {year}, want 40")
    unknown = [label for label in prov_labels if label not in AEAT_PROV_CPRO]
    if unknown:
        raise SystemExit(f"aeat: unmapped provinces for {year}: {unknown}")
    rows = []
    for depth, label, cells in parser.rows:
        if len(cells) != 11:
            raise SystemExit(f"aeat: {len(cells)} cells for {label!r} {year}, want 11")
        vals = [_int(cells[i], (label, year, i)) for i in (0, 2, 5, 8, 1, 4, 7, 10)]
        (n_total, n_hab, n_alq, n_dis, vc_total, vc_hab, vc_alq, vc_dis) = vals
        if n_total <= 0:
            raise SystemExit(f"aeat: non-positive total for {label!r} {year}")
        shares = [_pct(cells[i], (label, year, i)) for i in (3, 6, 9)]
        for n, share in zip((n_hab, n_alq, n_dis), shares, strict=True):
            if abs(share - 100.0 * n / n_total) >= PCT_TOL:
                raise SystemExit(f"aeat: share/count mismatch for {label!r} {year}")
        if depth == "0":
            grano, cpro = "total_nacional", None
        elif depth == "2":
            grano, cpro = "provincia", AEAT_PROV_CPRO[label]
        elif label in AEAT_SINGLES:
            grano, cpro = "ccaa_uniprovincial", AEAT_SINGLES[label]
        else:
            grano, cpro = "ccaa", None
        rows.append(
            {
                "anyo": year,
                "territorio": label,
                "grano": grano,
                "cpro": cpro,
                "n_total": n_total,
                "vc_medio_total": vc_total,
                "n_habitual": n_hab,
                "pct_habitual": shares[0],
                "vc_medio_habitual": vc_hab,
                "n_arrendadas": n_alq,
                "pct_arrendadas": shares[1],
                "vc_medio_arrendadas": vc_alq,
                "n_disposicion": n_dis,
                "pct_disposicion": shares[2],
                "vc_medio_disposicion": vc_dis,
            }
        )
    # Same-source aggregation: CCAA rows equal their province sums, Total
    # equals the CCAA sum, exactly (integer counts, no rounding involved).
    # All three use counts are compared, not just the row total.
    uses = ("n_total", "n_habitual", "n_arrendadas", "n_disposicion")
    by_cpro = {r["cpro"]: r for r in rows if r["grano"] == "provincia"}
    grouped = sorted(c for cpros in AEAT_CCAA_CPROS.values() for c in cpros)
    if grouped != sorted(by_cpro):
        raise SystemExit(f"aeat: CCAA groups do not partition provinces for {year}")
    by_label = {(r["territorio"], r["grano"]): r for r in rows}
    for ccaa, cpros in AEAT_CCAA_CPROS.items():
        for use in uses:
            want = sum(by_cpro[c][use] for c in cpros)
            got = by_label[(ccaa, "ccaa")][use]
            if want != got:
                raise SystemExit(f"aeat: {ccaa!r} {year} disagrees with its provinces on {use}")
    uses = ("n_total", "n_habitual", "n_arrendadas", "n_disposicion")
    total_row = by_label[("Total", "total_nacional")]
    gaps = {}
    for use in uses:
        parts = sum(r[use] for r in rows if r["grano"] in ("provincia", "ccaa_uniprovincial"))
        gaps[use] = total_row[use] - parts
    if any(gaps.values()):
        expected = NACIONAL_KNOWN_GAPS.get(year)
        if expected is None or any(gaps[u] != expected[u] for u in uses):
            raise SystemExit(f"aeat: nacional mismatch {year}: {gaps}")
        print(f"aeat: {year} Total row dropped (known publisher gap {gaps})")
        rows = [r for r in rows if r["grano"] != "total_nacional"]
    return rows


# Multi-province CCAA to their INE cpros, for the aggregation check.
AEAT_CCAA_CPROS = {
    "Andalucía": ["04", "11", "14", "18", "21", "23", "29", "41"],
    "Aragón": ["22", "44", "50"],
    "Canarias": ["35", "38"],
    "Castilla y León": ["05", "09", "24", "34", "37", "40", "42", "47", "49"],
    "Castilla - La Mancha": ["02", "13", "16", "19", "45"],
    "Cataluña": ["08", "17", "25", "43"],
    "Comunitat Valenciana": ["03", "12", "46"],
    "Extremadura": ["06", "10"],
    "Galicia": ["15", "27", "32", "36"],
}


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)


def main() -> None:
    all_rows: list[dict] = []
    for year, url in URLS.items():
        dest = RAW_HTML[year]
        download(url, dest)
        html = dest.read_text(encoding="utf-8")
        rows = parse_aeat_table(html, year)
        all_rows.extend(rows)
        nacional = [r for r in rows if r["grano"] == "total_nacional"]
        if nacional:
            base, tag = nacional[0], "nacional"
        else:
            base = {
                "n_total": sum(r["n_total"] for r in rows),
                "n_disposicion": sum(r["n_disposicion"] for r in rows),
            }
            tag = "parts sum (Total row dropped)"
        print(
            f"aeat {year}: {len(rows)} rows, {tag}={base['n_total']} "
            f"disposicion={100.0 * base['n_disposicion'] / base['n_total']:.2f}%"
        )
        manifest.record(
            f"data/raw/aeat_viviendas_uso_{year}.html",
            {
                "url": url,
                "publisher": "AEAT",
                "operation": "IRPFVIV",
                "accessed": date.today().isoformat(),
            },
        )
    n = csvx.write_parquet(all_rows, RAW_PARQUET)
    manifest.record(
        "data/raw/parquet/aeat_viviendas_uso.parquet",
        {
            "urls": URLS,
            "publisher": "AEAT",
            "operation": "IRPFVIV",
            "accessed": date.today().isoformat(),
        },
    )
    print(f"aeat viviendas uso: {n} rows -> {RAW_PARQUET}")


if __name__ == "__main__":
    main()
