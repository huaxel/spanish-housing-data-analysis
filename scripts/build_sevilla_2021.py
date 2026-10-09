"""Separate census-2021 municipal profile; not available supply or a causal model."""

from __future__ import annotations

import argparse
import csv
import io
import math
import re
import sys
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import manifest, muni_names  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

YEAR = 2021
DATABASE = PROCESSED / "sevilla_2021.duckdb"
URLS = {
    "households": "https://www.ine.es/jaxi/files/tpx/csv_bd/59543.csv",
    "metadata": "https://www.ine.es/jaxi/Tabla.htm?tpx=59543&L=0",
    "tenure": "https://www.ine.es/jaxi/files/tpx/csv_bd/59529.csv",
    "tenure_metadata": "https://www.ine.es/jaxi/Tabla.htm?tpx=59529&L=0",
}
INPUTS = {
    "households": ROOT / "data/raw/censo2021_hogares_59543.csv",
    "metadata": ROOT / "data/raw/censo2021_hogares_59543.html",
    "tenure": ROOT / "data/raw/censo2021_tenencia_59529.csv",
    "tenure_metadata": ROOT / "data/raw/censo2021_tenencia_59529.html",
    "stock": ROOT / "data/raw/parquet/censo2021_intensidad.parquet",
    "rent": ROOT / "data/raw/parquet/serpavi_municipal.parquet",
}
FIELDS = [
    "codigo",
    "municipio",
    "hogares",
    "viviendas",
    "vacias_consumo",
    "renta_vc",
    "estado_stock",
    "estado_renta",
    "perfil_completo",
]


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def validate_metadata(html):
    parser = Text()
    parser.feed(html)
    text = re.sub(r"\s+", " ", " ".join(parser.parts))
    for expected in [
        "Censo de Población y Viviendas 2021",
        "Hogares por municipios y tamaño del hogar",
        "Unidades: hogares",
    ]:
        if expected not in text:
            raise ValueError("Household source definition/year/unit changed")


def integer(value):
    value = value.strip()
    if value in {"", ".", ".."}:
        return None
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:\.\d{3})+)", value):
        raise ValueError("Unexpected household count")
    return int(value.replace(".", ""))


def households(contents, metadata):
    validate_metadata(metadata)
    reader = csv.DictReader(io.StringIO(contents), delimiter="\t")
    if reader.fieldnames != ["Total Nacional", "Municipios", "Tamaño del hogar", "Total"]:
        raise ValueError("Household CSV schema changed")
    categories = {
        "Total (tamaño del hogar)",
        "1 persona",
        "2 personas",
        "3 personas",
        "4 personas",
        "5 o más personas",
    }
    seen, output = set(), {}
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Malformed household row")
        label, category = row["Municipios"], row["Tamaño del hogar"]
        if row["Total Nacional"] != "Total Nacional" or category not in categories:
            raise ValueError("Household dimensions changed")
        value = integer(row["Total"])
        key = (label, category)
        if key in seen:
            raise ValueError("Duplicate household cell")
        seen.add(key)
        if not label:
            continue  # national margin, not a municipal household count
        match = re.fullmatch(r"(\d{5}) (\S.*)", label)
        if not match:
            raise ValueError("Invalid household municipality key")
        code, name = match.groups()
        if code.startswith("41") and category == "Total (tamaño del hogar)":
            if code in output or code.endswith("999") or re.match(r"resto\b", name, re.I):
                raise ValueError("Ambiguous or aggregate household key")
            output[code] = {"codigo": code, "municipio": name, "hogares": value}
    if not output:
        raise ValueError("No Sevilla household totals")
    return output


def validate_number(value, count=False):
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Nonfinite or nonnumeric source value")
    if count and (value < 0 or int(value) != value):
        raise ValueError("Invalid census count")


def label_matches(name, expected):
    # Province qualifiers are not a benign spelling of a city.
    if "(provincia)" in name.casefold() or re.match(r"resto\b", name, re.I):
        return False
    return muni_names.muni_key(name) == muni_names.muni_key(expected)


def derive(hh, stock_rows, rent_rows):
    stock, rent, excluded = {}, {}, []
    measures = {"Viviendas totales", "Viviendas vacías"}
    for source, rows in [("stock", stock_rows), ("rent", rent_rows)]:
        for row in rows:
            if source == "stock":
                if row["provincia_cod"] != "41" or row["medida"] not in measures:
                    continue
            elif row["cpro"] != "41" or row["anyo"] != YEAR or row["medida"] != "ALQM2_LV_M_VC":
                continue
            code, name, value = row["codigo"], row["municipio"], row["valor"]
            if not isinstance(code, str) or not re.fullmatch(r"41\d{3}|41", code):
                raise ValueError("Conflicting province/municipal code")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Missing source municipality label")
            validate_number(value, count=source == "stock")
            if len(code) != 5 or code.endswith("999"):
                excluded.append(
                    (source, code, name, row["medida"], None if value is None else str(value))
                )
                continue
            if code not in hh:
                raise ValueError("Selected municipal source is outside household universe")
            target = stock if source == "stock" else rent
            target.setdefault(code, []).append(row)
    output = []
    for code, h in sorted(hh.items()):
        srows, rrows = stock.get(code, []), rent.get(code, [])
        sstatus, rstatus = "missing", "missing"
        total = vacant = price = None
        if srows:
            grouped = {m: [r for r in srows if r["medida"] == m] for m in measures}
            if any(len(rs) > 1 for rs in grouped.values()):
                sstatus = "duplicate"
            elif any(not label_matches(r["municipio"], h["municipio"]) for r in srows):
                sstatus = "label_mismatch"
            elif (
                grouped["Viviendas totales"]
                and grouped["Viviendas totales"][0]["valor"] is not None
            ):
                total = int(grouped["Viviendas totales"][0]["valor"])
                vacant = (
                    grouped["Viviendas vacías"][0]["valor"] if grouped["Viviendas vacías"] else None
                )
                if vacant is not None:
                    vacant = int(vacant)
                    if vacant > total:
                        raise ValueError("Vacancy count exceeds census total")
                sstatus = "valid"
        if rrows:
            if len(rrows) != 1:
                rstatus = "duplicate"
            elif not label_matches(rrows[0]["municipio"], h["municipio"]):
                rstatus = "label_mismatch"
            elif rrows[0]["valor"] is not None:
                if rrows[0]["valor"] <= 0:
                    rstatus = "nonpositive"
                else:
                    price, rstatus = float(rrows[0]["valor"]), "valid"
        output.append(
            (
                code,
                h["municipio"],
                h["hogares"],
                total,
                vacant,
                price,
                sstatus,
                rstatus,
                h["hogares"] is not None and total is not None and price is not None,
            )
        )
    return output, sorted(excluded, key=lambda r: (*r[:4], r[4] is None, r[4] or ""))


TENURE_CODES = {"41004", "41038", "41091", "41095"}
TENURE_CATEGORIES = [
    "Total (régimen de tenencia)",
    "En propiedad",
    "En alquiler",
    "Otro régimen de tenencia",
]


def tenure(contents, metadata, hh):
    parser = Text()
    parser.feed(metadata)
    text = re.sub(r"\s+", " ", " ".join(parser.parts))
    for expected in [
        "Censo de Población y Viviendas 2021",
        "Unidades: viviendas",
        "Viviendas familiares principales convencionales según régimen de tenencia",
        "municipios de más de 50.000 habitantes",
    ]:
        if expected not in text:
            raise ValueError("Tenure source definition/year/unit/scope changed")
    reader = csv.DictReader(io.StringIO(contents), delimiter="\t")
    geo = "Municipios (con más de 50.000 habitantes) y capitales de provincia"
    if reader.fieldnames != [geo, "Régimen de tenencia de la vivienda", "Total"]:
        raise ValueError("Tenure CSV schema changed")
    seen, selected = set(), {}
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Malformed tenure row")
        match = re.fullmatch(r"(\d{5}) (\S.*)", row[geo])
        if not match or row["Régimen de tenencia de la vivienda"] not in TENURE_CATEGORIES:
            raise ValueError("Invalid tenure code/category")
        code, name = match.groups()
        category, raw = row["Régimen de tenencia de la vivienda"], row["Total"].strip()
        if (code, category) in seen:
            raise ValueError("Duplicate tenure cell")
        seen.add((code, category))
        if raw in {"", ".", ".."}:
            value = None
        elif re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)", raw):
            value = int(raw.replace(",", ""))
        else:
            raise ValueError("Unexpected tenure count/grouping")
        if code.startswith("41"):
            if code not in hh or not label_matches(name, hh[code]["municipio"]):
                raise ValueError("Tenure code/label not compatible with household universe")
            selected.setdefault(code, {})[category] = value
    output = []
    for code, cells in sorted(selected.items()):
        if set(cells) != set(TENURE_CATEGORIES):
            raise ValueError("Missing published tenure category")
        values = [cells[k] for k in TENURE_CATEGORIES]
        total, parts = values[0], values[1:]
        if total is not None:
            if sum(v for v in parts if v is not None) > total:
                raise ValueError("Tenure categories exceed total")
            if all(v is not None for v in parts) and sum(parts) != total:
                raise ValueError("Tenure categories do not conserve published total")
        state = "celdas_completas" if all(v is not None for v in values) else "celdas_incompletas"
        output.append((code, hh[code]["municipio"], *values, state))
    return output


def checked_tenure(contents, metadata, hh):
    result = tenure(contents, metadata, hh)
    if {r[0] for r in result} != TENURE_CODES:
        raise ValueError("Published Sevilla tenure scope changed")
    return result


def inputs():
    man = manifest.load()
    rels = [str(p.relative_to(ROOT)) for p in INPUTS.values()]
    if any(p not in man.get("sha256", {}) for p in rels):
        raise ValueError("Unpinned municipal profile inputs; fetch household source first")
    pins = {p: man["sha256"][p] for p in rels}
    missing, changed = manifest.check(pins)
    if missing or changed:
        raise ValueError("Municipal input missing/changed vs manifest")
    hh = households(
        INPUTS["households"].read_text(encoding="utf-8-sig"), INPUTS["metadata"].read_text()
    )
    if len(hh) != 106:
        raise ValueError("Sevilla census household universe changed")
    tables = {key: pq.read_table(INPUTS[key]) for key in ["stock", "rent"]}
    specs = {
        "stock": {
            "codigo": "string",
            "municipio": "string",
            "provincia_cod": "string",
            "medida": "string",
            "valor": "int64",
        },
        "rent": {
            "codigo": "string",
            "municipio": "string",
            "cpro": "string",
            "anyo": "int64",
            "medida": "string",
            "valor": "double",
        },
    }
    for key, fields in specs.items():
        actual = {f.name: str(f.type) for f in tables[key].schema}
        if any(actual.get(name) != kind for name, kind in fields.items()):
            raise ValueError("Municipal source schema changed")
    profiles, excluded = derive(hh, tables["stock"].to_pylist(), tables["rent"].to_pylist())
    meta = {
        **pins,
        "script_sha": manifest.sha256(Path(__file__)),
        "names_sha": manifest.sha256(Path(muni_names.__file__)),
        "duckdb": duckdb.__version__,
        "census_date": "2021-01-01",
        "rent_tax_year": "2021",
        "consumption_year": "2020",
        "rent_measure": "ALQM2_LV_M_VC",
    }
    context = checked_tenure(
        INPUTS["tenure"].read_text(encoding="utf-8-sig"), INPUTS["tenure_metadata"].read_text(), hh
    )
    meta["tenure_unit"] = "viviendas familiares principales convencionales"
    return profiles, excluded, meta, context


def verify():
    profiles, excluded, meta, context = inputs()
    if not DATABASE.is_file():
        raise ValueError("Missing municipal sidecar; rebuild with --offline")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        if con.execute("select * from profile_meta order by key,value").fetchall() != sorted(
            meta.items()
        ):
            raise ValueError("Stale municipal sidecar; rebuild with --offline")
        if con.execute("select * from perfiles order by codigo").fetchall() != profiles:
            raise ValueError("Municipal profiles differ from pinned derivation")
        if (
            con.execute(
                "select * from agregados_excluidos "
                "order by fuente,codigo,municipio,medida,valor_publicado"
            ).fetchall()
            != excluded
        ):
            raise ValueError("Excluded aggregates differ from pinned derivation")
        if con.execute("select * from tenencia_contexto order by codigo").fetchall() != context:
            raise ValueError("Tenure context differs from pinned derivation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        verify()
        print("municipal2021: exact profiles, tenure context, aggregates and pins verified")
        return
    if not args.offline:
        content = {}
        for key, url in URLS.items():
            with urllib.request.urlopen(url, timeout=60) as r:
                content[key] = r.read(10 * 1024 * 1024 + 1)
            if len(content[key]) > 10 * 1024 * 1024:
                raise ValueError("Household download exceeds bound")
        hh = households(
            content["households"].decode("utf-8-sig"), content["metadata"].decode("utf-8")
        )
        if len(hh) != 106:
            raise ValueError("Household universe changed; refusing to pin")
        checked_tenure(
            content["tenure"].decode("utf-8-sig"), content["tenure_metadata"].decode("utf-8"), hh
        )
        for key, value in content.items():
            INPUTS[key].parent.mkdir(parents=True, exist_ok=True)
            INPUTS[key].write_bytes(value)
            manifest.record(
                str(INPUTS[key].relative_to(ROOT)),
                {
                    "url": URLS[key],
                    "publisher": "INE Censo de Población y Viviendas 2021",
                    "accessed": date.today().isoformat(),
                    "note": (
                        "Table59529 conventional primary dwellings by tenure; census1Jan2021"
                        if key.startswith("tenure")
                        else "Table59543 municipal household counts; reference1Jan2021"
                    ),
                },
            )
    profiles, excluded, meta, context = inputs()
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATABASE.with_suffix(".tmp.duckdb")
    with duckdb.connect(str(tmp)) as con:
        con.execute(
            "create or replace table perfiles(codigo varchar,municipio varchar,hogares bigint,"
            "viviendas bigint,vacias_consumo bigint,renta_vc double,estado_stock varchar,"
            "estado_renta varchar,perfil_completo boolean)"
        )
        con.executemany("insert into perfiles values (?,?,?,?,?,?,?,?,?)", profiles)
        con.execute(
            "create or replace table agregados_excluidos(fuente varchar,codigo varchar,"
            "municipio varchar,medida varchar,valor_publicado varchar)"
        )
        if excluded:
            con.executemany("insert into agregados_excluidos values (?,?,?,?,?)", excluded)
        con.execute(
            "create or replace table tenencia_contexto(codigo varchar,municipio varchar,"
            "principales bigint,propiedad bigint,alquiler bigint,otro bigint,estado varchar)"
        )
        con.executemany("insert into tenencia_contexto values (?,?,?,?,?,?,?)", context)
        con.execute("create or replace table profile_meta(key varchar,value varchar)")
        con.executemany("insert into profile_meta values (?,?)", list(meta.items()))
    tmp.replace(DATABASE)
    verify()
    print(
        f"municipal2021: {len(profiles)} household-code profiles; "
        f"{sum(r[-1] for r in profiles)} complete"
    )


if __name__ == "__main__":
    main()
