"""Fetch all-Catalonia municipal quarterly rental deposits (INCASÒL) and BOE ZMRT lists.

Pins five official administrative inputs in data/input_manifest.json:
1. Generalitat INCASÒL quarterly habitual rental contracts by municipality (2005–latest)
2. Generalitat INCASÒL quarterly mean contractual rent (€/month) by municipality (2005–latest)
3. Generalitat INCASÒL quarterly seasonal rental contracts by municipality (2023–latest)
4. BOE-A-2024-5214 (Resolución 14 Mar 2024): Wave 1 Zona de Mercado Residencial Tensionado
   (140 Catalan municipalities, effective 16 Mar 2024 -> first full treated quarter 2024Q2)
5. BOE-A-2024-20576 (Resolución 8 Oct 2024): Wave 2 Zona de Mercado Residencial Tensionado
   (131 Catalan municipalities, effective 10 Oct 2024 -> first full treated quarter 2024Q4)

Notes:
- Mean rent is suppressed by Generalitat when a municipality has <= 5 contracts in a quarter;
  those cells appear as 0 in the source workbooks and are coerced to null here (never 0 €/month).
- Unpublished future quarters in the latest year sheet appear as None and are omitted.
- Use --offline to rebuild from pinned raw files; use --check to verify without rewriting.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

INCASOL_BASE = (
    "https://habitatge.gencat.cat/web/.content/home/dades/estadistiques/"
    "01_Estadistiques_de_construccio_i_mercat_immobiliari/03_Mercat_de_lloguer"
)
RAW_FILES = {
    "contractes": (
        RAW / "cat_incasol_municipis_trimestral_contractes.xlsx",
        f"{INCASOL_BASE}/02_Lloguers_per_ambits_geografics/Fitxers_contractes/"
        "municipis_trimestral_contractes.xlsx",
        "Generalitat de Catalunya, Secretaria d'Habitatge (INCASÒL fiances)",
        "Quarterly habitual rental contracts filed by Catalan municipality (2005–latest)",
    ),
    "lloguer": (
        RAW / "cat_incasol_municipis_trimestral_lloguer.xlsx",
        f"{INCASOL_BASE}/02_Lloguers_per_ambits_geografics/Lloguer_mitja/"
        "municipis_trimestral_lloguer.xlsx",
        "Generalitat de Catalunya, Secretaria d'Habitatge (INCASÒL fiances)",
        "Quarterly mean contractual rent (€/month) by Catalan municipality (>5 contracts)",
    ),
    "temporada": (
        RAW / "cat_incasol_temporada_mun.xlsx",
        f"{INCASOL_BASE}/08_Lloguer-de-temporada/lloguer_temporada_mun.xlsx",
        "Generalitat de Catalunya, Secretaria d'Habitatge (INCASÒL fiances)",
        "Quarterly seasonal rental contracts filed by Catalan municipality (2023–latest)",
    ),
    "boe_wave1": (
        RAW / "boe_zmrt_cat_wave1.xml",
        "https://www.boe.es/diario_boe/xml.php?id=BOE-A-2024-5214",
        "Ministerio de Vivienda y Agenda Urbana (BOE núm. 66, 15/03/2024)",
        "BOE-A-2024-5214: Wave 1 Catalonia ZMRT (140 municipalities, effective 16/03/2024)",
    ),
    "boe_wave2": (
        RAW / "boe_zmrt_cat_wave2.xml",
        "https://www.boe.es/diario_boe/xml.php?id=BOE-A-2024-20576",
        "Ministerio de Vivienda y Agenda Urbana (BOE núm. 244, 09/10/2024)",
        "BOE-A-2024-20576: Wave 2 Catalonia ZMRT (131 municipalities, effective 10/10/2024)",
    ),
}

OUT_PARQUET = PROCESSED / "catalonia_rent_control.parquet"

PROV_MAP = {
    "08": "Barcelona",
    "17": "Girona",
    "25": "Lleida",
    "43": "Tarragona",
}

SCHEMA = pa.schema(
    [
        ("codi", pa.string()),
        ("municipi", pa.string()),
        ("comarca", pa.string()),
        ("cpro", pa.string()),
        ("provincia", pa.string()),
        ("wave", pa.int64()),
        ("effective_quarter", pa.string()),
        ("anyo", pa.int64()),
        ("trimestre", pa.int64()),
        ("quarter_label", pa.string()),
        ("quarter_idx", pa.int64()),
        ("contractes", pa.int64()),
        ("lloguer_eur", pa.float64()),
        ("temporada_contractes", pa.int64()),
        ("temporada_share", pa.float64()),
    ]
)

# Known official spelling / punctuation differences between BOE text and INCASÒL workbooks.
NAME_ALIASES = {
    "manresa el masnou": ["manresa", "el masnou"],
    "castell platja d aro": ["castell d aro platja d aro i s agaro"],
    "castell d aro platja d aro i s agaro": ["castell platja d aro"],
    "roda de bera": ["roda de bara"],
    "calonge i sant antoni": ["calonge"],
    "santa maria de corco": ["l esquirol"],
    "brunola i sant marti sapresa": ["brunyola", "brunyola i sant marti sapresa"],
    "bigues i riells del fai": ["bigues i riells"],
    "les borges del camp": ["borges del camp"],
    "sant quirze safaja": ["sant quirze de safaja"],
    "torres de segre": ["torres de segre"],
    "cruilles monells i sant sadurni de l heura": ["cruilles monells i sant sadurni de l heura"],
    "la selva del camp": ["selva del camp"],
}


def norm_name(text: str) -> str:
    """Normalize Catalan/Spanish municipality name for deterministic matching."""
    text = text.strip().lower()
    # Handle "Name, el" / "Name, la" / "Name, l'" / "Name, les" / "Name, els"
    m = re.match(r"^(.+),\s*(el|la|els|les|l['’]|sa|es)$", text)
    if m:
        art = m.group(2).replace("’", "'")
        text = f"{art}{m.group(1)}" if art.endswith("'") else f"{art} {m.group(1)}"
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("`", "'").replace("·", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def strip_leading_article(norm: str) -> str:
    return re.sub(r"^(el|la|els|les|l|sa|es)\s+", "", norm).strip()


def download_all() -> None:
    for key, (path, url, publisher, note) in RAW_FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "housing-data-analysis/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (pinned official hosts)
            payload = resp.read()
        if path.suffix == ".xlsx" and not payload.startswith(b"PK"):
            raise SystemExit(f"{key}: expected XLSX/ZIP payload, got {payload[:40]!r}")
        if path.suffix == ".xml" and not payload.lstrip().startswith(b"<?xml"):
            raise SystemExit(f"{key}: expected XML payload, got {payload[:40]!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(payload)
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
        print(f"fetched {path.name} ({len(payload):,} bytes)")


def parse_boe_municipalities(xml_path: Path, expected_count: int) -> list[str]:
    """Extract the comma-separated list of Catalan municipalities from BOE XML."""
    root = ET.parse(xml_path).getroot()  # noqa: S314 (pinned local BOE XML)
    texto = root.find("texto")
    if texto is None:
        raise ValueError(f"{xml_path.name}: missing <texto>")
    candidates = []
    for td in texto.findall(".//td"):
        txt = " ".join("".join(td.itertext()).split())
        if txt.count(",") >= 50:
            candidates.append(txt)
    if len(candidates) != 1:
        raise ValueError(
            f"{xml_path.name}: expected 1 municipality list cell, found {len(candidates)}"
        )
    raw = candidates[0].rstrip(".")
    # Protect official municipality names containing internal commas before splitting.
    raw = raw.replace(
        "Castell d'Aro, Platja d'Aro i S'Agaró", "Castell d'Aro__COMMA__ Platja d'Aro i S'Agaró"
    )
    # Wave 1 ends with ", i Vilassar de Mar" (comma before conjunction);
    # Wave 2 ends with ", Vinyols i els Arcs" (no conjunction).
    raw = re.sub(r",\s+(?:y|i)\s+(?=[^,]+$)", ", ", raw)
    # Fix missing comma in BOE-A-2024-5214 ("Manresa el Masnou") if present.
    raw = re.sub(r"\bManresa\s+el\s+Masnou\b", "Manresa, el Masnou", raw)
    names = [part.strip().replace("__COMMA__", ",") for part in raw.split(",") if part.strip()]
    if len(names) != expected_count:
        raise ValueError(
            f"{xml_path.name}: parsed {len(names)} municipalities, expected {expected_count}"
        )
    return names


def parse_quarterly_workbook(
    xlsx_path: Path, *, is_rent: bool
) -> tuple[dict[str, tuple[str, str]], dict[tuple[str, int, int], float | int | None]]:
    """Parse all year sheets of an INCASÒL municipal quarterly workbook."""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    munis: dict[str, tuple[str, str]] = {}
    values: dict[tuple[str, int, int], float | int | None] = {}
    for sheet_name in wb.sheetnames:
        if not re.fullmatch(r"\d{4}", sheet_name.strip()):
            continue
        year = int(sheet_name.strip())
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        header_idx = None
        for idx, row in enumerate(rows):
            if row and str(row[0]).strip() == "Codi":
                header_idx = idx
                break
        if header_idx is None:
            raise ValueError(f"{xlsx_path.name} [{sheet_name}]: missing Codi header")
        header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
        q_cols = {}
        for q_num, roman in enumerate(("I", "II", "III", "IV"), start=1):
            # Take the first occurrence (quarterly, before cumulative columns)
            try:
                q_cols[q_num] = header.index(roman)
            except ValueError as exc:
                raise ValueError(
                    f"{xlsx_path.name} [{sheet_name}]: missing quarter column {roman}"
                ) from exc
        for row in rows[header_idx + 1 :]:
            if not row or row[0] is None:
                continue
            code = str(row[0]).strip()
            if not re.fullmatch(r"\d{5}", code):
                continue
            muni_name = str(row[1]).strip() if row[1] is not None else ""
            comarca = str(row[2]).strip() if row[2] is not None else ""
            # Keep the most recent sheet's canonical name (sheets are ordered newest-first)
            if code not in munis and muni_name:
                munis[code] = (muni_name, comarca)
            for q_num, col_idx in q_cols.items():
                raw_val = row[col_idx] if col_idx < len(row) else None
                if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
                    continue  # unpublished quarter
                if isinstance(raw_val, str):
                    s = raw_val.strip().lower().rstrip(".")
                    if s in {"nd", "n.d", "-", "..."}:
                        values[(code, year, q_num)] = None
                        continue
                    num = float(s.replace(",", "."))
                else:
                    num = float(raw_val)
                if is_rent:
                    # Generalitat encodes suppressed rent (<= 5 contracts) as 0
                    values[(code, year, q_num)] = None if num <= 0 else round(num, 4)
                else:
                    values[(code, year, q_num)] = int(round(num))
    wb.close()
    return munis, values


def match_wave_codes(
    boe_names: list[str], munis: dict[str, tuple[str, str]], label: str
) -> set[str]:
    """Match every BOE municipality name to its 5-digit INCASÒL/INE code."""
    by_norm: dict[str, list[str]] = {}
    by_bare: dict[str, list[str]] = {}
    for code, (name, _comarca) in munis.items():
        n = norm_name(name)
        by_norm.setdefault(n, []).append(code)
        by_bare.setdefault(strip_leading_article(n), []).append(code)

    matched: set[str] = set()
    unmatched: list[str] = []
    for raw_name in boe_names:
        n = norm_name(raw_name)
        candidates = by_norm.get(n)
        if not candidates:
            for alt in NAME_ALIASES.get(n, []):
                candidates = by_norm.get(alt) or by_bare.get(strip_leading_article(alt))
                if candidates:
                    break
        if not candidates:
            candidates = by_bare.get(strip_leading_article(n))
        if not candidates:
            # Prefix/substring fallback only if unique
            bare = strip_leading_article(n)
            hits = [c for k, cs in by_bare.items() if bare in k or k in bare for c in cs]
            if len(set(hits)) == 1:
                candidates = list(set(hits))
        if candidates and len(set(candidates)) == 1:
            matched.add(candidates[0])
        else:
            unmatched.append(f"{raw_name!r} (norm={n!r}, hits={candidates})")
    if unmatched:
        raise ValueError(
            f"{label}: {len(unmatched)} unmatched BOE municipalities: " + "; ".join(unmatched[:15])
        )
    if len(matched) != len(boe_names):
        raise ValueError(
            f"{label}: matched {len(matched)} unique codes from {len(boe_names)} BOE names"
        )
    return matched


def build_table() -> pa.Table:
    munis_c, contractes = parse_quarterly_workbook(RAW_FILES["contractes"][0], is_rent=False)
    munis_l, lloguer = parse_quarterly_workbook(RAW_FILES["lloguer"][0], is_rent=True)
    _munis_t, temporada = parse_quarterly_workbook(RAW_FILES["temporada"][0], is_rent=False)

    munis = {**munis_l, **munis_c}
    wave1_names = parse_boe_municipalities(RAW_FILES["boe_wave1"][0], expected_count=140)
    wave2_names = parse_boe_municipalities(RAW_FILES["boe_wave2"][0], expected_count=131)
    wave1_codes = match_wave_codes(wave1_names, munis, "Wave 1 (BOE-A-2024-5214)")
    wave2_codes = match_wave_codes(wave2_names, munis, "Wave 2 (BOE-A-2024-20576)")
    overlap = wave1_codes & wave2_codes
    if overlap:
        raise ValueError(f"Unexpected overlap between Wave 1 and Wave 2: {sorted(overlap)}")

    all_keys = sorted(set(contractes.keys()) | set(lloguer.keys()))
    rows = []
    for code, year, q_num in all_keys:
        name, comarca = munis.get(code, ("", ""))
        cpro = code[:2]
        prov = PROV_MAP.get(cpro, cpro)
        if code in wave1_codes:
            wave, eff_q = 1, "2024Q2"
        elif code in wave2_codes:
            wave, eff_q = 2, "2024Q4"
        else:
            wave, eff_q = 0, None
        c_val = contractes.get((code, year, q_num))
        r_val = lloguer.get((code, year, q_num))
        t_val = temporada.get((code, year, q_num))
        t_share = None
        if t_val is not None and c_val is not None and (c_val + t_val) > 0:
            t_share = round(t_val / (c_val + t_val), 6)
        rows.append(
            {
                "codi": code,
                "municipi": name,
                "comarca": comarca,
                "cpro": cpro,
                "provincia": prov,
                "wave": wave,
                "effective_quarter": eff_q,
                "anyo": year,
                "trimestre": q_num,
                "quarter_label": f"{year}Q{q_num}",
                "quarter_idx": year * 4 + q_num - 1,
                "contractes": c_val,
                "lloguer_eur": r_val,
                "temporada_contractes": t_val,
                "temporada_share": t_share,
            }
        )
    return pa.Table.from_pylist(rows, schema=SCHEMA)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Build from pinned raw files only")
    parser.add_argument("--check", action="store_true", help="Verify raw pins and processed output")
    args = parser.parse_args()

    if not args.offline and not args.check:
        download_all()

    for key, (path, *_rest) in RAW_FILES.items():
        if not path.is_file():
            raise SystemExit(f"Missing pinned raw input for {key}: {path}")

    table = build_table()
    if args.check:
        if not OUT_PARQUET.is_file():
            raise SystemExit(f"Missing processed output: {OUT_PARQUET}")
        existing = pq.read_table(OUT_PARQUET)
        if existing.schema != table.schema or existing.num_rows != table.num_rows:
            raise SystemExit(
                f"Stale {OUT_PARQUET.name}: expected {table.num_rows} rows, got {existing.num_rows}"
            )
        if existing.to_pylist() != table.to_pylist():
            raise SystemExit(f"Content mismatch in {OUT_PARQUET.name}")
        print(f"catalonia_rent_control: verified {table.num_rows:,} rows")
        return

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PARQUET.with_suffix(".parquet.tmp")
    pq.write_table(table, tmp, compression="snappy")
    tmp.replace(OUT_PARQUET)
    w1 = len({r["codi"] for r in table.to_pylist() if r["wave"] == 1})
    w2 = len({r["codi"] for r in table.to_pylist() if r["wave"] == 2})
    w0 = len({r["codi"] for r in table.to_pylist() if r["wave"] == 0})
    print(
        f"wrote {OUT_PARQUET.relative_to(ROOT)}: {table.num_rows:,} rows "
        f"(wave1={w1}, wave2={w2}, never_treated={w0})"
    )


if __name__ == "__main__":
    main()
