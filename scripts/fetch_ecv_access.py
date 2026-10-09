"""Pinned INE ECV 2025 housing-access module cells: home moves, blocked search,
youth living with parents (each with main reason).

Source: JAXI tpx tables 79621-79645 (three blocks, national grain; a single
CCAA cut in the blocked-search block; no municipal estimates).

Sidecar database: central marts and their estimator input hashes stay unchanged;
results land in the existing housing_access.duckdb sidecar as new tables
(access_moves, access_blocked, access_youth). Counts are persons in thousands;
percent rows are shares of the stated group, NOT shares of households. Reason
rows carry no unit marker in the source; they are validated as shares by the
per-group sum-to-100 check, so any future unmarked count row fails loudly.
Groups with suppressed cells skip the checks that need complete values and
carry status 'checks_skipped' (all other rows carry '').
Use --offline to rebuild exclusively from already pinned CSV inputs.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

SURVEY_YEAR = 2025  # single-year module; fieldwork February-May 2025.

# tpx: (sidecar table, breakdown code, stub vocab keys, measure header, groups, shape).
# Shape 'full' is population / headline-% / headline-count / reason shares;
# shape 'reasons' is reason shares only (table 79644 has no headline rows).
TABLES = {
    79621: ("access_moves", "edad_sexo", ("Sexo", "Edad16"), "moves", 15, "full"),
    79622: ("access_moves", "pais", ("Pais",), "moves", 4, "full"),
    79623: ("access_moves", "formacion", ("Formacion",), "moves", 5, "full"),
    79624: ("access_moves", "actividad", ("Actividad",), "moves", 5, "full"),
    79625: ("access_moves", "urbanizacion", ("Urba",), "moves", 4, "full"),
    79626: ("access_moves", "tam_muni", ("TamMuni",), "moves", 6, "full"),
    79627: ("access_moves", "tenencia", ("Tenencia",), "moves", 7, "full"),
    79628: ("access_moves", "quintil", ("Quintil",), "moves", 6, "full"),
    79629: ("access_blocked", "edad_sexo", ("Sexo", "Edad16"), "blocked", 15, "full"),
    79630: ("access_blocked", "pais", ("Pais",), "blocked", 4, "full"),
    79631: ("access_blocked", "formacion", ("Formacion",), "blocked", 5, "full"),
    79632: ("access_blocked", "actividad", ("Actividad",), "blocked", 5, "full"),
    79633: ("access_blocked", "urbanizacion", ("Urba",), "blocked", 4, "full"),
    79634: ("access_blocked", "tam_muni", ("TamMuni",), "blocked", 6, "full"),
    79635: ("access_blocked", "tenencia", ("Tenencia",), "blocked", 7, "full"),
    79636: ("access_blocked", "quintil", ("Quintil",), "blocked", 6, "full"),
    79637: ("access_blocked", "ccaa", ("CCAA",), "blocked", 20, "full"),
    79638: ("access_youth", "edad_sexo", ("Edad1834", "Sexo"), "youth", 9, "full"),
    79639: ("access_youth", "edad_pais", ("Edad1834", "Pais"), "youth", 12, "full"),
    79640: ("access_youth", "edad_formacion", ("Edad1834", "FormacionY"), "youth", 18, "full"),
    79641: ("access_youth", "edad_actividad", ("Edad1834", "ActividadY"), "youth", 15, "full"),
    79642: ("access_youth", "edad_urbanizacion", ("Edad1834", "Urba"), "youth", 12, "full"),
    79643: ("access_youth", "edad_tam_muni", ("Edad1834", "TamMuni"), "youth", 18, "full"),
    79644: (
        "access_youth",
        "edad_quintil",
        ("Edad1834", "Quintil"),
        "youth_reasons",
        18,
        "reasons",
    ),
    79645: (
        "access_youth",
        "edad_renta_personal",
        ("Edad1834", "RentaPersonal"),
        "youth",
        18,
        "full",
    ),
}
# Publisher measure-column headers, verbatim (including source typos).
MEASURE_HEADERS = {
    "moves": "Cambios de vivienda y razón principal",
    "blocked": "Razón principal por la que no ha encontrado vivienda",
    "youth": "Conviviencia con padres y razón principal",
    "youth_reasons": "Razón princpial",
}
MEASURES_MOVES = [
    "Personas de 16 o más años (miles)",
    "Han cambiado de vivienda (%)",
    "Han cambiado de vivienda (miles)",
    "Motivos económicos",
    "Características de la vivienda a la que se accede",
    "Otras razones (motivos familiares, laborales, personales, etc.)",
]
MEASURES_BLOCKED = [
    "Personas de 16 o más años (miles)",
    "Ha buscado vivienda activamente pero no se ha cambiado (%)",
    "Ha buscado vivienda activamente pero no se ha cambiado (miles)",
    "Precio excesivo",
    "La vivienda no reunía los requisitos que busco",
    "Yo no reunía las condiciones necesarias para el alquiler/compra",
    "Otras razones",
]
MEASURES_YOUTH = [
    "Personas entre 18 y 34 años (miles)",
    "Convive con alguno de sus padres (%)",
    "Convive con alguno de sus padres (miles)",
    "No me he planteado independizarme",
    "No puedo permitirme alquilar una vivienda",
    "No puedo acceder a la compra de vivienda",
    "Estoy ahorrando para comprar o alquilar",
    "Puedo pagar un alquiler o compra, pero prefiero vivir así",
    "Otra",
]
MEASURES = {
    "access_moves": MEASURES_MOVES,
    "access_blocked": MEASURES_BLOCKED,
    "access_youth": MEASURES_YOUTH,
    "reasons": MEASURES_YOUTH[3:],
}
VOCAB = {
    "Sexo": ["Ambos sexos", "Hombres", "Mujeres"],
    "Edad16": [
        "Total",
        "De 16 a 29 años",
        "De 30 a 44 años",
        "De 45 a 64 años",
        "65 y más años",
    ],
    "Edad1834": ["Total", "De 18 a 25 años", "De 26 a 34 años"],
    "Pais": [
        "Total",
        "España",
        "País Extranjero (Unión Europea)",
        "País Extranjero (Resto del mundo)",
    ],
    "Formacion": [
        "Total",
        "Educación primaria o inferior",
        "Educación secundaria primera etapa",
        "Educación secundaria segunda etapa",
        "Educación superior",
    ],
    "FormacionY": [
        "Total",
        "Sin educación superior",
        "Educación primaria o inferior",
        "Educación secundaria primera etapa",
        "Educación secundaria segunda etapa",
        "Educación superior",
    ],
    "Actividad": ["Total", "Ocupados", "Parados", "Jubilados", "Otros inactivos"],
    "ActividadY": ["Total", "Ocupados", "Parados", "Estudiantes", "Otros inactivos"],
    "Urba": [
        "Total",
        "Área densamente poblada",
        "Área poblada nivel intermedio",
        "Área poco poblada",
    ],
    "TamMuni": [
        "Total",
        "Menos de 10.000 habitantes",
        "Entre 10.000 y 50.000 habitantes",
        "Entre 50.000 y 100.000 habitantes",
        "Entre 100.000 y 500.000 habitantes",
        "Más de 500.000 habitantes",
    ],
    "Tenencia": [
        "Total",
        "Propiedad",
        "Propiedad sin hipoteca",
        "Propiedad con hipoteca",
        "Alquiler a precio de mercado",
        "Alquiler inferior al precio de mercado",
        "Cesión gratuita",
    ],
    "Quintil": [
        "Total",
        "Primer quintil",
        "Segundo quintil",
        "Tercer quintil",
        "Cuarto quintil",
        "Quinto quintil",
    ],
    "CCAA": [
        "Total",
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
        "Navarra, Comunidad Foral de",
        "País Vasco",
        "Rioja, La",
        "Ceuta",
        "Melilla",
    ],
    "RentaPersonal": [
        "Total",
        "Sin ingresos - Hasta 6.000 euros",
        "De más de 6.000 a 12.000 euros",
        "De más de 12.000 a 18.000 euros",
        "De más de 18.000 a 24.000 euros",
        "Más de 24.000 euros",
    ],
}
PARQUET = RAW / "parquet" / "ecv_access.parquet"
DATABASE = PROCESSED / "housing_access.duckdb"
SCHEMA = pa.schema(
    [
        ("tpx", pa.int64()),
        ("block", pa.string()),
        ("breakdown", pa.string()),
        ("group_label", pa.string()),
        ("geo", pa.string()),
        ("survey_year", pa.int64()),
        ("measure", pa.string()),
        ("kind", pa.string()),
        ("value", pa.float64()),
        ("status", pa.string()),
    ]
)


def url(tpx: int) -> str:
    return f"https://www.ine.es/jaxi/files/tpx/csv_bd/{tpx}.csv"


def raw_path(tpx):
    return RAW / f"ecv_access_{tpx}.csv"


def parse_number(text: str, tpx: int, label: str):
    text = text.strip()
    if text in ("", ".", ".."):
        return None
    # Strict Spanish format (dot thousands, comma decimals): a dot-decimal
    # like "3.9" must never silently parse as 39.
    if not re.fullmatch(r"\d{1,3}(\.\d{3})*(,\d+)?", text):
        raise ValueError(f"{tpx}: unexpected number format {label!r}")
    value = float(text.replace(".", "").replace(",", "."))
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{tpx}: invalid value {label!r}")
    return value


def parse(text: str, tpx: int) -> list[dict]:
    block, breakdown, stub_keys, header_key, want_groups, shape = TABLES[tpx]
    lines = text.lstrip("\ufeff").splitlines()
    reader = csv.reader(lines, delimiter="\t")
    header = next(reader)
    stubs = header[:-2]
    expected_stubs = [STUB_HEADERS[key] for key in stub_keys]
    if stubs != expected_stubs:
        raise ValueError(f"{tpx}: unexpected stub columns {stubs}")
    if header[-2] != MEASURE_HEADERS[header_key]:
        raise ValueError(f"{tpx}: unexpected measure column {header[-2]!r}")
    if header[-1] != "Total" or len(header) != len(stubs) + 2:
        raise ValueError(f"{tpx}: unexpected value columns {header[-1:]!r}")
    by_group: dict[tuple, list] = {}
    cell_values: dict[tuple, float | None] = {}
    for record in reader:
        if not any(cell.strip() for cell in record):
            continue
        if len(record) != len(header):
            raise ValueError(f"{tpx}: ragged row {record}")
        stub = tuple(record[:-2])
        for value, key in zip(stub, stub_keys, strict=True):
            if value not in VOCAB[key]:
                raise ValueError(f"{tpx}: unknown {key} value {value!r}")
        cell = (stub, record[-2])
        if cell in cell_values:
            raise ValueError(f"{tpx}: duplicate cell {cell}")
        cell_values[cell] = parse_number(record[-1], tpx, f"{stub}|{record[-2]}")
        by_group.setdefault(stub, []).append(record[-2])
    if len(by_group) != want_groups:
        raise ValueError(f"{tpx}: {len(by_group)} groups, expected {want_groups}")
    rows = []
    for stub, measures in by_group.items():
        want = MEASURES[block] if shape == "full" else MEASURES["reasons"]
        if measures != want:
            raise ValueError(f"{tpx}: unexpected measure sequence for {stub}")
        group_values = [cell_values[(stub, measure)] for measure in measures]
        kinds = [
            "count_thousands"
            if "(miles)" in measure
            else "rate_pct"
            if "(%)" in measure
            else "share_pct"
            for measure in measures
        ]
        # Validation coverage: groups with suppressed cells skip the checks
        # that need complete values. The flag keeps that gap visible instead
        # of silently weakening the share assumption behind kind inference.
        if shape == "full":
            pop, pct, count = group_values[0], group_values[1], group_values[2]
            identity_ran = None not in (pop, pct, count)
            if identity_ran:
                gap = abs(pct / 100 * pop - count)
                if gap > 0.0006 * pop + 0.1:
                    raise ValueError(f"{tpx}: headline identity fails for {stub}")
            shares = [v for v, k in zip(group_values[3:], kinds[3:], strict=True)]
            shares_ran = all(v is not None for v in shares)
            if shares_ran and abs(sum(shares) - 100) > 0.06 * len(shares):
                raise ValueError(f"{tpx}: reason shares do not sum for {stub}")
            status = "" if identity_ran and shares_ran else "checks_skipped"
        else:
            shares_ran = all(value is not None for value in group_values)
            if shares_ran and abs(sum(group_values) - 100) > 0.06 * len(group_values):
                raise ValueError(f"{tpx}: reason shares do not sum for {stub}")
            status = "" if shares_ran else "checks_skipped"
        for measure, kind, value in zip(measures, kinds, group_values, strict=True):
            if value is not None and kind != "count_thousands" and not 0 <= value <= 100:
                raise ValueError(f"{tpx}: share out of bounds for {stub}")
            if block == "access_blocked" and breakdown == "ccaa":
                geo = "ES" if stub[0] == "Total" else stub[0]
                group_label = "TOTAL"
            else:
                geo = "ES"
                group_label = " | ".join(stub)
            rows.append(
                {
                    "tpx": tpx,
                    "block": block,
                    "breakdown": breakdown,
                    "group_label": group_label,
                    "geo": geo,
                    "survey_year": SURVEY_YEAR,
                    "measure": measure,
                    "kind": kind,
                    "value": value,
                    "status": status,
                }
            )
    if not rows or not any(r["value"] is not None for r in rows):
        raise ValueError(f"{tpx}: no observed values")
    return rows


# Spanish stub headers, verbatim publisher labels keyed by vocab name.
STUB_HEADERS = {
    "Sexo": "Sexo",
    "Edad16": "Edad",
    "Edad1834": "Edad",
    "Pais": "País de nacimiento",
    "Formacion": "Nivel de formación alcanzado",
    "FormacionY": "Nivel de formación alcanzado",
    "Actividad": "Relación con la actividad",
    "ActividadY": "Relación con la actividad",
    "Urba": "Grado de urbanización",
    "TamMuni": "Tamaño del municipio",
    "Tenencia": "Régimen de tenencia de la vivienda principal",
    "Quintil": "Quintil de renta por unidad de consumo",
    "CCAA": "Comunidad Autónoma",
    "RentaPersonal": "Renta neta personal anual",
}


def pinned_rows() -> list[dict]:
    man = manifest.load()
    expected = {}
    for tpx in TABLES:
        rel = str(raw_path(tpx).relative_to(ROOT))
        if rel not in man["sha256"]:
            raise ValueError(f"Unpinned input {rel}; run fetch_ecv_access.py")
        expected[rel] = man["sha256"][rel]
    missing, mismatched = manifest.check(expected)
    if missing or mismatched:
        raise ValueError(f"Access inputs missing={missing}, changed={mismatched}")
    rows = []
    for tpx in TABLES:
        rows.extend(parse(raw_path(tpx).read_text(encoding="utf-8-sig"), tpx))
    return rows


def validate_headlines(rows):
    # The Total-group headline percent must agree across the tables of a block:
    # each cut republishes the same survey estimate. Reasons-only 79644 carries
    # no headline, so youth needs at least two headed sources (it has seven).
    headlines = {}
    for row in rows:
        if row["kind"] != "rate_pct" or row["value"] is None:
            continue
        if row["tpx"] == 79644:
            continue
        table, breakdown, stub_keys, _, _, _ = TABLES[row["tpx"]]
        if breakdown == "ccaa":
            is_total = row["group_label"] == "TOTAL" and row["geo"] == "ES"
        else:
            parts = row["group_label"].split(" | ")
            pairs = zip(parts, stub_keys, strict=True)
            is_total = all(part == VOCAB[key][0] for part, key in pairs)
        if not is_total:
            continue
        # Headline is the first rate_pct measure of its table's sequence.
        headlines.setdefault((table, row["measure"]), []).append(row["value"])
    for key, values in headlines.items():
        if len(values) < 2:
            raise ValueError(f"Single headline source for {key}: agreement uncheckable")
        if max(values) - min(values) > 0.15:
            raise ValueError(f"Headline disagreement for {key}: {values}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not args.offline:
        for tpx in TABLES:
            headers = {"User-Agent": "housing-data-analysis/1.0"}
            req = urllib.request.Request(url(tpx), headers=headers)
            with urllib.request.urlopen(req, timeout=120) as response:  # noqa: S310
                contents = response.read()
            parse(contents.decode("utf-8-sig"), tpx)  # validate before replacing local input
            path = raw_path(tpx)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(contents)
            tmp.replace(path)
            manifest.record(
                str(path.relative_to(ROOT)),
                {
                    "url": url(tpx),
                    "publisher": "INE, ECV 2025 housing-access module",
                    "accessed": date.today().isoformat(),
                    "note": f"JAXI tpx={tpx}; national grain plus CCAA cut in 79637 only",
                },
            )
    rows = pinned_rows()
    validate_headlines(rows)
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, PARQUET)
    # CREATE OR REPLACE on the live sidecar: existing tables are untouched,
    # and each statement is atomic, so an interrupted build is safely resumable.
    by_block: dict[str, list] = {}
    for row in rows:
        by_block.setdefault(row["block"], []).append(row)
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DATABASE)) as con:
        for name, block_rows in by_block.items():
            con.register("access_input", pa.Table.from_pylist(block_rows))
            con.execute(f"create or replace table {name} as select * from access_input")
            con.unregister("access_input")
    for path in [PARQUET, DATABASE]:
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "publisher": "INE, ECV 2025 housing-access module",
                "accessed": date.today().isoformat(),
                "note": "Derived from pinned ecv_access_79621..79645.csv by fetch_ecv_access.py",
            },
        )
    print(f"ecv access: {len(rows)} cells; sidecar {DATABASE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
