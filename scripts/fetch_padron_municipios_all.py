"""Fetch Padrón municipal for ALL provinces (every DPOP 'municipios y sexo' table).

Generic version of the Madrid/Barcelona/Valencia/Sevilla fetchers: each
table's Total-sexo series are kept per municipio, with two aggregate
patterns handled (verified per table, fail loudly on anything else):

- same-name province/city collision ('Madrid', 'Barcelona', 'Sevilla'):
  the series closest to the pinned provincial 2021 total is the aggregate
  and is dropped; the other is kept as '<name> (ciudad)'.
- distinctly-named aggregate ('Valencia/València' vs city 'València'):
  the single series matching the pinned total is dropped.

Anchor: padron_provincia 2021, matched by canonical muni_key (exactly one
match per table or fail). One dropped aggregate per table is REQUIRED —
a table without one means the upstream layout changed.
Writes data/raw/padron_municipios_all_<id>.json per table + a single
data/raw/parquet/padron_municipios_all.parquet.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402
from spanish_housing.muni_names import muni_key  # noqa: E402

AGG_TOL = 0.005


def v2021(s: dict) -> float | None:
    return next((x["Valor"] for x in s["Data"] if x["Anyo"] == 2021), None)


def get_table_retry(table_id: int) -> list:
    try:
        payload = ine_api.get_table(table_id, retries=5)
    except RuntimeError as exc:
        raise SystemExit(f"DPOP {table_id}: {exc}") from exc
    if isinstance(payload, dict):
        raise SystemExit(f"DPOP {table_id}: {payload}")
    return payload


def operation_tables(operation: str) -> list:
    url = f"{ine_api.BASE}/TABLAS_OPERACION/{operation}"
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (pinned host)
        return json.load(resp)


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    prov = pq.read_table(str(RAW / "parquet" / "padron_provincia.parquet")).to_pylist()
    anchor: dict[str, float] = {}
    for r in prov:
        if r["anyo"] == 2021:
            anchor.setdefault(muni_key(r["territorio"]), r["poblacion"])

    tables = operation_tables("DPOP")
    municipal = [t for t in tables if "municipios y sexo" in t["Nombre"]]
    print(f"DPOP municipal tables: {len(municipal)}")
    if len(municipal) < 50:
        raise SystemExit(f"DPOP layout changed: only {len(municipal)} municipal tables")

    all_rows, dropped = [], []
    for t in sorted(municipal, key=lambda t: t["Id"]):
        tid = t["Id"]
        prefix = t["Nombre"].split(":")[0]
        matches = [v for k, v in anchor.items() if k == muni_key(prefix)]
        if len(matches) != 1:
            raise SystemExit(f"table {tid} ({prefix!r}): {len(matches)} anchor matches")
        anchor_val = matches[0]
        payload = get_table_retry(tid)
        (RAW / f"padron_municipios_all_{tid}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        by_name: dict[str, list[dict]] = defaultdict(list)
        for s in payload:
            parts = ine_api.split_nombre(s["Nombre"])
            if len(parts) != 4 or parts[1] not in ("Total", "Hombres", "Mujeres"):
                raise SystemExit(f"table {tid}: unexpected pattern: {s['Nombre']!r}")
            if parts[1] != "Total":
                continue
            by_name[parts[0]].append(s)
        agg_dropped = 0
        for name, series in sorted(by_name.items()):
            if len(series) == 1:
                s = series[0]
                v = v2021(s)
                if v is not None and abs(v - anchor_val) / anchor_val <= AGG_TOL:
                    dropped.append((tid, prefix, s["COD"]))
                    agg_dropped += 1
                    continue
                tag = name
            elif len(series) == 2:
                scored = sorted(
                    ((abs((v2021(s) or -1) - anchor_val) / anchor_val, s) for s in series),
                    key=lambda t2: t2[0],
                )
                if scored[0][0] > AGG_TOL:
                    raise SystemExit(f"table {tid}: cannot disambiguate {name!r}")
                dropped.append((tid, prefix, scored[0][1]["COD"]))
                agg_dropped += 1
                s, tag = scored[1][1], name + " (ciudad)"
                print(f"table {tid}: collision {name!r}, kept city {s['COD']}")
            else:
                raise SystemExit(f"table {tid}: {len(series)} series for {name!r}")
            for x in s["Data"]:
                all_rows.append(
                    {
                        "provincia_tabla": prefix,
                        "territorio": tag,
                        "anyo": x["Anyo"],
                        "poblacion": int(x["Valor"]),
                        "serie_cod": s["COD"],
                        "tabla_id": tid,
                    }
                )
        if agg_dropped != 1:
            raise SystemExit(f"table {tid} ({prefix!r}): {agg_dropped} aggregates dropped")
        manifest.record(
            f"data/raw/padron_municipios_all_{tid}.json",
            {
                "api": f"wstempus/DATOS_TABLA/{tid}",
                "operation": "DPOP",
                "accessed": date.today().isoformat(),
            },
        )
    pq.write_table(
        pa.Table.from_pylist(all_rows), RAW / "parquet" / "padron_municipios_all.parquet"
    )
    manifest.record(
        "data/raw/parquet/padron_municipios_all.parquet",
        {"derived": "52 DPOP municipal tables", "accessed": date.today().isoformat()},
    )
    munis = {(r["provincia_tabla"], r["territorio"]) for r in all_rows}
    print(
        f"padron municipal all: {len(all_rows)} rows, {len(munis)} municipios, "
        f"years {min(r['anyo'] for r in all_rows)}-{max(r['anyo'] for r in all_rows)}, "
        f"aggregates dropped: {len(dropped)}"
    )


if __name__ == "__main__":
    main()
