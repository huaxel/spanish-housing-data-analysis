"""Fetch Padrón municipal Sevilla province (DPOP table 2895).

Same pattern as Madrid (table 2881): '{Municipio}. {sexo}. ...', Total sexo
kept. 'Sevilla' province/city collision handled like Madrid — matched
against the pinned provincial total (padron_provincia 2021), province
dropped, city kept as 'Sevilla (ciudad)'.
Writes data/raw/padron_municipios_sev.json + .parquet
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLE_ID = 2895
RAW_JSON = RAW / "padron_municipios_sev.json"
RAW_PARQUET = RAW / "parquet" / "padron_municipios_sev.parquet"
ANCHOR_PROV = "Sevilla"


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    payload = ine_api.get_table(TABLE_ID)
    if isinstance(payload, dict):
        raise SystemExit(f"DPOP 2895: {payload}")
    RAW_JSON.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    import pyarrow.parquet as _pq

    prov = _pq.read_table(str(RAW / "parquet" / "padron_provincia.parquet")).to_pylist()
    anchor_val = next(
        r["poblacion"] for r in prov if r["territorio"] == ANCHOR_PROV and r["anyo"] == 2021
    )

    by_name: dict[str, list[dict]] = defaultdict(list)
    for s in payload:
        parts = ine_api.split_nombre(s["Nombre"])
        if len(parts) != 4 or parts[1] not in ("Total", "Hombres", "Mujeres"):
            raise SystemExit(f"unexpected pattern: {s['Nombre']!r}")
        if parts[1] != "Total":
            continue
        by_name[parts[0]].append(s)

    rows = []
    for name, series in sorted(by_name.items()):
        if len(series) == 1:
            s, tag = series[0], name
        else:

            def v2021(s: dict) -> float | None:
                return next((x["Valor"] for x in s["Data"] if x["Anyo"] == 2021), None)

            scored = sorted(
                ((abs((v2021(s) or -1) - anchor_val) / anchor_val, s) for s in series),
                key=lambda t: t[0],
            )
            if scored[0][0] > 0.005:
                raise SystemExit(f"cannot disambiguate {name!r}")
            s, tag = scored[1][1], name + " (ciudad)"
            print(
                f"collision {name!r}: dropped province {scored[0][1]['COD']}, kept city {s['COD']}"
            )
        for x in s["Data"]:
            rows.append(
                {
                    "territorio": tag,
                    "anyo": x["Anyo"],
                    "poblacion": int(x["Valor"]),
                    "serie_cod": s["COD"],
                }
            )
    pq.write_table(pa.Table.from_pylist(rows), RAW_PARQUET)
    manifest.record(
        "data/raw/padron_municipios_sev.json",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "DPOP",
            "accessed": date.today().isoformat(),
        },
    )
    manifest.record(
        "data/raw/parquet/padron_municipios_sev.parquet",
        {
            "api": f"wstempus/DATOS_TABLA/{TABLE_ID}",
            "operation": "DPOP",
            "accessed": date.today().isoformat(),
        },
    )
    print(
        f"padron municipal sev: {len(rows)} rows, "
        f"{len({r['territorio'] for r in rows})} municipios, "
        f"years {min(r['anyo'] for r in rows)}-{max(r['anyo'] for r in rows)}"
    )


if __name__ == "__main__":
    main()
