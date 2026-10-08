"""Fetch selected Sevilla SIM context indicators at barrio grain.

These are separate public ArcGIS layers, each with 108 barrio records:
residents/households (2015–2021), housing typology, rehabilitation need,
housing use/vacancy, and tourist-housing pressure (2008, 2021-02, 2021-08,
2022-02 plus registered totals). The latter three thematic layers lack a
reference year in the field names; they remain undated SIM snapshots. The
services were last edited in 2023. Accessibility is published only at
Distrito/TM grain, not as barrio data, so it is intentionally not inferred.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import manifest  # noqa: E402

BASE = "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services"
SOURCES = {
    "poblacion": {
        "layer": f"{BASE}/Evolución_reciente_de_población_residente/FeatureServer/26",
        "fields": ["IDG", "ID_DIS", "DIS", "ID_BAR", "BAR", *[f"POB_{y}" for y in range(15, 22)]],
        "raw": "data/raw/sevilla_sim_poblacion.json",
        "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS feature layer",
    },
    "hogares": {
        "layer": f"{BASE}/Evolución_reciente_de_hogares_residentes/FeatureServer/30",
        "fields": ["IDG", "ID_DIS", "DIS", "ID_BAR", "BAR", *[f"HOG_{y}" for y in range(15, 22)]],
        "raw": "data/raw/sevilla_sim_hogares.json",
        "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS feature layer",
    },
    "tipologia": {
        "layer": f"{BASE}/ñññ/FeatureServer/2",
        "fields": [
            "IDG",
            "ID_DIS",
            "DIS",
            "ID_BAR",
            "BAR",
            "VF",
            "VF_COL",
            "VF_COL_100",
            "VF_UNI",
            "VF_UNI_100",
        ],
        "raw": "data/raw/sevilla_sim_tipologia.json",
        "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS feature layer",
    },
    "caracteristicas": {
        "layer": f"{BASE}/TTT/FeatureServer/4",
        "fields": [
            "IDG",
            "ID_DIS",
            "DIS",
            "ID_BAR",
            "BAR",
            "VF_COL_ANT",
            "VF_COL_CAL",
            "VF_COL_SUP",
            "VF_UNI_ANT",
            "VF_UNI_CAL",
            "VF_UNI_SUP",
        ],
        "raw": "data/raw/sevilla_sim_caracteristicas.json",
        "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS barrio layer",
    },
    "rehabilitacion": {
        "layer": f"{BASE}/rrr/FeatureServer/101",
        "fields": ["IDG", "ID_DIS", "DIS", "ID_BAR", "BAR", "VF_REH", "VF_REH_100"],
        "raw": "data/raw/sevilla_sim_rehabilitacion.json",
        "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS feature layer",
    },
    "uso": {
        "layer": f"{BASE}/VIVVAC/FeatureServer/133",
        "fields": [
            "IDG",
            "ID_DIS",
            "DIS",
            "ID_BAR",
            "BAR",
            "VFA",
            "VP",
            "VP_100",
            "VS",
            "VS_100",
            "VV",
            "VV_100",
        ],
        "raw": "data/raw/sevilla_sim_uso.json",
        "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS feature layer",
    },
    "turismo": {
        "layer": f"{BASE}/TTT/FeatureServer/4",
        "fields": [
            "IDG",
            "ID_DIS",
            "DIS",
            "ID_BAR",
            "BAR",
            "VFT_2008",
            "VFT_2102",
            "VFT_2108",
            "VFT_2202",
            "VFT_2008_PRE",
            "VFT_2102_PRE",
            "VFT_2108_PRE",
            "VFT_2202_PRE",
            "VFT_REG",
            "VFT_REG_PLA",
        ],
        "raw": "data/raw/sevilla_sim_turismo.json",
        "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS feature layer",
    },
}

PARQUETS = {
    "poblacion_hogares": "data/raw/parquet/sevilla_sim_pob_hog.parquet",
    "vivienda": "data/raw/parquet/sevilla_sim_vivienda.parquet",
    "turismo": "data/raw/parquet/sevilla_sim_turismo.parquet",
}
PARQUET_SOURCES = {
    "poblacion_hogares": ("poblacion", "hogares"),
    "vivienda": ("tipologia", "caracteristicas", "rehabilitacion", "uso"),
    "turismo": ("turismo",),
}


def get_json(url: str) -> dict:
    url = urllib.parse.quote(url, safe=":/?=&%")
    req = urllib.request.Request(url, headers={"User-Agent": "housing-data-analysis/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response:  # noqa: S310 (pinned ArcGIS host)
        return json.load(response)


def fetch_layer(config: dict) -> tuple[dict, list[dict]]:
    layer = config["layer"]
    metadata = get_json(layer + "?f=json")
    if metadata.get("error"):
        raise SystemExit(f"SIM layer metadata error: {metadata['error']}")
    fields = {f["name"] for f in metadata.get("fields", [])}
    if not set(config["fields"]).issubset(fields):
        missing = sorted(set(config["fields"]) - fields)
        raise SystemExit(f"SIM layer schema changed; missing fields: {missing}")
    params = urllib.parse.urlencode(
        {
            "where": "1=1",
            "outFields": ",".join(config["fields"]),
            "returnGeometry": "false",
            "f": "json",
        }
    )
    query = get_json(layer + "/query?" + params)
    if query.get("error"):
        raise SystemExit(f"SIM layer query error: {query['error']}")
    features = [f["attributes"] for f in query.get("features", [])]
    if len(features) != 108 or len({str(a["IDG"]) for a in features}) != 108:
        raise SystemExit(f"SIM barrio count changed: {len(features)} records")
    return {"metadata": metadata, "query": query}, features


def clean_base(a: dict) -> dict:
    return {
        "idg": str(a["IDG"]),
        "id_distrito": str(a["ID_DIS"]),
        "distrito": a["DIS"],
        "id_barrio": str(a["ID_BAR"]),
        "barrio": a["BAR"],
    }


def main() -> None:
    fetched = {}
    for name, config in SOURCES.items():
        payload, features = fetch_layer(config)
        raw_path = Path(config["raw"])
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_tmp = raw_path.with_suffix(raw_path.suffix + ".tmp")
        raw_tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        raw_tmp.replace(raw_path)
        by_id = {str(a["IDG"]): a for a in features}
        fetched[name] = (config, payload, by_id)
        edited = payload["metadata"].get("editingInfo", {}).get("dataLastEditDate")
        vintage = (
            datetime.fromtimestamp(edited / 1000, UTC).date().isoformat() if edited else "unknown"
        )
        manifest.record(
            config["raw"],
            {
                "url": config["layer"] + "/query",
                "publisher": config["publisher"],
                "accessed": date.today().isoformat(),
                "note": (
                    f"108 barrios; service data last edited {vintage}; fields pinned by fetcher"
                ),
            },
        )

    id_sets = {name: set(item[2]) for name, item in fetched.items()}
    if any(ids != id_sets["poblacion"] for ids in id_sets.values()):
        raise SystemExit("SIM barrio IDs differ across context layers; do not join")
    base = fetched["poblacion"][2]
    households = fetched["hogares"][2]
    for idg, a in base.items():
        b = households[idg]
        if (a["DIS"], a["BAR"]) != (b["DIS"], b["BAR"]):
            raise SystemExit(f"SIM geography label mismatch for {idg}")
    pop_hog_rows = []
    for idg, a in base.items():
        b = households[idg]
        keys = clean_base(a)
        for year in range(2015, 2022):
            pop_hog_rows.append(
                {
                    **keys,
                    "anyo": year,
                    "poblacion": a.get(f"POB_{year % 100}"),
                    "hogares": b.get(f"HOG_{year % 100}"),
                }
            )

    typology = fetched["tipologia"][2]
    characteristics = fetched["caracteristicas"][2]
    rehab = fetched["rehabilitacion"][2]
    use = fetched["uso"][2]
    housing_rows = []
    for idg, a in typology.items():
        for other in (characteristics[idg], rehab[idg], use[idg]):
            if (a["DIS"], a["BAR"]) != (other["DIS"], other["BAR"]):
                raise SystemExit(f"SIM geography label mismatch for {idg}")
        housing_rows.append(
            {
                **clean_base(a),
                "viviendas_familiares": a.get("VF"),
                "colectivas": a.get("VF_COL"),
                "colectivas_pct": a.get("VF_COL_100"),
                "unifamiliares": a.get("VF_UNI"),
                "unifamiliares_pct": a.get("VF_UNI_100"),
                "antiguedad_colectiva_anos": characteristics[idg].get("VF_COL_ANT"),
                "calidad_colectiva": characteristics[idg].get("VF_COL_CAL"),
                "superficie_colectiva_m2": characteristics[idg].get("VF_COL_SUP"),
                "antiguedad_unifamiliar_anos": characteristics[idg].get("VF_UNI_ANT"),
                "calidad_unifamiliar": characteristics[idg].get("VF_UNI_CAL"),
                "superficie_unifamiliar_m2": characteristics[idg].get("VF_UNI_SUP"),
                "rehabilitacion_estimada": rehab[idg].get("VF_REH"),
                "rehabilitacion_estimada_pct": rehab[idg].get("VF_REH_100"),
                "viviendas_familiares_uso": use[idg].get("VFA"),
                "principales": use[idg].get("VP"),
                "principales_pct": use[idg].get("VP_100"),
                "secundarias": use[idg].get("VS"),
                "secundarias_pct": use[idg].get("VS_100"),
                "deshabitadas": use[idg].get("VV"),
                "deshabitadas_pct": use[idg].get("VV_100"),
            }
        )

    tourism = fetched["turismo"][2]
    tourism_rows = []
    for a in tourism.values():
        tourism_rows.append(
            {
                **clean_base(a),
                "vft_2008": a.get("VFT_2008"),
                "vft_2008_pct": a.get("VFT_2008_PRE"),
                "vft_2021_02": a.get("VFT_2102"),
                "vft_2021_02_pct": a.get("VFT_2102_PRE"),
                "vft_2021_08": a.get("VFT_2108"),
                "vft_2021_08_pct": a.get("VFT_2108_PRE"),
                "vft_2022_02": a.get("VFT_2202"),
                "vft_2022_02_pct": a.get("VFT_2202_PRE"),
                "vft_registradas": a.get("VFT_REG"),
                "vft_registradas_plazas": a.get("VFT_REG_PLA"),
            }
        )

    datasets = {
        "poblacion_hogares": pop_hog_rows,
        "vivienda": housing_rows,
        "turismo": tourism_rows,
    }
    for name, rows in datasets.items():
        rel = PARQUETS[name]
        parquet = Path(rel)
        parquet.parent.mkdir(parents=True, exist_ok=True)
        parquet_tmp = parquet.with_suffix(parquet.suffix + ".tmp")
        pq.write_table(pa.Table.from_pylist(rows), parquet_tmp)
        parquet_tmp.replace(parquet)
        manifest.record(
            rel,
            {
                "url": "; ".join(fetched[source][0]["layer"] for source in PARQUET_SOURCES[name]),
                "publisher": "EMVISESA/Ayuntamiento de Sevilla SIM, ArcGIS feature layers",
                "accessed": date.today().isoformat(),
                "note": (
                    "derived from pinned SIM raw query JSON; nulls retained; "
                    "reference limitations documented"
                ),
            },
        )
        print(f"Sevilla SIM {name}: {len(rows)} rows")
    print(
        "null counts:",
        {
            "population": sum(r["poblacion"] is None for r in pop_hog_rows),
            "households": sum(r["hogares"] is None for r in pop_hog_rows),
            "rehab": sum(r["rehabilitacion_estimada"] is None for r in housing_rows),
            "vacancy": sum(r["deshabitadas"] is None for r in housing_rows),
            "tourism_pressure_2022_02": sum(r["vft_2022_02_pct"] is None for r in tourism_rows),
        },
    )


if __name__ == "__main__":
    main()
