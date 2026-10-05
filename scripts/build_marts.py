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
    "data/raw/parquet/ecp_hog_ccaa.parquet",
    "data/raw/parquet/ecp_hog_prov.parquet",
    "data/raw/parquet/valor_tasado.parquet",
    "data/raw/parquet/renta_hogar_ccaa.parquet",
    "data/raw/parquet/ecp_edad_ccaa.parquet",
    "data/raw/parquet/hipotecas_ccaa.parquet",
    "data/raw/parquet/hipotecas_prov.parquet",
    "data/raw/parquet/hipotecas_rates.parquet",
    "data/raw/parquet/turisticas_counts.parquet",
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
    pob = padron_by_name(pad_prov)
    ceuta = {
        a: pob.get((N("Ceuta"), a), 0) + pob.get((N("Melilla"), a), 0) for a in range(1996, 2022)
    }
    pad_ccaa = padron_by_name(load_parquet("padron_ccaa.parquet"))
    ecp_pob = {
        (N(r["territorio"]), r["anyo"]): r["poblacion"]
        for r in load_parquet("ecp_pob_ccaa.parquet")
    }
    hog_ccaa = {
        (N(r["territorio"]), r["anyo"]): r["hogares"] for r in load_parquet("ecp_hog_ccaa.parquet")
    }
    hog_prov = {
        (N(r["territorio"]), r["anyo"]): r["hogares"] for r in load_parquet("ecp_hog_prov.parquet")
    }
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
        for anyo in range(2001, 2022):  # parque ∩ padrón (provincial ECP blocked)
            pop = ceuta[anyo] if d["cpro"] == "51+52" else pob.get((N(d["provincia"]), anyo))
            cell = stock.get((d["cpro"], anyo))
            if pop is None or cell is None:
                continue  # recorded in coverage report, not silently zero
            if d["cpro"] == "51+52":
                hogar = (hog_prov.get((N("Ceuta"), anyo), 0) or 0) + (
                    hog_prov.get((N("Melilla"), anyo), 0) or 0
                ) or None
            else:
                hogar = hog_prov.get((N(d["provincia"]), anyo))
            eur_m2, eur_trim, vt_src = prov_valor(d["cpro"], anyo)
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
                    "pop_source": "padron",
                    "hogares": hogar,
                    "viv_por_1000_hab": round(cell["total"] / pop * 1000, 2),
                    "share_no_principal": round(cell["no_principal"] / cell["total"], 4),
                    "viv_por_hogar": round(cell["total"] / hogar, 3) if hogar else None,
                    "eur_m2_libre": eur_m2,
                    "eur_m2_n_trim": eur_trim,
                    "vt_source": vt_src,
                    "hip_viv_num": hip_num,
                    "hip_ticket_miles": hip_ticket,
                    "viv_turisticas": tur_v,
                    "share_turistica_no_princ": tur_s,
                }
            )
    prov_rows.sort(key=lambda r: (r["cpro"], r["anyo"]))

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
                    "viv_por_1000_hab": round(tot / pop * 1000, 2),
                    "viv_por_hogar": round(tot / hogar, 3) if hogar else None,
                    "eur_m2_libre": eur_m2,
                    "eur_m2_n_trim": eur_trim,
                    "vt_source": eur_src,
                    "hip_viv_num": hip_nc,
                    "hip_ticket_miles": hip_tc,
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
    for name in (
        "mart_provincia_anual",
        "mart_ccaa_anual",
        "dim_territorio",
        "valor_tasado_anual",
        "tipos_hipoteca_nacional",
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
        "pop_source_rule": "padron <=2021, ecp >=2022 (1-January both); provincia mart ends 2021",
        "hogares_window": "2021+ (ECP, 1-January); viv_por_hogar NULL before",
        "valor_vs_ipv_nacional_yoy_corr": vt_ipv_corr,
        "hipotecas_window": "2003+ monthly Viviendas; complete years in marts "
        "(prov NULL before 2003); importe in thousands of EUR; national rates table",
        "valor_window": "1995+ quarterly Libre/Protegida; marts carry Libre annual means + n_trim",
        "known_gaps": [
            "provincial ECP population (Tempus3 56945) unreachable "
            "(volume-blocked; probed 2026-10-06) — provincia mart ends 2021",
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
