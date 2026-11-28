"""How far the published rent reference can actually discriminate.

SERPAVI is the state rent-reference system (MIVAU tax-deposit exploitation),
i.e. the index the Housing Law (Ley 12/2023) points at when a CCAA declares a
`zona de mercado residencial tensionado`. It publishes, per municipio, a
median / P25 / P75 band rather than a point. This script asks three
descriptive questions about that band and writes
`artifacts/serpavi_reference_band.json`:

1. **Width.** How wide is the published inner band relative to its own median,
   for `vivienda colectiva` and `unifamiliar`, in EUR/m2 and EUR/month?
2. **Source of the width.** Is it estimation noise (shrinks with the published
   contract count) or cross-dwelling heterogeneity (does not)?
3. **Discriminating power.** Do neighbouring municipios' bands separate, and
   how far do observed contractual rents (INCASOL, Catalonia only) sit from
   the published reference?

Read as description of the published statistic, never as a legal assessment.
The P25/P75 are the spread of contract rents *inside* a municipio, so the band
is a statement about within-municipio heterogeneity, not a confidence interval
for the reference and not an uncertainty band around a legal ceiling.

Writes artifacts/serpavi_reference_band.json (git-ignored).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

MARTS = PROCESSED / "marts.duckdb"
CAT_PARQUET = PROCESSED / "catalonia_rent_control.parquet"
YEARS = (2011, 2018, 2024)
SIZE_CLASSES = (
    ("<500", 0, 500),
    ("500-2k", 500, 2_000),
    ("2k-10k", 2_000, 10_000),
    ("10k-50k", 10_000, 50_000),
    (">50k", 50_000, None),
)

con = duckdb.connect(str(MARTS), read_only=True)

con.execute(
    """
    CREATE TEMP VIEW band AS
    SELECT codigo, anyo,
      MAX(CASE WHEN medida='ALQM2_LV_M_VC'   THEN valor END) m2_vc,
      MAX(CASE WHEN medida='ALQM2_LV_25_VC'  THEN valor END) lo_vc,
      MAX(CASE WHEN medida='ALQM2_LV_75_VC'  THEN valor END) hi_vc,
      MAX(CASE WHEN medida='ALQM2_LV_M_VU'   THEN valor END) m2_vu,
      MAX(CASE WHEN medida='ALQM2_LV_25_VU'  THEN valor END) lo_vu,
      MAX(CASE WHEN medida='ALQM2_LV_75_VU'  THEN valor END) hi_vu,
      MAX(CASE WHEN medida='ALQTBID12_M_VC'  THEN valor END) mo_vc,
      MAX(CASE WHEN medida='ALQTBID12_25_VC' THEN valor END) mo_lo_vc,
      MAX(CASE WHEN medida='ALQTBID12_75_VC' THEN valor END) mo_hi_vc,
      MAX(CASE WHEN medida='SLVM2_M_VC'      THEN valor END) sf_vc,
      MAX(CASE WHEN medida='BI_ALVHEPCO_TVC' THEN valor END) n_vc
    FROM serpavi_municipal
    GROUP BY 1, 2
    """
)


def rows(sql: str, params: list | None = None) -> list[tuple]:
    return con.execute(sql, params or []).fetchall()


def pct(values: list[float], p: float) -> float:
    """Nearest-rank percentile of an already-sorted list."""
    if not values:
        raise ValueError("empty percentile input")
    return values[int(p * (len(values) - 1))]


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(a: list[float], b: list[float]) -> float:
    ra, rb = _ranks(a), _ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb, strict=True))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else float("nan")


def width_stats(year: int, lo: str, mid: str, hi: str) -> dict:
    """Percentiles and exceedance shares of (P75-P25)/median."""
    ws = sorted(
        (h - lo_v) / m
        for m, lo_v, h in rows(
            f"SELECT {mid},{lo},{hi} FROM band WHERE anyo=? AND {mid}>0"
            f" AND {lo} IS NOT NULL AND {hi} IS NOT NULL",
            [year],
        )
    )
    n = len(ws)
    return {
        "municipios": n,
        "p10": round(pct(ws, 0.10), 3),
        "p50": round(pct(ws, 0.50), 3),
        "p90": round(pct(ws, 0.90), 3),
        "share_gt_0.20": round(sum(w > 0.20 for w in ws) / n, 3),
        "share_gt_0.30": round(sum(w > 0.30 for w in ws) / n, 3),
        "share_gt_0.50": round(sum(w > 0.50 for w in ws) / n, 3),
    }


# ---------------------------------------------------------------- 1. width
band = {
    f"{kind}_{year}": width_stats(year, lo, mid, hi)
    for year in YEARS
    for kind, lo, mid, hi in (
        ("vc_eur_m2", "lo_vc", "m2_vc", "hi_vc"),
        ("vc_eur_month", "mo_lo_vc", "mo_vc", "mo_hi_vc"),
        ("vu_eur_m2", "lo_vu", "m2_vu", "hi_vu"),
    )
}

# ------------------------------------------------------- 2. where width comes from
width_n = [
    (n, (hi - lo) / m)
    for m, lo, hi, n in rows(
        "SELECT m2_vc, lo_vc, hi_vc, n_vc FROM band WHERE anyo=2024 AND m2_vc>0"
        " AND lo_vc IS NOT NULL AND hi_vc IS NOT NULL AND n_vc>0"
    )
]
width_n.sort(key=lambda t: t[0])
_quintile = len(width_n) // 5
quintiles = []
for i in range(5):
    part = width_n[i * _quintile : (i + 1) * _quintile] if i < 4 else width_n[4 * _quintile :]
    counts = sorted(n for n, _ in part)
    widths = [w for _, w in part]
    quintiles.append(
        {
            "quintile": i + 1,
            "contracts_min": int(counts[0]),
            "contracts_max": int(counts[-1]),
            "contracts_median": int(counts[len(counts) // 2]),
            "mean_relative_iqr": round(sum(widths) / len(widths), 3),
        }
    )
size_diagnostic = {
    "year": 2024,
    "municipios": len(width_n),
    "spearman_contracts_vs_relative_iqr": round(
        spearman([n for n, _ in width_n], [w for _, w in width_n]), 3
    ),
    "quintiles": quintiles,
}

# ------------------------------------------- 3a. do neighbours' bands separate?
size = {
    code: viv
    for code, viv in rows(
        "SELECT codigo, valor FROM censo2021_intensidad WHERE medida='Viviendas totales'"
    )
}


def _class(viv: float | None) -> str:
    if viv is None:
        return "unknown"
    for label, low, high in SIZE_CLASSES:
        if viv >= low and (high is None or viv < high):
            return label
    return "unknown"


bands_2024 = rows(
    "SELECT codigo, lo_vc, hi_vc, mo_lo_vc, mo_hi_vc FROM band WHERE anyo=2024"
    " AND lo_vc IS NOT NULL AND hi_vc IS NOT NULL"
)
by_province: dict[str, list[tuple[float, float, str]]] = {}
for code, lo, hi, _mo_lo, _mo_hi in bands_2024:
    by_province.setdefault(code[:2], []).append((lo, hi, _class(size.get(code))))

overlap = {"all": [0, 0], "by_size": {label: [0, 0] for label, _, _ in SIZE_CLASSES}}
overlap["by_size"]["unknown"] = [0, 0]
overlap["by_size"]["mixed"] = [0, 0]
for _province, items in by_province.items():
    for i in range(len(items)):
        lo_i, hi_i, cls_i = items[i]
        for j in range(i + 1, len(items)):
            lo_j, hi_j, cls_j = items[j]
            key = cls_i if cls_i == cls_j else "mixed"
            overlap["all"][1] += 1
            overlap["by_size"][key][1] += 1
            if lo_i <= hi_j and lo_j <= hi_i:
                overlap["all"][0] += 1
                overlap["by_size"][key][0] += 1

neighbour = {
    "municipios": len(bands_2024),
    "pairs": overlap["all"][1],
    "overlapping_pairs": overlap["all"][0],
    "share_overlapping": round(overlap["all"][0] / overlap["all"][1], 3),
    "by_size": {
        k: {"pairs": v[1], "overlapping": v[0], "share": round(v[0] / v[1], 3)}
        for k, v in overlap["by_size"].items()
        if v[1]
    },
}

# ------------------------------------ 3b. do the three published measures cohere?
coherence = rows(
    "SELECT mo_vc/(m2_vc*sf_vc) FROM band WHERE anyo=2024 AND m2_vc>0"
    " AND sf_vc>0 AND mo_vc IS NOT NULL"
)
coherence = sorted(r[0] for r in coherence)
coherence_stats = {
    "year": 2024,
    "municipios": len(coherence),
    "ratio_eur_month_over_eur_m2_times_surface_p10": round(pct(coherence, 0.10), 3),
    "p50": round(pct(coherence, 0.50), 3),
    "p90": round(pct(coherence, 0.90), 3),
}

# ------------------------------------------- 4. coverage, population-weighted
tot_n, tot_pop = rows("SELECT COUNT(*), SUM(poblacion) FROM muni_all WHERE anyo=2024")[0]
cov_n, cov_pop = rows(
    "SELECT COUNT(*), SUM(poblacion) FROM muni_all WHERE anyo=2024 AND rent_eur_m2 IS NOT NULL"
)[0]
coverage = {
    "year": 2024,
    "municipios": tot_n,
    "with_published_median_vc": cov_n,
    "share_municipios": round(cov_n / tot_n, 3),
    "population": int(tot_pop),
    "population_covered": int(cov_pop),
    "share_population": round(cov_pop / tot_pop, 3),
    "vu_median_municipios": rows("SELECT COUNT(*) FROM band WHERE anyo=2024 AND m2_vu IS NOT NULL")[
        0
    ][0],
}

# ------------------------------- 5. observed contractual rents vs the reference
catalonia = {"status": "not_built"}
if CAT_PARQUET.exists():
    cat_path = str(CAT_PARQUET).replace("'", "''")
    con.execute(
        f"""
        CREATE TEMP VIEW cat_obs AS
        SELECT codi, anyo,
               SUM(contractes) AS n,
               SUM(lloguer_eur * contractes) / SUM(contractes) AS rent
        FROM read_parquet('{cat_path}')
        WHERE lloguer_eur IS NOT NULL AND contractes > 0
        GROUP BY 1, 2
        """
    )

    # Is the level gap a fixed property of the reference, or the standing stock
    # lagging a repricing flow? Three probes, all descriptive.
    def gap_by_year(years: range, codes: list[str] | None) -> dict[str, dict]:
        if codes:
            marks = ",".join("?" * len(codes))
            extra = f" AND o.codi IN ({marks})"
        else:
            extra = ""
        out: dict[str, dict] = {}
        for year in years:
            matched = rows(
                "SELECT o.rent / b.mo_vc FROM cat_obs o"
                " JOIN band b ON b.codigo=o.codi AND b.anyo=o.anyo"
                f" WHERE o.anyo=? AND b.mo_vc>0{extra}",
                [year, *(codes or [])],
            )
            if len(matched) < 30:
                continue
            ratio = sorted(r[0] for r in matched)
            n = len(ratio)
            out[str(year)] = {
                "municipios": n,
                "p25": round(pct(ratio, 0.25), 3),
                "p50": round(pct(ratio, 0.50), 3),
                "p75": round(pct(ratio, 0.75), 3),
            }
        return out

    balanced = [
        r[0]
        for r in rows(
            "SELECT o.codi FROM cat_obs o JOIN band b"
            " ON b.codigo=o.codi AND b.anyo=o.anyo"
            " WHERE o.anyo BETWEEN 2011 AND 2024 AND b.mo_vc>0"
            " GROUP BY 1 HAVING COUNT(*)=14"
        )
    ]

    # Lognormal mean/median implied by the published P25/P75, restricted to the
    # municipios actually matched below: how much of the gap can a
    # mean-versus-median comparison explain on its own?
    z75 = 1.3489795003921634  # 2 * 0.67448975
    mean_median = sorted(
        math.exp((math.log(r[2] / r[1]) / z75) ** 2 / 2)
        for r in rows(
            "SELECT o.codi, b.mo_lo_vc, b.mo_hi_vc FROM cat_obs o"
            " JOIN band b ON b.codigo=o.codi AND b.anyo=o.anyo"
            " WHERE o.anyo=2024 AND b.mo_vc>0 AND b.mo_lo_vc>0 AND b.mo_hi_vc>0"
        )
    )

    # Cross-section: does a wider gap follow municipalities where rents rose faster
    # before the cap? Municipal growth 2019 -> 2023.
    growth = {
        code: r23 / r19
        for code, r19, r23 in rows(
            "SELECT a.codi, a.rent, b.rent FROM cat_obs a JOIN cat_obs b"
            " ON b.codi=a.codi AND a.anyo=2019 AND b.anyo=2023 WHERE a.rent>0"
        )
    }
    cross = [
        (r[1] / r[2], growth[r[0]])
        for r in rows(
            "SELECT o.codi, o.rent, b.mo_vc FROM cat_obs o"
            " JOIN band b ON b.codigo=o.codi AND b.anyo=o.anyo"
            " WHERE o.anyo=2024 AND b.mo_vc>0"
        )
        if r[0] in growth
    ]
    all_years = sorted(
        {r[0] for r in rows("SELECT DISTINCT anyo FROM cat_obs WHERE anyo BETWEEN 2011 AND 2024")}
    )

    catalonia = {
        "status": "built",
        "source": "INCASOL fiances (new habitual contracts), municipal mean EUR/month",
        "reference": "SERPAVI ALQTBID12 median/P25/P75 EUR/month, vivienda colectiva",
        "not_like_for_like": (
            "observed = mean of newly filed contracts; reference = median of the "
            "tax-deposit population. A level gap is expected and is not evidence "
            "of a breach or of a binding cap."
        ),
        "level_gap_all_years": gap_by_year(range(2011, 2025), None),
        "balanced_panel": {
            "municipios_present_every_year": len(balanced),
            "level_gap": gap_by_year(range(2011, 2025), balanced),
        },
        "mean_versus_median_explains": {
            "year": 2024,
            "p50": round(pct(mean_median, 0.50), 3),
            "p10": round(pct(mean_median, 0.10), 3),
            "p90": round(pct(mean_median, 0.90), 3),
        },
        "gap_versus_pre_cap_growth": {
            "municipios": len(cross),
            "spearman": round(spearman([c[0] for c in cross], [c[1] for c in cross]), 3),
        },
        "years_available": all_years,
    }

    # Pinned 2022-2024 readout, with the P75/P25 exceedance shares.
    for year in (2022, 2023, 2024):
        matched = rows(
            "SELECT o.rent, b.mo_vc, b.mo_lo_vc, b.mo_hi_vc FROM cat_obs o"
            " JOIN band b ON b.codigo=o.codi AND b.anyo=o.anyo"
            " WHERE o.anyo=? AND b.mo_vc>0 AND b.mo_lo_vc IS NOT NULL AND b.mo_hi_vc IS NOT NULL",
            [year],
        )
        if not matched:
            continue
        ratio = sorted(r[0] / r[1] for r in matched)
        n = len(matched)
        catalonia.setdefault("readout", {})[str(year)] = {
            "municipios": n,
            "observed_over_reference_p10": round(pct(ratio, 0.10), 3),
            "p50": round(pct(ratio, 0.50), 3),
            "p90": round(pct(ratio, 0.90), 3),
            "share_above_reference_p75": round(sum(1 for r in matched if r[0] > r[3]) / n, 3),
            "share_below_reference_p25": round(sum(1 for r in matched if r[0] < r[2]) / n, 3),
        }

out = {
    "meta": {
        "source": "SERPAVI (MIVAU) via marts.duckdb serpavi_municipal",
        "band_definition": "(P75 - P25) / median, within-municipio contract spread",
        "years": list(YEARS),
        "catalonia_panel": "data/processed/catalonia_rent_control.parquet",
    },
    "coverage": coverage,
    "band_width": band,
    "width_is_not_sampling_noise": size_diagnostic,
    "neighbour_overlap": neighbour,
    "internal_coherence": coherence_stats,
    "observed_vs_reference_catalonia": catalonia,
}

(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "serpavi_reference_band.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)

print(
    f"coverage 2024: {cov_n}/{tot_n} municipios = {cov_n / tot_n:.1%}"
    f" | population {cov_pop / 1e6:.2f}M/{tot_pop / 1e6:.2f}M = {cov_pop / tot_pop:.1%}"
)
for key, v in band.items():
    print(
        f"band {key}: n={v['municipios']:5d} p50={v['p50']:.3f} p90={v['p90']:.3f}"
        f" >0.30={v['share_gt_0.30']:.1%}"
    )
print(
    f"width vs contracts: spearman={size_diagnostic['spearman_contracts_vs_relative_iqr']:+.3f}"
    f" quintile means={[q['mean_relative_iqr'] for q in quintiles]}"
)
print(
    f"neighbours: {neighbour['overlapping_pairs']}/{neighbour['pairs']} pairs overlap"
    f" = {neighbour['share_overlapping']:.1%}"
)
print(f"internal coherence EUR/month vs EUR/m2*surface: p50={coherence_stats['p50']}")
if catalonia["status"] == "built":
    for year, v in catalonia.get("readout", {}).items():
        print(
            f"Catalonia {year}: n={v['municipios']:3d} obs/ref p50={v['p50']:.3f}"
            f" above P75={v['share_above_reference_p75']:.1%}"
            f" below P25={v['share_below_reference_p25']:.1%}"
        )
    bp = catalonia["balanced_panel"]
    print(f"balanced panel: {bp['municipios_present_every_year']} municipios, gap path")
    for year in ("2013", "2018", "2024"):
        v = bp["level_gap"].get(year)
        if v:
            print(f"  {year}: n={v['municipios']:3d} p25={v['p25']:.3f} p50={v['p50']:.3f}")
    mm = catalonia["mean_versus_median_explains"]
    print(f"mean/median (lognormal) explains p50={mm['p50']:.3f}")
    gv = catalonia["gap_versus_pre_cap_growth"]
    print(f"gap vs 2019-23 municipal growth: spearman={gv['spearman']:+.3f} (n={gv['municipios']})")
else:
    print("Catalonia panel not built — run make build for the observed-vs-reference section")
