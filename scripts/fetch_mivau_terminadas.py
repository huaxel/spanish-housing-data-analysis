"""Pinned MIVAU started/finished dwellings (VDP005_01 + VDP007_01, monthly).

Two Ministry open-data CSVs, following the definition in the Observatorio de
Vivienda y Suelo annual bulletin 2024, table 1.2:
- free-market starts and completions: VDP005_01;
- protected completions: final approvals ("calificación definitiva") in
  VDP007_01.

Until 2026-10 VDP005_01 also carried protected rows. Their completions fell far
short of the bulletin (2024: 1,134 against 14,371), and the layout seen
2026-11-26 has none. Protected starts are NOT included: VDP007_01 publishes two
unlabelled provisional entries per province-month and their sum matches the
bulletin in no year. Visados proper (CSCAE) are not fetched here.

Blank cells are kept null, never zero-filled. The final-approval block has no
blanks, but its zeros may include non-reporting: for Canarias, July-December
2022, it shows zero while VDP007_01's other protected-provisional and
rehabilitation blocks have blank cells. National totals must equal
the bulletin for 2008-2024; a publisher revision fails closed for review. Use
--offline to rebuild from the pinned CSVs and --check to verify without writing.
"""

from __future__ import annotations

import argparse
import csv
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW, ROOT  # noqa: E402

BASE = "https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/"
URL_FREE = BASE + "VDP005_01.csv"
URL_PROTECTED = BASE + "VDP007_01.csv"
RAW_CSV = RAW / "mivau_iniciadas_terminadas.csv"
RAW_VP_CSV = RAW / "mivau_calificaciones.csv"
PARQUET = RAW / "parquet" / "mivau_terminadas.parquet"
TERRITORY = ["COD_CCAA", "NOM_CCAA", "COD_PROV", "NOM_PROV", "ANIO", "MES"]
HEADER_FREE = [*TERRITORY, "REGIMEN_VIVIENDA", "ESTADO_CONSTRUCCION", "NUM_VIVIENDAS"]
HEADER_PROTECTED = [
    *TERRITORY,
    "TIPO_VIVIENDA",
    "TIPO_TRAMITE",
    "ESTADO_TRAMITACION",
    "NUM_VIVIENDAS",
]
# The publisher spells the free regime two ways, one per construction state.
FREE_REGIMES = ("Libre", "Libres")
FREE_ESTADOS = {"Iniciada": "Iniciadas", "Terminada": "Terminadas"}
FINAL_APPROVAL = ("Protegida", "Calificación", "Definitiva")
# Other published blocks, deliberately unused.
UNUSED_BLOCKS = {
    ("Protegida", "Calificación", "Provisional"),
    ("Rehabilitación", "Solicitudes", "Provisional"),
    ("Rehabilitación", "Aprobaciones", "Provisional"),
    ("Rehabilitación", "Aprobaciones", "Definitiva"),
}
CPROS = {f"{n:02d}" for n in range(1, 53)}
# Latest calendar year used by the deficit windows.
LAST_REQUIRED_YEAR = 2025
# Bulletin 2024, table 1.2: year -> (free starts, free completions,
# protected final approvals).
BULLETIN = {
    2008: (237959, 563631, 68587),
    2009: (80230, 356555, 67904),
    2010: (63090, 218572, 58311),
    2011: (51956, 121043, 58308),
    2012: (34580, 80083, 53332),
    2013: (29232, 43230, 17059),
    2014: (32120, 35382, 15046),
    2015: (44679, 41541, 7931),
    2016: (59168, 37512, 7118),
    2017: (74201, 49336, 4938),
    2018: (91477, 58853, 5191),
    2019: (96245, 71562, 7248),
    2020: (75930, 77531, 9973),
    2021: (100504, 84091, 10637),
    2022: (96996, 79935, 9610),
    2023: (98040, 80473, 8847),
    2024: (112220, 86609, 14371),
}
SCHEMA = pa.schema(
    [
        ("cpro", pa.string()),
        ("provincia", pa.string()),
        ("ccaa", pa.string()),
        ("anyo", pa.int64()),
        ("mes", pa.int64()),
        ("tipo", pa.string()),
        ("estado", pa.string()),
        ("viviendas", pa.int64()),
    ]
)


def parse_number(text: str, label: str):
    text = text.strip()
    if text == "":
        return None
    if not text.isdigit():
        raise ValueError(f"terminadas: nonnumeric value {label!r}")
    return int(text)


def records(text: str, header: list[str]):
    reader = csv.reader(text.lstrip("\ufeff").splitlines(), delimiter=";")
    found = next(reader, [])
    if found != header:
        raise ValueError(f"terminadas: unexpected header {found}")
    for record in reader:
        if not any(cell.strip() for cell in record):
            continue
        if len(record) != len(header):
            raise ValueError(f"terminadas: ragged row {record}")
        yield dict(zip(header, record, strict=True))


def cell(rec: dict, tipo: str, estado: str, seen: set) -> dict:
    try:
        anyo, mes = int(rec["ANIO"]), int(rec["MES"])
    except ValueError:
        raise ValueError(f"terminadas: nonnumeric year/month {rec}") from None
    if not 2008 <= anyo <= 2100:
        raise ValueError(f"terminadas: year out of range {anyo}")
    if not 1 <= mes <= 12:
        raise ValueError(f"terminadas: month out of range {mes}")
    cpro = rec["COD_PROV"]
    if cpro not in CPROS:
        raise ValueError(f"terminadas: unknown CPRO {cpro!r}")
    if not rec["NOM_PROV"].strip() or not rec["NOM_CCAA"].strip():
        raise ValueError(f"terminadas: blank territory label {rec}")
    key = (cpro, anyo, mes, tipo, estado)
    if key in seen:
        raise ValueError(f"terminadas: duplicate cell {key}")
    seen.add(key)
    return {
        "cpro": cpro,
        "provincia": rec["NOM_PROV"].strip(),
        "ccaa": rec["NOM_CCAA"].strip(),
        "anyo": anyo,
        "mes": mes,
        "tipo": tipo,
        "estado": estado,
        "viviendas": parse_number(rec["NUM_VIVIENDAS"], f"{key}"),
    }


def require_values(rows: list[dict]) -> list[dict]:
    if not any(r["viviendas"] is not None for r in rows):
        raise ValueError("terminadas: no observed values")
    return rows


def parse_free(text: str) -> list[dict]:
    rows, seen = [], set()
    for rec in records(text, HEADER_FREE):
        if rec["REGIMEN_VIVIENDA"] not in FREE_REGIMES:
            raise ValueError(f"terminadas: unknown regimen {rec['REGIMEN_VIVIENDA']!r}")
        estado = FREE_ESTADOS.get(rec["ESTADO_CONSTRUCCION"])
        if estado is None:
            raise ValueError(f"terminadas: unknown estado {rec['ESTADO_CONSTRUCCION']!r}")
        rows.append(cell(rec, "Libre", estado, seen))
    return require_values(rows)


def parse_protected(text: str) -> list[dict]:
    """Protected completions only: the final-approval block of VDP007_01."""
    rows, seen = [], set()
    for rec in records(text, HEADER_PROTECTED):
        block = (rec["TIPO_VIVIENDA"], rec["TIPO_TRAMITE"], rec["ESTADO_TRAMITACION"])
        if block == FINAL_APPROVAL:
            rows.append(cell(rec, "Protegida", "Terminadas", seen))
        elif block not in UNUSED_BLOCKS:
            raise ValueError(f"terminadas: unknown approval block {block}")
    return require_values(rows)


def validate_coverage(rows: list[dict]) -> None:
    """Dataset-level invariants: no silently dropped province, stable start."""
    if {r["cpro"] for r in rows} != CPROS:
        raise ValueError("terminadas: silently dropped province")
    if min(r["anyo"] for r in rows) != 2008:
        raise ValueError("terminadas: series start moved")


def validate_grid(rows: list[dict]) -> None:
    """Every province-month row from 2008-01 to each series' last month.

    The bulletin anchors stop at 2024, so absent later rows would otherwise
    shrink the window sums unnoticed. Present-but-blank cells are allowed.
    """
    series: dict[tuple[str, str], set] = {}
    for r in rows:
        series.setdefault((r["tipo"], r["estado"]), set()).add((r["cpro"], r["anyo"], r["mes"]))
    for name, cells in sorted(series.items()):
        last = max((anyo, mes) for _, anyo, mes in cells)
        if last < (LAST_REQUIRED_YEAR, 12):
            raise ValueError(f"terminadas: {name} ends {last}, before {LAST_REQUIRED_YEAR}-12")
        months = (last[0] - 2008) * 12 + last[1]
        if len(cells) != months * len(CPROS):
            raise ValueError(f"terminadas: {name} has gaps in the province-month grid")


def validate_bulletin(rows: list[dict]) -> None:
    """National annual totals must equal the Ministry bulletin."""
    series = (("Libre", "Iniciadas"), ("Libre", "Terminadas"), ("Protegida", "Terminadas"))
    totals: dict[tuple[str, str, int], int] = {}
    for r in rows:
        key = (r["tipo"], r["estado"], r["anyo"])
        totals[key] = totals.get(key, 0) + (r["viviendas"] or 0)
    for year, expected in BULLETIN.items():
        for (tipo, estado), want in zip(series, expected, strict=True):
            got = totals.get((tipo, estado, year), 0)
            if got != want:
                raise ValueError(
                    f"terminadas: {tipo} {estado} {year} = {got}, bulletin says {want}"
                )


def parse_sources(free: str, protected: str) -> list[dict]:
    parts = [parse_free(free), parse_protected(protected)]
    for part in parts:
        validate_coverage(part)
    rows = [row for part in parts for row in part]
    validate_grid(rows)
    validate_bulletin(rows)
    return rows


def pinned_rows() -> list[dict]:
    man = manifest.load()
    texts = []
    for path in (RAW_CSV, RAW_VP_CSV):
        rel = str(path.relative_to(ROOT))
        if rel not in man["sha256"]:
            raise ValueError(f"Unpinned input {rel}; run fetch_mivau_terminadas.py")
        missing, mismatched = manifest.check({rel: man["sha256"][rel]})
        if missing or mismatched:
            raise ValueError(f"Terminadas input missing={missing}, changed={mismatched}")
        texts.append(path.read_text(encoding="utf-8-sig"))
    return parse_sources(*texts)


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "housing-data-analysis/1.0"})
    with urllib.request.urlopen(req, timeout=300) as response:  # noqa: S310
        return response.read()


def write_parquet(rows: list[dict]) -> None:
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, PARQUET)


def record_outputs(note: str) -> None:
    for path in [PARQUET]:
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "publisher": "MIVAU, VDP005_01 (free) + VDP007_01 (protected approvals)",
                "accessed": date.today().isoformat(),
                "note": note,
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        rows = pinned_rows()
        current = pq.read_table(PARQUET).to_pylist()
        want = pa.Table.from_pylist(rows, schema=SCHEMA).to_pylist()
        if current != want:
            raise ValueError("Terminadas parquet stale vs parser + pinned input")
        print(f"terminadas: {len(rows)} monthly cells; pins and derivation verified")
        return
    if not args.offline:
        sources = (
            (
                RAW_CSV,
                URL_FREE,
                "MIVAU, viviendas iniciadas y terminadas (VDP005_01)",
                "Monthly free-market starts/completions by CPRO; blanks kept null",
            ),
            (
                RAW_VP_CSV,
                URL_PROTECTED,
                "MIVAU, vivienda protegida y rehabilitación (VDP007_01)",
                "Monthly approvals by CPRO; only protected final approvals are used",
            ),
        )
        contents = [download(url) for _, url, _, _ in sources]
        # Validate both before replacing either local input.
        parse_sources(*(raw.decode("utf-8-sig") for raw in contents))
        for (path, url, publisher, note), raw in zip(sources, contents, strict=True):
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(raw)
            tmp.replace(path)
            manifest.record(
                str(path.relative_to(ROOT)),
                {
                    "url": url,
                    "publisher": publisher,
                    "accessed": date.today().isoformat(),
                    "note": note,
                },
            )
    rows = pinned_rows()
    write_parquet(rows)
    note = "Derived from pinned mivau_iniciadas_terminadas.csv + mivau_calificaciones.csv"
    record_outputs(note + " by fetch_mivau_terminadas.py")
    missing = sum(1 for r in rows if r["viviendas"] is None)
    where = PARQUET.relative_to(ROOT)
    print(f"terminadas: {len(rows)} monthly cells ({missing} missing); parquet {where}")


if __name__ == "__main__":
    main()
