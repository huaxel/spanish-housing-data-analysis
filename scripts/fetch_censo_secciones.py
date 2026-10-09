"""Fetch Censo 2021 section-grain indicators (dwellings/persons/households).

Source: INE C2021_Indicadores.csv — one row per census section
(01/01/2021 geography) with total persons (t1_1), dwelling counts
(t18_1 total, t19_1/2 principal/non-principal, t20_1/2/3 tenure split of
principal), households (t21_1, t22_1..5 sizes) and population shares/means
(t2-t17). Full codebook: indicadores_seccen_c2021.xlsx (not pinned; the
column contract below mirrors it).

Suppression is all-or-t1-only: 1,363 sections publish total persons but
no other indicator (statistical secrecy); anything in between fails
loudly, and empty cells are never zero-filled. Internal rules measured
2026-10-09 on the live file: principales + no-principales == total
exactly; household sizes sum to households exactly; tenure splits never
exceed principales (78 sections fall short by up to 261 dwellings —
unimputed tenure, documented not repaired).

Cartography join keys verified (not vendored — 64 MB): the CSV key
cpro+cmun+dist+secc equals the SECC_CE_20210101 CUSEC set exactly
(36,333 = 36,333, UTF-8 DBF). INE warns section assignment is still
being updated for some dwellings: provisionality is quoted, not resolved.

Writes data/raw/censo2021_secciones.csv (byte evidence) and
data/raw/parquet/censo2021_secciones.parquet (validated mirror, NULLs kept).
"""

from __future__ import annotations

import csv
import math
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = "https://www.ine.es/censos2021/C2021_Indicadores.csv"
RAW_CSV = RAW / "censo2021_secciones.csv"
RAW_PARQUET = RAW / "parquet" / "censo2021_secciones.parquet"

KEYS = ["ccaa", "cpro", "cmun", "dist", "secc"]
# File order is sequential t1_1 .. t22_5 (housing block t18-t22 sits between
# t17 and the end, not grouped with t1_1): keep this list in file order.
HEAD = ["t1_1", "t2_1", "t2_2", "t3_1", "t4_1", "t4_2", "t4_3"]
HEAD += [f"t{i}_1" for i in range(5, 17)]
INDICATORS = HEAD + [
    "t17_1",
    "t17_2",
    "t17_3",
    "t17_4",
    "t17_5",
    "t18_1",
    "t19_1",
    "t19_2",
    "t20_1",
    "t20_2",
    "t20_3",
    "t21_1",
    "t22_1",
    "t22_2",
    "t22_3",
    "t22_4",
    "t22_5",
]
BASE_COUNTS = ["t1_1", "t18_1", "t19_1", "t19_2", "t20_1", "t20_2", "t20_3", "t21_1"]
COUNTS = BASE_COUNTS + [f"t22_{i}" for i in range(1, 6)]
SHARES = [c for c in INDICATORS if c not in COUNTS]
KEY_RE = {
    "ccaa": re.compile(r"\d{2}"),
    "cpro": re.compile(r"\d{2}"),
    "cmun": re.compile(r"\d{3}"),
    "dist": re.compile(r"\d{2}"),
    "secc": re.compile(r"\d{3}"),
}
INT_RE = re.compile(r"\d+")


def parse_secciones(text: str, expect_rows: int = 36333) -> list[dict]:
    """Parse and validate the section indicator CSV. SystemExit on drift."""
    lines = text.splitlines()
    if not lines:
        raise SystemExit("secciones: empty file")
    header = [h.strip() for h in lines[0].split(",")]
    if header != KEYS + INDICATORS:
        raise SystemExit(f"secciones: header drift ({len(header)} cols)")
    rows = list(csv.DictReader(lines))
    if len(rows) != expect_rows:
        raise SystemExit(f"secciones: {len(rows)} rows, want {expect_rows}")
    seen = set()
    out = []
    for i, r in enumerate(rows):
        key = {k: r[k].strip() for k in KEYS}
        for k, v in key.items():
            if not KEY_RE[k].fullmatch(v):
                raise SystemExit(f"secciones: bad {k} {v!r} at row {i}")
        code = key["cpro"] + key["cmun"] + key["dist"] + key["secc"]
        if code in seen:
            raise SystemExit(f"secciones: duplicate section {code}")
        seen.add(code)
        row: dict = {"seccion": key["ccaa"] + code, **key}
        empties = [c for c in COUNTS + SHARES if r[c].strip() == ""]
        if empties:
            if set(empties) != set(COUNTS[1:] + SHARES) or r["t1_1"].strip() == "":
                raise SystemExit(f"secciones: partial suppression at {code}")
            raw = r["t1_1"].strip()
            if not INT_RE.fullmatch(raw):
                raise SystemExit(f"secciones: unparsable count {raw!r} at {code}")
            row["t1_1"] = int(raw)
            for c in COUNTS[1:] + SHARES:
                row[c] = None
            row["suprimido"] = True
            out.append(row)
            continue
        vals: dict[str, float | int] = {}
        for c in COUNTS:
            raw = r[c].strip()
            if not INT_RE.fullmatch(raw):
                raise SystemExit(f"secciones: unparsable count {raw!r} at {code}")
            vals[c] = int(raw)
        for c in SHARES:
            try:
                value = float(r[c].strip())
            except ValueError:
                raise SystemExit(f"secciones: unparsable share {r[c]!r} at {code}") from None
            if not math.isfinite(value) or value < 0:
                raise SystemExit(f"secciones: non-finite or negative share {r[c]!r} at {code}")
            vals[c] = value
        if vals["t19_1"] + vals["t19_2"] != vals["t18_1"]:
            raise SystemExit(f"secciones: type split breaks total at {code}")
        if vals["t18_1"] <= 0 or vals["t19_1"] <= 0:
            raise SystemExit(f"secciones: non-positive usable denominator at {code}")
        if sum(vals[f"t22_{j}"] for j in range(1, 6)) != vals["t21_1"]:
            raise SystemExit(f"secciones: size split breaks households at {code}")
        if sum(vals[f"t20_{j}"] for j in range(1, 4)) > vals["t19_1"]:
            raise SystemExit(f"secciones: tenure split exceeds principales at {code}")
        row.update(vals)
        row["suprimido"] = False
        out.append(row)
    return out


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)


def main() -> None:
    download(URL, RAW_CSV)
    text = RAW_CSV.read_text(encoding="utf-8-sig")
    rows = parse_secciones(text)
    usable = sum(1 for r in rows if not r["suprimido"])
    print(f"secciones: {len(rows)} sections, {usable} usable ({len(rows) - usable} suppressed)")
    n = csvx.write_parquet(rows, RAW_PARQUET)
    manifest.record(
        "data/raw/censo2021_secciones.csv",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "CENSO2021SEC",
            "accessed": date.today().isoformat(),
        },
    )
    manifest.record(
        "data/raw/parquet/censo2021_secciones.parquet",
        {
            "url": URL,
            "publisher": "INE",
            "operation": "CENSO2021SEC",
            "accessed": date.today().isoformat(),
        },
    )
    print(f"censo secciones: {n} rows -> {RAW_PARQUET}")


if __name__ == "__main__":
    main()
