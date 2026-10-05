"""Fetch Padrón municipal Madrid province (DPOP table 2881).

Pattern '{Municipio}. {Total|Hombres|Mujeres}. Total habitantes. Personas.'
Keeps Total sexo, all years. COLLISION: 'Madrid. Total...' exists twice —
province aggregate (DPOP12922, ~7.1M) and capital city (DPOP13156, ~3.5M).
Disambiguated against the pinned provincial total (padron_provincia 2021):
within 0.5% -> 'Madrid (provincia)' [dropped, we have it], else
'Madrid (ciudad)'. Anything else ambiguous fails loudly.
Writes data/raw/padron_municipios_mad.json + .parquet
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLE_ID = 2881
RAW_JSON = RAW / "padron_municipios_mad.json"
RAW_PARQUET = RAW / "parquet" / "padron_municipios_mad.parquet"


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    payload = ine_api.get_table(TABLE_ID)
    if isinstance(payload, dict):
        raise SystemExit(f"DPOP 2881: {payload}")
    (RAW_JSON).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # Provincial anchor for disambiguation (pinned input, not magic number).
    import pyarrow.parquet as _pq

    prov = _pq.read_table(str(RAW / "parquet" / "padron_provincia.parquet")).to_pylist()
    anchor_val = next(
        r["poblacion"] for r in prov if r["territorio"] == "Madrid" and r["anyo"] == 2021
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
            s = series[0]
            tag = name
        else:
            # Madrid collision: match province aggregate to the anchor.
            def v2021(s: dict) -> float | None:
                for x in s["Data"]:
                    if x["Anyo"] == 2021:
                        return x["Valor"]
                return None

            scored = [(abs((v2021(s) or -1) - anchor_val) / anchor_val, s) for s in series]
            scored.sort(key=lambda t: t[0])
            if scored[0][0] > 0.005:
                raise SystemExit(f"cannot disambiguate {name!r}: {[v for v, _ in scored]}")
            s = scored[1][1]  # the non-province one = capital city
            tag = name + " (ciudad)"
            dropped = scored[0][1]["COD"]
            print(f"collision {name!r}: dropped province {dropped}, kept city {s['COD']}")
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
        "data/raw/padron_municipios_mad.json",
        {"api": f"wstempus/DATOS_TABLA/{TABLE_ID}", "operation": "DPOP", "accessed": "2026-10-06"},
    )
    manifest.record(
        "data/raw/parquet/padron_municipios_mad.parquet",
        {"api": f"wstempus/DATOS_TABLA/{TABLE_ID}", "operation": "DPOP", "accessed": "2026-10-06"},
    )
    terrs = sorted({r["territorio"] for r in rows})
    print(
        f"padron municipal mad: {len(rows)} rows, {len(terrs)} municipios, "
        f"years {min(r['anyo'] for r in rows)}-{max(r['anyo'] for r in rows)}"
    )


if __name__ == "__main__":
    main()
