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
def _real_change_sql(municipio: str) -> str:
    """Real 2007-25 % change of Madrid municipal €/m² (Madrid CPI deflator)."""
    i25 = "(SELECT ipc FROM ipc_anual WHERE territorio='Madrid, Comunidad de' AND anyo=2025)"
    i07 = "(SELECT ipc FROM ipc_anual WHERE territorio='Madrid, Comunidad de' AND anyo=2007)"
    v25 = "MAX(CASE WHEN m.anyo=2025 THEN m.eur_m2 END)"
    v07 = "MAX(CASE WHEN m.anyo=2007 THEN m.eur_m2 END)"
    return (
        f"SELECT ({v25} - {v07} * {i25} / {i07}) / ({v07} * {i25} / {i07}) * 100 "
        f"FROM valor_municipal_madrid m WHERE m.municipio='{municipio}'"
    )


CLAIMS: list[tuple[str, str, str, float, float]] = [
    (
        "synthesis",
        "IPV Nacional 2007",
        "SELECT ipv_general FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
        83.155,
        0.01,
    ),
    (
        "synthesis",
        "IPV Nacional 2013",
        "SELECT ipv_general FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2013",
        53.509,
        0.01,
    ),
    (
        "synthesis",
        "EUR/m2 Nacional 2007",
        "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
        2056.3,
        0.1,
    ),
    (
        "synthesis",
        "EUR/m2 Nacional 2025",
        "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2025",
        2127.6,
        0.1,
    ),
    (
        "synthesis",
        "viv/1000 Nacional 2007",
        "SELECT viv_por_1000_hab FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
        531.74,
        0.01,
    ),
    (
        "synthesis",
        "viv/hogar Nacional 2021",
        "SELECT viv_por_hogar FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2021",
        1.441,
        0.001,
    ),
    (
        "synthesis",
        "viv/hogar Nacional 2025",
        "SELECT viv_por_hogar FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2025",
        1.388,
        0.001,
    ),
    (
        "synthesis",
        "afford 2007",
        "SELECT afford_90m2_years FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
        6.43,
        0.01,
    ),
    (
        "synthesis",
        "mortgages Nacional 2007",
        "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
        1238890.0,
        1.0,
    ),
    (
        "synthesis",
        "mortgages Nacional 2013",
        "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2013",
        199703.0,
        1.0,
    ),
    (
        "synthesis",
        "mortgages Nacional 2025",
        "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2025",
        498429.0,
        1.0,
    ),
    (
        "deepcut",
        "Madrid viv/1000 2025 (lowest)",
        "SELECT MIN(viv_por_1000_hab) FROM mart_ccaa_anual WHERE anyo=2025 AND ccaa!='Nacional'",
        429.41,
        0.01,
    ),
    (
        "deepcut",
        "Madrid EUR/m2 2025",
        "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Madrid, Comunidad de' AND anyo=2025",
        3685.6,
        0.1,
    ),
    (
        "deepcut",
        "Alicante non-primary 2021",
        "SELECT share_no_principal FROM mart_provincia_anual WHERE cpro='03' AND anyo=2021",
        0.4363,
        0.0001,
    ),
    (
        "young",
        "20-34 Nacional 2007",
        "SELECT pob_20_34 FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
        10546410.0,
        1.0,
    ),
    (
        "young",
        "20-34 Nacional 2019",
        "SELECT pob_20_34 FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2019",
        7653051.0,
        1.0,
    ),
    (
        "afford",
        "Balears afford 2024 (worst)",
        "SELECT MAX(afford_90m2_years) FROM mart_ccaa_anual WHERE anyo=2024 AND ccaa!='Nacional'",
        6.41,
        0.01,
    ),
    (
        "deepcut",
        "Valencia tourist share of non-primary 2025",
        "SELECT share_turistica_no_princ FROM mart_ccaa_anual "
        "WHERE ccaa='Comunitat Valenciana' AND anyo=2025",
        0.0432,
        0.0001,
    ),
    (
        "municipios",
        "Barcelona sale 2024",
        "SELECT sale_eur_m2 FROM muni_bcn WHERE municipio='Barcelona' AND anyo=2024",
        4481.77,
        0.01,
    ),
    (
        "municipios",
        "Barcelona rent burden 2022",
        "SELECT rent_burden FROM muni_bcn WHERE municipio='Barcelona' AND anyo=2022",
        51.22986737621087,
        0.01,
    ),
    (
        "municipios",
        "Santa Coloma tourist 2022 (none)",
        "SELECT tourist FROM muni_bcn WHERE municipio='Santa Coloma de Gramenet' AND anyo=2022",
        5.0,
        1.0,
    ),
    (
        "credit",
        "mortgaged households Nacional 2011",
        "SELECT SUM(hogares) FROM censo2011_tenencia WHERE ccaa = '' AND provincia = '' "
        "AND tamano = 'Total (tamaño del hogar)' "
        "AND tenencia = 'Propia, por compra, con pagos pendientes (hipotecas)'",
        5940928.0,
        1.0,
    ),
    (
        "bust",
        "new-vacant share Nacional 2011 (boom fringe)",
        "SELECT ROUND(SUM(CASE WHEN tipo='vacia' AND vintage='De 2002 a 2011' "
        "THEN viviendas END) * 100.0 / SUM(CASE WHEN tipo='vacia' "
        "AND vintage='Total' THEN viviendas END), 1) "
        "FROM censo2011_vintage WHERE ccaa = '' AND provincia = ''",
        22.3,
        0.1,
    ),
    (
        "bust",
        "new-vacant share Almeria 2011 (boom belt)",
        "SELECT ROUND(SUM(CASE WHEN vintage='De 2002 a 2011' THEN viviendas END) "
        "* 100.0 / SUM(CASE WHEN vintage='Total' THEN viviendas END), 1) "
        "FROM censo2011_vintage WHERE provincia='Almería' AND tipo='vacia'",
        45.3,
        0.1,
    ),
    (
        "municipios",
        "Torrevieja second homes 2011",
        "SELECT ROUND(SUM(CASE WHEN tipo='Vivienda secundaria' THEN viviendas_2011 END) "
        "* 100.0 / SUM(CASE WHEN tipo='Total viviendas' THEN viviendas_2011 END), 1) "
        "FROM censo2011_val WHERE municipio='Torrevieja'",
        51.2,
        0.1,
    ),
    (
        "municipios",
        "Denia vacant share 2011 (highest)",
        "SELECT ROUND(SUM(CASE WHEN tipo='Vivienda vacía' THEN viviendas_2011 END) "
        "* 100.0 / SUM(CASE WHEN tipo='Total viviendas' THEN viviendas_2011 END), 1) "
        "FROM censo2011_val WHERE municipio='Dénia'",
        31.3,
        0.1,
    ),
    (
        "credit",
        "transactions Nacional 2007 (liquidity peak)",
        "SELECT trx_total FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2007",
        775300.0,
        1.0,
    ),
    (
        "credit",
        "nueva share Nacional 2024 (used market recovery)",
        "SELECT share_nueva FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2024",
        0.2098,
        0.0001,
    ),
    (
        "young",
        "solo-household share Nacional 2025",
        "SELECT share_1persona FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2025",
        0.2822,
        0.0001,
    ),
    (
        "municipios",
        "Barcelona vacant dwellings 2011",
        "SELECT viviendas_2011 FROM censo2011_bcn "
        "WHERE municipio='Barcelona' AND tipo='Vivienda vacía'",
        88259.0,
        1.0,
    ),
    (
        "municipios",
        "Madrid capital 2025",
        "SELECT eur_m2 FROM valor_municipal_madrid WHERE codigo='0796' AND anyo=2025",
        4993.3,
        0.1,
    ),
    (
        "municipios",
        "Parla trough 2013",
        "SELECT eur_m2 FROM valor_municipal_madrid WHERE municipio='Parla' AND anyo=2013",
        1083.1,
        0.1,
    ),
    (
        "municipios",
        "Madrid city vacant dwellings 2011",
        "SELECT viviendas_2011 FROM censo2011_mad "
        "WHERE municipio='Madrid' AND tipo='Vivienda vacía'",
        153101.0,
        1.0,
    ),
    (
        "municipios",
        "Parla vacant share 2011 (south = vacancy)",
        "SELECT ROUND(SUM(CASE WHEN tipo='Vivienda vacía' THEN viviendas_2011 END) "
        "* 100.0 / SUM(CASE WHEN tipo='Total viviendas' THEN viviendas_2011 END), 1) "
        "FROM censo2011_mad WHERE municipio='Parla'",
        6.0,
        0.1,
    ),
    (
        "municipios",
        "Rivas population growth 2007-2025",
        "SELECT ROUND((MAX(CASE WHEN anyo=2025 THEN poblacion END) "
        "- MAX(CASE WHEN anyo=2007 THEN poblacion END)) * 100.0 "
        "/ MAX(CASE WHEN anyo=2007 THEN poblacion END), 1) FROM muni_madrid "
        "WHERE municipio='Rivas-Vaciamadrid'",
        73.6,
        0.1,
    ),
    (
        "municipios",
        "Parla price change 2007-2025 (negative)",
        "SELECT ROUND((MAX(CASE WHEN anyo=2025 THEN eur_m2 END) "
        "- MAX(CASE WHEN anyo=2007 THEN eur_m2 END)) * 100.0 "
        "/ MAX(CASE WHEN anyo=2007 THEN eur_m2 END), 1) FROM muni_madrid "
        "WHERE municipio='Parla'",
        -13.1,
        0.1,
    ),
    (
        "municipios",
        "Fuenlabrada 2025 vs 2007 (flat)",
        "SELECT MAX(CASE WHEN anyo=2025 THEN eur_m2 END) "
        "- MAX(CASE WHEN anyo=2007 THEN eur_m2 END) FROM valor_municipal_madrid "
        "WHERE municipio='Fuenlabrada'",
        14.0,
        5.0,
    ),
    (
        "deepcut",
        "Balears tourist dwellings 2025 (falling)",
        "SELECT viv_turisticas FROM mart_ccaa_anual WHERE ccaa='Balears, Illes' AND anyo=2025",
        19398.0,
        1.0,
    ),
    (
        "boom_bust",
        "viv/1000 2007-13 construction effect",
        "SELECT (b.viviendas_total - a.viviendas_total) * 1000.0 / a.poblacion "
        "FROM mart_ccaa_anual a JOIN mart_ccaa_anual b ON a.ccaa = b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2007 AND b.anyo=2013",
        35.1,
        0.1,
    ),
    (
        "boom_bust",
        "viv/1000 2007-13 population effect",
        "SELECT b.viviendas_total * (1.0 / b.poblacion - 1.0 / a.poblacion) * 1000.0 "
        "FROM mart_ccaa_anual a JOIN mart_ccaa_anual b ON a.ccaa = b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2007 AND b.anyo=2013",
        -23.2,
        0.1,
    ),
    (
        "boom_bust",
        "viv/1000 2021-25 construction effect",
        "SELECT (b.viviendas_total - a.viviendas_total) * 1000.0 / a.poblacion "
        "FROM mart_ccaa_anual a JOIN mart_ccaa_anual b ON a.ccaa = b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2021 AND b.anyo=2025",
        8.0,
        0.1,
    ),
    ("madrid", "capital real change 2007-25 (Madrid CPI)", _real_change_sql("Madrid"), -7.5, 0.15),
    (
        "madrid",
        "Fuenlabrada real change 2007-25 (Madrid CPI)",
        _real_change_sql("Fuenlabrada"),
        -28.4,
        0.15,
    ),
    ("madrid", "Getafe real change 2007-25 (Madrid CPI)", _real_change_sql("Getafe"), -30.3, 0.15),
    ("madrid", "Parla real change 2007-25 (Madrid CPI)", _real_change_sql("Parla"), -38.1, 0.15),
    (
        "synthesis",
        "viv/hogar Nacional 2011 (exact census)",
        "SELECT viv_por_hogar FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2011",
        1.396,
        0.005,
    ),
    (
        "synthesis",
        "viv/hogar Nacional 2014 (ECH)",
        "SELECT viv_por_hogar FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2014",
        1.412,
        0.005,
    ),
    (
        "synthesis",
        "viv/hogar Nacional 2020 (ECH)",
        "SELECT viv_por_hogar FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2020",
        1.424,
        0.005,
    ),
    (
        "synthesis",
        "viv/hogar Nacional 2001 (principales proxy)",
        "SELECT SUM(viviendas_total) * 1.0 / SUM(hogares_2001_proxy) "
        "FROM mart_provincia_anual WHERE anyo=2001",
        1.483,
        0.005,
    ),
    (
        "boom_bust",
        "viv/1000 2021-25 population effect",
        "SELECT b.viviendas_total * (1.0 / b.poblacion - 1.0 / a.poblacion) * 1000.0 "
        "FROM mart_ccaa_anual a JOIN mart_ccaa_anual b ON a.ccaa = b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2021 AND b.anyo=2025",
        -20.3,
        0.1,
    ),
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
