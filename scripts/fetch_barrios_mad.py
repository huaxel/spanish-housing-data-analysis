"""Fetch Madrid city barrio registry prices (Banco de datos, Registradores).

Serie 0504020100060: precio medio declarado (EUR/m2) by Distrito x Barrio
x year x vivienda type (Total/Nuevas/Usadas), 2007-. Source is the
Colegio de Registradores (declared transaction values, ~96-98%
coverage); barrios publish only with >=15 cases. Methodologically a
registry series like the provincial pipelines — NOT offer prices.

Access: the bank is a session-state query builder (no static file). This
script replays the browser flow: GET seleccionSerie (session) -> parse
the embedded variable/value catalog -> setearFiltroS (axes) ->
setearFiltroValor (all value ids) -> POST generarCsv. Catalog IDs are
parsed dynamically (new years arrive with new IDs); anything unexpected
fails loudly instead of fetching a partial cube.
Writes data/raw/barrios_madrid.csv + .parquet (Spanish decimals parsed;
suppressed cells stay null, never zero).
"""

from __future__ import annotations

import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import csvx, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

BASE = "https://servpub.madrid.es/CSEBD_WBINTER"
SERIE = "0504020100060"
RAW_CSV = RAW / "barrios_madrid.csv"
RAW_PARQUET = RAW / "parquet" / "barrios_madrid.parquet"
PUBLISHER = "Ayto. Madrid Banco de datos (Colegio de Registradores)"


def parse_catalog(html: str) -> dict[str, dict]:
    cat: dict[str, dict] = {}
    cur: str | None = None
    pat = re.compile(
        r'varTmp = new variable\("(\d+)" , "([^"]+)"'
        r'|valTmp = new valor \("(\d+)" , "([^"]+)"'
    )
    for m in pat.finditer(html):
        if m.group(1):
            cur = m.group(1)
            cat[cur] = {"name": m.group(2), "values": []}
        elif cur is not None:
            cat[cur]["values"].append({"id": m.group(3), "name": m.group(4)})
    return cat


def find_var(cat: dict, *fragments: str) -> str:
    hits = [
        vid
        for vid, v in cat.items()
        if all(f.casefold() in v["name"].casefold() for f in fragments)
    ]
    if len(hits) != 1:
        raise SystemExit(f"variable {fragments}: {len(hits)} hits")
    return hits[0]


def find_val(cat: dict, vid: str, name: str) -> str:
    hits = [v["id"] for v in cat[vid]["values"] if v["name"] == name]
    if len(hits) != 1:
        raise SystemExit(f"value {name!r} in var {vid}: {len(hits)} hits")
    return hits[0]


def parse_eur(s: str | None) -> float | None:
    s = (s or "").strip()
    if not s:
        return None
    cleaned = s.replace(".", "").replace(",", ".")
    if cleaned.strip(".+-") == "":
        return None  # separator-only cell: suppressed, not zero
    return float(cleaned)


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def get(path: str, params: dict | None = None, timeout: int = 60) -> bytes:
        url = f"{BASE}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        with op.open(url, timeout=timeout) as resp:  # noqa: S310 (pinned host)
            return resp.read()

    html = get("seleccionSerie.html", {"numSerie": SERIE}).decode("utf-8", "replace")
    cat = parse_catalog(html)
    v_dist = find_var(cat, "DISTRITO")
    v_bar = find_var(cat, "BARRIO")
    v_any = find_var(cat, "AÑO")
    v_pre = find_var(cat, "PRECIO")
    v_viv = find_var(cat, "VIVIENDA")
    euros = find_val(cat, v_pre, "Euros/m2")
    tipos = [find_val(cat, v_viv, t) for t in ("Total", "Nuevas", "Usadas")]
    any_ids = [v["id"] for v in cat[v_any]["values"]]
    if len(any_ids) < 15:
        raise SystemExit(f"suspiciously few years: {len(any_ids)}")
    ids = (
        [v["id"] for v in cat[v_dist]["values"]]
        + [v["id"] for v in cat[v_bar]["values"]]
        + any_ids
        + [euros]
        + tipos
    )
    get(
        "setearFiltroS.html",
        {"varFilas": f"{v_dist} {v_bar}", "varColumnas": f"{v_any} {v_pre} {v_viv}"},
    )
    get("setearFiltroValor.html", {"valores": "-".join(ids)})
    req = urllib.request.Request(
        f"{BASE}/detalleSerie.html",
        data=urllib.parse.urlencode({"generarCsv": "generarCsv"}).encode(),
        method="POST",
    )
    with op.open(req, timeout=300) as resp:  # noqa: S310 (pinned host)
        body = resp.read()
    if not body.lstrip()[:1] == b"\xef" and b"Distrito" not in body[:200]:
        raise SystemExit("export did not return the expected CSV")
    RAW_CSV.write_bytes(body)
    _, records = csvx.read_csv_records(RAW_CSV, delimiter=";")
    rows = [
        {
            "distrito": r["Distrito"],
            "barrio": r["Barrio"],
            "anyo": int(r["Año"]),
            "tipo": r["Tipo de vivienda"],
            "eur_m2": parse_eur(r["Total"]),
        }
        for r in records
    ]
    n = csvx.write_parquet(rows, RAW_PARQUET)
    manifest.record(
        "data/raw/barrios_madrid.csv",
        {
            "url": f"{BASE}/seleccionSerie.html?numSerie={SERIE}",
            "publisher": PUBLISHER,
            "accessed": date.today().isoformat(),
            "note": "session-built CSV export; bank query builder, no static file",
        },
    )
    manifest.record(
        "data/raw/parquet/barrios_madrid.parquet",
        {
            "url": f"{BASE}/seleccionSerie.html?numSerie={SERIE}",
            "publisher": PUBLISHER,
            "accessed": date.today().isoformat(),
            "note": "suppressed (<15 cases) cells stay null",
        },
    )
    years = sorted({r["anyo"] for r in rows})
    print(
        f"barrios madrid: {n} rows, {len({r['barrio'] for r in rows})} barrios, "
        f"years {years[0]}-{years[-1]}, nulls={sum(r['eur_m2'] is None for r in rows)}"
    )


if __name__ == "__main__":
    main()
