"""Cross-sectional age-rent gradient: cadastre era profiles vs IPRA rent per barrio.

Descriptive exploration only: joins the property-weighted construction-era
profile (same proxy as explorations/cadastre_eras.py) with the IPRA 2022
rent level (EUR/m2/month, contracts 2019-2021) per Sevilla barrio, with
equal barrio weight. No causal claim, no p-values, no model.

Writes artifacts/cadastre_age_rent.json.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

STOCK_DB = PROCESSED / "stock.duckdb"
MARTS_DB = PROCESSED / "marts.duckdb"
ARTIFACT = ROOT / "artifacts" / "cadastre_age_rent.json"
RENT_YEAR = 2022
ERAS = [
    (0, 1950, "Pre-1951"),
    (1951, 1970, "1951-1970"),
    (1971, 1990, "1971-1990"),
    (1991, 2010, "1991-2010"),
    (2011, 9999, "2011+"),
]


def _load_era_module():
    spec = importlib.util.spec_from_file_location(
        "cadastre_eras", ROOT / "explorations" / "cadastre_eras.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def era_profiles(con: duckdb.DuckDBPyConnection) -> dict[str, dict]:
    """Property-weighted era profile per barrio, mirroring cadastre_eras.py."""
    mod = _load_era_module()
    rows = con.execute(
        "SELECT b.barrio_id, br.barrio, br.distrito, "
        "b.year_start, b.dwelling_properties "
        "FROM stock.buildings b JOIN stock.barrios br ON b.barrio_id = br.idg "
        "WHERE b.dwelling_properties is not null and b.dwelling_properties > 0 "
        "ORDER BY br.barrio"
    ).fetchall()
    profiles: dict[str, dict] = {}
    for bid, barrio, distrito, year_start, props in rows:
        p = profiles.setdefault(
            bid,
            {
                "barrio": barrio,
                "distrito": distrito,
                "total_properties": 0,
                "dated_properties": 0,
                "years": [],
                "era_counts": {e[2]: 0 for e in ERAS},
            },
        )
        p["total_properties"] += props
        if year_start is not None:
            p["dated_properties"] += props
            e = mod.era(year_start)
            if e:
                p["era_counts"][e] += props
            p["years"].extend([year_start] * props)
    for p in profiles.values():
        years = sorted(p.pop("years"))
        counts = p.pop("era_counts")
        n = len(years)
        median = years[n // 2] if n % 2 else (years[n // 2 - 1] + years[n // 2]) / 2
        dated = p["dated_properties"]
        p["median_year"] = median
        for _, _, label in ERAS:
            p[label] = counts[label] / dated * 100 if dated else None
    return profiles


def ranks(values: list[float]) -> list[float]:
    """1-based ranks with ties averaged."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    if den == 0:
        raise ValueError("zero variance")
    return num / den


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(ranks(x), ranks(y))


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def main():
    if not STOCK_DB.is_file() or not MARTS_DB.is_file():
        raise SystemExit("Missing stock or marts database; run make build first")
    con = duckdb.connect()
    con.execute(f"attach '{STOCK_DB}' as stock (read_only)")
    con.execute(f"attach '{MARTS_DB}' as housing (read_only)")
    profiles = era_profiles(con)
    rents = {
        r[0]: r[1]
        for r in con.execute(
            "select idg, ipra_eur_m2 from housing.barrios_sevilla "
            "where anyo = ? and ipra_eur_m2 is not null",
            [RENT_YEAR],
        ).fetchall()
    }
    con.close()

    joined = {bid: (p, rents[bid]) for bid, p in profiles.items() if bid in rents}
    no_rent = sorted(f"{bid} {profiles[bid]['barrio']}" for bid in profiles if bid not in rents)
    rent_without_era = sorted(b for b in rents if b not in profiles)

    ids = sorted(joined)
    rent = [joined[b][1] for b in ids]
    median_year = [joined[b][0]["median_year"] for b in ids]
    era_shares = {label: [joined[b][0][label] for b in ids] for _, _, label in ERAS}

    # Median-year terciles: oldest / middle / newest third of barrios
    by_age = sorted(ids, key=lambda b: joined[b][0]["median_year"])
    third = len(by_age) // 3
    tercile_rows = []
    for name, group in (
        ("oldest_third", by_age[:third]),
        ("middle_third", by_age[third : len(by_age) - third]),
        ("newest_third", by_age[len(by_age) - third :]),
    ):
        tercile_rows.append(
            {
                "group": name,
                "n_barrios": len(group),
                "median_year_range": [
                    joined[group[0]][0]["median_year"],
                    joined[group[-1]][0]["median_year"],
                ]
                if group
                else None,
                "mean_rent_eur_m2": round(mean([joined[b][1] for b in group]), 2),
                "median_rent_eur_m2": round(sorted(joined[b][1] for b in group)[len(group) // 2], 2)
                if group
                else None,
            }
        )

    def extreme_barrios(oldest: bool, k: int = 5) -> list[dict]:
        picked = sorted(ids, key=lambda b: joined[b][0]["median_year"], reverse=not oldest)[:k]
        return [
            {
                "barrio": joined[b][0]["barrio"],
                "distrito": joined[b][0]["distrito"],
                "median_year": joined[b][0]["median_year"],
                "ipra_2022_eur_m2": joined[b][1],
            }
            for b in picked
        ]

    results = {
        "method": (
            "Descriptive cross-section, equal barrio weight; no causal claim, "
            "no significance testing"
        ),
        "rent_definition": ("IPRA 2022 EUR/m2/month (contracts 2019-2021), marts.barrios_sevilla"),
        "age_definition": (
            "Property-weighted median earliest construction year of BU records "
            "per barrio; record-date proxy, not individual dwelling age"
        ),
        "coverage": {
            "era_barrios": len(profiles),
            "rent_2022_barrios": len(rents),
            "joined": len(joined),
            "era_barrios_without_rent_2022": no_rent,
            "rent_barrios_without_era_profile": rent_without_era,
        },
        "correlations": {
            "median_year_vs_rent": {
                "pearson": round(pearson(median_year, rent), 6),
                "spearman": round(spearman(median_year, rent), 6),
                "n": len(ids),
            },
            "era_share_vs_rent_spearman": {
                label: round(spearman(era_shares[label], rent), 6) for _, _, label in ERAS
            },
        },
        "median_year_terciles": tercile_rows,
        "oldest_barrios": extreme_barrios(True),
        "newest_barrios": extreme_barrios(False),
        "barrios": {
            bid: {
                "barrio": p["barrio"],
                "distrito": p["distrito"],
                "median_year": p["median_year"],
                "ipra_2022_eur_m2": joined[bid][1],
                **{
                    label: round(p[label], 1) if p[label] is not None else None
                    for _, _, label in ERAS
                },
            }
            for bid, p in ((b, joined[b][0]) for b in ids)
        },
        "_meta": ols.model_meta(
            str(Path(__file__).resolve()),
            [
                str(STOCK_DB.relative_to(ROOT)),
                str(MARTS_DB.relative_to(ROOT)),
            ],
        ),
    }
    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {ARTIFACT.relative_to(ROOT)}: {len(joined)} barrios, "
        f"spearman median_year vs rent {results['correlations']['median_year_vs_rent']['spearman']}"
    )


if __name__ == "__main__":
    main()
