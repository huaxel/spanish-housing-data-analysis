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
def _bcn_real_sql(municipio: str) -> str:
    """Real 2013-24 % change of Barcelona-metro sale €/m² (Cataluña CPI)."""
    i24 = "(SELECT ipc FROM ipc_anual WHERE territorio='Cataluña' AND anyo=2024)"
    i13 = "(SELECT ipc FROM ipc_anual WHERE territorio='Cataluña' AND anyo=2013)"
    v24 = "MAX(CASE WHEN m.anyo=2024 THEN m.sale_eur_m2 END)"
    v13 = "MAX(CASE WHEN m.anyo=2013 THEN m.sale_eur_m2 END)"
    safe = municipio.replace("'", "''")
    return (
        f"SELECT ({v24} - {v13} * {i24} / {i13}) / ({v13} * {i24} / {i13}) * 100 "
        f"FROM muni_bcn m WHERE m.municipio='{safe}'"
    )


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
        "anchor",
        "censo2021 total dwellings (Total x Total)",
        "SELECT SUM(viviendas) FROM censo2021_viviendas WHERE tipo='Total' AND banda='Total'",
        26623708.0,
        1.0,
    ),
    (
        "anchor",
        "censo2021 worst provincial gap vs parque 2021 (%)",
        "WITH c AS (SELECT CASE WHEN cpro IN ('51', '52') THEN '51+52' ELSE cpro END AS cpro, "
        "SUM(viviendas) AS v FROM censo2021_viviendas "
        "WHERE tipo='Total' AND banda='Total' GROUP BY 1) "
        "SELECT MAX(ABS(c.v - m.viviendas_total) * 100.0 / m.viviendas_total) "
        "FROM c JOIN mart_provincia_anual m ON c.cpro = m.cpro WHERE m.anyo = 2021",
        0.77,
        0.03,
    ),
    (
        "barcelona",
        "Barcelona city real sale change 2013-24",
        _bcn_real_sql("Barcelona"),
        33.4,
        0.15,
    ),
    (
        "barcelona",
        "Hospitalet real sale change 2013-24",
        _bcn_real_sql("L'Hospitalet de Llobregat"),
        19.9,
        0.15,
    ),
    (
        "barcelona",
        "Badalona real sale change 2013-24",
        _bcn_real_sql("Badalona"),
        21.0,
        0.15,
    ),
    (
        "barcelona",
        "Sant Adria real sale change 2013-24",
        _bcn_real_sql("Sant Adrià de Besòs"),
        13.7,
        0.15,
    ),
    (
        "barcelona",
        "Santa Coloma real sale change 2013-24",
        _bcn_real_sql("Santa Coloma de Gramenet"),
        5.7,
        0.15,
    ),
    (
        "migration",
        "foreign inflow Nacional 2008 (boom tail)",
        "SELECT flujo FROM migra_anual WHERE provincia='Nacional' "
        "AND nacionalidad='Extranjero' AND anyo=2008",
        567373.0,
        1.0,
    ),
    (
        "migration",
        "foreign inflow Nacional 2013 (trough)",
        "SELECT flujo FROM migra_anual WHERE provincia='Nacional' "
        "AND nacionalidad='Extranjero' AND anyo=2013",
        248347.0,
        1.0,
    ),
    (
        "migration",
        "foreign inflow Nacional 2019 (record)",
        "SELECT flujo FROM migra_anual WHERE provincia='Nacional' "
        "AND nacionalidad='Extranjero' AND anyo=2019",
        666022.0,
        1.0,
    ),
    (
        "migration",
        "Madrid foreign stock 1998 (shares base)",
        "SELECT extranjeros FROM padron_extranjeros WHERE cpro='28' AND anyo=1998",
        115202.0,
        1.0,
    ),
    (
        "synthesis",
        "Madrid non-primary share 2025",
        "SELECT 1.0 - viviendas_principales * 1.0 / viviendas_total "
        "FROM mart_ccaa_anual WHERE ccaa='Madrid, Comunidad de' AND anyo=2025",
        0.116,
        0.003,
    ),
    (
        "migration",
        "Moroccans in Almeria 2008",
        "SELECT personas FROM padron_extranjeros_origen WHERE nacionalidad='Marruecos' "
        "AND cpro='04' AND sexo='Ambos sexos' AND anyo=2008",
        35431.0,
        1.0,
    ),
    (
        "migration",
        "Ecuadorians in Madrid 2008",
        "SELECT personas FROM padron_extranjeros_origen WHERE nacionalidad='Ecuador' "
        "AND cpro='28' AND sexo='Ambos sexos' AND anyo=2008",
        138667.0,
        1.0,
    ),
    (
        "migration",
        "Ecuador net change 2003 (surge peak)",
        "SELECT (SELECT SUM(personas) FROM padron_extranjeros_origen "
        "WHERE nacionalidad='Ecuador' AND sexo='Ambos sexos' AND cpro != '00' AND anyo=2003)"
        " - (SELECT SUM(personas) FROM padron_extranjeros_origen "
        "WHERE nacionalidad='Ecuador' AND sexo='Ambos sexos' AND cpro != '00' AND anyo=2002)",
        130775.0,
        1.0,
    ),
    (
        "migration",
        "Romania net change 2008 (EU accession wave)",
        "SELECT (SELECT SUM(personas) FROM padron_extranjeros_origen "
        "WHERE nacionalidad='Rumanía' AND sexo='Ambos sexos' AND cpro != '00' AND anyo=2008)"
        " - (SELECT SUM(personas) FROM padron_extranjeros_origen "
        "WHERE nacionalidad='Rumanía' AND sexo='Ambos sexos' AND cpro != '00' AND anyo=2007)",
        204787.0,
        1.0,
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


# Model-output claims (doc <-> committed explorations/iv_results.json).
# Mart SQL cannot recompute 2SLS; instead the doc numbers must match the
# committed estimator output, and re-running explorations/iv_migration.py
# (deterministic) must reproduce that file. Guards transcription drift.
IV_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("synthesis", "IV 2SLS tau (base)", "base.tsls.tau", 0.67, 0.005),
    ("synthesis", "IV AR lower bound (base)", "base.ar_set.0", 0.35, 0.005),
    ("synthesis", "IV AR upper bound (base)", "base.ar_set.1", 1.0, 0.005),
    ("synthesis", "IV first-stage F (base)", "base.first_stage_F", 47.67, 0.05),
    ("synthesis", "IV first-stage F (bust)", "bust_2002_2013.first_stage_F", 88.4, 0.05),
    ("synthesis", "IV first-stage F (recovery)", "recovery_2014_2021.first_stage_F", 0.13, 0.05),
    ("synthesis", "IV 2SLS tau (+province trends)", "province_trends.tsls.tau", 0.762, 0.005),
    (
        "synthesis",
        "IV first-stage F (+province trends)",
        "province_trends.first_stage_F",
        56.28,
        0.05,
    ),
    (
        "synthesis",
        "IV AR lower bound (+province trends)",
        "province_trends.ar_set.0",
        0.4,
        0.005,
    ),
    (
        "synthesis",
        "IV AR upper bound (+province trends)",
        "province_trends.ar_set.1",
        1.15,
        0.005,
    ),
    (
        "synthesis",
        "IV 2SLS tau (drop Madrid/Barcelona)",
        "drop_madrid_barcelona.tsls.tau",
        0.653,
        0.005,
    ),
    (
        "synthesis",
        "IV first-stage F (drop Madrid/Barcelona)",
        "drop_madrid_barcelona.first_stage_F",
        35.45,
        0.05,
    ),
    (
        "synthesis",
        "IV AR lower bound (drop Madrid/Barcelona)",
        "drop_madrid_barcelona.ar_set.0",
        0.25,
        0.005,
    ),
    (
        "synthesis",
        "IV AR upper bound (drop Madrid/Barcelona)",
        "drop_madrid_barcelona.ar_set.1",
        1.05,
        0.005,
    ),
    ("synthesis", "IV 2SLS tau (bust 2002-13)", "bust_2002_2013.tsls.tau", 0.841, 0.005),
    ("synthesis", "IV AR lower bound (bust)", "bust_2002_2013.ar_set.0", 0.45, 0.005),
    ("synthesis", "IV AR upper bound (bust)", "bust_2002_2013.ar_set.1", 1.4, 0.005),
]


# (doc, description, provincia, field, expected, tolerance)
# Probe series: terrain-derived, so re-running the probe is the only way to
# reproduce it. Pinned here so a doc quote cannot drift from the JSON.
PROBE_CLAIMS = [
    (
        "saiz_gis_probe",
        "Valladolid undevelopable",
        "Valladolid",
        "undevelopable_share",
        0.07,
        0.005,
    ),
    ("saiz_gis_probe", "Salamanca undevelopable", "Salamanca", "undevelopable_share", 0.14, 0.005),
    ("saiz_gis_probe", "Segovia undevelopable", "Segovia", "undevelopable_share", 0.165, 0.005),
    ("saiz_gis_probe", "Toledo undevelopable", "Toledo", "undevelopable_share", 0.165, 0.005),
    ("saiz_gis_probe", "Zamora undevelopable", "Zamora", "undevelopable_share", 0.182, 0.005),
    ("saiz_gis_probe", "Gipuzkoa undevelopable", "Gipuzkoa", "undevelopable_share", 0.925, 0.005),
    ("saiz_gis_probe", "Asturias undevelopable", "Asturias", "undevelopable_share", 0.883, 0.005),
    ("saiz_gis_probe", "Bizkaia undevelopable", "Bizkaia", "undevelopable_share", 0.839, 0.005),
    ("saiz_gis_probe", "Cantabria undevelopable", "Cantabria", "undevelopable_share", 0.798, 0.005),
    ("saiz_gis_probe", "Ceuta undevelopable", "Ceuta", "undevelopable_share", 0.789, 0.005),
    ("saiz_gis_probe", "Malaga undevelopable", "Málaga", "undevelopable_share", 0.66, 0.005),
    ("saiz_gis_probe", "Barcelona undevelopable", "Barcelona", "undevelopable_share", 0.643, 0.005),
    ("saiz_gis_probe", "Madrid inland water share", "Madrid", "water_share", 0.008, 0.005),
    (
        "saiz_gis_probe",
        "Alicante inland water share",
        "Alicante/Alacant",
        "water_share",
        0.014,
        0.005,
    ),
    ("saiz_gis_probe", "Ceuta inland water share", "Ceuta", "water_share", 0.06, 0.005),
    ("saiz_gis_probe", "Madrid land area km2", "Madrid", "land_km2", 7984.33, 1.0),
    ("saiz_gis_probe", "Asturias land area km2", "Asturias", "land_km2", 10535.44, 1.0),
    ("saiz_gis_probe", "Gipuzkoa land area km2", "Gipuzkoa", "land_km2", 1967.57, 1.0),
    ("saiz_gis_probe", "Valladolid land area km2", "Valladolid", "land_km2", 8062.34, 1.0),
]

# (doc, description, tile key, resolution, expected, tolerance)
SENSITIVITY_CLAIMS = [
    ("saiz_gis_probe", "Extremadura steep 30m", "extremadura_rolling", "30m", 0.29, 0.005),
    ("saiz_gis_probe", "Extremadura steep 90m", "extremadura_rolling", "90m", 0.248, 0.005),
    ("saiz_gis_probe", "Extremadura steep 180m", "extremadura_rolling", "180m", 0.192, 0.005),
    ("saiz_gis_probe", "Pyrenees steep 30m", "pyrenees_steep", "30m", 0.88, 0.005),
    ("saiz_gis_probe", "Pyrenees steep 90m", "pyrenees_steep", "90m", 0.876, 0.005),
    ("saiz_gis_probe", "Pyrenees steep 180m", "pyrenees_steep", "180m", 0.853, 0.005),
]

# (doc, description, json path, expected, tolerance) against
# explorations/panel_saiz_municipal_results.json.
PANEL_SAIZ_MUNI_CLAIMS = [
    ("panel_saiz_muni", "muni count", "n_municipios", 310, 0),
    ("panel_saiz_muni", "premise starts coef /0.1", "premise_starts.coef_per_0p1", -0.023, 0.005),
    ("panel_saiz_muni", "premise starts se /0.1", "premise_starts.se_per_0p1", 0.026, 0.005),
    (
        "panel_saiz_muni",
        "premise completions coef /0.1",
        "premise_completions.coef_per_0p1",
        -0.008,
        0.005,
    ),
    (
        "panel_saiz_muni",
        "premise starts+density coef /0.1",
        "premise_starts_density.coef_per_0p1",
        -0.028,
        0.005,
    ),
    ("panel_saiz_muni", "exclusion price coef /0.1", "exclusion_price.coef_per_0p1", -0.009, 0.005),
    (
        "panel_saiz_muni",
        "exclusion price+density coef /0.1",
        "exclusion_price_density.coef_per_0p1",
        0.05,
        0.005,
    ),
    ("panel_saiz_muni", "exclusion price n", "exclusion_price.n", 1414, 0),
    ("panel_saiz_muni", "exclusion price clusters", "exclusion_price.clusters", 130, 0),
    ("panel_saiz_muni", "mean starts per 1000", "mean_starts_pc", 1.5219, 0.005),
    ("panel_saiz_muni", "mean price growth", "mean_d_price", 4.2094, 0.005),
]

# (doc, description, json path, expected, tolerance) against
# explorations/panel_saiz_results.json -- terrain x migration diagnostics.
PANEL_SAIZ_CLAIMS = [
    (
        "panel_saiz",
        "premise build coef /0.1",
        "premise_build_on_constraint.coef_per_0p1",
        -0.054,
        0.005,
    ),
    (
        "panel_saiz",
        "premise build se /0.1",
        "premise_build_on_constraint.se_per_0p1",
        0.165,
        0.005,
    ),
    (
        "panel_saiz",
        "exclusion d_eur coef /0.1",
        "exclusion_d_eur_on_constraint.coef_per_0p1",
        -0.052,
        0.005,
    ),
    (
        "panel_saiz",
        "exclusion d_eur se /0.1",
        "exclusion_d_eur_on_constraint.se_per_0p1",
        0.075,
        0.005,
    ),
    ("panel_saiz", "median constraint", "median_constraint", 0.445, 0.005),
    ("panel_saiz", "low-constraint 2SLS tau", "low_constraint.tsls.tau", 0.636, 0.005),
    ("panel_saiz", "low-constraint first-stage F", "low_constraint.first_stage_F", 40.28, 0.05),
    ("panel_saiz", "low-constraint AR upper", "low_constraint.ar_set.1", 1.3, 0.005),
    ("panel_saiz", "high-constraint 2SLS tau", "high_constraint.tsls.tau", 0.74, 0.005),
    (
        "panel_saiz",
        "high-constraint first-stage F",
        "high_constraint.first_stage_F",
        22.82,
        0.05,
    ),
    ("panel_saiz", "high-constraint AR upper", "high_constraint.ar_set.1", 1.3, 0.005),
    ("panel_saiz", "low-constraint OLS tau", "low_constraint.ols.tau", 0.066, 0.005),
    ("panel_saiz", "high-constraint OLS tau", "high_constraint.ols.tau", 0.246, 0.005),
    ("panel_saiz", "interaction coefficient", "interaction_ols.interaction", 0.288, 0.005),
    (
        "panel_saiz",
        "interaction wild p",
        "interaction_ols.wild_p_interaction",
        0.3313,
        0.005,
    ),
]


def _json_path(data: dict, path: str):
    for part in path.split("."):
        data = data[int(part) if part.isdigit() else part]
    return data


def main() -> int:
    failures = 0
    for doc, desc, sql, expected, tol in CLAIMS:
        got = con.execute(sql).fetchone()[0]
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    import json

    iv = json.loads(
        (Path(__file__).resolve().parents[1] / "explorations" / "iv_results.json").read_text()
    )
    for doc, desc, path, expected, tol in IV_CLAIMS:
        got = _json_path(iv, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok

    expl = Path(__file__).resolve().parents[1] / "explorations"
    probe = json.loads((expl / "saiz_probe_results.json").read_text())
    by_prov = {r["provincia"]: r for r in probe}
    for doc, desc, prov, field, expected, tol in PROBE_CLAIMS:
        got = by_prov.get(prov, {}).get(field)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok

    sens = json.loads((expl / "saiz_resolution_sensitivity.json").read_text())
    for doc, desc, tile, res, expected, tol in SENSITIVITY_CLAIMS:
        got = sens.get(tile, {}).get(res)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok

    # Spain's land area (505,990 km2) is an EXTERNAL anchor the probe did not
    # choose. Summing to ~503k is what catches a cos(lat) area regression;
    # the shares alone would stay valid while the areas silently broke.
    got_area = round(sum(r["land_km2"] for r in probe), 1)
    ok = abs(got_area - 503189.7) <= 2.0
    print(f"[{'OK' if ok else 'FAIL'}] saiz_gis_probe: total land km2 = {got_area} (doc: 503189.7)")
    failures += not ok

    total = len(CLAIMS) + len(IV_CLAIMS) + len(PROBE_CLAIMS) + len(SENSITIVITY_CLAIMS) + 1
    saiz_panel = json.loads((expl / "panel_saiz_results.json").read_text())
    for doc, desc, path, expected, tol in PANEL_SAIZ_CLAIMS:
        got = _json_path(saiz_panel, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(PANEL_SAIZ_CLAIMS)
    muni = json.loads((expl / "panel_saiz_municipal_results.json").read_text())
    for doc, desc, path, expected, tol in PANEL_SAIZ_MUNI_CLAIMS:
        got = _json_path(muni, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(PANEL_SAIZ_MUNI_CLAIMS)
    muniterr = json.loads((expl / "saiz_municipal_bcn.json").read_text())
    muni_tot_land = round(sum(x["land_km2"] for x in muniterr), 1)
    muni_tot_lau = round(sum(x["lau_km2"] for x in muniterr), 1)
    muni_med = sorted(x["area_err_pct"] for x in muniterr)[len(muniterr) // 2]
    for desc, got, expected, tol in (
        ("municipal LAU units", len(muniterr), 311, 0),
        ("municipal total computed km2", muni_tot_land, 7685.2, 0.5),
        ("municipal total LAU km2", muni_tot_lau, 7729.5, 0.5),
        ("municipal median area err pct", muni_med, 0.99, 0.02),
    ):
        ok = abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] saiz_muni_probe: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 4
    madrid = json.loads((expl / "panel_saiz_madrid_results.json").read_text())
    for desc, got, expected, tol in (
        ("Madrid municipios joined", madrid["n_municipios"], 28, 0),
        ("Madrid priced-constraint max", madrid["constraint_max"], 0.245, 0.005),
        ("Madrid province constraint max", madrid["province_constraint_max"], 0.984, 0.005),
        ("Madrid price-growth coef /0.1", madrid["price_growth"]["coef_per_0p1"], -0.134, 0.005),
        (
            "Madrid log-levels coef /0.1",
            madrid["log_price_levels"]["coef_per_0p1"],
            -0.0809,
            0.005,
        ),
        (
            "Madrid log-levels+density coef /0.1",
            madrid["log_price_levels_density"]["coef_per_0p1"],
            -0.1008,
            0.005,
        ),
    ):
        ok = abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] panel_saiz_madrid: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 6
    ratio = json.loads(
        (Path(__file__).resolve().parents[1] / "artifacts" / "ratio_ccaa.json").read_text()
    )
    for desc, path, expected, tol in (
        ("national r01", "national.r01", 511.6, 0.1),
        ("national r07", "national.r07", 531.7, 0.1),
        ("national r25", "national.r25", 551.6, 0.1),
        ("stock growth 01-25", "national.stock_growth_01_25_pct", 28.8, 0.1),
        ("pop growth 01-25", "national.pop_growth_01_25_pct", 19.5, 0.1),
        ("Madrid ratio change", "ccaa.Madrid, Comunidad de.d_07_25", -29.7, 0.1),
        ("Cataluña ratio change", "ccaa.Cataluña.d_07_25", -27.6, 0.1),
        ("Asturias ratio change", "ccaa.Asturias, Principado de.d_07_25", 130.3, 0.1),
        ("CyL ratio change", "ccaa.Castilla y León.d_07_25", 122.0, 0.1),
        ("Pearson ratio-vs-price", "corr_ratio_vs_real_price.pearson", -0.385, 0.005),
        ("Spearman ratio-vs-price", "corr_ratio_vs_real_price.spearman", -0.407, 0.005),
        ("n", "corr_ratio_vs_real_price.n", 17, 0),
        (
            "median real price scarcity",
            "groups.median_real_price.scarcity",
            -8.6,
            0.1,
        ),
        ("median real price overstock", "groups.median_real_price.overstock", -23.6, 0.1),
        ("vacancy pearson", "vacancy_2021.corr_ratio_vs_vacancy.pearson", 0.523, 0.005),
        ("vacancy spearman", "vacancy_2021.corr_ratio_vs_vacancy.spearman", 0.475, 0.005),
        ("vacancy n", "vacancy_2021.corr_ratio_vs_vacancy.n", 17, 0),
        ("vacancy galicia pct", "vacancy_2021.by_ccaa_pct.Galicia", 28.81, 0.05),
        ("vacancy madrid pct", "vacancy_2021.by_ccaa_pct.Madrid, Comunidad de", 6.34, 0.05),
        ("vacancy CyL pct", "vacancy_2021.by_ccaa_pct.Castilla y León", 19.38, 0.05),
    ):
        got = _json_path(ratio, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] ratio_ccaa: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 21
    serp = json.loads(
        (Path(__file__).resolve().parents[1] / "artifacts" / "serpavi_analysis.json").read_text()
    )
    for desc, path, expected, tol in (
        ("diba-serpavi pearson", "rent_cross_diba_2023.pearson", 0.825, 0.005),
        ("diba-serpavi n", "rent_cross_diba_2023.n", 202, 0),
        ("bcn yield pct", "gross_yield_bcn_2023.barcelona.yield_pct", 3.61, 0.02),
        ("yield median", "gross_yield_bcn_2023.stats.median", 4.58, 0.02),
        ("rent-vac pearson", "rent_vs_vacancy_2023.pearson", -0.429, 0.005),
        ("rent-vac spearman", "rent_vs_vacancy_2023.spearman", -0.024, 0.005),
        ("rent-vac n", "rent_vs_vacancy_2023.n", 2237, 0),
        ("serpavi munis 2024 rent", "coverage.serpavi_munis_2024_rent", 2555, 0),
    ):
        got = _json_path(serp, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] serpavi: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 8
    tr = json.loads(
        (Path(__file__).resolve().parents[1] / "artifacts" / "tourist_rents.json").read_text()
    )
    for desc, path, expected, tol in (
        (
            "bcn tour-rent level pearson",
            "bcn_municipal.corr_tour_vs_rent_level.pearson",
            0.087,
            0.005,
        ),
        (
            "bcn tour-rent level spearman",
            "bcn_municipal.corr_tour_vs_rent_level.spearman",
            0.037,
            0.005,
        ),
        (
            "bcn tour-rent growth pearson",
            "bcn_municipal.corr_tour_vs_rent_growth.pearson",
            0.020,
            0.005,
        ),
        (
            "bcn tour-rent growth spearman",
            "bcn_municipal.corr_tour_vs_rent_growth.spearman",
            -0.024,
            0.005,
        ),
        (
            "prov tour-rent level pearson",
            "provincial.corr_tour_vs_rent_level.pearson",
            0.619,
            0.005,
        ),
        (
            "prov tour-rent level spearman",
            "provincial.corr_tour_vs_rent_level.spearman",
            0.016,
            0.005,
        ),
        (
            "prov tour-rent growth pearson",
            "provincial.corr_tour_vs_rent_growth.pearson",
            0.225,
            0.005,
        ),
        (
            "prov tour-rent growth spearman",
            "provincial.corr_tour_vs_rent_growth.spearman",
            0.041,
            0.005,
        ),
        ("tourist-rents n prov", "provincial.n", 45, 0),
        ("Tenerife rent growth", "provincial.top_tourist", 27.95, 0.01),
    ):
        if desc == "Tenerife rent growth":
            got = next(
                (
                    r["rent_growth_pct"]
                    for r in tr["provincial"]["top_tourist"]
                    if r["provincia"] == "Santa Cruz de Tenerife"
                ),
                None,
            )
        else:
            got = _json_path(tr, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] tourist_rents: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 10
    print(f"{total - failures}/{total} claims hold")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
