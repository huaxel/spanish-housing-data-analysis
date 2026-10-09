"""CaixaBank-style housing-deficit arithmetic: household creation vs completions.

Descriptive exploration only: per-province and national gaps between ECP
household creation and MIVAU finished dwellings over two pre-specified
windows, plus a tourist-adjusted partial variant. No causal claim, no
p-values, no model, no forecast.

Conventions (pre-specified, disclosed in docs/explorations/deficit_vivienda.md):
Jan-1 household stocks (ECP), so creation during years a..b is stock(b+1)
minus stock(a); completions are summed calendar-month Ministerio flows over
the same years. Tourist flow is the December-snapshot stock difference, the
same window alignment. Missing monthly completion cells are never filled:
sums exclude them and the shortfall is inventoried. Ceuta y Melilla are
combined, matching the marts. The foreign-buyer adjustment in CaixaBank's
third variant is not reproducible from in-repo inputs and is omitted;
deficit_v3p subtracts tourist conversions only and is labeled partial.

Writes artifacts/deficit_vivienda.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

MARTS_DB = PROCESSED / "marts.duckdb"
TERMINADAS = RAW / "parquet" / "mivau_terminadas.parquet"
ECP_HOG = RAW / "parquet" / "ecp_hog_prov.parquet"
ARTIFACT = ROOT / "artifacts" / "deficit_vivienda.json"
WINDOWS = {
    "2021-2024": {"flow_years": (2021, 2022, 2023, 2024), "stock_end": 2025},
    "2021-2025": {"flow_years": (2021, 2022, 2023, 2024, 2025), "stock_end": 2026},
}
# CaixaBank published benchmarks (diagnostic comparison only, never gates).
BENCHMARKS = {
    "v2_2021-2024": 600000,
    "v2_2021-2025": 734000,
    "top5_concentration": ("Madrid", "Barcelona", "Valencia", "Alicante", "Murcia"),
    "top5_share": 0.49,
    "exceptions": ("Guipúzcoa", "Cáceres", "Soria"),
}


def annual_flows(monthly: list[dict], years: tuple[int, ...]) -> tuple[dict, list]:
    """Sum monthly completions to annual provincial totals.

    Returns (totals, missing): totals maps (cpro, year) to summed dwellings
    (both regimes); missing lists (cpro, year, month) cells with no value.
    Missing cells are excluded from sums, never filled.
    """
    totals: dict[tuple[str, int], int] = {}
    missing: list[tuple[str, int, int]] = []
    for row in monthly:
        if row["anyo"] not in years or row["estado"] != "Terminadas":
            continue
        if row["viviendas"] is None:
            missing.append((row["cpro"], row["anyo"], row["mes"]))
            continue
        key = (row["cpro"], row["anyo"])
        totals[key] = totals.get(key, 0) + row["viviendas"]
    return totals, missing


def creation(start: dict[str, int], end: dict[str, int]) -> dict[str, int]:
    """Household creation per key: end stock minus start stock (Jan-1)."""
    keys = set(start) & set(end)
    if len(keys) < len(start) or len(keys) < len(end):
        raise ValueError("household stock coverage differs between endpoints")
    return {key: end[key] - start[key] for key in keys}


def combine_ceuta_melilla(
    values: dict[str, int], names: dict[str, str]
) -> tuple[dict[str, int], dict[str, str]]:
    """Aggregate CPRO 51/52 into the mart '51+52' key."""
    combined = {key: value for key, value in values.items() if key not in ("51", "52")}
    combined_names = {key: name for key, name in names.items() if key not in ("51", "52")}
    if "51" in values and "52" in values:
        combined["51+52"] = values["51"] + values["52"]
        combined_names["51+52"] = "Ceuta y Melilla"
    elif "51" in values or "52" in values:
        raise ValueError("partial Ceuta/Melilla coverage")
    return combined, combined_names


def deficits(
    creation_map: dict[str, int],
    completions: dict[str, int],
    tourist_flow: dict[str, int | None],
) -> dict[str, dict]:
    """Arithmetic gaps per province key. Tourist flow None propagates to v3p."""
    rows = {}
    for key, created in creation_map.items():
        finished = completions.get(key, 0)
        v2 = created - finished
        flow = tourist_flow.get(key)
        rows[key] = {
            "creation": created,
            "terminadas": finished,
            "deficit_v2": v2,
            "tourist_flow": flow,
            "deficit_v3p": None if flow is None else v2 - flow,
            "deficit_per_creation": None if created <= 0 else round(v2 / created, 4),
        }
    return rows


def national(rows: dict[str, dict]) -> dict:
    """National rollup with concentration diagnostics."""
    positive = sorted(
        ((key, row["deficit_v2"]) for key, row in rows.items() if row["deficit_v2"] > 0),
        key=lambda kv: -kv[1],
    )
    total_v2 = sum(row["deficit_v2"] for row in rows.values())
    total_v3p = (
        None
        if any(row["deficit_v3p"] is None for row in rows.values())
        else sum(row["deficit_v3p"] for row in rows.values())
    )
    top5 = sum(value for _, value in positive[:5])
    return {
        "deficit_v2": total_v2,
        "deficit_v3p": total_v3p,
        "top5_deficit": top5,
        "top5_share": round(top5 / sum(value for _, value in positive), 4) if positive else None,
        "top5_keys": [key for key, _ in positive[:5]],
        "negative_keys": sorted(key for key, row in rows.items() if row["deficit_v2"] < 0),
    }


def load_inputs():
    monthly = pq.read_table(TERMINADAS).to_pylist()
    provinces: dict[str, str] = {}
    for row in monthly:
        provinces.setdefault(row["cpro"], row["provincia"])
    con = duckdb.connect(str(MARTS_DB), read_only=True)
    try:
        mart = con.execute(
            "select cpro, provincia, anyo, hogares, viv_turisticas from mart_provincia_anual"
        ).fetchall()
    finally:
        con.close()
    stocks: dict[int, dict[str, int]] = {}
    names: dict[str, str] = {}
    tourist: dict[int, dict[str, int | None]] = {}
    for cpro, provincia, anyo, hogares, tur in mart:
        names[cpro] = provincia
        if hogares is not None:
            stocks.setdefault(anyo, {})[cpro] = hogares
        tourist.setdefault(anyo, {})[cpro] = tur
    ecp = [r for r in pq.read_table(ECP_HOG).to_pylist() if r["tamano"] == "Total"]
    ecp_names = {r["territorio"] for r in ecp if r["anyo"] == 2026}
    mart_names = {names[c] for c in names if c != "51+52"} | {"Ceuta", "Melilla"}
    # Same ECP series feeds both: province name sets must agree exactly.
    if {n for n in ecp_names if n != "Total Nacional"} != mart_names:
        raise ValueError("ECP/mart province name sets differ")
    ecp26 = {r["territorio"]: r["hogares"] for r in ecp if r["anyo"] == 2026}
    return monthly, stocks, names, tourist, ecp26


def main():
    monthly, stocks, names, tourist, ecp26 = load_inputs()
    for year in (2021, 2025):
        if year not in stocks or len(stocks[year]) != 51:
            raise ValueError(f"incomplete mart household stock for {year}")
    stock26: dict[str, int] = {}
    for cpro, name in names.items():
        if cpro == "51+52":
            pair = [ecp26.get(n) for n in ("Ceuta", "Melilla")]
            if any(v is None for v in pair):
                raise ValueError("missing ECP 2026 Ceuta/Melilla")
            stock26[cpro] = pair[0] + pair[1]
        elif name in ecp26:
            stock26[cpro] = ecp26[name]
        else:
            raise ValueError(f"missing ECP 2026 for {name}")
    windows = {}
    for label, spec in WINDOWS.items():
        totals, missing = annual_flows(monthly, spec["flow_years"])
        yearly = {
            cpro: sum(totals.get((cpro, y), 0) for y in spec["flow_years"])
            for cpro in provinces(monthly)
        }
        prov_totals = combine_ceuta_melilla(yearly, {})[0]
        pinned_2026 = spec["stock_end"] == 2026
        end = stock26 if pinned_2026 else stocks[spec["stock_end"]]
        created = creation(stocks[2021], end)
        created, _ = combine_ceuta_melilla(created, names)
        t_first, t_last = spec["flow_years"][0], spec["flow_years"][-1]
        flows = {
            key: (
                None
                if tourist.get(t_last, {}).get(key) is None
                or tourist.get(t_first - 1, {}).get(key) is None
                else tourist[t_last][key] - tourist[t_first - 1][key]
            )
            for key in created
        }
        rows = deficits(created, prov_totals, flows)
        nat = national(rows)
        bench_key = f"v2_{label}"
        windows[label] = {
            "provinces": {names[key]: {"cpro": key, **row} for key, row in sorted(rows.items())},
            "national": nat,
            "missing_months": [[c, y, m] for c, y, m in missing],
            "benchmark": {
                "caixabank_v2": BENCHMARKS[bench_key],
                "reproduced_v2": nat["deficit_v2"],
                "delta": nat["deficit_v2"] - BENCHMARKS[bench_key],
            },
        }
    results = {
        "windows": windows,
        "benchmarks": BENCHMARKS,
        "notes": (
            "Arithmetic gaps only: household creation minus finished dwellings "
            "(v2), minus tourist-stock net flow (v3p, partial: foreign-buyer "
            "adjustment unavailable). Not missing-home counts, not causal."
        ),
        "_meta": ols.model_meta(
            str(Path(__file__).resolve()),
            [
                str(MARTS_DB.relative_to(ROOT)),
                str(TERMINADAS.relative_to(ROOT)),
                str(ECP_HOG.relative_to(ROOT)),
            ],
        ),
    }
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    for label, window in windows.items():
        print(
            f"wrote {ARTIFACT.relative_to(ROOT)} [{label}]: "
            f"v2={window['national']['deficit_v2']} "
            f"v3p={window['national']['deficit_v3p']} "
            f"benchmark_delta={window['benchmark']['delta']}"
        )


def provinces(monthly):
    return sorted({row["cpro"] for row in monthly})


if __name__ == "__main__":
    main()
