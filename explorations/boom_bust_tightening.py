"""Exploration 01: boom-bust (2007-2013) vs tightening (2021-2025).

Reads marts.duckdb (read-only), prints snapshot tables and writes
artifacts/exploration_01.json. All numbers are descriptive co-movements;
no causal claims. See docs/explorations/boom_bust_vs_tightening.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402
from spanish_housing.data_paths import PROCESSED  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)


def rows(sql: str) -> list[dict]:
    return [dict(zip([d[0] for d in con.description], r, strict=True))
            for r in con.execute(sql).fetchall()]


nacional = rows(
    "SELECT anyo, viviendas_total, poblacion, viv_por_1000_hab, hogares, "
    "viv_por_hogar, eur_m2_libre, ipv_general FROM mart_ccaa_anual "
    "WHERE ccaa = 'Nacional' AND anyo IN (2007, 2013, 2019, 2021, 2025) ORDER BY anyo"
)

# Absorption 2021-2025 by CCAA: new dwellings vs new households (both observed).
absorption = rows(
    """WITH a AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2021),
            b AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2025)
     SELECT b.ccaa, b.viviendas_total - a.viviendas_total AS d_viv,
            b.hogares - a.hogares AS d_hog,
            b.eur_m2_libre - a.eur_m2_libre AS d_eur_m2,
            b.ipv_general - a.ipv_general AS d_ipv
     FROM a JOIN b ON a.ccaa = b.ccaa
     WHERE b.ccaa != 'Nacional' AND a.hogares IS NOT NULL AND b.hogares IS NOT NULL
     ORDER BY b.ccaa"""
)
for r in absorption:
    r["viv_per_new_hogar"] = round(r["d_viv"] / r["d_hog"], 2) if r["d_hog"] else None

# Bust 2007-2013: price fall vs stock-per-capita rise, by CCAA.
bust = rows(
    """WITH a AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2007),
            b AS (SELECT * FROM mart_ccaa_anual WHERE anyo = 2013)
     SELECT b.ccaa,
            b.viviendas_total - a.viviendas_total AS d_viv,
            ROUND((b.ipv_general - a.ipv_general) / a.ipv_general * 100, 1) AS ipv_pct,
            ROUND((b.eur_m2_libre - a.eur_m2_libre) / a.eur_m2_libre * 100, 1) AS eur_pct,
            ROUND(b.viv_por_1000_hab - a.viv_por_1000_hab, 1) AS d_viv1000
     FROM a JOIN b ON a.ccaa = b.ccaa
     WHERE b.ccaa != 'Nacional' ORDER BY ipv_pct"""
)

out = {"nacional_snapshots": nacional, "absorption_2021_2025": absorption,
       "bust_2007_2013": bust}
(inews := PROCESSED.parent / "artifacts").mkdir(exist_ok=True)
(inews / "exploration_01.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

print("== NACIONAL ==")
for r in nacional:
    print(f"{r['anyo']}: ipv={r['ipv_general']} eur/m2={r['eur_m2_libre']} "
          f"viv/1000={r['viv_por_1000_hab']} viv/hogar={r['viv_por_hogar']}")
print("\n== ABSORPTION 2021-2025 (dwellings built per new household) ==")
for r in sorted(absorption, key=lambda x: (x["viv_per_new_hogar"] is None, x["viv_per_new_hogar"])):
    print(f"{r['ccaa']}: d_viv={r['d_viv']} d_hog={r['d_hog']} "
          f"viv/new_hogar={r['viv_per_new_hogar']} d_eur/m2={r['d_eur_m2']:+.0f}")
print("\n== BUST 2007-2013 (IPV % vs stock-per-capita change) ==")
for r in bust:
    print(f"{r['ccaa']}: ipv {r['ipv_pct']:+.1f}% eur {r['eur_pct']:+.1f}% "
          f"d_viv/1000={r['d_viv1000']:+.1f} (+{r['d_viv']} dwellings)")
