"""Build analysis marts from pinned raw inputs.

Reads data/input_manifest.json; refuses to build if pinned bytes are
missing/changed (mirrors four-prices verify-data before cross-regime).

Marts (CCAA grain carries prices — INE publishes NO provincial IPV):
  mart_provincia_anual  2001–2021: stock (MIVAU) x población (Padrón)
  mart_ccaa_anual       2007–2021: above aggregated + IPV (general/nueva/segunda)
  dim_territorio        canonical codes/names
Also mirrors each mart as data/processed/<name>.parquet for Evidence.

Join rules (see docs/methods.md):
- counts are summed across provinces (legitimate); IPV index values are
  NEVER summed/averaged across territories — CCAA IPV comes from INE rows.
- Ceuta+Melilla: MIVAU publishes one aggregate; Padrón publishes both
  separately (summed here); IPV publishes both separately (kept separate,
  no aggregate fabricated).
- Base identity: Nacional General 2025 must equal 100.0 (base 2025). If INE
  serves a mixed-vintage series this fails loudly instead of splicing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ine_api, manifest  # noqa: E402
from spanish_housing.data_paths import MARTS_DB, PROCESSED, RAW  # noqa: E402

N = ine_api.norm_name

# CPRO (zero-padded) -> INE CCAA name. 51/52 aggregate as "Ceuta y Melilla".
CPRO_CCAA = {
    "04": "Andalucía",
    "11": "Andalucía",
    "14": "Andalucía",
    "18": "Andalucía",
    "21": "Andalucía",
    "23": "Andalucía",
    "29": "Andalucía",
    "41": "Andalucía",
    "22": "Aragón",
    "44": "Aragón",
    "50": "Aragón",
    "33": "Asturias, Principado de",
    "07": "Balears, Illes",
    "35": "Canarias",
    "38": "Canarias",
    "39": "Cantabria",
    "05": "Castilla y León",
    "09": "Castilla y León",
    "24": "Castilla y León",
    "34": "Castilla y León",
    "37": "Castilla y León",
    "40": "Castilla y León",
    "42": "Castilla y León",
    "47": "Castilla y León",
    "49": "Castilla y León",
    "02": "Castilla - La Mancha",
    "13": "Castilla - La Mancha",
    "16": "Castilla - La Mancha",
    "19": "Castilla - La Mancha",
    "45": "Castilla - La Mancha",
    "08": "Cataluña",
    "17": "Cataluña",
    "25": "Cataluña",
    "43": "Cataluña",
    "03": "Comunitat Valenciana",
    "12": "Comunitat Valenciana",
    "46": "Comunitat Valenciana",
    "06": "Extremadura",
    "10": "Extremadura",
    "15": "Galicia",
    "27": "Galicia",
    "32": "Galicia",
    "36": "Galicia",
    "28": "Madrid, Comunidad de",
    "30": "Murcia, Región de",
    "31": "Navarra, Comunidad Foral de",
    "01": "País Vasco",
    "20": "País Vasco",
    "48": "País Vasco",
    "26": "Rioja, La",
}

REQUIRED_RAW = [
    "data/raw/parquet/parque_viviendas.parquet",
    "data/raw/parquet/ipv_ccaa_anual.parquet",
    "data/raw/parquet/padron_provincia.parquet",
    "data/raw/parquet/padron_ccaa.parquet",
    "data/raw/parquet/ecp_pob_ccaa.parquet",
    "data/raw/parquet/censo_anual_pob_prov.parquet",
    "data/raw/parquet/ecp_hog_ccaa.parquet",
    "data/raw/parquet/ecp_hog_prov.parquet",
    "data/raw/parquet/valor_tasado.parquet",
    "data/raw/parquet/renta_hogar_ccaa.parquet",
    "data/raw/parquet/ecp_edad_ccaa.parquet",
    "data/raw/parquet/hipotecas_ccaa.parquet",
    "data/raw/parquet/hipotecas_prov.parquet",
    "data/raw/parquet/hipotecas_rates.parquet",
    "data/raw/parquet/turisticas_counts.parquet",
    "data/raw/parquet/valor_municipal_madrid.parquet",
    "data/raw/parquet/ipc_ccaa.parquet",
    "data/raw/parquet/ech_hogares.parquet",
    "data/raw/parquet/censo2021_viviendas.parquet",
    "data/raw/parquet/migracion_flujos.parquet",
    "data/raw/parquet/padron_extranjeros.parquet",
    "data/raw/parquet/padron_extranjeros_origen.parquet",
    "data/raw/parquet/padron_municipios_mad.parquet",
    "data/raw/parquet/censo2011_municipios.parquet",
    "data/raw/diba_opendata.zip",
    "data/raw/parquet/diba_m19.parquet",
    "data/raw/parquet/diba_m23.parquet",
    "data/raw/parquet/diba_h9a.parquet",
    "data/raw/parquet/diba_h18a.parquet",
    "data/raw/parquet/diba_m11d.parquet",
    "data/raw/parquet/diba_m11e.parquet",
    "data/raw/parquet/diba_m12.parquet",
    "data/raw/parquet/diba_m13.parquet",
    "data/raw/parquet/padron_municipios_bcn.parquet",
]
# Affordability reference dwelling. A single explicit assumption (documented
# in methods §2), not an empirical claim about what households buy.
AFFORD_M2 = 90
# Population splice: Padrón (Revisión) through 2021, ECP from 2022.
# Same reference point (1 January), different methodology — never blended.
POP_SPLICE_YEAR = 2022
# Provinces with no direct valor-tasado rows; filled from their (identical)
# CCAA aggregate and flagged via vt_source.
VT_CCAA_FILL = {
    "28": "Madrid, Comunidad de",
    "30": "Murcia, Región de",
    "31": "Navarra, Comunidad Foral de",
    "33": "Asturias, Principado de",
}


def load_parquet(name: str) -> list[dict]:
    return pq.read_table(str(RAW / "parquet" / name)).to_pylist()


def build_dim(parque: list[dict], padron_prov: list[dict]) -> list[dict]:
    """Canonical provinces from MIVAU codes; names cross-checked vs Padrón."""
    padron_names = {N(r["territorio"]) for r in padron_prov} - {N("Total Nacional")}
    dim, seen = [], set()
    for r in parque:
        if not r["CPRO"]:
            continue
        cpro = r["CPRO"].zfill(2)
        if cpro in seen:
            continue
        seen.add(cpro)
        if N(r["Provincia"]) not in padron_names:
            raise SystemExit(
                f"province name mismatch: MIVAU={r['Provincia']!r} has no Padrón counterpart"
            )
        if cpro not in CPRO_CCAA:
            raise SystemExit(f"CPRO {cpro} missing from CPRO_CCAA map")
        dim.append({"cpro": cpro, "provincia": r["Provincia"], "ccaa": CPRO_CCAA[cpro]})
    if len(dim) != 50:
        raise SystemExit(f"expected 50 provinces, got {len(dim)}")
    dim.append({"cpro": "51+52", "provincia": "Ceuta y Melilla", "ccaa": "Ceuta y Melilla"})
    return dim


def pivot_parque(parque: list[dict]) -> dict[tuple[str, int], dict]:
    out: dict[tuple[str, int], dict] = {}
    for r in parque:
        key = (r["CPRO"].zfill(2) if r["CPRO"] else "51+52", int(r["Año"]))
        cell = out.setdefault(key, {})
        val = int(str(r["Valor"]).replace(".", "").replace(",", ""))
        if r["Tipo_Vivienda"] == "Vivienda_Principal":
            cell["principal"] = val
        elif r["Tipo_Vivienda"] == "Vivienda_No_Principal":
            cell["no_principal"] = val
        elif r["Tipo_Vivienda"] == "Viviendas_Totales":
            cell["total"] = val
        else:
            raise SystemExit(f"unknown Tipo_Vivienda {r['Tipo_Vivienda']!r}")
    for key, cell in out.items():
        if set(cell) != {"principal", "no_principal", "total"}:
            raise SystemExit(f"incomplete parque cell {key}: {cell}")
        if cell["principal"] + cell["no_principal"] != cell["total"]:
            raise SystemExit(f"parque additive check failed {key}: {cell}")
    return out


def padron_by_name(rows: list[dict]) -> dict[tuple[str, int], int]:
    return {(N(r["territorio"]), r["anyo"]): r["poblacion"] for r in rows}


def flat(s: str) -> str:
    """Accent/case/punctuation-insensitive compare for MIVAU name quirks."""
    return "".join(c for c in N(s) if c.isalnum())


def annualize_valor(rows: list[dict]) -> dict[tuple[str, int, str], dict]:
    """Mean of published quarters per (territory-key, year, regimen).

    Returns {(key, anyo, regimen): {eur_m2, n_trim}}. Empty Valor =
    unpublished quarter (skipped, counted via n_trim — never zero-filled).
    """
    buckets: dict[tuple[str, int, str], list[float]] = {}
    for r in rows:
        if not (r["Valor"] or "").strip():
            continue
        cpro = (r["CPRO"] or "").strip()
        prov_f, ccaa_f = flat(r["Provincia"]), flat(r["Comunidad_Autónoma"])
        if cpro and cpro != "null":
            key = "P" + cpro.zfill(2)
        elif (prov_f, ccaa_f) == ("TOTALCCAA", "TOTALNACIONAL"):
            key = "NACIONAL"
        elif prov_f == "CEUTAYMELILLA":
            key = "C51+52"
        elif prov_f == "TOTALCCAA":
            key = "C" + ccaa_f
        else:
            raise SystemExit(f"valor tasado: unclassifiable row {r}")
        buckets.setdefault((key, int(r["Año"]), r["Régimen"]), []).append(float(r["Valor"]))
    return {k: {"eur_m2": round(sum(v) / len(v), 1), "n_trim": len(v)} for k, v in buckets.items()}


def main() -> None:
    man = manifest.load()
    missing, mismatched = manifest.check(man.get("sha256", {}))
    required_missing = [m for m in missing if m in REQUIRED_RAW]
    if required_missing or mismatched:
        raise SystemExit(
            f"refusing to build: missing={required_missing} "
            f"mismatched={mismatched}. Run make fetch first; "
            "never edit data/raw by hand."
        )
    for req in REQUIRED_RAW:
        if req not in man.get("sha256", {}):
            raise SystemExit(f"{req} not pinned in manifest — run make fetch.")

    parque = load_parquet("parque_viviendas.parquet")
    ipv = load_parquet("ipv_ccaa_anual.parquet")
    pad_prov = load_parquet("padron_provincia.parquet")
    censo_anual = {
        (N(r["territorio"]), r["anyo"]): r["poblacion"]
        for r in load_parquet("censo_anual_pob_prov.parquet")
        if r["granularity"] == "provincia"
    }
    censo_anual_ceuta = {
        a: censo_anual.get((N("Ceuta"), a), 0) + censo_anual.get((N("Melilla"), a), 0)
        for a in range(2021, 2026)
    }

    # Base identity: Nacional/General/2025 == 100 (base 2025, full-history rebase).
    base = [
        r
        for r in ipv
        if r["territorio"] == "Nacional" and r["tipo_vivienda"] == "General" and r["anyo"] == 2025
    ]
    if not base or base[0]["indice"] != 100.0:
        raise SystemExit(f"IPV base identity broken: {base} — check methods.md §1")

    dim = build_dim(parque, pad_prov)
    stock = pivot_parque(parque)
    # Census-2011 household totals by provincia (exact; tenencia Total×Total).
    # Uniprovincial CCAA appear as CCAA rows; Ceuta/Melilla separately.
    ten11 = [
        r
        for r in load_parquet("censo2011_tenencia.parquet")
        if r["tamano"] == "Total (tamaño del hogar)"
        and r["tenencia"] == "Total (régimen de tenencia)"
    ]
    mart_prov_by_norm = {N(d["provincia"]): d["provincia"] for d in dim}
    # ECH annual households 2014-2020 (survey, thousands->units at fetch).
    ech: dict[tuple[str, int], int] = {}
    for r in load_parquet("ech_hogares.parquet"):
        key = mart_prov_by_norm.get(N(r["provincia"]))
        if key is None:
            if N(r["provincia"]) not in (N("Ceuta"), N("Melilla")):
                raise SystemExit(f"ECH unknown provincia: {r['provincia']!r}")
            key = r["provincia"]  # aggregated to 51+52 at use, like ECP
        ech[(key, r["anyo"])] = r["hogares"]
    ech_years = sorted({a for (_p, a) in ech})
    print(f"ECH hogares: {len(ech)} cells, {ech_years[0]}-{ech_years[-1]}")
    sole_prov = {}
    for d in dim:
        sole_prov.setdefault(d["ccaa"], []).append(d["provincia"])
    sole_prov = {c: ps[0] for c, ps in sole_prov.items() if len(ps) == 1}
    hog2011: dict[str, int] = {}
    for r in ten11:
        if r["provincia"] not in ("", "Total Nacional"):
            key = mart_prov_by_norm.get(N(r["provincia"]))
            if key is None:
                raise SystemExit(f"censo2011 hogares unknown provincia: {r['provincia']!r}")
            hog2011[key] = r["hogares"]
        elif r["ccaa"] in ("Ceuta", "Melilla"):
            hog2011["Ceuta y Melilla"] = hog2011.get("Ceuta y Melilla", 0) + r["hogares"]
        elif r["ccaa"]:
            # CCAA aggregate row: keep only for uniprovincial CCAA
            # (multi-province aggregates would double-count provincias).
            match = [c for c in sole_prov if N(c) == N(r["ccaa"])]
            if match:
                hog2011[sole_prov[match[0]]] = r["hogares"]
    need_hog = {d["provincia"] for d in dim}
    if set(hog2011) != need_hog:
        raise SystemExit(f"censo2011 hogares coverage gap: {need_hog - set(hog2011)}")
    # Proxy validation: principales-as-households, worst 2011 disagreement.
    gaps = [
        abs(hog2011[d["provincia"]] - stock[(d["cpro"], 2011)]["principal"])
        / stock[(d["cpro"], 2011)]["principal"]
        for d in dim
    ]
    proxy_tol = round(max(gaps) * 100, 2)
    print(f"censo2011 hogares: 51 provincias exact; principales-proxy worst gap {proxy_tol}%")
    pob = padron_by_name(pad_prov)
    ceuta = {
        a: pob.get((N("Ceuta"), a), 0) + pob.get((N("Melilla"), a), 0) for a in range(1996, 2022)
    }
    pad_ccaa = padron_by_name(load_parquet("padron_ccaa.parquet"))
    ecp_pob = {
        (N(r["territorio"]), r["anyo"]): r["poblacion"]
        for r in load_parquet("ecp_pob_ccaa.parquet")
    }

    # Household sizes 1/2/3/4+ must sum to Total (additive guard, like parque).
    def pivot_hog(fname: str) -> tuple[dict, dict]:
        cells: dict[tuple[str, int], dict] = {}
        for r in load_parquet(fname):
            cells.setdefault((N(r["territorio"]), r["anyo"]), {})[r["tamano"]] = r["hogares"]
        bad = {
            k: v
            for k, v in cells.items()
            if set(v) != {"Total", "1", "2", "3", "4 y más"}
            or v["1"] + v["2"] + v["3"] + v["4 y más"] != v["Total"]
        }
        if bad:
            raise SystemExit(f"hogares size additive check failed: {dict(list(bad.items())[:3])}")
        totals = {k: v["Total"] for k, v in cells.items()}
        sizes = {
            k: {"1": v["1"], "2": v["2"], "3": v["3"], "4p": v["4 y más"]} for k, v in cells.items()
        }
        return totals, sizes

    hog_ccaa, hog_ccaa_sz = pivot_hog("ecp_hog_ccaa.parquet")
    hog_prov, hog_prov_sz = pivot_hog("ecp_hog_prov.parquet")
    edad_2034 = {
        (N(r["territorio"]), r["anyo"]): r["poblacion"]
        for r in load_parquet("ecp_edad_ccaa.parquet")
        if r["banda"] == "20-34"
    }
    for ccaa in {d["ccaa"] for d in dim} - {"Ceuta y Melilla"}:
        if (N(ccaa), 2025) not in edad_2034:
            raise SystemExit(f"edad 20-34 missing for {ccaa}")
    if (N("Total Nacional"), 2025) not in edad_2034:
        raise SystemExit("edad 20-34 missing for Total Nacional")
    # ECP names must cover every CCAA (+ Ceuta/Melilla separately) and province.
    ecp_ccaa_names = {t for (t, _a) in ecp_pob} - {N("Total Nacional")}
    need_ccaa = {N(c) for c in {d["ccaa"] for d in dim} - {"Ceuta y Melilla"}}
    need_ccaa |= {N("Ceuta"), N("Melilla")}
    if need_ccaa - ecp_ccaa_names:
        raise SystemExit(f"ECP missing CCAA: {need_ccaa - ecp_ccaa_names}")
    need_prov = {N(d["provincia"]) for d in dim if d["cpro"] != "51+52"}
    need_prov |= {N("Ceuta"), N("Melilla")}
    if need_prov - {t for (t, _a) in hog_prov}:
        raise SystemExit(
            f"ECP hogares missing provinces: {need_prov - {t for (t, _a) in hog_prov}}"
        )
    # Overlap diagnostic: ECP Jan-2021 vs Padrón 2021 (same reference point).
    overlap = {}
    for (terr, anyo), v_ecp in ecp_pob.items():
        if anyo != 2021:
            continue
        v_pad = pad_ccaa.get((terr, anyo))
        if v_pad:
            overlap[terr] = round((v_ecp - v_pad) / v_pad * 100, 3)
    print(f"pop seam 2021, ECP-vs-Padrón % (ccaa): {overlap}")

    def ccaa_pop(ccaa: str, anyo: int) -> tuple[int | None, str]:
        if anyo < POP_SPLICE_YEAR:
            return pad_ccaa.get((N(ccaa), anyo)), "padron"
        if ccaa == "Ceuta y Melilla":
            v = ecp_pob.get((N("Ceuta"), anyo), 0) + ecp_pob.get((N("Melilla"), anyo), 0)
            return (v or None), "ecp"
        if ccaa == "Nacional":
            return ecp_pob.get((N("Total Nacional"), anyo)), "ecp"
        return ecp_pob.get((N(ccaa), anyo)), "ecp"

    def ccaa_hog(ccaa: str, anyo: int) -> int | None:
        if ccaa == "Ceuta y Melilla":
            v = hog_ccaa.get((N("Ceuta"), anyo), 0) + hog_ccaa.get((N("Melilla"), anyo), 0)
            return v or None
        if ccaa == "Nacional":
            return hog_ccaa.get((N("Total Nacional"), anyo))
        return hog_ccaa.get((N(ccaa), anyo))

    def ccaa_hog1(ccaa: str, anyo: int) -> int | None:
        if ccaa == "Ceuta y Melilla":
            v = hog_ccaa_sz.get((N("Ceuta"), anyo), {}).get("1", 0) + hog_ccaa_sz.get(
                (N("Melilla"), anyo), {}
            ).get("1", 0)
            return v or None
        if ccaa == "Nacional":
            return hog_ccaa_sz.get((N("Total Nacional"), anyo), {}).get("1")
        return hog_ccaa_sz.get((N(ccaa), anyo), {}).get("1")

    vt = annualize_valor(load_parquet("valor_tasado.parquet"))
    renta = {
        (N(r["territorio"]), r["renta_anyo"]): r["renta_eur"]
        for r in load_parquet("renta_hogar_ccaa.parquet")
        if r["indicador"] == "neta"
    }
    # ECV names 'Total Nacional' where marts say 'Nacional'.
    renta_terrs = {t for (t, _a) in renta}
    need_renta = {N(d["ccaa"]) for d in dim} - {N("Ceuta y Melilla")} | {N("Total Nacional")}
    if need_renta - renta_terrs:
        raise SystemExit(f"renta missing CCAA: {need_renta - renta_terrs}")

    # Transactions (registrars, 2007-). Additive guard: nueva + usada == total.
    trx: dict[tuple[str, int], dict] = {}
    for r in load_parquet("transmisiones.parquet"):
        trx.setdefault((N(r["territorio"]), r["grain"], r["anyo"]), {})[r["categoria"]] = r[
            "transacciones"
        ]
    trx_bad = {
        k: v
        for k, v in trx.items()
        if set(v) != {"total", "nueva", "usada", "libre", "protegida"}
        or v["nueva"] + v["usada"] != v["total"]
    }
    if trx_bad:
        raise SystemExit(f"transmisiones additive check failed: {dict(list(trx_bad.items())[:3])}")

    def trx_triple(grain: str, terr: str, anyo: int) -> tuple[float | None, float | None]:
        cell = trx.get((N(terr), grain, anyo), {})
        tot, nue = cell.get("total"), cell.get("nueva")
        if not tot or nue is None:
            return None, None
        return tot, round(nue / tot, 4)

    def ccaa_renta(ccaa: str, anyo: int) -> float | None:
        key = N("Total Nacional") if ccaa == "Nacional" else N(ccaa)
        return renta.get((key, anyo))

    # Tourist dwellings (VTE, December snapshot). Uniprovincial names already
    # deduped at fetch (identical values asserted).
    tur = {
        (N(r["territorio"]), r["anyo"]): r["viv_turisticas"]
        for r in load_parquet("turisticas_counts.parquet")
    }

    def tur_share(
        no_princ: int | None, terr_key: str, anyo: int
    ) -> tuple[int | None, float | None]:
        v = tur.get((N(terr_key), anyo))
        if v is None or not no_princ:
            return None, None
        return v, round(v / no_princ, 4)

    # Mortgages on dwellings (HPT). Complete (12-month) years only; importe
    # unit is thousands of euros (ticket 2006 ~= EUR 140k — sanity-checked).
    hip_ccaa: dict[tuple[str, int], dict] = {}
    for r in load_parquet("hipotecas_ccaa.parquet"):
        if r["n_months"] != 12:
            continue
        cell = hip_ccaa.setdefault((N(r["territorio"]), r["anyo"]), {})
        cell[r["medida"]] = r["valor"]
    hip_prov: dict[tuple[str, int], dict] = {}
    for r in load_parquet("hipotecas_prov.parquet"):
        if r["n_months"] != 12:
            continue
        cell = hip_prov.setdefault((N(r["territorio"]), r["anyo"]), {})
        cell[r["medida"]] = r["valor"]

    def hip_pair(
        store: dict[tuple[str, int], dict], terr: str, anyo: int
    ) -> tuple[float | None, float | None]:
        cell = store.get((N(terr), anyo), {})
        num = cell.get("Número de hipotecas")
        imp = cell.get("Importe de hipotecas")
        if not num or not imp:
            return None, None
        return num, round(imp / num, 1)

    def ccaa_hip(ccaa: str, anyo: int) -> tuple[float | None, float | None]:
        terr = "Total Nacional" if ccaa == "Nacional" else ccaa
        return hip_pair(hip_ccaa, terr, anyo)

    def prov_valor(cpro: str, anyo: int) -> tuple[float | None, int | None, str | None]:
        cell = vt.get(("P" + cpro, anyo, "Libre"))
        if cell:
            return cell["eur_m2"], cell["n_trim"], "prov_direct"
        if cpro == "51+52":
            cell = vt.get(("C51+52", anyo, "Libre"))
            if cell:
                return cell["eur_m2"], cell["n_trim"], "ccaa_direct"
            return None, None, None
        fill_ccaa = VT_CCAA_FILL.get(cpro)
        if fill_ccaa:
            cell = vt.get(("C" + flat(fill_ccaa), anyo, "Libre"))
            if cell:
                return cell["eur_m2"], cell["n_trim"], "ccaa_fill"
        return None, None, None

    def ccaa_valor(
        ccaa: str, anyo: int, provs: list[dict]
    ) -> tuple[float | None, int | None, str | None]:
        if ccaa == "Nacional":
            cell = vt.get(("NACIONAL", anyo, "Libre"))
            return (cell["eur_m2"], cell["n_trim"], "ccaa_direct") if cell else (None, None, None)
        cell = vt.get(("C" + flat(ccaa), anyo, "Libre"))
        if cell:
            return cell["eur_m2"], cell["n_trim"], "ccaa_direct"
        # Single-province CCAA without an aggregate row: identical geography.
        if len(provs) == 1:
            cell = vt.get(("P" + provs[0]["cpro"], anyo, "Libre"))
            if cell:
                return cell["eur_m2"], cell["n_trim"], "prov_fill"
        return None, None, None

    prov_rows = []
    for d in dim:
        for anyo in range(2001, 2026):  # parque ∩ (padrón → censo anual provincial)
            if anyo < POP_SPLICE_YEAR:
                pop = ceuta[anyo] if d["cpro"] == "51+52" else pob.get((N(d["provincia"]), anyo))
                pop_src = "padron"
            else:
                pop = (
                    censo_anual_ceuta[anyo]
                    if d["cpro"] == "51+52"
                    else censo_anual.get((N(d["provincia"]), anyo))
                )
                pop_src = "censo_anual"
            cell = stock.get((d["cpro"], anyo))
            if pop is None or cell is None:
                continue  # recorded in coverage report, not silently zero
            if d["cpro"] == "51+52":
                hogar = (hog_prov.get((N("Ceuta"), anyo), 0) or 0) + (
                    hog_prov.get((N("Melilla"), anyo), 0) or 0
                ) or None
            else:
                hogar = hog_prov.get((N(d["provincia"]), anyo))
            if anyo == 2011:
                # Exact census households (tenencia totals); ECP starts 2021.
                hogar = hog2011[d["provincia"]]
            elif 2014 <= anyo <= 2020:
                # ECH annual survey; Ceuta y Melilla aggregated like ECP.
                if d["cpro"] == "51+52":
                    hogar = (ech.get(("Ceuta", anyo), 0) or 0) + (
                        ech.get(("Melilla", anyo), 0) or 0
                    ) or None
                else:
                    hogar = ech.get((d["provincia"], anyo))
            eur_m2, eur_trim, vt_src = prov_valor(d["cpro"], anyo)
            if d["cpro"] == "51+52":
                _t1 = trx.get((N("Ceuta"), "provincia", anyo), {})
                _t2 = trx.get((N("Melilla"), "provincia", anyo), {})
                if _t1.get("total") and _t2.get("total"):
                    _tt = _t1["total"] + _t2["total"]
                    trx_p = (_tt, round((_t1["nueva"] + _t2["nueva"]) / _tt, 4))
                else:
                    trx_p = (None, None)
            else:
                trx_p = trx_triple("provincia", d["provincia"], anyo)
            if d["cpro"] == "51+52":
                t1 = tur.get((N("Ceuta"), anyo), 0) or 0
                t2 = tur.get((N("Melilla"), anyo), 0) or 0
                tur_v = t1 + t2 or None
                tur_s = round((t1 + t2) / cell["no_principal"], 4) if tur_v else None
            else:
                tur_v, tur_s = tur_share(cell["no_principal"], d["provincia"], anyo)
            if d["cpro"] == "51+52":
                n1, t1 = hip_pair(hip_prov, "Ceuta", anyo)
                n2, t2 = hip_pair(hip_prov, "Melilla", anyo)
                if n1 and n2:
                    hip_num = n1 + n2
                    hip_ticket = round((t1 * n1 + t2 * n2) / hip_num, 1)
                else:
                    hip_num, hip_ticket = None, None
            else:
                hip_num, hip_ticket = hip_pair(hip_prov, d["provincia"], anyo)
            prov_rows.append(
                {
                    "cpro": d["cpro"],
                    "provincia": d["provincia"],
                    "ccaa": d["ccaa"],
                    "anyo": anyo,
                    "viviendas_total": cell["total"],
                    "viviendas_principales": cell["principal"],
                    "viviendas_no_principales": cell["no_principal"],
                    "poblacion": pop,
                    "pop_source": pop_src,
                    "hogares": hogar,
                    "hogares_2001_proxy": (cell["principal"] if anyo == 2001 else None),
                    "viv_por_1000_hab": round(cell["total"] / pop * 1000, 2),
                    "share_no_principal": round(cell["no_principal"] / cell["total"], 4),
                    "viv_por_hogar": round(cell["total"] / hogar, 3) if hogar else None,
                    "viv_por_hogar_2001_proxy": (
                        round(cell["total"] / cell["principal"], 3) if anyo == 2001 else None
                    ),
                    "eur_m2_libre": eur_m2,
                    "eur_m2_n_trim": eur_trim,
                    "vt_source": vt_src,
                    "hip_viv_num": hip_num,
                    "hip_ticket_miles": hip_ticket,
                    "trx_total": trx_p[0],
                    "share_nueva": trx_p[1],
                    "viv_turisticas": tur_v,
                    "share_turistica_no_princ": tur_s,
                }
            )
    prov_rows.sort(key=lambda r: (r["cpro"], r["anyo"]))

    # Cross-mart coherence: provincial Censo Anual sums must equal the ECP
    # national total used in the CCAA mart (same register-based series).
    ecp_national = {
        r["anyo"]: r["poblacion"]
        for r in load_parquet("ecp_pob_ccaa.parquet")
        if r["territorio"] == "Total Nacional"
    }
    for anyo in range(POP_SPLICE_YEAR, 2026):
        prov_sum = sum(
            r["poblacion"]
            for r in prov_rows
            if r["anyo"] == anyo and r["pop_source"] == "censo_anual"
        )
        ecp_n = ecp_national.get(anyo)
        if ecp_n and prov_sum != ecp_n:
            raise SystemExit(f"censo-anual sum {prov_sum:,} != ECP national {ecp_n:,} for {anyo}")

    # CCAA mart: aggregate counts, take IPV from INE rows (never averaged).
    ipv_cell = {(r["territorio"], r["anyo"], r["tipo_vivienda"]): r["indice"] for r in ipv}
    ccaa_names = sorted({d["ccaa"] for d in dim} - {"Ceuta y Melilla"})
    ccaa_rows = []
    for ccaa in ccaa_names + ["Nacional"]:
        provs = [d for d in dim] if ccaa == "Nacional" else [d for d in dim if d["ccaa"] == ccaa]
        for anyo in range(2007, 2026):  # IPV ∩ (padrón + ECP)
            cells = [stock.get((p["cpro"], anyo)) for p in provs]
            if any(c is None for c in cells):
                continue
            if ccaa == "Nacional":
                if anyo < POP_SPLICE_YEAR:
                    pops = [
                        ceuta[anyo] if p["cpro"] == "51+52" else pob.get((N(p["provincia"]), anyo))
                        for p in provs
                    ]
                    if any(p is None for p in pops):
                        continue
                    pop, source = sum(pops), "padron"
                else:
                    pop = ecp_pob.get((N("Total Nacional"), anyo))
                    source = "ecp"
                    if pop is None:
                        continue
            else:
                pop, source = ccaa_pop(ccaa, anyo)
            if pop is None:
                continue
            tot = sum(c["total"] for c in cells)
            hogar = ccaa_hog(ccaa, anyo)
            if anyo == 2011:
                # Exact census households summed over member provinces.
                hogar = sum(hog2011[p["provincia"]] for p in provs)
            elif 2014 <= anyo <= 2020:
                # ECH summed over member provinces (counts sum legitimately).
                vals = [
                    ech.get(("Ceuta", anyo), 0) + ech.get(("Melilla", anyo), 0)
                    if p["cpro"] == "51+52"
                    else ech.get((p["provincia"], anyo))
                    for p in provs
                ]
                hogar = sum(vals) if all(vals) else None
            trx_t, trx_n = trx_triple(
                "nacional" if ccaa == "Nacional" else "ccaa",
                "Total Nacional" if ccaa == "Nacional" else ccaa,
                anyo,
            )
            no_princ = sum(c["no_principal"] for c in cells)
            terr_t = "Total Nacional" if ccaa == "Nacional" else ccaa
            tur_v, tur_s = tur_share(no_princ, terr_t, anyo)
            ipv_key = ccaa if ccaa != "Nacional" else "Nacional"
            eur_m2, eur_trim, eur_src = ccaa_valor(ccaa, anyo, provs)
            hip_nc, hip_tc = ccaa_hip(ccaa, anyo)
            ccaa_rows.append(
                {
                    "ccaa": ccaa,
                    "anyo": anyo,
                    "viviendas_total": tot,
                    "viviendas_principales": sum(c["principal"] for c in cells),
                    "viviendas_no_principales": sum(c["no_principal"] for c in cells),
                    "poblacion": pop,
                    "pop_source": source,
                    "hogares": hogar,
                    "hogares_2001_proxy": (
                        sum(c["principal"] for c in cells) if anyo == 2001 else None
                    ),
                    "hog_1persona": (h1 := ccaa_hog1(ccaa, anyo)),
                    "share_1persona": round(h1 / hogar, 4) if hogar and h1 else None,
                    "viv_por_1000_hab": round(tot / pop * 1000, 2),
                    "viv_por_hogar": round(tot / hogar, 3) if hogar else None,
                    "eur_m2_libre": eur_m2,
                    "eur_m2_n_trim": eur_trim,
                    "vt_source": eur_src,
                    "hip_viv_num": hip_nc,
                    "hip_ticket_miles": hip_tc,
                    "trx_total": trx_t,
                    "share_nueva": trx_n,
                    "viv_turisticas": tur_v,
                    "share_turistica_no_princ": tur_s,
                    "renta_hogar_neta": (renta_v := ccaa_renta(ccaa, anyo)),
                    "afford_90m2_years": (
                        round(eur_m2 * AFFORD_M2 / renta_v, 2) if eur_m2 and renta_v else None
                    ),
                    "pob_20_34": (
                        y2034 := edad_2034.get(
                            (N("Total Nacional") if ccaa == "Nacional" else N(ccaa), anyo)
                        )
                    ),
                    "share_20_34": round(y2034 / pop, 4) if y2034 else None,
                    "ipv_general": ipv_cell.get((ipv_key, anyo, "General")),
                    "ipv_nueva": ipv_cell.get((ipv_key, anyo, "Vivienda nueva")),
                    "ipv_segunda_mano": ipv_cell.get((ipv_key, anyo, "Vivienda segunda mano")),
                }
            )

    missing_ipv = [r for r in ccaa_rows if r["ipv_general"] is None]
    if missing_ipv:
        print(
            f"note: {len(missing_ipv)} CCAA-year cells without IPV "
            f"(years: {sorted({r['anyo'] for r in missing_ipv})}) — "
            "kept with NULL ipv, see coverage report"
        )

    # Cross-check: valor-tasado Libre trend vs IPV trend (Nacional, YoY %).
    nat = sorted(
        (r for r in ccaa_rows if r["ccaa"] == "Nacional" and r["eur_m2_libre"]),
        key=lambda r: r["anyo"],
    )
    vt_yoy, ipv_yoy = [], []
    for a, b in zip(nat, nat[1:], strict=False):  # consecutive pairs: lengths differ by design
        if b["anyo"] == a["anyo"] + 1 and a["ipv_general"] and b["ipv_general"]:
            vt_yoy.append((b["eur_m2_libre"] - a["eur_m2_libre"]) / a["eur_m2_libre"] * 100)
            ipv_yoy.append((b["ipv_general"] - a["ipv_general"]) / a["ipv_general"] * 100)
    vt_ipv_corr = None
    if len(vt_yoy) > 3:
        n = len(vt_yoy)
        mx, my = sum(vt_yoy) / n, sum(ipv_yoy) / n
        cov = sum((x - mx) * (y - my) for x, y in zip(vt_yoy, ipv_yoy, strict=True))
        vx = sum((x - mx) ** 2 for x in vt_yoy) ** 0.5
        vy = sum((y - my) ** 2 for y in ipv_yoy) ** 0.5
        vt_ipv_corr = round(cov / (vx * vy), 3) if vx and vy else None
    print(f"valor-vs-IPV Nacional YoY correlation ({len(vt_yoy)} years): {vt_ipv_corr}")

    vt_annual = [{"terr_key": k[0], "anyo": k[1], "regimen": k[2], **v} for k, v in vt.items()]
    rates: dict[int, dict] = {}
    for r in load_parquet("hipotecas_rates.parquet"):
        if r["n_months"] != 12:
            continue
        rates.setdefault(r["anyo"], {})[r["medida"]] = r["valor"]
    rates_rows = [
        {"anyo": a, **{k.lower(): v for k, v in m.items()}} for a, m in sorted(rates.items())
    ]
    con = duckdb.connect(str(MARTS_DB))
    con.register("prov_df", pa.Table.from_pylist(prov_rows))
    con.register("ccaa_df", pa.Table.from_pylist(ccaa_rows))
    con.register("dim_df", pa.Table.from_pylist(dim))
    con.register("vt_df", pa.Table.from_pylist(vt_annual))
    con.execute("CREATE OR REPLACE TABLE mart_provincia_anual AS SELECT * FROM prov_df")
    con.execute("CREATE OR REPLACE TABLE mart_ccaa_anual AS SELECT * FROM ccaa_df")
    con.execute("CREATE OR REPLACE TABLE dim_territorio AS SELECT * FROM dim_df")
    con.execute("CREATE OR REPLACE TABLE valor_tasado_anual AS SELECT * FROM vt_df")
    con.register("rates_df", pa.Table.from_pylist(rates_rows))
    con.execute("CREATE OR REPLACE TABLE tipos_hipoteca_nacional AS SELECT * FROM rates_df")
    ipc_buckets: dict[tuple[str, int], list[float]] = {}
    for r in load_parquet("ipc_ccaa.parquet"):
        ipc_buckets.setdefault((r["territorio"], r["anyo"]), []).append(r["ipc"])
    ipc_rows = [
        {"territorio": t, "anyo": a, "ipc": round(sum(v) / len(v), 3), "n_months": len(v)}
        for (t, a), v in sorted(ipc_buckets.items())
    ]
    con.register("ipc_df", pa.Table.from_pylist(ipc_rows))
    con.execute("CREATE OR REPLACE TABLE ipc_anual AS SELECT * FROM ipc_df")
    mun = [
        {
            "codigo": r["Código territorio"],
            "municipio": r["Territorio"],
            "anyo": int(r["Año"]),
            "eur_m2": float(r["Valor"]),
        }
        for r in load_parquet("valor_municipal_madrid.parquet")
    ]
    con.register("mun_df", pa.Table.from_pylist(mun))
    con.execute("CREATE OR REPLACE TABLE valor_municipal_madrid AS SELECT * FROM mun_df")
    pad_mun = {
        (N(r["territorio"]), r["anyo"]): r["poblacion"]
        for r in load_parquet("padron_municipios_mad.parquet")
    }
    # Valor ↔ padrón name aliases (verified 2026-10-06, fail loudly on more).
    MUNI_ALIAS = {
        N("Madrid"): N("Madrid (ciudad)"),
        N("Rozas de Madrid (Las)"): N("Rozas de Madrid, Las"),
    }
    muni_rows, muni_unmapped = [], []
    for r in load_parquet("valor_municipal_madrid.parquet"):
        key = MUNI_ALIAS.get(N(r["Territorio"]), N(r["Territorio"]))
        pop = pad_mun.get((key, int(r["Año"])))
        if pop is None:
            muni_unmapped.append(r["Territorio"])
            continue
        muni_rows.append(
            {
                "municipio": r["Territorio"],
                "anyo": int(r["Año"]),
                "eur_m2": float(r["Valor"]),
                "poblacion": pop,
            }
        )
    if muni_unmapped:
        raise SystemExit(f"municipal pop unmapped: {sorted(set(muni_unmapped))}")
    con.register("muni_df", pa.Table.from_pylist(muni_rows))
    con.execute("CREATE OR REPLACE TABLE muni_madrid AS SELECT * FROM muni_df")
    # Barcelona metro join: DIBA indicators (all keyed by municipio+year) +
    # Padrón municipal. Name match is flat()-exact; 'Barcelona' is the city
    # in DIBA (province aggregate is 'Barcelona (provincia)').
    from spanish_housing.muni_names import muni_key

    # Cross-publisher renames (verified 2026-10-06): DIBA keeps the old name.
    BCN_ALIAS = {
        muni_key("Bigues i Riells"): muni_key("Bigues i Riells del Fai"),
        muni_key("Santa Maria de Corcó"): muni_key("L'Esquirol"),
    }
    # NOTE: 'Barcelona (provincia)' (aggregate) and 'Barcelona' (city) share
    # the canonical key — the aggregate is skipped here on display name so
    # the city survives. Never filter on the bare key.
    diba: dict[tuple[str, int], dict] = {}
    diba_display: dict[str, str] = {}
    for code in ("m19", "m23", "h9a", "h18a", "m11d", "m11e", "m12", "m13"):
        for r in load_parquet(f"diba_{code}.parquet"):
            if r["valor"] is None:
                continue
            if r["municipio"] == "Barcelona (provincia)":
                continue  # province aggregate; the homonym municipio is kept
            diba.setdefault((muni_key(r["municipio"]), r["anyo"]), {})[code] = r["valor"]
            diba_display.setdefault(muni_key(r["municipio"]), r["municipio"])
    pad_bcn = {
        (muni_key(r["territorio"]), r["anyo"]): r["poblacion"]
        for r in load_parquet("padron_municipios_bcn.parquet")
    }
    # No silent merges: one padrón name per key (qualifiers already stripped).
    pad_key_names: dict[str, set] = {}
    for r in load_parquet("padron_municipios_bcn.parquet"):
        pad_key_names.setdefault(muni_key(r["territorio"]), set()).add(r["territorio"])
    dup = {k: v for k, v in pad_key_names.items() if len(v) > 1}
    if dup:
        raise SystemExit(f"muni_key collisions: {dict(list(dup.items())[:5])}")
    bcn_rows, bcn_missing_pop = [], 0
    for (nname, anyo), m in sorted(diba.items()):
        pop = pad_bcn.get((BCN_ALIAS.get(nname, nname), anyo))
        if pop is None:
            bcn_missing_pop += 1
            continue
        starts = m.get("m12")
        complet = m.get("m13")
        bcn_rows.append(
            {
                "municipio": diba_display[nname],
                "anyo": anyo,
                "poblacion": pop,
                "starts": int(starts) if starts is not None else None,
                "completions": int(complet) if complet is not None else None,
                "sale_eur_m2": m.get("m19"),
                "rent_month": m.get("m23"),
                "vacant_reg": m.get("h9a"),
                "tourist": m.get("h18a"),
                "rent_burden": m.get("m11d"),
                "mortgage_burden": m.get("m11e"),
            }
        )
    print(f"muni_bcn: {len(bcn_rows)} rows, missing pop for {bcn_missing_pop}")
    con.register("bcn_df", pa.Table.from_pylist(bcn_rows))
    con.execute("CREATE OR REPLACE TABLE muni_bcn AS SELECT * FROM bcn_df")
    # flat() already unifies 'Rozas de Madrid (Las)' vs ', Las' variants.
    valor_names = {flat(r["Territorio"]) for r in load_parquet("valor_municipal_madrid.parquet")}
    cen11 = [
        {"municipio": r["municipio"], "tipo": r["tipo"], "viviendas_2011": r["viviendas"]}
        for r in load_parquet("censo2011_municipios.parquet")
        if flat(r["municipio"]) in valor_names
    ]
    missing = valor_names - {flat(c["municipio"]) for c in cen11}
    if missing:
        raise SystemExit(f"censo2011 missing valor municipios: {sorted(missing)}")
    con.register("cen11_df", pa.Table.from_pylist(cen11))
    con.execute("CREATE OR REPLACE TABLE censo2011_mad AS SELECT * FROM cen11_df")
    # Same 2011 split for Barcelona demarcation municipios (muni_key join).
    from spanish_housing.muni_names import muni_key as _mk

    bcn_names = set()
    for code in ("m19", "m23"):
        for r in load_parquet(f"diba_{code}.parquet"):
            if r["municipio"] == "Barcelona (provincia)":
                continue  # aggregate; homonym city kept (same key!)
            bcn_names.add(_mk(r["municipio"]))
    cen_bcn = [
        {"municipio": r["municipio"], "tipo": r["tipo"], "viviendas_2011": r["viviendas"]}
        for r in load_parquet("censo2011_municipios.parquet")
        if _mk(r["municipio"]) in bcn_names
    ]
    have_bcn = {_mk(c["municipio"]) for c in cen_bcn}
    missing_bcn = {v for v in bcn_names if v not in have_bcn}
    print(f"censo2011_bcn: {len(have_bcn)} municipios, missing {len(missing_bcn)}")
    if missing_bcn:
        print(f"  (e.g. {sorted(missing_bcn)[:8]} — small municipios under census threshold)")
    con.register("cenbcn_df", pa.Table.from_pylist(cen_bcn))
    con.execute("CREATE OR REPLACE TABLE censo2011_bcn AS SELECT * FROM cenbcn_df")
    # Valencia 2011 split: second-home coast vs vacant interior for the
    # composition-crisis baseline (display names as published).
    VAL_FOCUS = {
        "València",
        "Alacant/Alicante",
        "Elx/Elche",
        "Torrevieja",
        "Benidorm",
        "Orihuela",
        "Gandia",
        "Dénia",
        "Castelló de la Plana/Castellón de la Plana",
    }
    cen_val = [
        {"municipio": r["municipio"], "tipo": r["tipo"], "viviendas_2011": r["viviendas"]}
        for r in load_parquet("censo2011_municipios.parquet")
        if r["municipio"] in VAL_FOCUS
    ]
    have_val = {c["municipio"] for c in cen_val}
    if have_val != VAL_FOCUS:
        raise SystemExit(f"censo2011 missing valencia focus: {VAL_FOCUS - have_val}")
    con.register("cenval_df", pa.Table.from_pylist(cen_val))
    con.execute("CREATE OR REPLACE TABLE censo2011_val AS SELECT * FROM cenval_df")
    # Vintage additive guard: bands (+ No consta) sum to Total per cell.
    vint: dict[tuple[str, str], dict] = {}
    for r in load_parquet("censo2011_vintage.parquet"):
        vint.setdefault((r["provincia"], r["tipo"]), {})[r["vintage"]] = r["viviendas"]
    # Tolerance 10 dwellings absolute: published cells carry ±1 rounding
    # noise (observed); structural breaks would be thousands.
    vint_bad = {}
    for k, v in vint.items():
        if v.get("Total") is None:
            vint_bad[k] = v
            continue
        s = sum(x for b, x in v.items() if b != "Total" and x is not None)
        if abs(s - (v["Total"] or 0)) > 10:
            vint_bad[k] = (s, v["Total"])
    if vint_bad:
        raise SystemExit(f"vintage additive check failed: {dict(list(vint_bad.items())[:3])}")
    vint_rows = [
        {
            "ccaa": r["ccaa"],
            "provincia": r["provincia"],
            "tipo": r["tipo"],
            "vintage": r["vintage"],
            "viviendas": r["viviendas"],
        }
        for r in load_parquet("censo2011_vintage.parquet")
    ]
    con.register("vint_df", pa.Table.from_pylist(vint_rows))
    con.execute("CREATE OR REPLACE TABLE censo2011_vintage AS SELECT * FROM vint_df")
    ten_rows = [
        {
            "ccaa": r["ccaa"],
            "provincia": r["provincia"],
            "tamano": r["tamano"],
            "tenencia": r["tenencia"],
            "hogares": r["hogares"],
        }
        for r in load_parquet("censo2011_tenencia.parquet")
    ]
    con.register("ten_df", pa.Table.from_pylist(ten_rows))
    con.execute("CREATE OR REPLACE TABLE censo2011_tenencia AS SELECT * FROM ten_df")
    con.execute("CREATE OR REPLACE TABLE censo2011_tenencia AS SELECT * FROM ten_df")
    # Third anchor: 2021 census totals vs parque 2021 (rebase cross-check).
    # Totals only — the 2021 tipo split is occupancy-based and diverges
    # definitionally from MIVAU modelled principal/no-principal (up to ~20%).
    cen21 = [
        r
        for r in load_parquet("censo2021_viviendas.parquet")
        if r["tipo"] == "Total" and r["banda"] == "Total"
    ]
    cen_tot = {r["cpro"]: r["viviendas"] for r in cen21}
    cen_tot["51+52"] = cen_tot.pop("51", 0) + cen_tot.pop("52", 0)
    gaps21 = {}
    for r in prov_rows:
        if r["anyo"] != 2021:
            continue
        c = cen_tot.get(r["cpro"])
        if c is None:
            raise SystemExit(f"censo2021 anchor missing cpro {r['cpro']}")
        gaps21[r["cpro"]] = abs(c - r["viviendas_total"]) / r["viviendas_total"] * 100
    worst21 = max(gaps21.items(), key=lambda kv: kv[1])
    print(f"censo2021 anchor: {len(gaps21)} provincias, worst gap {worst21[1]:.2f}% ({worst21[0]})")
    if worst21[1] >= 1.0:
        raise SystemExit(f"censo2021 anchor drifted: {worst21}")
    con.register(
        "cen21_df",
        pa.Table.from_pylist(load_parquet("censo2021_viviendas.parquet")),
    )
    con.execute("CREATE OR REPLACE TABLE censo2021_viviendas AS SELECT * FROM cen21_df")
    con.register("pade_df", pa.Table.from_pylist(load_parquet("padron_extranjeros.parquet")))
    con.execute("CREATE OR REPLACE TABLE padron_extranjeros AS SELECT * FROM pade_df")
    con.register(
        "padeo_df", pa.Table.from_pylist(load_parquet("padron_extranjeros_origen.parquet"))
    )
    con.execute("CREATE OR REPLACE TABLE padron_extranjeros_origen AS SELECT * FROM padeo_df")
    # Foreign immigration flows 2008-2021 (EM 24322, annual). Counts sum:
    # Nacional + Ceuta-y-Melilla aggregates built locally, like ECP.
    mig_rows = []
    for r in load_parquet("migracion_flujos.parquet"):
        key = mart_prov_by_norm.get(N(r["provincia"]))
        if key is None:
            if N(r["provincia"]) not in (N("Ceuta"), N("Melilla")):
                raise SystemExit(f"migracion unknown provincia: {r['provincia']!r}")
            key = r["provincia"]
        mig_rows.append(
            {
                "provincia": key,
                "anyo": r["anyo"],
                "nacionalidad": r["nacionalidad"],
                "flujo": r["flujo"],
            }
        )
    for agg_name, members in [
        ("Nacional", None),
        ("Ceuta y Melilla", ("Ceuta", "Melilla")),
    ]:
        pool = [r for r in mig_rows if members is None or r["provincia"] in members]
        acc: dict[tuple[int, str], float] = {}
        for r in pool:
            acc[(r["anyo"], r["nacionalidad"])] = (
                acc.get((r["anyo"], r["nacionalidad"]), 0) + r["flujo"]
            )
        mig_rows += [
            {"provincia": agg_name, "anyo": a, "nacionalidad": n, "flujo": v}
            for (a, n), v in sorted(acc.items())
        ]
    con.register("mig_df", pa.Table.from_pylist(mig_rows))
    con.execute("CREATE OR REPLACE TABLE migra_anual AS SELECT * FROM mig_df")
    for name in (
        "mart_provincia_anual",
        "mart_ccaa_anual",
        "dim_territorio",
        "valor_tasado_anual",
        "tipos_hipoteca_nacional",
        "ipc_anual",
        "valor_municipal_madrid",
        "muni_madrid",
        "censo2011_mad",
        "muni_bcn",
        "censo2011_bcn",
        "censo2011_val",
        "censo2011_vintage",
        "censo2011_tenencia",
        "censo2021_viviendas",
        "migra_anual",
        "padron_extranjeros",
        "padron_extranjeros_origen",
    ):
        con.execute(f"COPY (SELECT * FROM {name}) TO '{PROCESSED / name}.parquet' (FORMAT PARQUET)")
    coverage = {
        "mart_provincia_anual_rows": len(prov_rows),
        "mart_ccaa_anual_rows": len(ccaa_rows),
        "prov_years": [min(r["anyo"] for r in prov_rows), max(r["anyo"] for r in prov_rows)],
        "ccaa_years": [min(r["anyo"] for r in ccaa_rows), max(r["anyo"] for r in ccaa_rows)],
        "ccaa_year_cells_without_ipv": len(missing_ipv),
        "ipv_base_check": "Nacional/General/2025 == 100.0 OK",
        "pop_seam_2021_ecp_vs_padron_pct": overlap,
        "pop_source_rule": "padron <=2021, ecp (CCAA) / censo anual (prov) >=2022 (1-January both)",
        "hogares_window": "2021+ (ECP, 1-January); 2014-2020 ECH annual survey;"
        " 2011 exact (censo tenencia totals, 51 provincias); viv_por_hogar NULL otherwise",
        "censo2021_anchor": "provincial totals vs parque 2021, worst gap <1.0% (tipo split"
        " diverges definitionally, unchecked)",
        "padron_extranjeros_window": "1998-2022 annual foreign stocks by provincia"
        " (TOTAL EXTRANJEROS x Ambos sexos; Bartik shares base)",
        "migracion_window": "2008-2021 annual foreign/Spanish inflows by provincia"
        " (EM 24322, Ambos sexos, Total edad); Nacional + 51+52 aggregated locally",
        "hogares_2001_proxy": "principales-as-households; worst 2011 disagreement"
        f" {proxy_tol}% — documented tolerance, not exact",
        "valor_vs_ipv_nacional_yoy_corr": vt_ipv_corr,
        "transmisiones_window": "2007+ registrars; nueva+usada==total asserted; "
        "share_nueva in both marts",
        "hipotecas_window": "2003+ monthly Viviendas; complete years in marts "
        "(prov NULL before 2003); importe in thousands of EUR; national rates table",
        "valor_window": "1995+ quarterly Libre/Protegida; marts carry Libre annual means + n_trim",
        "ipc_window": "2002+ monthly general index (base 2021), CCAA + Nacional (+Ceuta/Melilla"
        " separately); ipc_anual carries annual means + n_months",
        "known_gaps": [
            "provincial ECP population (Tempus3 56945) unreachable (volume-blocked;"
            " probed 2026-10-06) — provincia mart continues 2022-2025 on the Censo"
            " Anual de Población static CSV (verified: 2025 national = ECP exact,"
            " 2021 prov-vs-padrón mean |Δ| 0.17%)",
            "IPV starts 2007 — no quality-adjusted price index before",
            "IPV has no provincial grain — price joins are CCAA/national only",
            "Ceuta/Melilla have separate IPV rows but aggregated stock — excluded from CCAA mart",
        ],
    }
    (PROCESSED / "coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(coverage, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if "--refresh-manifest" in sys.argv:
        print("refresh-manifest not implemented: re-run make fetch to re-pin.")
        sys.exit(2)
    main()
