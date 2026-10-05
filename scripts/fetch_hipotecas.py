"""Fetch INE Hipotecas (HPT): mortgages on dwellings + rates.

- 76316: CCAA monthly, 2003- ('{Naturaleza}. {Terr}. {Medida}. Base nueva. Mensual.')
- 76317: provincia monthly, 2003- ('{Naturaleza}. {Medida}. {Terr}. Base nueva. Mensual.')
  NOTE the swapped positions — parsed structurally, not positionally.
- 76315: national rates (Viviendas, Total/Fijo/Variable).
Keeps nature == 'Viviendas' only. Annual sums (número, importe) / means
(rates) with n_months; marts use complete (12-month) years only.
Writes data/raw/hipotecas_{ccaa,prov,rates}.json + .parquet
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

TABLES = {76316: "ccaa", 76317: "prov", 76315: "rates"}
MONTHS = set(range(1, 13))


def classify(nombre: str) -> tuple[str, str, str] | None:
    """Return (kind, territorio, medida) or None to skip. kind: count|rates."""
    parts = ine_api.split_nombre(nombre)
    if len(parts) < 5 or parts[0] != "Viviendas":
        return None
    if parts[1] == "Tipo de interés medio":
        # 'Viviendas. Tipo de interés medio. Total Nacional. Base nueva. Mensual. Total.'
        if len(parts) != 6 or parts[2] != "Total Nacional":
            return None
        return ("rates", parts[2], parts[5])
    # count/capital: territory and measure swap positions between tables.
    rest = [p for p in parts[1:-2] if p in ("Número de hipotecas", "Importe de hipotecas")]
    terr = [p for p in parts[1:-2] if p not in ("Número de hipotecas", "Importe de hipotecas")]
    if len(rest) != 1 or len(terr) != 1:
        return None
    return ("count", terr[0], rest[0])


def main() -> None:
    (RAW / "parquet").mkdir(parents=True, exist_ok=True)
    for table_id, kind in TABLES.items():
        payload = ine_api.get_table(table_id)
        if isinstance(payload, dict):
            raise SystemExit(f"HPT {table_id}: {payload}")
        units = {(s.get("FK_Unidad"), s.get("FK_Escala")) for s in payload}
        print(f"HPT {table_id} units/escala: {sorted(units)}")
        annual: dict[tuple[str, int, str], list[float]] = {}
        skipped: list[str] = []
        for s in payload:
            cls = classify(s["Nombre"])
            if cls is None:
                skipped.append(s["Nombre"])
                continue
            _k, terr, medida = cls
            for x in s["Data"]:
                if x["FK_Periodo"] not in MONTHS:
                    skipped.append(f"{s['Nombre']} periodo={x['FK_Periodo']}")
                    continue
                annual.setdefault((terr, x["Anyo"], medida), []).append(x["Valor"])
        agg_mean = kind == "rates"  # rates average; counts/capital sum
        rows = [
            {
                "territorio": t,
                "anyo": a,
                "medida": m,
                "valor": round(sum(v) / len(v), 2) if agg_mean else round(sum(v), 2),
                "n_months": len(v),
            }
            for (t, a, m), v in sorted(annual.items())
        ]
        if not rows:
            raise SystemExit(f"HPT {kind}: zero rows — format changed?")
        out = RAW / "parquet" / f"hipotecas_{kind}.parquet"
        pq.write_table(pa.Table.from_pylist(rows), out)
        (RAW / f"hipotecas_{kind}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        manifest.record(
            f"data/raw/hipotecas_{kind}.json",
            {
                "api": f"wstempus/DATOS_TABLA/{table_id}",
                "operation": "HPT",
                "accessed": "2026-10-06",
            },
        )
        manifest.record(
            f"data/raw/parquet/hipotecas_{kind}.parquet",
            {
                "api": f"wstempus/DATOS_TABLA/{table_id}",
                "operation": "HPT",
                "accessed": "2026-10-06",
                "note": "Viviendas only; annual sums/means + n_months",
            },
        )
        print(f"hipotecas {kind}: {len(rows)} annual rows; skipped {len(skipped)}")


if __name__ == "__main__":
    main()
