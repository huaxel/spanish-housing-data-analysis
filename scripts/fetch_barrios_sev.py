"""Fetch Sevilla barrio rent and purchase indicators from the SIM ArcGIS layers.

Layer 179 (X FeatureServer) publishes IPRA rents; layer 171 (VHS
FeatureServer) publishes SIM purchase-price indicators by housing type.
Both expose 108 barrios. IPRA values are EUR/m² built/month, from AVRA
rental-deposit records, and annual labels are rolling three-year windows.
The purchase indicators are €/m² built but have no time field; the reference
period/method is not specified in the service metadata, last edited
2023-02-12. Keep them as cross-sectional indicators, not annual transaction
prices. Missing values remain null.

Writes raw JSON and parquet for both datasets.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import RAW  # noqa: E402

URL = (
    "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/"
    "X/FeatureServer/179/query?where=1%3D1&outFields=*&returnGeometry=false&f=json"
)
LAYER_URL = "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/X/FeatureServer/179"
PRICE_LAYER_URL = (
    "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/VHS/FeatureServer/171"
)
PRICE_URL = PRICE_LAYER_URL + "/query?where=1%3D1&outFields=*&returnGeometry=false&f=json"
RAW_JSON = RAW / "barrios_sevilla_ipra.json"
RAW_PARQUET = RAW / "parquet" / "barrios_sevilla_ipra.parquet"
PRICE_JSON = RAW / "barrios_sevilla_compra.json"
PRICE_PARQUET = RAW / "parquet" / "barrios_sevilla_compra.parquet"


def main() -> None:
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "housing-data-analysis/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (pinned ArcGIS host)
        payload = json.load(resp)
    if payload.get("error"):
        raise SystemExit(f"SIM IPRA query error: {payload['error']}")
    features = payload.get("features", [])
    if len(features) < 100:
        raise SystemExit(f"SIM IPRA layer unexpectedly small: {len(features)} features")
    years = sorted(
        int(field["name"].removeprefix("IPRA_")) + 2000
        for field in payload.get("fields", [])
        if field["name"].startswith("IPRA_")
    )
    if years != list(range(2016, 2023)):
        raise SystemExit(f"SIM IPRA year schema changed: {years}")
    RAW_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for feature in features:
        a = feature["attributes"]
        for year in years:
            value = a.get(f"IPRA_{year - 2000}")
            rows.append(
                {
                    "idg": str(a["IDG"]),
                    "id_distrito": str(a["ID_DIS"]),
                    "distrito": a["DIS"],
                    "id_barrio": str(a["ID_BAR"]),
                    "barrio": a["BAR"],
                    "anyo": year,
                    "ipra_eur_m2": float(value) if value is not None else None,
                }
            )
    pq.write_table(pa.Table.from_pylist(rows), RAW_PARQUET)
    outputs = (
        "data/raw/barrios_sevilla_ipra.json",
        "data/raw/parquet/barrios_sevilla_ipra.parquet",
    )
    for rel in outputs:
        manifest.record(
            rel,
            {
                "url": URL if rel.endswith(".json") else LAYER_URL,
                "publisher": (
                    "EMVISESA/Ayuntamiento de Sevilla SIM (AVRA fianzas), ArcGIS feature layer"
                ),
                "accessed": date.today().isoformat(),
                "note": "IPRA 2016-2022; rolling 3-year windows; metadata last edited 2023-02-12",
            },
        )
    print(
        f"barrios Sevilla IPRA: {len(rows)} rows, {len(features)} barrios, "
        f"years {years[0]}-{years[-1]}, "
        f"nulls={sum(r['ipra_eur_m2'] is None for r in rows)}"
    )

    price_req = urllib.request.Request(
        PRICE_URL, headers={"User-Agent": "housing-data-analysis/1.0"}
    )
    with urllib.request.urlopen(price_req, timeout=120) as resp:  # noqa: S310 (pinned ArcGIS host)
        price_payload = json.load(resp)
    if price_payload.get("error"):
        raise SystemExit(f"SIM purchase layer query error: {price_payload['error']}")
    price_features = price_payload.get("features", [])
    if len(price_features) != 108:
        raise SystemExit(f"SIM purchase layer barrio count changed: {len(price_features)}")
    required_fields = {"PRO_COL_UNT", "PRO_UNI_UNT"}
    if not required_fields.issubset({f["name"] for f in price_payload.get("fields", [])}):
        raise SystemExit("SIM purchase layer schema changed")
    PRICE_JSON.write_text(json.dumps(price_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    price_rows = []
    for feature in price_features:
        a = feature["attributes"]
        price_rows.append(
            {
                "idg": str(a["IDG"]),
                "id_distrito": str(a["ID_DIS"]),
                "distrito": a["DIS"],
                "id_barrio": str(a["ID_BAR"]),
                "barrio": a["BAR"],
                "compra_colectiva_eur_m2": a.get("PRO_COL_UNT"),
                "compra_unifamiliar_eur_m2": a.get("PRO_UNI_UNT"),
            }
        )
    pq.write_table(pa.Table.from_pylist(price_rows), PRICE_PARQUET)
    price_outputs = (
        "data/raw/barrios_sevilla_compra.json",
        "data/raw/parquet/barrios_sevilla_compra.parquet",
    )
    for rel in price_outputs:
        manifest.record(
            rel,
            {
                "url": PRICE_URL if rel.endswith(".json") else PRICE_LAYER_URL,
                "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS feature layer",
                "accessed": date.today().isoformat(),
                "note": (
                    "PRO_COL_UNT/PRO_UNI_UNT = purchase €/m² built by housing type; "
                    "no period field; reference period/method unspecified; "
                    "service last edited 2023-02-12"
                ),
            },
        )
    missing_uni = sum(r["compra_unifamiliar_eur_m2"] is None for r in price_rows)
    print(
        f"barrios Sevilla SIM purchase: {len(price_rows)} barrios, "
        f"collective nulls={sum(r['compra_colectiva_eur_m2'] is None for r in price_rows)}, "
        f"unifamiliar nulls={missing_uni}"
    )


if __name__ == "__main__":
    main()
