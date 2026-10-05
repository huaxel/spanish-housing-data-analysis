"""Deep cut: Madrid (magnet) vs Comunitat Valenciana (tightest absorption).

CCAA trajectories 2007-2025 + provincial detail (valor tasado has provinces;
IPV does not). Descriptive. Writes artifacts/deepcut_mad_val.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)


def rows(sql: str, params: list | None = None) -> list[dict]:
    cur = con.execute(sql, params or [])
    return [dict(zip([d[0] for d in cur.description], r, strict=True)) for r in cur.fetchall()]


CCAA = ["Madrid, Comunidad de", "Comunitat Valenciana"]
traj = rows(
    "SELECT ccaa, anyo, poblacion, viv_por_1000_hab, viv_por_hogar, share_20_34,"
    " eur_m2_libre, ipv_general, renta_hogar_neta, afford_90m2_years,"
    " hip_viv_num, hip_ticket_miles FROM mart_ccaa_anual"
    " WHERE ccaa IN ('Madrid, Comunidad de', 'Comunitat Valenciana')"
    " AND anyo IN (2007, 2013, 2019, 2021, 2025) ORDER BY ccaa, anyo"
)
provs = rows(
    "SELECT cpro, provincia, anyo, viviendas_total, poblacion, viv_por_1000_hab,"
    " share_no_principal, eur_m2_libre, vt_source, hip_viv_num"
    " FROM mart_provincia_anual WHERE cpro IN ('28', '03', '12', '46')"
    " AND anyo IN (2007, 2013, 2019, 2021) ORDER BY cpro, anyo"
)
# Second-home share 2021 + absorption 2021-25 already in marts; pull 2025 stock share via raw?
out = {"ccaa_trajectories": traj, "provincial_detail": provs}
(ROOT / "artifacts").mkdir(exist_ok=True)
(ROOT / "artifacts" / "deepcut_mad_val.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)

for c in CCAA:
    print(f"== {c} ==")
    for r in [x for x in traj if x["ccaa"] == c]:
        print(
            f"  {r['anyo']}: pop={r['poblacion']} viv/1k={r['viv_por_1000_hab']} "
            f"viv/h={r['viv_por_hogar']} eur={r['eur_m2_libre']} ipv={r['ipv_general']} "
            f"aff={r['afford_90m2_years']} yshare={r['share_20_34']} hip={r['hip_viv_num']}"
        )
print("== PROVINCES (Alicante03 Castellon12 Valencia46 Madrid28) ==")
for r in provs:
    print(
        f"  {r['provincia']} {r['anyo']}: viv/1k={r['viv_por_1000_hab']} "
        f"nonprinc={r['share_no_principal']} eur={r['eur_m2_libre']} hip={r['hip_viv_num']}"
    )
