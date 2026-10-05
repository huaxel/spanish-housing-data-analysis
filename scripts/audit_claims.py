"""Audit headline doc claims against the marts. Fails on drift.

Each claim pins (doc, value) to a live query. Run: make audit.
Add a claim whenever a doc states a number someone might quote.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402
from spanish_housing.data_paths import PROCESSED  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)

# (doc, description, sql, expected, tolerance)
CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("synthesis", "IPV Nacional 2007",
     "SELECT ipv_general FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
     83.155, 0.01),
    ("synthesis", "IPV Nacional 2013",
     "SELECT ipv_general FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2013",
     53.509, 0.01),
    ("synthesis", "EUR/m2 Nacional 2007",
     "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
     2056.3, 0.1),
    ("synthesis", "EUR/m2 Nacional 2025",
     "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2025",
     2127.6, 0.1),
    ("synthesis", "viv/1000 Nacional 2007",
     "SELECT viv_por_1000_hab FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
     531.74, 0.01),
    ("synthesis", "viv/hogar Nacional 2021",
     "SELECT viv_por_hogar FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2021",
     1.441, 0.001),
    ("synthesis", "viv/hogar Nacional 2025",
     "SELECT viv_por_hogar FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2025",
     1.388, 0.001),
    ("synthesis", "afford 2007",
     "SELECT afford_90m2_years FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
     6.43, 0.01),
    ("synthesis", "mortgages Nacional 2007",
     "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
     1238890.0, 1.0),
    ("synthesis", "mortgages Nacional 2013",
     "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2013",
     199703.0, 1.0),
    ("synthesis", "mortgages Nacional 2025",
     "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2025",
     498429.0, 1.0),
    ("deepcut", "Madrid viv/1000 2025 (lowest)",
     "SELECT MIN(viv_por_1000_hab) FROM mart_ccaa_anual WHERE anyo=2025 AND ccaa!='Nacional'",
     429.41, 0.01),
    ("deepcut", "Madrid EUR/m2 2025",
     "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Madrid, Comunidad de' AND anyo=2025",
     3685.6, 0.1),
    ("deepcut", "Alicante non-primary 2021",
     "SELECT share_no_principal FROM mart_provincia_anual "
     "WHERE cpro='03' AND anyo=2021",
     0.4363, 0.0001),
    ("young", "20-34 Nacional 2007",
     "SELECT pob_20_34 FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
     10546410.0, 1.0),
    ("young", "20-34 Nacional 2019",
     "SELECT pob_20_34 FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2019",
     7653051.0, 1.0),
    ("afford", "Balears afford 2024 (worst)",
     "SELECT MAX(afford_90m2_years) FROM mart_ccaa_anual WHERE anyo=2024 AND ccaa!='Nacional'",
     6.41, 0.01),
]


def main() -> int:
    failures = 0
    for doc, desc, sql, expected, tol in CLAIMS:
        got = con.execute(sql).fetchone()[0]
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    print(f"{len(CLAIMS) - failures}/{len(CLAIMS)} claims hold")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
