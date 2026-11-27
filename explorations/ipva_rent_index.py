"""Cross-check SERPAVI municipal rents against INE's rental price index (IPVA).

SERPAVI (MIVAU tax-deposit exploitation) is the repo's municipal rent *level*
series and the basis of every municipal rent claim. Its municipal trajectory has
never been tested against an independent official instrument: the DIBA
cross-validation covers Barcelona province only.

INE's IPVA (operation 432, table 59060) is a different instrument — a
quality-controlled price index for municipios above 10,000 inhabitants,
2012–2023 — so it can test whether SERPAVI's municipal *changes* are
corroborated. Only changes are comparable: an index and a median of filed
contracts have no common level.

Join: the IPVA publishes names, not codes, so both sides go through
`muni_names.muni_key`, with a bilingual-name fallback that splits "Alicante/Alacant"
and retries each half. Coverage is reported, never silently dropped.

Outputs: artifacts/ipva_rent_index.json (coverage, both windows, rank and level
agreement, quartile breakdown) with an `_meta` freshness key.
Use --check to verify the artifact matches the pinned inputs.
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402
from spanish_housing.muni_names import muni_key  # noqa: E402

IPVA_PARQUET = RAW / "parquet" / "ipva_municipal.parquet"
MARTS = PROCESSED / "marts.duckdb"
ARTIFACT = ROOT / "artifacts/ipva_rent_index.json"
WINDOWS = [(2013, 2023), (2019, 2023)]


def load_ipva() -> dict[str, dict[int, float]]:
    rows = pq.read_table(IPVA_PARQUET).to_pylist()
    index: dict[str, dict[int, float]] = collections.defaultdict(dict)
    for r in rows:
        if r["medida"] != "indice":
            continue
        index[r["municipio"]][r["anyo"]] = r["valor"]
    return index


def load_serpavi() -> dict[str, dict[int, tuple[float, str]]]:
    con = duckdb.connect(str(MARTS), read_only=True)
    try:
        rows = con.execute(
            """
            select cpro, municipio, anyo, rent_eur_m2, poblacion
            from muni_all
            where rent_eur_m2 is not null
            """
        ).fetchall()
    finally:
        con.close()
    out: dict[str, dict[int, tuple[float, str]]] = collections.defaultdict(dict)
    for cpro, municipio, anyo, rent, _pop in rows:
        out[muni_key(municipio)][anyo] = (rent, cpro)
    return out


def match(name: str, serpavi: dict) -> str | None:
    """muni_key, then each half of a bilingual 'Castellón/Castelló' name."""
    key = muni_key(name)
    if key in serpavi:
        return key
    for part in name.split("/"):
        alt = muni_key(part)
        if alt and alt in serpavi:
            return alt
    return None


def spearman(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    rx = {v: i for i, v in enumerate(sorted(xs))}
    ry = {v: i for i, v in enumerate(sorted(ys))}
    rank_x = [rx[v] for v in xs]
    rank_y = [ry[v] for v in ys]
    mean = (n - 1) / 2
    cov = sum((a - mean) * (b - mean) for a, b in zip(rank_x, rank_y, strict=True))
    return cov / (n * statistics.pvariance(range(n)))


def pct(a: float, b: float) -> float:
    return 100.0 * (b / a - 1.0)


def build() -> dict:
    ipva = load_ipva()
    serpavi = load_serpavi()

    matched: dict[str, str] = {}
    unmatched: list[str] = []
    for name in ipva:
        key = match(name, serpavi)
        if key is None:
            unmatched.append(name)
        else:
            matched[name] = key

    windows = []
    for y0, y1 in WINDOWS:
        pairs = []
        for name, key in matched.items():
            years = ipva[name]
            if y0 not in years or y1 not in years:
                continue
            if y0 not in serpavi[key] or y1 not in serpavi[key]:
                continue
            ipva_chg = pct(years[y0], years[y1])
            rent0, cpro = serpavi[key][y0]
            rent1, _ = serpavi[key][y1]
            pairs.append(
                {
                    "municipio": name,
                    "cpro": cpro,
                    "ipva_pct": ipva_chg,
                    "serpavi_pct": pct(rent0, rent1),
                }
            )
        if len(pairs) < 50:
            windows.append({"from": y0, "to": y1, "n": len(pairs), "insufficient": True})
            continue
        ipva_chg = [p["ipva_pct"] for p in pairs]
        serp_chg = [p["serpavi_pct"] for p in pairs]
        gaps = sorted(a - b for a, b in zip(ipva_chg, serp_chg, strict=True))
        n = len(gaps)

        def quantile(values: list[float], p: float, size: int = n) -> float:
            return round(values[min(size - 1, int(p * size))], 2)

        # Does the level gap depend on how expensive the market was at the start?
        ordered = sorted(pairs, key=lambda p: p["serpavi_pct"])
        quartiles = []
        for i in range(4):
            chunk = ordered[i * n // 4 : (i + 1) * n // 4]
            quartiles.append(
                {
                    "quartile": i + 1,
                    "n": len(chunk),
                    "median_serpavi_pct": round(
                        statistics.median(p["serpavi_pct"] for p in chunk), 2
                    ),
                    "median_gap_pp": round(
                        statistics.median(p["ipva_pct"] - p["serpavi_pct"] for p in chunk), 2
                    ),
                }
            )

        windows.append(
            {
                "from": y0,
                "to": y1,
                "n": n,
                "ipva_median_pct": round(statistics.median(ipva_chg), 2),
                "serpavi_median_pct": round(statistics.median(serp_chg), 2),
                "pearson": round(statistics.correlation(ipva_chg, serp_chg), 3),
                "spearman": round(spearman(ipva_chg, serp_chg), 3),
                "gap_pp": {
                    "p10": quantile(gaps, 0.10),
                    "median": round(statistics.median(gaps), 2),
                    "p90": quantile(gaps, 0.90),
                },
                "quartiles_by_serpavi_change": quartiles,
            }
        )

    return {
        "coverage": {
            "ipva_municipios": len(ipva),
            "matched": len(matched),
            "unmatched": len(unmatched),
            "unmatched_examples": sorted(unmatched)[:10],
        },
        "windows": windows,
        "_meta": ols.model_meta(
            __file__,
            [
                str(IPVA_PARQUET.relative_to(ROOT)),
                str(MARTS.relative_to(ROOT)),
            ],
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify artifact matches inputs")
    args = parser.parse_args()

    data = build()
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not ARTIFACT.is_file() or ARTIFACT.read_text() != payload:
            raise SystemExit("Stale artifacts/ipva_rent_index.json; re-run ipva_rent_index.py")
        print("ipva_rent_index: verified")
        return
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(payload)
    cov = data["coverage"]
    print(
        f"IPVA municipios {cov['ipva_municipios']}, "
        f"matched {cov['matched']} ({cov['unmatched']} unmatched)"
    )
    for w in data["windows"]:
        if w.get("insufficient"):
            print(f"  {w['from']}->{w['to']}: insufficient pairs ({w['n']})")
            continue
        span = f"{w['from']}->{w['to']}"
        print(
            f"  {span}: n={w['n']} | IPVA {w['ipva_median_pct']:+.1f}% vs "
            f"SERPAVI {w['serpavi_median_pct']:+.1f}% | r={w['pearson']:+.3f} "
            f"rho={w['spearman']:+.3f} | gap median {w['gap_pp']['median']:+.1f} pp "
            f"({w['gap_pp']['p10']:+.1f} to {w['gap_pp']['p90']:+.1f})"
        )


if __name__ == "__main__":
    main()
