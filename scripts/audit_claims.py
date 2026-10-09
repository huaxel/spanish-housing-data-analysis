"""Audit headline doc claims against the marts. Fails on drift.

Each claim pins (doc, value) to a live query. Run: make audit.
Add a claim whenever a doc states a number someone might quote.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED  # noqa: E402

con = duckdb.connect(str(PROCESSED / "marts.duckdb"), read_only=True)
ROOT = Path(__file__).resolve().parents[1]

# (label, output json, estimator script). The output must carry a _meta
# freshness key (see ols.model_meta); the audit fails when the committed
# result predates its estimator code or its input data, so a green audit
# can no longer pass on stale model numbers. Added 2026-10-06: the audit
# previously compared docs against saved JSON without checking whether
# the JSON still reflected the code (it did not — see iv_results.json
# carrying pre-transpose-fix SEs while the script had moved on).
MODEL_FRESHNESS = [
    ("iv_migration", "explorations/iv_results.json", "explorations/iv_migration.py"),
    ("panel_saiz", "explorations/panel_saiz_results.json", "explorations/panel_saiz.py"),
    ("panel_provincial", "artifacts/panel_provincial.json", "explorations/panel_provincial.py"),
    ("panel_adjusted", "artifacts/panel_adjusted.json", "explorations/panel_adjusted.py"),
    ("panel_tourist", "artifacts/panel_tourist.json", "explorations/panel_tourist.py"),
    ("panel_quarterly", "artifacts/panel_quarterly.json", "explorations/panel_quarterly.py"),
    ("wild_ar_bust", "artifacts/wild_ar_bust.json", "explorations/wild_ar_bust.py"),
    ("tourist_inversion", "artifacts/tourist_inversion.json", "scripts/invert_tourist.py"),
    ("cadastre_eras", "artifacts/cadastre_eras.json", "explorations/cadastre_eras.py"),
    ("cadastre_age_rent", "artifacts/cadastre_age_rent.json", "explorations/cadastre_age_rent.py"),
    (
        "cadastre_era_rehab",
        "artifacts/cadastre_era_rehab.json",
        "explorations/cadastre_era_rehab.py",
    ),
    (
        "cadastre_era_quality",
        "artifacts/cadastre_era_quality.json",
        "explorations/cadastre_era_quality.py",
    ),
    (
        "cadastre_era_surface",
        "artifacts/cadastre_era_surface.json",
        "explorations/cadastre_era_surface.py",
    ),
    (
        "cadastre_vacancy_alignment",
        "artifacts/cadastre_vacancy_alignment.json",
        "explorations/cadastre_vacancy_alignment.py",
    ),
    (
        "cadastre_household_alignment",
        "artifacts/cadastre_household_alignment.json",
        "explorations/cadastre_household_alignment.py",
    ),
    ("cadastre_capitals", "artifacts/cadastre_capitals.json", "explorations/cadastre_capitals.py"),
    ("province_inventory", "artifacts/province_inventory.json", "scripts/inventory_province.py"),
    ("cadastre_province", "artifacts/cadastre_province.json", "explorations/cadastre_province.py"),
    (
        "malaga_barrios",
        "artifacts/cadastre_malaga_barrios.json",
        "explorations/cadastre_malaga_barrios.py",
    ),
    (
        "granada_distritos",
        "artifacts/cadastre_granada_distritos.json",
        "explorations/cadastre_granada_distritos.py",
    ),
    ("censo_vintage", "artifacts/censo_vintage.json", "explorations/censo_vintage.py"),
    # Descriptive outputs (no estimator math, but quotable numbers): stamped
    # + registered 2026-10-07 — a rebuild + audit without analysis used to
    # pass on stale-but-doc-consistent JSONs.
    ("tourist_rents", "artifacts/tourist_rents.json", "explorations/tourist_rents.py"),
    ("ratio_ccaa", "artifacts/ratio_ccaa.json", "explorations/ratio_ccaa.py"),
    ("serpavi_analysis", "artifacts/serpavi_analysis.json", "explorations/serpavi_analysis.py"),
    (
        "municipios_nacional",
        "artifacts/municipios_nacional.json",
        "explorations/municipios_nacional.py",
    ),
    (
        "barrios_bcn_yield",
        "artifacts/barrios_bcn_yield.json",
        "explorations/barrios_bcn_yield.py",
    ),
    (
        "desahucios_renta",
        "artifacts/desahucios_renta.json",
        "explorations/desahucios_renta.py",
    ),
    (
        "madrid_vacancy",
        "artifacts/madrid_vacancy_terrain.json",
        "explorations/panel_saiz_madrid_vacancy.py",
    ),
    (
        "panel_saiz_municipal",
        "explorations/panel_saiz_municipal_results.json",
        "explorations/panel_saiz_municipal.py",
    ),
    (
        "panel_saiz_madrid",
        "explorations/panel_saiz_madrid_results.json",
        "explorations/panel_saiz_madrid.py",
    ),
    (
        "hypothesis_01",
        "artifacts/hypothesis_01.json",
        "explorations/test_absorption_hypothesis.py",
    ),
    (
        "panel_tourist",
        "artifacts/panel_tourist.json",
        "explorations/panel_tourist.py",
    ),
]


def _model_output(rel: str) -> dict:
    """Load a model-output JSON, failing with guidance when absent.

    The artifacts/ copies are git-ignored and exist only after `make
    analysis`; on a fresh clone the audit must say what to run instead of
    crashing with a traceback (or silently skipping the claims those
    files back)."""
    p = ROOT / rel
    if not p.exists():
        print(
            f"FAIL: {rel} missing — model outputs not built; "
            "run `make analysis` (or `make gates`), then make audit"
        )
        sys.exit(2)
    return json.loads(p.read_text())


def check_freshness() -> int:
    """Fail when a model output predates its code or data. Returns failures."""
    failures = 0
    ols_sha = ols.sha_file(str(Path(ols.__file__)))
    for label, rel_json, rel_script in MODEL_FRESHNESS:
        p = ROOT / rel_json
        if not p.exists():
            print(
                f"[FAIL] {label}: {rel_json} absent — run `make analysis` "
                "(or `make gates`) before auditing"
            )
            failures += 1
            continue
        meta = json.loads(p.read_text()).get("_meta")
        if not meta:
            print(f"[FAIL] {label}: {rel_json} has no _meta key — re-run {rel_script}")
            failures += 1
            continue
        ok = True
        if meta.get("script_sha") != ols.sha_file(str(ROOT / rel_script)):
            print(f"[FAIL] {label}: estimator {rel_script} changed since output — re-run it")
            ok = False
        if meta.get("ols_sha") != ols_sha:
            print(f"[FAIL] {label}: src/spanish_housing/ols.py changed since output — re-run")
            ok = False
        if label == "tourist_inversion" and meta.get("wild_grid_sha") != ols.sha_file(
            str(ROOT / "src/spanish_housing/wild_grid.py")
        ):
            print(f"[FAIL] {label}: src/spanish_housing/wild_grid.py changed since output — re-run")
            ok = False
        for rel_data, want in (meta.get("data_sha") or {}).items():
            if not (ROOT / rel_data).exists():
                print(
                    f"[FAIL] {label}: input {rel_data} absent — run "
                    "`make analysis` (or `make gates`) before auditing"
                )
                ok = False
            elif ols.sha_file(str(ROOT / rel_data)) != want:
                print(f"[FAIL] {label}: input {rel_data} changed since output — re-run")
                ok = False
        if ok:
            print(f"[OK] {label}: output fresh vs code + data")
        failures += not ok
    return failures


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
        "Valencia city pop 2025",
        "SELECT poblacion FROM muni_vlc WHERE municipio='València' AND anyo=2025",
        840792.0,
        1.0,
    ),
    (
        "municipios",
        "Valencia city rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc WHERE municipio='València' AND anyo=2024",
        8.18,
        0.01,
    ),
    (
        "municipios",
        "Valencia city rent 2011",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc WHERE municipio='València' AND anyo=2011",
        5.15,
        0.01,
    ),
    (
        "municipios",
        "Valencia city vacant share 2011",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_vlc "
        "WHERE municipio='València' AND anyo=2011",
        13.6,
        0.1,
    ),
    (
        "municipios",
        "Valencia city vacant dwellings 2011",
        "SELECT vacant_2011 FROM muni_vlc WHERE municipio='València' AND anyo=2011",
        57193.0,
        1.0,
    ),
    (
        "municipios",
        "Canet rent 2024 (highest VLC)",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc "
        "WHERE municipio='Canet d''En Berenguer' AND anyo=2024",
        8.33,
        0.01,
    ),
    (
        "municipios",
        "Font de la Figuera vacant 2011 (highest VLC)",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_vlc "
        "WHERE municipio='Font de la Figuera, la' AND anyo=2011",
        44.4,
        0.1,
    ),
    (
        "municipios",
        "Torrent rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc WHERE municipio='Torrent' AND anyo=2024",
        6.28,
        0.01,
    ),
    (
        "municipios",
        "Gandia rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc WHERE municipio='Gandia' AND anyo=2024",
        5.22,
        0.01,
    ),
    (
        "municipios",
        "Torrent rent 2011",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc WHERE municipio='Torrent' AND anyo=2011",
        4.22,
        0.01,
    ),
    (
        "municipios",
        "Gandia rent 2011",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc WHERE municipio='Gandia' AND anyo=2011",
        3.93,
        0.01,
    ),
    (
        "municipios",
        "Loriguilla rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc WHERE municipio='Loriguilla' AND anyo=2024",
        8.26,
        0.01,
    ),
    (
        "municipios",
        "Valencia city share of province 2025",
        "SELECT ROUND(100.0 * (SELECT poblacion FROM muni_vlc "
        "WHERE municipio='València' AND anyo=2025) / "
        "(SELECT SUM(poblacion) FROM muni_vlc WHERE anyo=2025), 1)",
        30.5,
        0.1,
    ),
    (
        "municipios",
        "Sevilla city pop 2025",
        "SELECT poblacion FROM muni_sev WHERE municipio='Sevilla (ciudad)' AND anyo=2025",
        689423.0,
        1.0,
    ),
    (
        "municipios",
        "Sevilla city rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev "
        "WHERE municipio='Sevilla (ciudad)' AND anyo=2024",
        9.17,
        0.01,
    ),
    (
        "municipios",
        "Sevilla city rent 2011",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev "
        "WHERE municipio='Sevilla (ciudad)' AND anyo=2011",
        7.01,
        0.01,
    ),
    (
        "municipios",
        "Sevilla city vacant share 2011",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_sev "
        "WHERE municipio='Sevilla (ciudad)' AND anyo=2011",
        14.3,
        0.1,
    ),
    (
        "municipios",
        "Sevilla city vacant dwellings 2011",
        "SELECT vacant_2011 FROM muni_sev WHERE municipio='Sevilla (ciudad)' AND anyo=2011",
        48178.0,
        1.0,
    ),
    (
        "municipios",
        "Sevilla city share of province 2025",
        "SELECT ROUND(100.0 * (SELECT poblacion FROM muni_sev "
        "WHERE municipio='Sevilla (ciudad)' AND anyo=2025) / "
        "(SELECT SUM(poblacion) FROM muni_sev WHERE anyo=2025), 1)",
        34.9,
        0.1,
    ),
    (
        "municipios",
        "Espartinas rent 2024 (highest SEV)",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev WHERE municipio='Espartinas' AND anyo=2024",
        9.67,
        0.01,
    ),
    (
        "municipios",
        "Puebla de Cazalla vacant 2011 (highest SEV)",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_sev "
        "WHERE municipio='Puebla de Cazalla, La' AND anyo=2011",
        26.0,
        0.1,
    ),
    (
        "municipios",
        "Dos Hermanas rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev WHERE municipio='Dos Hermanas' AND anyo=2024",
        7.45,
        0.01,
    ),
    (
        "municipios",
        "Dos Hermanas rent 2011",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev WHERE municipio='Dos Hermanas' AND anyo=2011",
        5.88,
        0.01,
    ),
    (
        "municipios",
        "Alcala rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev "
        "WHERE municipio='Alcalá de Guadaíra' AND anyo=2024",
        6.29,
        0.01,
    ),
    (
        "municipios",
        "Alcala rent 2011",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev "
        "WHERE municipio='Alcalá de Guadaíra' AND anyo=2011",
        5.14,
        0.01,
    ),
    (
        "municipios",
        "Mairena rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev "
        "WHERE municipio='Mairena del Aljarafe' AND anyo=2024",
        8.44,
        0.01,
    ),
    (
        "municipios",
        "Mairena rent 2011",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev "
        "WHERE municipio='Mairena del Aljarafe' AND anyo=2011",
        6.6,
        0.01,
    ),
    (
        "municipios",
        "Puebla de los Infantes vacant 2011",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_sev "
        "WHERE municipio='Puebla de los Infantes, La' AND anyo=2011",
        25.4,
        0.1,
    ),
    (
        "municipios",
        "Villanueva del Rio vacant 2011",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_sev "
        "WHERE municipio='Villanueva del Río y Minas' AND anyo=2011",
        24.6,
        0.1,
    ),
    (
        "municipios",
        "national muni count",
        "SELECT COUNT(DISTINCT (cpro, municipio)) FROM muni_all",
        8136.0,
        1.0,
    ),
    (
        "municipios",
        "Madrid city pop 2025 (national table)",
        "SELECT poblacion FROM muni_all WHERE municipio='Madrid (ciudad)' AND anyo=2025",
        3506730.0,
        1.0,
    ),
    (
        "municipios",
        "Madrid city rent 2024 (national table)",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_all "
        "WHERE municipio='Madrid (ciudad)' AND anyo=2024",
        13.97,
        0.01,
    ),
    (
        "municipios",
        "Sant Josep rent 2024 (highest national)",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_all "
        "WHERE municipio='Sant Josep de sa Talaia' AND anyo=2024",
        14.63,
        0.01,
    ),
    (
        "municipios",
        "Donostia rent 2024",
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_all "
        "WHERE municipio='Donostia/San Sebastián' AND anyo=2024",
        13.99,
        0.01,
    ),
    (
        "municipios",
        "Yebes vacant 2011 (highest national)",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_all "
        "WHERE municipio='Yebes' AND anyo=2011",
        60.0,
        0.1,
    ),
    (
        "municipios",
        "Ezcaray vacant 2011",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_all "
        "WHERE municipio='Ezcaray' AND anyo=2011",
        49.1,
        0.1,
    ),
    (
        "municipios",
        "Chilches vacant 2011",
        "SELECT ROUND(100.0 * vacant_2011 / dwellings_2011, 1) FROM muni_all "
        "WHERE municipio='Chilches/Xilxes' AND anyo=2011",
        45.1,
        0.1,
    ),
    (
        "municipios",
        "national rent municipios 2024",
        "SELECT COUNT(DISTINCT (cpro, municipio)) FROM muni_all "
        "WHERE anyo=2024 AND rent_eur_m2 IS NOT NULL",
        2515.0,
        1.0,
    ),
    (
        "municipios",
        "Madrid barrios city 2025 Total",
        "SELECT eur_m2 FROM barrios_madrid WHERE distrito='Ciudad de Madrid' "
        "AND barrio='Ciudad de Madrid' AND anyo=2025 AND tipo='Total'",
        5285.72,
        0.01,
    ),
    (
        "municipios",
        "Madrid barrios city 2025 Nuevas",
        "SELECT eur_m2 FROM barrios_madrid WHERE distrito='Ciudad de Madrid' "
        "AND barrio='Ciudad de Madrid' AND anyo=2025 AND tipo='Nuevas'",
        5041.46,
        0.01,
    ),
    (
        "municipios",
        "Madrid barrios city 2025 Usadas",
        "SELECT eur_m2 FROM barrios_madrid WHERE distrito='Ciudad de Madrid' "
        "AND barrio='Ciudad de Madrid' AND anyo=2025 AND tipo='Usadas'",
        5333.59,
        0.01,
    ),
    (
        "municipios",
        "Recoletos 2025",
        "SELECT eur_m2 FROM barrios_madrid "
        "WHERE barrio='041. Recoletos' AND anyo=2025 AND tipo='Total'",
        14108.83,
        0.01,
    ),
    (
        "municipios",
        "Castellana 2025",
        "SELECT eur_m2 FROM barrios_madrid "
        "WHERE barrio='046. Castellana' AND anyo=2025 AND tipo='Total'",
        11685.39,
        0.01,
    ),
    (
        "municipios",
        "Almagro 2025",
        "SELECT eur_m2 FROM barrios_madrid "
        "WHERE barrio='074. Almagro' AND anyo=2025 AND tipo='Total'",
        10795.41,
        0.01,
    ),
    (
        "municipios",
        "Orcasitas 2025",
        "SELECT eur_m2 FROM barrios_madrid "
        "WHERE barrio='121. Orcasitas' AND anyo=2025 AND tipo='Total'",
        2357.51,
        0.01,
    ),
    (
        "municipios",
        "San Cristobal 2025",
        "SELECT eur_m2 FROM barrios_madrid "
        "WHERE barrio='172. San Cristóbal' AND anyo=2025 AND tipo='Total'",
        1909.6,
        0.01,
    ),
    (
        "municipios",
        "barrios count",
        "SELECT COUNT(DISTINCT barrio) FROM barrios_madrid",
        153,
        0,
    ),
    (
        "municipios",
        "barrios null count",
        "SELECT COUNT(*) FROM barrios_madrid WHERE eur_m2 IS NULL",
        3546,
        0,
    ),
    (
        "municipios",
        "barrio top-bottom ratio",
        "SELECT ROUND(MAX(eur_m2) / MIN(eur_m2), 1) FROM barrios_madrid "
        "WHERE anyo=2025 AND tipo='Total' AND eur_m2 > 0",
        7.4,
        0.1,
    ),
    (
        "municipios",
        "Sevilla IPRA barrios",
        "SELECT COUNT(DISTINCT idg) FROM barrios_sevilla",
        108,
        0,
    ),
    (
        "municipios",
        "Sevilla IPRA rows",
        "SELECT COUNT(*) FROM barrios_sevilla",
        756,
        0,
    ),
    (
        "municipios",
        "Sevilla IPRA missing cells",
        "SELECT COUNT(*) FROM barrios_sevilla WHERE ipra_eur_m2 IS NULL",
        37,
        0,
    ),
    (
        "municipios",
        "Sevilla IPRA 2022 maximum",
        "SELECT MAX(ipra_eur_m2) FROM barrios_sevilla WHERE anyo=2022",
        10.83,
        0.01,
    ),
    (
        "municipios",
        "Sevilla IPRA El Carmen 2022 (highest)",
        "SELECT ipra_eur_m2 FROM barrios_sevilla WHERE barrio='EL CARMEN' AND anyo=2022",
        10.83,
        0.01,
    ),
    (
        "municipios",
        "Sevilla IPRA 2022 minimum",
        "SELECT MIN(ipra_eur_m2) FROM barrios_sevilla WHERE anyo=2022",
        3.30,
        0.01,
    ),
    (
        "municipios",
        "Sevilla IPRA Valdezorras 2022 (lowest)",
        "SELECT ipra_eur_m2 FROM barrios_sevilla WHERE barrio='VALDEZORRAS' AND anyo=2022",
        3.30,
        0.01,
    ),
    (
        "municipios",
        "Sevilla IPRA Alfalfa 2022",
        "SELECT ipra_eur_m2 FROM barrios_sevilla WHERE barrio='ALFALFA' AND anyo=2022",
        6.80,
        0.01,
    ),
    (
        "municipios",
        "Sevilla SIM purchase collective coverage",
        "SELECT COUNT(compra_colectiva_eur_m2) FROM barrios_sevilla_compra",
        108,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM purchase unifamiliar missing",
        "SELECT COUNT(*) FROM barrios_sevilla_compra WHERE compra_unifamiliar_eur_m2 IS NULL",
        31,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM collective purchase maximum",
        "SELECT MAX(compra_colectiva_eur_m2) FROM barrios_sevilla_compra",
        2585,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM collective purchase minimum",
        "SELECT MIN(compra_colectiva_eur_m2) FROM barrios_sevilla_compra",
        796,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM Museo collective purchase maximum",
        "SELECT compra_colectiva_eur_m2 FROM barrios_sevilla_compra WHERE barrio='MUSEO'",
        2585,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM Torreblanca collective purchase minimum",
        "SELECT compra_colectiva_eur_m2 FROM barrios_sevilla_compra WHERE barrio='TORREBLANCA'",
        796,
        0,
    ),
    (
        "municipios",
        "Sevilla offer-price rows",
        "SELECT COUNT(*) FROM sevilla_oferta_zona",
        336,
        0,
    ),
    (
        "municipios",
        "Sevilla Fotocasa district count",
        "SELECT COUNT(DISTINCT zona) FROM sevilla_oferta_zona WHERE provider='Fotocasa'",
        11,
        0,
    ),
    (
        "municipios",
        "Sevilla Idealista zone count",
        "SELECT COUNT(DISTINCT zona) FROM sevilla_oferta_zona WHERE provider='Idealista'",
        17,
        0,
    ),
    (
        "municipios",
        "Sevilla Fotocasa highest offer",
        "SELECT MAX(precio_oferta_eur_m2) FROM sevilla_oferta_zona WHERE provider='Fotocasa'",
        3876,
        0,
    ),
    (
        "municipios",
        "Sevilla Fotocasa Casco Antiguo September offer",
        "SELECT precio_oferta_eur_m2 FROM sevilla_oferta_zona "
        "WHERE provider='Fotocasa' AND zona='Casco Antiguo' AND mes=9",
        3876,
        0,
    ),
    (
        "municipios",
        "Sevilla Idealista lowest offer",
        "SELECT MIN(precio_oferta_eur_m2) FROM sevilla_oferta_zona WHERE provider='Idealista'",
        665,
        0,
    ),
    (
        "municipios",
        "Sevilla Idealista Torreblanca July offer",
        "SELECT precio_oferta_eur_m2 FROM sevilla_oferta_zona "
        "WHERE provider='Idealista' AND zona='16. Torreblanca' AND mes=7",
        665,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM population/household barrio-years",
        "SELECT COUNT(*) FROM sevilla_sim_poblacion_hogares",
        756,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM population barrios",
        "SELECT COUNT(DISTINCT idg) FROM sevilla_sim_poblacion_hogares",
        108,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM Alfalfa population 2015",
        "SELECT poblacion FROM sevilla_sim_poblacion_hogares WHERE barrio='ALFALFA' AND anyo=2015",
        4479,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM Alfalfa households 2015",
        "SELECT hogares FROM sevilla_sim_poblacion_hogares WHERE barrio='ALFALFA' AND anyo=2015",
        1972,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM vivienda barrios",
        "SELECT COUNT(DISTINCT idg) FROM sevilla_sim_vivienda",
        108,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM Alfalfa vacancy snapshot",
        "SELECT deshabitadas_pct FROM sevilla_sim_vivienda WHERE barrio='ALFALFA'",
        7,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM Alfalfa rehabilitation estimate",
        "SELECT rehabilitacion_estimada_pct FROM sevilla_sim_vivienda WHERE barrio='ALFALFA'",
        4,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM tourism barrios",
        "SELECT COUNT(DISTINCT idg) FROM sevilla_sim_turismo",
        108,
        0,
    ),
    (
        "municipios",
        "Sevilla SIM Alfalfa tourist listings 2008",
        "SELECT vft_2008 FROM sevilla_sim_turismo WHERE barrio='ALFALFA'",
        557,
        0,
    ),
    (
        "municipios",
        "Barcelona INCASÒL annual rows",
        "SELECT COUNT(*) FROM barrios_bcn_lloguer_anual",
        2184,
        0,
    ),
    (
        "municipios",
        "Barcelona INCASÒL areas",
        "SELECT COUNT(DISTINCT codi) FROM barrios_bcn_lloguer_anual",
        84,
        0,
    ),
    (
        "municipios",
        "Barcelona INCASÒL city contracts 2024",
        "SELECT contractes FROM barrios_bcn_lloguer_anual WHERE codi='BCN' AND anyo=2024",
        32903,
        0,
    ),
    (
        "municipios",
        "Barcelona INCASÒL city rent per m2 2024",
        "SELECT ROUND(lloguer_m2, 2) FROM barrios_bcn_lloguer_anual WHERE codi='BCN' AND anyo=2024",
        16.13,
        0.01,
    ),
    (
        "municipios",
        "Barcelona INCASÒL Barceloneta rent per m2 2025",
        "SELECT ROUND(lloguer_m2, 2) FROM barrios_bcn_lloguer_anual "
        "WHERE nom='la Barceloneta' AND anyo=2025",
        22.70,
        0.01,
    ),
    (
        "municipios",
        "Barcelona INCASÒL quarterly rows",
        "SELECT COUNT(*) FROM barrios_bcn_lloguer_trimestral",
        4984,
        0,
    ),
    (
        "municipios",
        "Barcelona compravendes rows",
        "SELECT COUNT(*) FROM barrios_bcn_compraventes",
        2520,
        0,
    ),
    (
        "municipios",
        "Barcelona compravendes city transactions 2024Q4",
        "SELECT trx_total FROM barrios_bcn_compraventes "
        "WHERE codi='BCN' AND anyo=2024 AND trimestre=4",
        4368,
        0,
    ),
    (
        "municipios",
        "Barcelona compravendes city price per m2 2024Q4",
        "SELECT eur_m2_total FROM barrios_bcn_compraventes "
        "WHERE codi='BCN' AND anyo=2024 AND trimestre=4",
        4622.43,
        0.01,
    ),
    (
        "municipios",
        "SERPAVI district cells",
        "SELECT COUNT(*) FROM serpavi_distritos",
        1099206,
        0,
    ),
    (
        "municipios",
        "SERPAVI districts with data",
        "SELECT COUNT(DISTINCT distrito) FROM serpavi_distritos",
        9680,
        0,
    ),
    (
        "municipios",
        "Salamanca district rent per m2 2024",
        "SELECT ROUND(valor, 2) FROM serpavi_distritos WHERE distrito='2807904' "
        "AND anyo=2024 AND medida='ALQM2_LV_M_VC'",
        18.31,
        0.01,
    ),
    (
        "synthesis",
        "CGPJ launch rows",
        "SELECT COUNT(*) FROM desahucios_provincia",
        3850,
        0,
    ),
    (
        "synthesis",
        "CGPJ national launches 2025",
        "SELECT SUM(lanz_total) FROM desahucios_provincia WHERE anyo=2025",
        24540,
        0,
    ),
    (
        "synthesis",
        "CGPJ national launches 2020Q2 (moratorium)",
        "SELECT SUM(lanz_total) FROM desahucios_provincia WHERE anyo=2020 AND trimestre=2",
        1383,
        0,
    ),
    (
        "synthesis",
        "Cadiz launches 2024Q4",
        "SELECT lanz_total FROM desahucios_provincia "
        "WHERE provincia='Cádiz' AND anyo=2024 AND trimestre=4",
        141,
        0,
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
        "anchor",
        "censo2001 total dwellings",
        "SELECT SUM(viviendas) FROM censo2001_2011_viviendas WHERE periodo = 2001",
        20946554.0,
        1.0,
    ),
    (
        "anchor",
        "censo2011 total dwellings",
        "SELECT SUM(viviendas) FROM censo2001_2011_viviendas WHERE periodo = 2011",
        25208623.0,
        1.0,
    ),
    (
        "anchor",
        "censo2001 worst provincial gap vs parque 2001 (%)",
        "SELECT MAX(ABS(c.viviendas - m.viviendas_total) * 100.0 / m.viviendas_total) "
        "FROM censo2001_2011_viviendas c JOIN mart_provincia_anual m "
        "ON c.cpro = m.cpro AND c.periodo = m.anyo WHERE c.periodo = 2001",
        1.28,
        0.03,
    ),
    (
        "anchor",
        "censo2011 worst provincial gap vs parque 2011 (%)",
        "SELECT MAX(ABS(c.viviendas - m.viviendas_total) * 100.0 / m.viviendas_total) "
        "FROM censo2001_2011_viviendas c JOIN mart_provincia_anual m "
        "ON c.cpro = m.cpro AND c.periodo = m.anyo WHERE c.periodo = 2011",
        0.51,
        0.03,
    ),
    (
        "anchor",
        "aeat 2023 dwellings with cadastral value (parts sum)",
        "SELECT SUM(n_total) FROM aeat_viviendas_uso "
        "WHERE anyo = 2023 AND grano IN ('provincia', 'ccaa_uniprovincial')",
        17804320.0,
        1.0,
    ),
    (
        "anchor",
        "aeat 2024 dwellings with cadastral value (parts sum)",
        "SELECT SUM(n_total) FROM aeat_viviendas_uso "
        "WHERE anyo = 2024 AND grano IN ('provincia', 'ccaa_uniprovincial')",
        18221324.0,
        1.0,
    ),
    (
        "anchor",
        "aeat 2023 at-disposition share of parts (%)",
        "SELECT 100.0 * SUM(n_disposicion) / SUM(n_total) FROM aeat_viviendas_uso "
        "WHERE anyo = 2023 AND grano IN ('provincia', 'ccaa_uniprovincial')",
        26.91,
        0.03,
    ),
    (
        "anchor",
        "aeat 2024 at-disposition share of parts (%)",
        "SELECT 100.0 * SUM(n_disposicion) / SUM(n_total) FROM aeat_viviendas_uso "
        "WHERE anyo = 2024 AND grano IN ('provincia', 'ccaa_uniprovincial')",
        26.71,
        0.03,
    ),
    (
        "anchor",
        "censo2021 sections usable rows",
        "SELECT COUNT(*) FROM censo2021_secciones WHERE NOT suprimido",
        34970.0,
        1.0,
    ),
    (
        "anchor",
        "censo2021 sections persons (t1_1 sum)",
        "SELECT SUM(t1_1) FROM censo2021_secciones",
        47400798.0,
        1.0,
    ),
    (
        "anchor",
        "censo2021 sections dwellings (t18_1 sum, suppressed excluded)",
        "SELECT SUM(t18_1) FROM censo2021_secciones WHERE NOT suprimido",
        26470415.0,
        1.0,
    ),
    (
        "anchor",
        "censo2021 sections households (t21_1 sum)",
        "SELECT SUM(t21_1) FROM censo2021_secciones WHERE NOT suprimido",
        18500241.0,
        1.0,
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
    (
        "synthesis",
        "EUR/m2 Nacional 2013",
        "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2013",
        1495.3,
        0.5,
    ),
    (
        "synthesis",
        "viv/1000 Nacional 2013",
        "SELECT viv_por_1000_hab FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2013",
        543.62,
        0.05,
    ),
    (
        "synthesis",
        "EUR/m2 Nacional 2021",
        "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2021",
        1657.6,
        0.5,
    ),
    (
        "synthesis",
        "viv/1000 Nacional 2021",
        "SELECT viv_por_1000_hab FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2021",
        563.89,
        0.05,
    ),
    (
        "synthesis",
        "mortgages Nacional 2021",
        "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2021",
        418058.0,
        1.0,
    ),
    (
        "synthesis",
        "bust IPV fall pct 2007-13",
        "SELECT ROUND((b.ipv_general-a.ipv_general)/a.ipv_general*100,1) "
        "FROM mart_ccaa_anual a JOIN mart_ccaa_anual b ON a.ccaa=b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2007 AND b.anyo=2013",
        -35.7,
        0.1,
    ),
    (
        "synthesis",
        "mortgage count fall pct 2007-13",
        "SELECT ROUND((1-b.hip_viv_num*1.0/a.hip_viv_num)*100,1) "
        "FROM mart_ccaa_anual a JOIN mart_ccaa_anual b ON a.ccaa=b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2007 AND b.anyo=2013",
        83.9,
        0.1,
    ),
    (
        "synthesis",
        "new-vacant count Nacional 2011",
        "SELECT SUM(viviendas) FROM censo2011_vintage "
        "WHERE ccaa='' AND provincia='' AND tipo='vacia' AND vintage='De 2002 a 2011'",
        767925.0,
        1.0,
    ),
    (
        "synthesis",
        "20-34 cohort 2013",
        "SELECT SUM(pob_20_34) FROM mart_ccaa_anual WHERE ccaa!='Nacional' AND anyo=2013",
        8999575.0,
        1.0,
    ),
    (
        "synthesis",
        "20-34 cohort 2019",
        "SELECT SUM(pob_20_34) FROM mart_ccaa_anual WHERE ccaa!='Nacional' AND anyo=2019",
        7618270.0,
        1.0,
    ),
    (
        "synthesis",
        "net dwelling additions 2021-25",
        "SELECT b.viviendas_total-a.viviendas_total FROM mart_ccaa_anual a "
        "JOIN mart_ccaa_anual b ON a.ccaa=b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2021 AND b.anyo=2025",
        379651.0,
        1.0,
    ),
    (
        "synthesis",
        "net household additions 2021-25",
        "SELECT b.hogares-a.hogares FROM mart_ccaa_anual a "
        "JOIN mart_ccaa_anual b ON a.ccaa=b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2021 AND b.anyo=2025",
        981823.0,
        1.0,
    ),
    (
        "synthesis",
        "IPV rise pct 2021-25",
        "SELECT ROUND((b.ipv_general-a.ipv_general)/a.ipv_general*100,1) "
        "FROM mart_ccaa_anual a JOIN mart_ccaa_anual b ON a.ccaa=b.ccaa "
        "WHERE a.ccaa='Nacional' AND a.anyo=2021 AND b.anyo=2025",
        36.4,
        0.1,
    ),
    (
        "synthesis",
        "Madrid affordability 2024",
        "SELECT afford_90m2_years FROM mart_ccaa_anual "
        "WHERE ccaa='Madrid, Comunidad de' AND anyo=2024",
        6.15,
        0.05,
    ),
    (
        "synthesis",
        "Barcelona sale rise pct 2013-24",
        "SELECT ROUND((MAX(CASE WHEN anyo=2024 THEN sale_eur_m2 END) "
        "- MAX(CASE WHEN anyo=2013 THEN sale_eur_m2 END)) "
        "/ MAX(CASE WHEN anyo=2013 THEN sale_eur_m2 END)*100,1) "
        "FROM muni_bcn WHERE municipio='Barcelona'",
        64.8,
        0.1,
    ),
    (
        "synthesis",
        "Barcelona rent rise pct 2013-24",
        "SELECT ROUND((MAX(CASE WHEN anyo=2024 THEN rent_month END) "
        "- MAX(CASE WHEN anyo=2013 THEN rent_month END)) "
        "/ MAX(CASE WHEN anyo=2013 THEN rent_month END)*100,1) "
        "FROM muni_bcn WHERE municipio='Barcelona'",
        68.3,
        0.1,
    ),
    (
        "synthesis",
        "Barcelona mortgage burden 2022",
        "SELECT mortgage_burden FROM muni_bcn WHERE municipio='Barcelona' AND anyo=2022",
        63.592250410969044,
        0.1,
    ),
    (
        "synthesis",
        "Sant Adria mortgage burden 2022",
        "SELECT mortgage_burden FROM muni_bcn WHERE municipio='Sant Adrià de Besòs' AND anyo=2022",
        71.87417256544035,
        0.1,
    ),
    (
        "synthesis",
        "Alicante ratio peak",
        "SELECT MAX(viv_por_1000_hab) FROM mart_provincia_anual WHERE provincia='Alicante/Alacant'",
        724.04,
        0.05,
    ),
    (
        "synthesis",
        "Alicante non-primary 2020",
        "SELECT ROUND(100.0*viviendas_no_principales/viviendas_total,1) "
        "FROM mart_provincia_anual WHERE provincia='Alicante/Alacant' AND anyo=2020",
        44.1,
        0.1,
    ),
    (
        "synthesis",
        "Alicante non-primary 2025",
        "SELECT ROUND(100.0*viviendas_no_principales/viviendas_total,1) "
        "FROM mart_provincia_anual WHERE provincia='Alicante/Alacant' AND anyo=2025",
        40.3,
        0.1,
    ),
    (
        "synthesis",
        "interior ratio min 2025 (Galicia)",
        "SELECT MIN(viv_por_1000_hab) FROM mart_ccaa_anual "
        "WHERE ccaa IN ('Galicia','Castilla y León','Asturias, Principado de') AND anyo=2025",
        652.85,
        0.05,
    ),
    (
        "synthesis",
        "interior ratio max 2025 (CyL)",
        "SELECT MAX(viv_por_1000_hab) FROM mart_ccaa_anual "
        "WHERE ccaa IN ('Galicia','Castilla y León','Asturias, Principado de') AND anyo=2025",
        770.67,
        0.05,
    ),
    (
        "synthesis",
        "national ratio growth pct 01-25",
        "WITH p AS (SELECT SUM(viviendas_total) s, SUM(poblacion) p "
        "FROM mart_provincia_anual WHERE anyo=2001), "
        "c AS (SELECT viviendas_total s, poblacion p FROM mart_ccaa_anual "
        "WHERE ccaa='Nacional' AND anyo=2025) "
        "SELECT ROUND((c.s/c.p-p.s/p.p)/(p.s/p.p)*100,1) FROM p, c",
        7.8,
        0.1,
    ),
    (
        "synthesis",
        "absorption min 2021-25",
        "WITH a AS (SELECT * FROM mart_ccaa_anual WHERE anyo=2021), "
        "b AS (SELECT * FROM mart_ccaa_anual WHERE anyo=2025) "
        "SELECT ROUND(MIN((b.viviendas_total-a.viviendas_total)*1.0/(b.hogares-a.hogares)),3) "
        "FROM a JOIN b ON a.ccaa=b.ccaa WHERE b.ccaa!='Nacional' AND b.hogares>a.hogares",
        0.234,
        0.005,
    ),
    (
        "synthesis",
        "absorption max 2021-25",
        "WITH a AS (SELECT * FROM mart_ccaa_anual WHERE anyo=2021), "
        "b AS (SELECT * FROM mart_ccaa_anual WHERE anyo=2025) "
        "SELECT ROUND(MAX((b.viviendas_total-a.viviendas_total)*1.0/(b.hogares-a.hogares)),3) "
        "FROM a JOIN b ON a.ccaa=b.ccaa WHERE b.ccaa!='Nacional' AND b.hogares>a.hogares",
        0.899,
        0.005,
    ),
    (
        "synthesis",
        "Benidorm second homes 2011",
        "SELECT ROUND(SUM(CASE WHEN tipo='Vivienda secundaria' THEN viviendas_2011 END) "
        "* 100.0 / SUM(CASE WHEN tipo='Total viviendas' THEN viviendas_2011 END), 1) "
        "FROM censo2011_val WHERE municipio='Benidorm'",
        43.3,
        0.1,
    ),
    (
        "synthesis",
        "overstock min d_07_25 (Extremadura)",
        "WITH p AS (SELECT SUM(viviendas_total) s, SUM(poblacion) p "
        "FROM mart_provincia_anual WHERE anyo=2007 AND ccaa='Extremadura'), "
        "c AS (SELECT viviendas_total s, poblacion p FROM mart_ccaa_anual "
        "WHERE ccaa='Extremadura' AND anyo=2025) "
        "SELECT ROUND(1000.0*c.s/c.p-1000.0*p.s/p.p,1) FROM p, c",
        100.0,
        0.1,
    ),
    (
        "synthesis",
        "Alicante ratio 2025",
        "SELECT viv_por_1000_hab FROM mart_provincia_anual "
        "WHERE provincia='Alicante/Alacant' AND anyo=2025",
        675.64,
        0.05,
    ),
    (
        "affordability",
        "renta rise pct 2008-24",
        "SELECT ROUND((MAX(CASE WHEN anyo=2024 THEN renta_hogar_neta END) "
        "- MAX(CASE WHEN anyo=2008 THEN renta_hogar_neta END)) "
        "/ MAX(CASE WHEN anyo=2008 THEN renta_hogar_neta END)*100,1) "
        "FROM mart_ccaa_anual WHERE ccaa='Nacional'",
        29.8,
        0.1,
    ),
    (
        "affordability",
        "eur fall pct 2008-24",
        "SELECT ROUND((MAX(CASE WHEN anyo=2024 THEN eur_m2_libre END) "
        "- MAX(CASE WHEN anyo=2008 THEN eur_m2_libre END)) "
        "/ MAX(CASE WHEN anyo=2008 THEN eur_m2_libre END)*100,1) "
        "FROM mart_ccaa_anual WHERE ccaa='Nacional'",
        -7.6,
        0.1,
    ),
    (
        "affordability",
        "Madrid renta 2024",
        "SELECT renta_hogar_neta FROM mart_ccaa_anual "
        "WHERE ccaa='Madrid, Comunidad de' AND anyo=2024",
        47375.0,
        1.0,
    ),
    (
        "affordability",
        "highest renta 2024 (superlative check)",
        "SELECT MAX(renta_hogar_neta) FROM mart_ccaa_anual WHERE ccaa!='Nacional' AND anyo=2024",
        47375.0,
        1.0,
    ),
    (
        "barcelona_municipios",
        "Sant Adria rent burden 2022",
        "SELECT rent_burden FROM muni_bcn WHERE municipio='Sant Adrià de Besòs' AND anyo=2022",
        66.84037527446937,
        0.1,
    ),
    (
        "barcelona_municipios",
        "Cornella rent burden 2022",
        "SELECT rent_burden FROM muni_bcn WHERE municipio='Cornellà de Llobregat' AND anyo=2022",
        50.895847994370165,
        0.1,
    ),
    (
        "barcelona_municipios",
        "Badalona rent burden 2022",
        "SELECT rent_burden FROM muni_bcn WHERE municipio='Badalona' AND anyo=2022",
        57.93296289657645,
        0.1,
    ),
    (
        "barcelona_municipios",
        "Santa Coloma rent burden 2022",
        "SELECT rent_burden FROM muni_bcn WHERE municipio='Santa Coloma de Gramenet' AND anyo=2022",
        54.60951564509216,
        0.1,
    ),
    (
        "barcelona_municipios",
        "Cornella mortgage burden 2022",
        "SELECT mortgage_burden FROM muni_bcn "
        "WHERE municipio='Cornellà de Llobregat' AND anyo=2022",
        62.122235088715115,
        0.1,
    ),
    (
        "ratio_ccaa",
        "national ratio growth pct 07-25",
        "WITH p AS (SELECT SUM(viviendas_total) s, SUM(poblacion) p "
        "FROM mart_provincia_anual WHERE anyo=2007), "
        "c AS (SELECT viviendas_total s, poblacion p FROM mart_ccaa_anual "
        "WHERE ccaa='Nacional' AND anyo=2025) "
        "SELECT ROUND((c.s/c.p-p.s/p.p)/(p.s/p.p)*100,1) FROM p, c",
        3.7,
        0.1,
    ),
    (
        "censo_anual_probe",
        "Nacional pop 2025 (Censo Anual cross-check)",
        "SELECT poblacion FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2025",
        49128297.0,
        1.0,
    ),
    (
        "censo_anual_probe",
        "mart Nacional pop 2021 (seam base)",
        "SELECT poblacion FROM mart_ccaa_anual WHERE ccaa='Nacional' AND anyo=2021",
        47385107.0,
        1.0,
    ),
    (
        "ratio_ccaa",
        "Madrid pop growth pct 01-21",
        "SELECT ROUND((SUM(CASE WHEN anyo=2021 THEN poblacion END) "
        "-SUM(CASE WHEN anyo=2001 THEN poblacion END)) "
        "/SUM(CASE WHEN anyo=2001 THEN poblacion END)*100,1) "
        "FROM mart_provincia_anual WHERE ccaa='Madrid, Comunidad de' AND anyo IN (2001,2021)",
        25.7,
        0.1,
    ),
    (
        "ratio_ccaa",
        "Madrid stock growth pct 01-21",
        "SELECT ROUND((SUM(CASE WHEN anyo=2021 THEN viviendas_total END) "
        "-SUM(CASE WHEN anyo=2001 THEN viviendas_total END)) "
        "/SUM(CASE WHEN anyo=2001 THEN viviendas_total END)*100,1) "
        "FROM mart_provincia_anual WHERE ccaa='Madrid, Comunidad de' AND anyo IN (2001,2021)",
        20.0,
        0.1,
    ),
    (
        "ratio_ccaa",
        "CyL stock growth pct 01-21",
        "SELECT ROUND((SUM(CASE WHEN anyo=2021 THEN viviendas_total END) "
        "-SUM(CASE WHEN anyo=2001 THEN viviendas_total END)) "
        "/SUM(CASE WHEN anyo=2001 THEN viviendas_total END)*100,1) "
        "FROM mart_provincia_anual WHERE ccaa='Castilla y León' AND anyo IN (2001,2021)",
        26.0,
        0.1,
    ),
    (
        "ratio_ccaa",
        "CyL pop growth pct 01-21",
        "SELECT ROUND((SUM(CASE WHEN anyo=2021 THEN poblacion END) "
        "-SUM(CASE WHEN anyo=2001 THEN poblacion END)) "
        "/SUM(CASE WHEN anyo=2001 THEN poblacion END)*100,1) "
        "FROM mart_provincia_anual WHERE ccaa='Castilla y León' AND anyo IN (2001,2021)",
        -3.9,
        0.1,
    ),
    (
        "ratio_ccaa",
        "Asturias pop growth pct 01-21",
        "SELECT ROUND((SUM(CASE WHEN anyo=2021 THEN poblacion END) "
        "-SUM(CASE WHEN anyo=2001 THEN poblacion END)) "
        "/SUM(CASE WHEN anyo=2001 THEN poblacion END)*100,1) "
        "FROM mart_provincia_anual WHERE ccaa='Asturias, Principado de' AND anyo IN (2001,2021)",
        -5.9,
        0.1,
    ),
    (
        "madrid_vs_valencia",
        "Madrid ratio 2007",
        "SELECT viv_por_1000_hab FROM mart_ccaa_anual "
        "WHERE ccaa='Madrid, Comunidad de' AND anyo=2007",
        459.1,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Madrid ratio 2025",
        "SELECT viv_por_1000_hab FROM mart_ccaa_anual "
        "WHERE ccaa='Madrid, Comunidad de' AND anyo=2025",
        429.41,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Madrid fewest ratio 2025 (superlative check)",
        "SELECT MIN(viv_por_1000_hab) FROM mart_ccaa_anual WHERE ccaa!='Nacional' AND anyo=2025",
        429.41,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Madrid non-primary 2007",
        "SELECT ROUND(100.0*viviendas_no_principales/viviendas_total,1) "
        "FROM mart_ccaa_anual WHERE ccaa='Madrid, Comunidad de' AND anyo=2007",
        18.7,
        0.1,
    ),
    (
        "madrid_vs_valencia",
        "Madrid non-primary 2025",
        "SELECT ROUND(100.0*viviendas_no_principales/viviendas_total,1) "
        "FROM mart_ccaa_anual WHERE ccaa='Madrid, Comunidad de' AND anyo=2025",
        11.6,
        0.1,
    ),
    (
        "madrid_vs_valencia",
        "Madrid most expensive 2025 (superlative check)",
        "SELECT MAX(eur_m2_libre) FROM mart_ccaa_anual WHERE ccaa!='Nacional' AND anyo=2025",
        3685.6,
        0.5,
    ),
    (
        "madrid_vs_valencia",
        "Madrid bust eur fall pct",
        "SELECT ROUND((b.eur_m2_libre-a.eur_m2_libre)/a.eur_m2_libre*100,1) "
        "FROM mart_ccaa_anual a JOIN mart_ccaa_anual b ON a.ccaa=b.ccaa "
        "WHERE a.ccaa='Madrid, Comunidad de' AND a.anyo=2007 AND b.anyo=2013",
        -32.6,
        0.1,
    ),
    (
        "madrid_vs_valencia",
        "Madrid affordability 2007",
        "SELECT afford_90m2_years FROM mart_ccaa_anual "
        "WHERE ccaa='Madrid, Comunidad de' AND anyo=2007",
        7.97,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Madrid affordability 2013",
        "SELECT afford_90m2_years FROM mart_ccaa_anual "
        "WHERE ccaa='Madrid, Comunidad de' AND anyo=2013",
        5.76,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Madrid mortgages 2007",
        "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Madrid, Comunidad de' AND anyo=2007",
        137344.0,
        1.0,
    ),
    (
        "madrid_vs_valencia",
        "Madrid mortgages 2013",
        "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Madrid, Comunidad de' AND anyo=2013",
        31843.0,
        1.0,
    ),
    (
        "madrid_vs_valencia",
        "Madrid young share 2021 pct",
        "SELECT ROUND(share_20_34*100,2) FROM mart_ccaa_anual "
        "WHERE ccaa='Madrid, Comunidad de' AND anyo=2021",
        17.12,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Madrid young share 2025 pct",
        "SELECT ROUND(share_20_34*100,2) FROM mart_ccaa_anual "
        "WHERE ccaa='Madrid, Comunidad de' AND anyo=2025",
        18.5,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Madrid young inflow 21-25",
        "SELECT b.pob_20_34-a.pob_20_34 FROM mart_ccaa_anual a "
        "JOIN mart_ccaa_anual b ON a.ccaa=b.ccaa "
        "WHERE a.ccaa='Madrid, Comunidad de' AND a.anyo=2021 AND b.anyo=2025",
        160279.0,
        1.0,
    ),
    (
        "madrid_vs_valencia",
        "Madrid household inflow 21-25",
        "SELECT b.hogares-a.hogares FROM mart_ccaa_anual a "
        "JOIN mart_ccaa_anual b ON a.ccaa=b.ccaa "
        "WHERE a.ccaa='Madrid, Comunidad de' AND a.anyo=2021 AND b.anyo=2025",
        161957.0,
        1.0,
    ),
    (
        "madrid_vs_valencia",
        "Castellon ratio 2025",
        "SELECT viv_por_1000_hab FROM mart_provincia_anual "
        "WHERE provincia='Castellón/Castelló' AND anyo=2025",
        717.24,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Balears affordability 2024 (worst)",
        "SELECT afford_90m2_years FROM mart_ccaa_anual WHERE ccaa='Balears, Illes' AND anyo=2024",
        6.41,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Castellon eur 2021",
        "SELECT eur_m2_libre FROM mart_provincia_anual "
        "WHERE provincia='Castellón/Castelló' AND anyo=2021",
        1069.6,
        0.5,
    ),
    (
        "madrid_vs_valencia",
        "Castellon eur 2025",
        "SELECT eur_m2_libre FROM mart_provincia_anual "
        "WHERE provincia='Castellón/Castelló' AND anyo=2025",
        1298.8,
        0.5,
    ),
    (
        "madrid_vs_valencia",
        "Valencia eur 2021",
        "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Comunitat Valenciana' AND anyo=2021",
        1253.8,
        0.5,
    ),
    (
        "madrid_vs_valencia",
        "Valencia eur 2025",
        "SELECT eur_m2_libre FROM mart_ccaa_anual WHERE ccaa='Comunitat Valenciana' AND anyo=2025",
        1707.8,
        0.5,
    ),
    (
        "madrid_vs_valencia",
        "Valencia mortgages 2013",
        "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Comunitat Valenciana' AND anyo=2013",
        19905.0,
        1.0,
    ),
    (
        "madrid_vs_valencia",
        "Valencia mortgages 2025",
        "SELECT hip_viv_num FROM mart_ccaa_anual WHERE ccaa='Comunitat Valenciana' AND anyo=2025",
        60543.0,
        1.0,
    ),
    (
        "madrid_vs_valencia",
        "Valencia young share 2021 pct",
        "SELECT ROUND(share_20_34*100,2) FROM mart_ccaa_anual "
        "WHERE ccaa='Comunitat Valenciana' AND anyo=2021",
        15.87,
        0.05,
    ),
    (
        "madrid_vs_valencia",
        "Valencia young share 2025 pct",
        "SELECT ROUND(share_20_34*100,2) FROM mart_ccaa_anual "
        "WHERE ccaa='Comunitat Valenciana' AND anyo=2025",
        16.72,
        0.05,
    ),
    (
        "panel_saiz_municipal",
        "Madrid-leg Arganda 2025",
        "SELECT eur_m2 FROM muni_madrid WHERE municipio='Arganda del Rey' AND anyo=2025",
        2280.0,
        0.5,
    ),
    (
        "panel_saiz_municipal",
        "Madrid-leg Aranjuez 2025",
        "SELECT eur_m2 FROM muni_madrid WHERE municipio='Aranjuez' AND anyo=2025",
        1930.6,
        0.5,
    ),
    (
        "panel_saiz_municipal",
        "Madrid-leg Valdemoro 2025",
        "SELECT eur_m2 FROM muni_madrid WHERE municipio='Valdemoro' AND anyo=2025",
        2355.7,
        0.5,
    ),
    (
        "panel_saiz_municipal",
        "Madrid-leg Pozuelo 2025",
        "SELECT eur_m2 FROM muni_madrid WHERE municipio='Pozuelo de Alarcón' AND anyo=2025",
        4794.1,
        0.5,
    ),
    (
        "panel_saiz_municipal",
        "Madrid-leg Madrid city 2025",
        "SELECT eur_m2 FROM muni_madrid WHERE municipio='Madrid' AND anyo=2025",
        4993.3,
        0.5,
    ),
    (
        "identification",
        "origen cell count (coverage anchor)",
        "SELECT COUNT(*) FROM padron_extranjeros_origen",
        544575.0,
        0.0,
    ),
    (
        "madrid_vs_valencia",
        "Alicante non-primary 2020",
        "SELECT ROUND(100.0*viviendas_no_principales/viviendas_total,1) "
        "FROM mart_provincia_anual WHERE provincia='Alicante/Alacant' AND anyo=2020",
        44.1,
        0.1,
    ),
    (
        "madrid_vs_valencia",
        "Castellon non-primary 2020",
        "SELECT ROUND(100.0*viviendas_no_principales/viviendas_total,1) "
        "FROM mart_provincia_anual WHERE provincia='Castellón/Castelló' AND anyo=2020",
        46.7,
        0.1,
    ),
    (
        "madrid_vs_valencia",
        "Pais Vasco ratio 2007 (below Madrid then)",
        "SELECT viv_por_1000_hab FROM mart_ccaa_anual WHERE ccaa='País Vasco' AND anyo=2007",
        453.54,
        0.05,
    ),
]


# Model-output claims (doc <-> committed explorations/iv_results.json).
# Mart SQL cannot recompute 2SLS; instead the doc numbers must match the
# committed estimator output, and re-running explorations/iv_migration.py
# (deterministic) must reproduce that file. Guards transcription drift.
# Corrected 2026-10-06: the two-way within transform now demeans the year
# dummies too (demeaned X + raw dummies biased every estimate below).
IV_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("iv_note", "IV 2SLS tau (base)", "base.tsls.tau", 0.083, 0.005),
    ("iv_note", "IV AR lower bound (base)", "base.ar_set.0", -0.2, 0.005),
    ("iv_note", "IV AR upper bound (base)", "base.ar_set.1", 0.4, 0.005),
    ("iv_note", "IV first-stage F (base)", "base.first_stage_F", 44.51, 0.05),
    ("iv_note", "IV first-stage F (bust)", "bust_2002_2013.first_stage_F", 34.44, 0.05),
    ("iv_note", "IV first-stage F (recovery)", "recovery_2014_2021.first_stage_F", 30.85, 0.05),
    ("iv_note", "IV 2SLS tau (+province trends)", "province_trends.tsls.tau", 0.201, 0.005),
    (
        "iv_note",
        "IV first-stage F (+province trends)",
        "province_trends.first_stage_F",
        44.16,
        0.05,
    ),
    (
        "iv_note",
        "IV AR lower bound (+province trends)",
        "province_trends.ar_set.0",
        -0.15,
        0.005,
    ),
    (
        "iv_note",
        "IV AR upper bound (+province trends)",
        "province_trends.ar_set.1",
        0.65,
        0.005,
    ),
    (
        "iv_note",
        "IV 2SLS tau (drop Madrid/Barcelona)",
        "drop_madrid_barcelona.tsls.tau",
        0.079,
        0.005,
    ),
    (
        "iv_note",
        "IV first-stage F (drop Madrid/Barcelona)",
        "drop_madrid_barcelona.first_stage_F",
        40.66,
        0.05,
    ),
    (
        "iv_note",
        "IV AR lower bound (drop Madrid/Barcelona)",
        "drop_madrid_barcelona.ar_set.0",
        -0.2,
        0.005,
    ),
    (
        "iv_note",
        "IV AR upper bound (drop Madrid/Barcelona)",
        "drop_madrid_barcelona.ar_set.1",
        0.4,
        0.005,
    ),
    ("iv_note", "IV 2SLS tau (bust 2002-13)", "bust_2002_2013.tsls.tau", 0.458, 0.005),
    ("iv_note", "IV OLS tau (base)", "base.ols.tau", 0.002, 0.005),
    ("iv_note", "IV OLS tau (bust 2002-13)", "bust_2002_2013.ols.tau", 0.032, 0.005),
    ("iv_note", "IV OLS tau (recovery 2014-21)", "recovery_2014_2021.ols.tau", 0.02, 0.005),
    ("iv_note", "IV n (base)", "base.n", 1000, 0),
    ("iv_note", "IV n (bust 2002-13)", "bust_2002_2013.n", 600, 0),
    ("iv_note", "IV n (recovery 2014-21)", "recovery_2014_2021.n", 400, 0),
    ("iv_note", "IV n (drop Madrid/Barcelona)", "drop_madrid_barcelona.n", 960, 0),
    ("iv_note", "IV AR lower bound (bust)", "bust_2002_2013.ar_set.0", -0.1, 0.005),
    ("iv_note", "IV AR upper bound (bust)", "bust_2002_2013.ar_set.1", 1.4, 0.005),
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
    ("panel_saiz", "low-constraint 2SLS tau", "low_constraint.tsls.tau", 0.05, 0.005),
    ("panel_saiz", "low-constraint first-stage F", "low_constraint.first_stage_F", 51.1, 0.05),
    ("panel_saiz", "low-constraint AR upper", "low_constraint.ar_set.1", 0.3, 0.005),
    ("panel_saiz", "high-constraint 2SLS tau", "high_constraint.tsls.tau", 0.137, 0.005),
    (
        "panel_saiz",
        "high-constraint first-stage F",
        "high_constraint.first_stage_F",
        21.33,
        0.05,
    ),
    ("panel_saiz", "high-constraint AR upper", "high_constraint.ar_set.1", 0.65, 0.005),
    ("panel_saiz", "low-constraint AR lower", "low_constraint.ar_set.0", -0.45, 0.005),
    ("panel_saiz", "high-constraint AR lower", "high_constraint.ar_set.0", -0.2, 0.005),
    ("panel_saiz", "low-constraint OLS tau", "low_constraint.ols.tau", -0.081, 0.005),
    ("panel_saiz", "high-constraint OLS tau", "high_constraint.ols.tau", 0.108, 0.005),
    ("panel_saiz", "interaction coefficient", "interaction_ols.interaction", 0.314, 0.005),
    (
        "panel_saiz",
        "interaction wild p",
        "interaction_ols.wild_p_interaction",
        0.288,
        0.005,
    ),
]


def _json_path(data: dict, path: str):
    for part in path.split("."):
        data = data[int(part)] if isinstance(data, list) and part.isdigit() else data[part]
    return data


def main() -> int:
    failures = 0
    for doc, desc, sql, expected, tol in CLAIMS:
        got = con.execute(sql).fetchone()[0]
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok

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
    ce = _model_output("artifacts/cadastre_eras.json")
    for desc, path, expected, tol in (
        ("cadastre eras barrios", "global.n_barrios", 107, 0),
        ("cadastre eras n_buildings", "global.n_buildings", 57723, 0),
        ("cadastre eras pre-1951 pct", "global.era_pct.Pre-1951", 6.8, 0.05),
        ("cadastre eras 1971-1990 pct", "global.era_pct.1971-1990", 37.7, 0.05),
        ("cadastre eras 2011+ pct", "global.era_pct.2011+", 4.7, 0.05),
        ("cadastre eras median year heliopolis", "barrios.10104.median_year", 1929, 0.5),
        ("cadastre eras pre-1951 heliopolis", "barrios.10104.Pre-1951", 75.0, 0.5),
        ("cadastre eras median year palmete", "barrios.04050.median_year", 2002, 0.5),
        ("cadastre eras 2011+ colores", "barrios.09097.2011+", 24.1, 0.5),
    ):
        got = _json_path(ce, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_eras: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 9

    ar = _model_output("artifacts/cadastre_age_rent.json")
    for desc, path, expected, tol in (
        ("age-rent joined barrios", "coverage.joined", 101, 0),
        ("age-rent era barrios", "coverage.era_barrios", 107, 0),
        (
            "age-rent spearman median year",
            "correlations.median_year_vs_rent.spearman",
            -0.158908,
            0.0005,
        ),
        (
            "age-rent pearson median year",
            "correlations.median_year_vs_rent.pearson",
            -0.138144,
            0.0005,
        ),
        (
            "age-rent spearman pre-1951 share",
            "correlations.era_share_vs_rent_spearman.Pre-1951",
            0.228364,
            0.0005,
        ),
        (
            "age-rent spearman 1951-1970 share",
            "correlations.era_share_vs_rent_spearman.1951-1970",
            0.317634,
            0.0005,
        ),
        (
            "age-rent spearman 1971-1990 share",
            "correlations.era_share_vs_rent_spearman.1971-1990",
            -0.136847,
            0.0005,
        ),
        (
            "age-rent spearman 1991-2010 share",
            "correlations.era_share_vs_rent_spearman.1991-2010",
            -0.123281,
            0.0005,
        ),
        (
            "age-rent spearman 2011+ share",
            "correlations.era_share_vs_rent_spearman.2011+",
            -0.004765,
            0.0005,
        ),
        ("age-rent oldest mean rent", "median_year_terciles.0.mean_rent_eur_m2", 7.22, 0.005),
        ("age-rent middle mean rent", "median_year_terciles.1.mean_rent_eur_m2", 7.36, 0.005),
        ("age-rent newest mean rent", "median_year_terciles.2.mean_rent_eur_m2", 6.87, 0.005),
        ("age-rent heliopolis rent", "oldest_barrios.0.ipra_2022_eur_m2", 3.67, 0.005),
        ("age-rent el tardon rent", "oldest_barrios.3.ipra_2022_eur_m2", 8.56, 0.005),
        ("age-rent palmete rent", "newest_barrios.0.ipra_2022_eur_m2", 3.64, 0.005),
        ("age-rent san bernardo rent", "newest_barrios.4.ipra_2022_eur_m2", 7.56, 0.005),
    ):
        got = _json_path(ar, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_age_rent: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 16

    er = _model_output("artifacts/cadastre_era_rehab.json")
    for desc, path, expected, tol in (
        ("era-rehab joined barrios", "coverage.joined_with_rehab", 101, 0),
        (
            "era-rehab spearman median year",
            "correlations.median_year_vs_rehab.spearman",
            -0.503165,
            0.0005,
        ),
        (
            "era-rehab pearson median year",
            "correlations.median_year_vs_rehab.pearson",
            -0.503805,
            0.0005,
        ),
        (
            "era-rehab spearman pre-1951 share",
            "correlations.pre_1951_share_vs_rehab.spearman",
            -0.382876,
            0.0005,
        ),
        (
            "era-rehab spearman sim ref vs rehab",
            "correlations.sim_ref_year_vs_rehab.spearman",
            -0.555186,
            0.0005,
        ),
        (
            "era-rehab spearman median year vs sim ref",
            "correlations.median_year_vs_sim_ref_year.spearman",
            0.848791,
            0.0005,
        ),
        (
            "era-rehab pearson median year vs sim ref",
            "correlations.median_year_vs_sim_ref_year.pearson",
            0.857981,
            0.0005,
        ),
        (
            "era-rehab oldest tercile mean rehab",
            "median_year_terciles_rehab.0.mean_rehab_pct",
            56.03,
            0.005,
        ),
        (
            "era-rehab middle tercile mean rehab",
            "median_year_terciles_rehab.1.mean_rehab_pct",
            50.14,
            0.005,
        ),
        (
            "era-rehab newest tercile mean rehab",
            "median_year_terciles_rehab.2.mean_rehab_pct",
            19.06,
            0.005,
        ),
        (
            "era-rehab pearson pre-1951 share",
            "correlations.pre_1951_share_vs_rehab.pearson",
            -0.21829,
            0.0005,
        ),
        (
            "era-rehab pearson sim ref vs rehab",
            "correlations.sim_ref_year_vs_rehab.pearson",
            -0.560476,
            0.0005,
        ),
        ("era-rehab cerezo rehab", "top_rehab_barrios.0.rehab_pct", 100, 0),
        ("era-rehab cerezo median year", "top_rehab_barrios.0.median_year", 1970, 0),
        (
            "era-rehab barzola pre-1951 share",
            "top_rehab_barrios.3.pre_1951_share",
            58.9,
            0.05,
        ),
        ("era-rehab san pablo median year", "top_rehab_barrios.5.median_year", 1963, 0),
    ):
        got = _json_path(er, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_era_rehab: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 16

    eq = _model_output("artifacts/cadastre_era_quality.json")
    for desc, path, expected, tol in (
        ("era-quality joined colectiva", "coverage.joined_calidad_colectiva", 107, 0),
        ("era-quality joined unifamiliar", "coverage.joined_calidad_unifamiliar", 77, 0),
        (
            "era-quality spearman median year vs colectiva",
            "correlations.median_year_vs_calidad_colectiva.spearman",
            -0.277203,
            0.0005,
        ),
        (
            "era-quality pearson median year vs colectiva",
            "correlations.median_year_vs_calidad_colectiva.pearson",
            -0.223601,
            0.0005,
        ),
        (
            "era-quality spearman median year vs unifamiliar",
            "correlations.median_year_vs_calidad_unifamiliar.spearman",
            -0.11873,
            0.0005,
        ),
        (
            "era-quality pearson median year vs unifamiliar",
            "correlations.median_year_vs_calidad_unifamiliar.pearson",
            -0.04183,
            0.0005,
        ),
        (
            "era-quality spearman colectiva vs rehab",
            "correlations.calidad_colectiva_vs_rehab.spearman",
            0.873959,
            0.0005,
        ),
        (
            "era-quality pearson colectiva vs rehab",
            "correlations.calidad_colectiva_vs_rehab.pearson",
            0.865413,
            0.0005,
        ),
        (
            "era-quality colectiva vs rehab n",
            "correlations.calidad_colectiva_vs_rehab.n",
            101,
            0,
        ),
        (
            "era-quality oldest tercile mean score",
            "median_year_terciles_calidad.0.mean_calidad_col",
            5.37,
            0.005,
        ),
        (
            "era-quality middle tercile mean score",
            "median_year_terciles_calidad.1.mean_calidad_col",
            5.29,
            0.005,
        ),
        (
            "era-quality newest tercile mean score",
            "median_year_terciles_calidad.2.mean_calidad_col",
            4.86,
            0.005,
        ),
        ("era-quality barzola score", "highest_score_barrios.0.calidad_colectiva", 7.0, 0),
        ("era-quality el prado score", "lowest_score_barrios.0.calidad_colectiva", 3.24, 0),
    ):
        got = _json_path(eq, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_era_quality: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 14

    es = _model_output("artifacts/cadastre_era_surface.json")
    for desc, path, expected, tol in (
        ("era-surface dated records", "coverage.records_with_valid_year", 50320, 0),
        ("era-surface q1 cutoff", "quartile_cutoffs_m2.q1", 132, 0),
        ("era-surface q2 cutoff", "quartile_cutoffs_m2.q2", 227, 0),
        ("era-surface q3 cutoff", "quartile_cutoffs_m2.q3", 623, 0),
        (
            "era-surface spearman year vs floor",
            "spearman_year_vs_floor_record_level",
            0.121969,
            0.0005,
        ),
        (
            "era-surface pre-1951 m2 per property",
            "eras.0.median_m2_per_property",
            152.0,
            0.05,
        ),
        (
            "era-surface 1951-1970 m2 per property",
            "eras.1.median_m2_per_property",
            99.0,
            0.05,
        ),
        (
            "era-surface 1971-1990 m2 per property",
            "eras.2.median_m2_per_property",
            131.4,
            0.05,
        ),
        (
            "era-surface 1991-2010 m2 per property",
            "eras.3.median_m2_per_property",
            152.0,
            0.05,
        ),
        (
            "era-surface 2011+ m2 per property",
            "eras.4.median_m2_per_property",
            176.0,
            0.05,
        ),
        (
            "era-surface pre-1951 q4 share",
            "eras.0.quartile_share_pct.4",
            38.2,
            0.05,
        ),
        (
            "era-surface 1951-1970 q4 share",
            "eras.1.quartile_share_pct.4",
            67.7,
            0.05,
        ),
        (
            "era-surface 1971-1990 q4 share",
            "eras.2.quartile_share_pct.4",
            87.1,
            0.05,
        ),
        (
            "era-surface 1991-2010 q4 share",
            "eras.3.quartile_share_pct.4",
            90.1,
            0.05,
        ),
        (
            "era-surface 2011+ q4 share",
            "eras.4.quartile_share_pct.4",
            93.4,
            0.05,
        ),
        (
            "era-surface 2011+ median floor",
            "eras.4.median_gross_floor_m2",
            329.0,
            0.05,
        ),
    ):
        got = _json_path(es, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_era_surface: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 16

    va = _model_output("artifacts/cadastre_vacancy_alignment.json")
    for desc, path, expected, tol in (
        ("vacancy census total dwellings", "city_41091.census_total_dwellings", 327393, 0),
        ("vacancy census empty", "city_41091.census_empty_dwellings", 24621, 0),
        ("vacancy census low consumption", "city_41091.census_low_consumption", 4990, 0),
        ("vacancy census sporadic", "city_41091.census_sporadic_use", 17200, 0),
        ("vacancy upper band", "city_41091.upper_nonoccupied_band", 46811, 0),
        (
            "vacancy cadastre city total",
            "city_41091.cadastre_declared_properties",
            327237,
            0,
        ),
        (
            "vacancy cadastre to census ratio",
            "city_41091.cadastre_to_census_ratio",
            0.999524,
            0.00005,
        ),
        ("vacancy self empty rate", "city_41091.census_self_empty_rate_pct", 7.52, 0.005),
        ("vacancy upper band rate", "city_41091.upper_band_census_rate_pct", 14.3, 0.05),
        ("vacancy joined barrios", "coverage.joined_with_deshabitadas", 100, 0),
        (
            "vacancy denominator spearman",
            "denominator_consistency.spearman_cadastre_props_vs_sim_familiares",
            0.99847,
            0.00005,
        ),
        (
            "vacancy joined cadastre props",
            "denominator_consistency.joined_cadastre_properties",
            315107,
            0,
        ),
        (
            "vacancy joined sim dwellings",
            "denominator_consistency.joined_sim_family_dwellings",
            313398,
            0,
        ),
        (
            "vacancy joined sim unoccupied",
            "denominator_consistency.joined_sim_deshabitadas",
            17977,
            0,
        ),
        (
            "vacancy denominator ratio median",
            "denominator_consistency.denominator_ratio_median",
            1.002395,
            0.0005,
        ),
        ("vacancy sim mean rate", "rates.sim_own_rate_mean_pct", 5.28, 0.005),
        ("vacancy cad mean rate", "rates.cadastre_referenced_rate_mean_pct", 5.33, 0.005),
        (
            "vacancy rate series spearman",
            "rates.spearman_sim_rate_vs_cadastre_rate",
            0.995644,
            0.00005,
        ),
    ):
        got = _json_path(va, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_vacancy: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 18

    ha = _model_output("artifacts/cadastre_household_alignment.json")
    for desc, path, expected, tol in (
        ("households census 2021", "city.census_households_2021", 266703, 0),
        (
            "households cadastre assigned",
            "city.cadastre_properties_barrio_assigned",
            323737,
            0,
        ),
        ("households cadastre full", "city.cadastre_properties_full_extract", 327237, 0),
        ("households sim joined", "city.sim_households_joined", 267970, 0),
        (
            "households props per census hh",
            "city.properties_per_census_household",
            1.227,
            0.0005,
        ),
        (
            "households props per sim hh",
            "city.properties_per_sim_household",
            1.2081,
            0.0005,
        ),
        ("households joined barrios", "coverage.joined", 107, 0),
        ("households sim barrios", "coverage.sim_barrios", 108, 0),
        (
            "households spearman props vs hh",
            "alignment.spearman_properties_vs_households",
            0.985398,
            0.00005,
        ),
        (
            "households median hog per prop",
            "alignment.households_per_property_median",
            0.8278,
            0.0005,
        ),
        (
            "households min hog per prop",
            "alignment.households_per_property_min",
            0.5769,
            0.0005,
        ),
        (
            "households max hog per prop",
            "alignment.households_per_property_max",
            1.257,
            0.0005,
        ),
    ):
        got = _json_path(ha, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_households: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 12

    cc = _model_output("artifacts/cadastre_capitals.json")
    for desc, path, expected, tol in (
        ("capitals malaga props", "cities.29067.total_properties", 261269, 0),
        ("capitals granada props", "cities.18087.total_properties", 140818, 0),
        ("capitals cordoba props", "cities.14021.total_properties", 158873, 0),
        ("capitals sevilla props", "cities.41091.total_properties", 327237, 0),
        ("capitals malaga records", "cities.29067.n_records", 40231, 0),
        ("capitals granada records", "cities.18087.n_records", 18149, 0),
        ("capitals cordoba records", "cities.14021.n_records", 32852, 0),
        ("capitals malaga median year", "cities.29067.median_year_property_weighted", 1979, 0),
        ("capitals granada median year", "cities.18087.median_year_property_weighted", 1977, 0),
        ("capitals cordoba median year", "cities.14021.median_year_property_weighted", 1980, 0),
        ("capitals sevilla median year", "cities.41091.median_year_property_weighted", 1976, 0),
        ("capitals malaga peak share", "cities.29067.era_share_pct.1971-1990", 39.5, 0.05),
        ("capitals granada peak share", "cities.18087.era_share_pct.1971-1990", 42.1, 0.05),
        ("capitals cordoba peak share", "cities.14021.era_share_pct.1971-1990", 34.7, 0.05),
        ("capitals sevilla peak share", "cities.41091.era_share_pct.1971-1990", 37.9, 0.05),
        ("capitals cordoba 2011+ share", "cities.14021.era_share_pct.2011+", 6.8, 0.05),
    ):
        got = _json_path(cc, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_capitals: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 16

    pi = _model_output("artifacts/province_inventory.json")
    for desc, path, expected, tol in (
        ("province municipalities", "n_municipalities", 106, 0),
        ("province total bytes", "total_archive_bytes", 266942849, 0),
        ("province sevilla bytes", "municipalities.0.archive_bytes", 35431544, 0),
        ("province dos hermanas bytes", "municipalities.1.archive_bytes", 14912472, 0),
    ):
        got = _json_path(pi, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] province_inventory: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 4

    cp = _model_output("artifacts/cadastre_province.json")
    for desc, path, expected, tol in (
        ("province-db municipalities", "province.n_municipalities", 106, 0),
        ("province-db housing records", "province.total_records", 415518, 0),
        ("province-db properties", "province.total_properties", 891374, 0),
        ("province-db sevilla share", "province.sevilla_city_property_share_pct", 36.7, 0.05),
        ("province-db rest median year", "province.rest_median_of_median_years", 1986, 0),
        ("province-db pre-1951 share", "province.era_share_pct.Pre-1951", 7.8, 0.05),
        ("province-db 1951-1970 share", "province.era_share_pct.1951-1970", 20.2, 0.05),
        ("province-db 1971-1990 share", "province.era_share_pct.1971-1990", 31.0, 0.05),
        ("province-db 1991-2010 share", "province.era_share_pct.1991-2010", 35.6, 0.05),
        ("province-db 2011+ share", "province.era_share_pct.2011+", 5.3, 0.05),
        (
            "province-db castillo pph",
            "municipalities.41031.properties_per_household",
            2.8161,
            0.0005,
        ),
    ):
        got = _json_path(cp, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] cadastre_province: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 11

    mb = _model_output("artifacts/cadastre_malaga_barrios.json")
    for desc, path, expected, tol in (
        ("malaga barrios joined", "global.n_barrios", 360, 0),
        ("malaga barrios properties", "global.total_properties", 261073, 0),
        ("malaga barrios dated", "global.dated_properties", 261066, 0),
        ("malaga barrios pre-1951", "global.era_pct.Pre-1951", 4.2, 0.05),
        ("malaga barrios 1951-1970", "global.era_pct.1951-1970", 22.6, 0.05),
        ("malaga barrios 1971-1990", "global.era_pct.1971-1990", 39.5, 0.05),
        ("malaga barrios 1991-2010", "global.era_pct.1991-2010", 28.5, 0.05),
        ("malaga barrios 2011+", "global.era_pct.2011+", 5.2, 0.05),
    ):
        got = _json_path(mb, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] malaga_barrios: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 8

    gd = _model_output("artifacts/cadastre_granada_distritos.json")
    for desc, path, expected, tol in (
        ("granada districts joined", "global.n_barrios", 8, 0),
        ("granada districts properties", "global.total_properties", 140817, 0),
        ("granada districts dated", "global.dated_properties", 140785, 0),
        ("granada districts pre-1951", "global.era_pct.Pre-1951", 6.5, 0.05),
        ("granada districts 1951-1970", "global.era_pct.1951-1970", 24.5, 0.05),
        ("granada districts 1971-1990", "global.era_pct.1971-1990", 42.1, 0.05),
        ("granada districts 1991-2010", "global.era_pct.1991-2010", 23.0, 0.05),
        ("granada districts 2011+", "global.era_pct.2011+", 3.9, 0.05),
        ("granada albayzin median", "barrios.18087-ALBAYZIN.median_year", 1960, 0),
        ("granada albayzin pre-1951", "barrios.18087-ALBAYZIN.Pre-1951", 46.7, 0.05),
        ("granada centro pre-1951", "barrios.18087-CENTRO.Pre-1951", 30.0, 0.05),
    ):
        got = _json_path(gd, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] granada_distritos: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 11

    cv = _model_output("artifacts/censo_vintage.json")
    for desc, path, expected, tol in (
        ("censo vintage total viviendas", "nacional_total.viviendas_total", 26623708, 0),
        ("censo vintage principal", "nacional_total.viviendas_principal", 18536616, 0),
        ("censo vintage no principal", "nacional_total.viviendas_no_principal", 8087092, 0),
        ("censo vintage pct no principal", "nacional_total.pct_no_principal", 30.4, 0.05),
        ("censo vintage boom 2001-2010", "boom_vs_postboom.boom_2001_2010", 5240772, 0),
        ("censo vintage post-boom 2011-20", "boom_vs_postboom.post_boom_2011_2020", 734659, 0),
        ("censo vintage ratio boom post", "boom_vs_postboom.ratio_boom_to_post", 7.13, 0.05),
        ("censo vintage avila boom", "boom_by_province.05.pct_no_principal", 52.0, 0.05),
        ("censo vintage castellon boom", "boom_by_province.12.pct_no_principal", 49.2, 0.05),
        ("censo vintage alicante boom", "boom_by_province.03.pct_no_principal", 44.1, 0.05),
        ("censo vintage madrid boom", "boom_by_province.28.pct_no_principal", 14.7, 0.05),
        ("censo vintage barcelona boom", "boom_by_province.08.pct_no_principal", 13.8, 0.05),
        ("censo vintage bizkaia boom", "boom_by_province.48.pct_no_principal", 10.7, 0.05),
        ("censo vintage avila total", "total_by_province.05.pct_no_principal", 59.4, 0.05),
        ("censo vintage madrid total", "total_by_province.28.pct_no_principal", 13.9, 0.05),
    ):
        got = _json_path(cv, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] censo_vintage: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 15

    ratio = _model_output("artifacts/ratio_ccaa.json")
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
        ("vacancy CLM pct", "vacancy_2021.by_ccaa_pct.Castilla - La Mancha", 22.51, 0.05),
        ("vacancy Extremadura pct", "vacancy_2021.by_ccaa_pct.Extremadura", 17.61, 0.05),
        ("vacancy PV pct", "vacancy_2021.by_ccaa_pct.País Vasco", 6.48, 0.05),
        ("vacancy Cataluna pct", "vacancy_2021.by_ccaa_pct.Cataluña", 10.67, 0.05),
        ("Balears d_07_25", "ccaa.Balears, Illes.d_07_25", -13.3, 0.1),
        ("Canarias d_07_25", "ccaa.Canarias.d_07_25", -1.2, 0.1),
        ("Galicia d_07_25", "ccaa.Galicia.d_07_25", 107.4, 0.1),
        ("Pais Vasco d_07_25", "ccaa.País Vasco.d_07_25", 36.2, 0.1),
        ("Aragon d_07_25", "ccaa.Aragón.d_07_25", 59.3, 0.1),
        ("Rioja d_07_25", "ccaa.Rioja, La.d_07_25", 64.8, 0.1),
        ("CLM d_07_25", "ccaa.Castilla - La Mancha.d_07_25", 65.5, 0.1),
        ("Cantabria d_07_25", "ccaa.Cantabria.d_07_25", 69.7, 0.1),
        ("median real price scarcity", "groups.median_real_price.scarcity", -8.6, 0.1),
        ("median real price overstock", "groups.median_real_price.overstock", -23.6, 0.1),
        ("Extremadura r25", "ccaa.Extremadura.r25", 671.3, 0.05),
        ("CLM r25", "ccaa.Castilla - La Mancha.r25", 642.7, 0.05),
    ):
        got = _json_path(ratio, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] ratio_ccaa: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 36
    serp = _model_output("artifacts/serpavi_analysis.json")
    for desc, path, expected, tol in (
        ("diba-serpavi pearson", "rent_cross_diba_2023.pearson", 0.825, 0.005),
        ("diba-serpavi spearman", "rent_cross_diba_2023.spearman", 0.866, 0.005),
        ("diba-serpavi n", "rent_cross_diba_2023.n", 202, 0),
        ("bcn yield pct", "gross_yield_bcn_2023.barcelona.yield_pct", 3.61, 0.02),
        ("yield median", "gross_yield_bcn_2023.stats.median", 4.58, 0.02),
        ("rent-vac pearson", "rent_vs_vacancy_2023.pearson", -0.429, 0.005),
        ("rent-vac spearman", "rent_vs_vacancy_2023.spearman", -0.507, 0.005),
        ("rent-vac n", "rent_vs_vacancy_2023.n", 2237, 0),
        ("serpavi munis 2024 rent", "coverage.serpavi_munis_2024_rent", 2555, 0),
        ("yield p25", "gross_yield_bcn_2023.stats.p25", 4.11, 0.02),
        ("yield p75", "gross_yield_bcn_2023.stats.p75", 5.23, 0.02),
        ("bcn sale level", "gross_yield_bcn_2023.barcelona.sale", 4370.96, 0.05),
        ("bcn rent_m2 level", "gross_yield_bcn_2023.barcelona.rent_m2", 13.14, 0.02),
    ):
        got = _json_path(serp, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] serpavi: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 13
    tr = _model_output("artifacts/tourist_rents.json")
    for desc, path, expected, tol in (
        (
            "bcn tour-rent level pearson",
            "bcn_municipal.corr_tour_vs_rent_level.pearson",
            0.157,
            0.005,
        ),
        (
            "bcn tour-rent level spearman",
            "bcn_municipal.corr_tour_vs_rent_level.spearman",
            0.085,
            0.005,
        ),
        (
            "bcn tour-rent growth pearson",
            "bcn_municipal.corr_tour_vs_rent_growth.pearson",
            0.0,
            0.005,
        ),
        (
            "bcn tour-rent growth spearman",
            "bcn_municipal.corr_tour_vs_rent_growth.spearman",
            0.169,
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
            0.525,
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
            0.304,
            0.005,
        ),
        ("tourist-rents n prov", "provincial.n", 45, 0),
        ("tourist-rents n bcn", "bcn_municipal.n", 199, 0),
        ("Tenerife rent growth", "provincial.top_tourist", 27.95, 0.01),
        ("Balears rent growth", "provincial.top_tourist.1.rent_growth_pct", 22.96, 0.01),
        ("Girona rent growth", "provincial.top_tourist.0.rent_growth_pct", 18.73, 0.01),
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
    total += 13
    mv = _model_output("artifacts/madrid_vacancy_terrain.json")
    for desc, path, expected, tol in (
        ("named both n", "n_named_both", 135, 0),
        ("constraint max", "constraint_max", 0.8263, 0.005),
        ("vacancy max", "vacancy_max", 38.52, 0.05),
        ("vacancy min", "vacancy_min", 2.67, 0.05),
        ("corr pearson", "pearson", 0.375, 0.005),
        ("corr spearman", "spearman", 0.557, 0.005),
        ("steep in table", "steep_villages_in_table", 0, 0),
    ):
        got = _json_path(mv, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] madrid_vacancy: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 7
    mn = _model_output("artifacts/municipios_nacional.json")
    for desc, path, expected, tol in (
        ("rent median 2024", "rent_geo_2024.median", 5.22, 0.02),
        ("rent p25", "rent_geo_2024.p25", 3.97, 0.02),
        ("rent p75", "rent_geo_2024.p75", 6.77, 0.02),
        ("rent n 2024", "rent_geo_2024.n", 2515, 0),
        ("rent max level", "rent_geo_2024.max.rent", 14.63, 0.02),
        ("rent min level", "rent_geo_2024.min.rent", 1.84, 0.02),
        ("growth n", "rent_growth_2011_2024.n", 1678, 0),
        ("growth median pct", "rent_growth_2011_2024.median_pct", 29.0, 0.1),
        ("fastest growth pct", "rent_growth_2011_2024.fastest.growth_pct", 223.4, 0.1),
        ("rent-vac pearson", "rent_vs_vacancy.pearson", -0.393, 0.005),
        ("rent-vac spearman", "rent_vs_vacancy.spearman", -0.434, 0.005),
        ("rent-vac n", "rent_vs_vacancy.n", 1927, 0),
        ("pop-rent pearson", "pop_vs_rent_growth.pearson", 0.051, 0.005),
        ("pop-rent spearman", "pop_vs_rent_growth.spearman", 0.115, 0.005),
        ("pop-rent n", "pop_vs_rent_growth.n", 1678, 0),
        ("coverage municipios", "coverage.municipios", 8136, 0),
    ):
        got = _json_path(mn, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] municipios_nacional: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 16
    by_ = _model_output("artifacts/barrios_bcn_yield.json")
    for desc, path, expected, tol in (
        ("yield n 2024", "n", 71, 0),
        ("yield median", "median_yield", 4.51, 0.02),
        ("yield top pct", "top.yield_pct", 7.71, 0.02),
        ("yield bottom pct", "bottom.yield_pct", 2.02, 0.02),
        ("rent-vs-sale pearson", "rent_vs_sale_pearson", 0.754, 0.005),
        ("yield median 2023 (peak)", "by_year.2023.median_yield", 4.71, 0.02),
        ("yield median 2018", "by_year.2018.median_yield", 4.15, 0.02),
    ):
        got = _json_path(by_, path)
        if isinstance(expected, str):
            ok = got == expected
        else:
            ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] barrios_bcn_yield: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 7
    dr = _model_output("artifacts/desahucios_renta.json")
    for desc, path, expected, tol in (
        ("lau-rent n", "n", 50, 0),
        ("lau-rent pearson", "pearson", 0.28, 0.005),
        ("lau-rent spearman", "spearman", 0.359, 0.005),
        ("lau top rate", "top.lau_per_100k", 95.6, 0.1),
        ("lau bottom rate", "bottom.lau_per_100k", 13.1, 0.1),
        ("lau national rate", "national_lau_per_100k", 42.4, 0.1),
    ):
        got = _json_path(dr, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] desahucios_renta: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 6

    pp = _model_output("artifacts/panel_provincial.json")
    for desc, path, expected, tol in (
        ("prov panel S0 absor b", "s0_absorption_only.coefs.absor.b", -0.024, 0.005),
        ("prov panel S0 absor se", "s0_absorption_only.coefs.absor.se", 0.008, 0.005),
        ("prov panel S0 wild-p", "s0_absorption_only.coefs.absor.wild_p", 0.194, 0.01),
        ("prov panel S0 n", "s0_absorption_only.n", 777, 0),
        ("prov panel S1 absor b", "s1_with_controls.coefs.absor.b", -0.012, 0.01),
        ("prov panel S1 absor se", "s1_with_controls.coefs.absor.se", 0.137, 0.005),
        ("prov panel S1 wild-p", "s1_with_controls.coefs.absor.wild_p", 0.972, 0.005),
        ("prov panel S1 n", "s1_with_controls.n", 178, 0),
        ("prov panel window max", "window.max", 2025, 0),
        ("prov panel n provinces", "window.n_provinces", 50, 0),
    ):
        got = _json_path(pp, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] panel_provincial: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 10
    pq = _model_output("artifacts/panel_quarterly.json")
    for desc, path, expected, tol in (
        ("quarterly n", "n", 1156, 0),
        ("h b", "coefs.h.b", -0.048, 0.001),
        ("h wild-p", "wild_bootstrap.h.p", 0.429, 0.005),
        ("L1 b", "coefs.L1h.b", -0.014, 0.001),
        ("L1 wild-p", "wild_bootstrap.L1h.p", 0.792, 0.005),
        ("L2 b", "coefs.L2h.b", -0.063, 0.001),
        ("L2 wild-p", "wild_bootstrap.L2h.p", 0.108, 0.005),
        ("L3 b", "coefs.L3h.b", 0.071, 0.001),
        ("L3 wild-p", "wild_bootstrap.L3h.p", 0.057, 0.005),
        ("L4 b", "coefs.L4h.b", -0.006, 0.001),
        ("L4 wild-p", "wild_bootstrap.L4h.p", 0.885, 0.005),
        ("L5 b", "coefs.L5h.b", 0.055, 0.001),
        ("L5 wild-p", "wild_bootstrap.L5h.p", 0.272, 0.005),
        ("L6 b", "coefs.L6h.b", 0.025, 0.001),
        ("L6 wild-p", "wild_bootstrap.L6h.p", 0.513, 0.005),
        ("L7 b", "coefs.L7h.b", -0.127, 0.001),
        ("L7 wild-p", "wild_bootstrap.L7h.p", 0.005, 0.005),
        ("L8 b", "coefs.L8h.b", -0.065, 0.001),
        ("L8 wild-p", "wild_bootstrap.L8h.p", 0.064, 0.005),
        ("dr b", "coefs.dr.b", 1.001, 0.001),
        ("dr wild-p", "wild_bootstrap.dr.p", 0.018, 0.005),
        ("L1dr b", "coefs.L1dr.b", 0.595, 0.001),
        ("L1dr wild-p", "wild_bootstrap.L1dr.p", 0.059, 0.005),
    ):
        got = _json_path(pq, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] panel_quarterly: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 23
    wb = _model_output("artifacts/wild_ar_bust.json")
    for desc, path, expected, tol in (
        ("wild-AR bust set lower", "set.0", 0.25, 0.001),
        ("wild-AR bust set upper", "set.1", 1.0, 0.001),
        ("wild-AR reps", "reps", 299, 0),
        ("wild-AR seed", "seed", 20261007, 0),
    ):
        got = _json_path(wb, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] wild_ar_bust: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 4
    pt = _model_output("artifacts/panel_tourist.json")
    for desc, path, expected, tol in (
        ("sale wild-p", "sale_tour_only.wild_bootstrap.d_tour.p", 0.494, 0.005),
        ("sale+pop wild-p", "sale_with_pop.wild_bootstrap.d_tour.p", 0.561, 0.005),
        ("rent wild-p", "rent_tour_only.wild_bootstrap.d_tour.p", 0.9605, 0.005),
        ("rent+pop wild-p", "rent_with_pop.wild_bootstrap.d_tour.p", 0.9615, 0.005),
    ):
        got = _json_path(pt, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] panel_tourist: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 4
    for desc, path, expected, tol in (
        ("sale b", "sale_tour_only.coefs.d_tour.b", -0.2107, 0.001),
        ("sale n", "sale_tour_only.n", 1159, 0),
        ("sale+pop b", "sale_with_pop.coefs.d_tour.b", -0.1818, 0.001),
        ("sale+pop n", "sale_with_pop.n", 1159, 0),
        ("rent b", "rent_tour_only.coefs.d_tour.b", 0.0091, 0.001),
        ("rent n", "rent_tour_only.n", 2109, 0),
        ("rent+pop b", "rent_with_pop.coefs.d_tour.b", 0.0125, 0.001),
        ("rent+pop n", "rent_with_pop.n", 2109, 0),
        ("sale SE", "sale_tour_only.coefs.d_tour.se", 0.3092, 0.0001),
        ("sale normal CI lower", "sale_tour_only.coefs.d_tour.ci95.0", -0.8168, 0.0001),
        ("sale normal CI upper", "sale_tour_only.coefs.d_tour.ci95.1", 0.3955, 0.0001),
        ("sale+pop SE", "sale_with_pop.coefs.d_tour.se", 0.3138, 0.0001),
        ("sale+pop normal CI lower", "sale_with_pop.coefs.d_tour.ci95.0", -0.7968, 0.0001),
        ("sale+pop normal CI upper", "sale_with_pop.coefs.d_tour.ci95.1", 0.4332, 0.0001),
        ("rent SE", "rent_tour_only.coefs.d_tour.se", 0.2302, 0.0001),
        ("rent normal CI lower", "rent_tour_only.coefs.d_tour.ci95.0", -0.442, 0.0001),
        ("rent normal CI upper", "rent_tour_only.coefs.d_tour.ci95.1", 0.4602, 0.0001),
        ("rent+pop SE", "rent_with_pop.coefs.d_tour.se", 0.2332, 0.0001),
        ("rent+pop normal CI lower", "rent_with_pop.coefs.d_tour.ci95.0", -0.4445, 0.0001),
        ("rent+pop normal CI upper", "rent_with_pop.coefs.d_tour.ci95.1", 0.4695, 0.0001),
        ("sale clusters", "sale_tour_only.clusters", 130, 0),
        ("rent clusters", "rent_tour_only.clusters", 253, 0),
    ):
        got = _json_path(pt, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] panel_tourist: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 22
    inv = _model_output("artifacts/tourist_inversion.json")
    for desc, path, expected, tol in (
        ("inversion grid length", "grid", 41, 0),
        ("inversion grid lo", "grid.0", -2.0, 0.0001),
        ("inversion grid hi", "grid.40", 2.0, 0.0001),
        ("inversion reps", "reps", 1999, 0),
        ("inversion seed", "seed", 20261006, 0),
        ("inversion alpha", "alpha", 0.05, 0.0001),
        ("inversion sale c0 p", "models.sale_tour_only.p.20", 0.494, 0.0005),
        ("inversion rent c0 p", "models.rent_tour_only.p.20", 0.9605, 0.0005),
        ("inversion sale accepted lo", "models.sale_tour_only.keep.10", True, 0),
        ("inversion sale accepted hi", "models.sale_tour_only.keep.27", True, 0),
        ("inversion sale rejected", "models.sale_tour_only.keep.28", False, 0),
        ("inversion sale+pop accepted lo", "models.sale_with_pop.keep.10", True, 0),
        ("inversion sale+pop accepted hi", "models.sale_with_pop.keep.27", True, 0),
        ("inversion rent accepted lo", "models.rent_tour_only.keep.16", True, 0),
        ("inversion rent accepted hi", "models.rent_tour_only.keep.25", True, 0),
        ("inversion rent rejected lo", "models.rent_tour_only.keep.15", False, 0),
        ("inversion rent rejected hi", "models.rent_tour_only.keep.26", False, 0),
        ("inversion rent+pop accepted lo", "models.rent_with_pop.keep.16", True, 0),
        ("inversion rent+pop accepted hi", "models.rent_with_pop.keep.25", True, 0),
        ("inversion sale warnings count", "models.sale_tour_only.warnings", 0, 0),
        ("inversion sale+pop warnings count", "models.sale_with_pop.warnings", 0, 0),
        ("inversion rent warnings count", "models.rent_tour_only.warnings", 0, 0),
        ("inversion rent+pop warnings count", "models.rent_with_pop.warnings", 0, 0),
    ):
        got = _json_path(inv, path)
        if isinstance(got, list):
            got = len(got)
        ok = got is not None and (got == expected or abs(got - expected) <= tol)
        print(f"[{'OK' if ok else 'FAIL'}] tourist_inversion: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 23
    h1 = _model_output("artifacts/hypothesis_01.json")
    for desc, path, expected, tol in (
        ("pooled spearman ccaa", "pooled.ccaa.spearman", -0.406, 0.005),
        ("pooled spearman prov", "pooled.prov.spearman", -0.381, 0.005),
        ("pooled n prov", "pooled.prov.n", 153, 0),
        ("prov 21-25 spearman", "prov_windows.2021-2025.spearman", -0.421, 0.005),
        ("prov 21-25 ci lo", "prov_windows.2021-2025.spearman_ci95.0", -0.64, 0.01),
        ("prov 21-25 ci hi", "prov_windows.2021-2025.spearman_ci95.1", -0.14, 0.01),
    ):
        got = _json_path(h1, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] hypothesis_01: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 6

    pa = _model_output("artifacts/panel_adjusted.json")
    for desc, path, expected, tol in (
        ("S0 absor b", "s0_absorption_only.coefs.absor.b", -0.141, 0.001),
        ("S0 absor wild-p", "s0_absorption_only.wild_bootstrap.absor.p", 0.0823, 0.002),
        ("S0 n", "s0_absorption_only.n", 194, 0),
        ("S1 absor b", "s1_with_demand_controls.coefs.absor.b", -0.112, 0.001),
        ("S1 absor wild-p", "s1_with_demand_controls.wild_bootstrap.absor.p", 0.1163, 0.002),
        ("S1 d_hip b", "s1_with_demand_controls.coefs.d_hip.b", 0.033, 0.001),
        ("S1 d_hip wild-p", "s1_with_demand_controls.wild_bootstrap.d_hip.p", 0.2637, 0.002),
        ("S1 d_renta b", "s1_with_demand_controls.coefs.d_renta.b", 0.003, 0.001),
        ("S1 d_renta wild-p", "s1_with_demand_controls.wild_bootstrap.d_renta.p", 0.9347, 0.002),
        ("S1 d_coh b", "s1_with_demand_controls.coefs.d_coh.b", 3.392, 0.001),
        ("S1 d_coh wild-p", "s1_with_demand_controls.wild_bootstrap.d_coh.p", 0.068, 0.002),
        ("S1 n", "s1_with_demand_controls.n", 178, 0),
        ("S2 absor b", "s2_with_lags.coefs.absor.b", -0.051, 0.001),
        ("S2 absor wild-p", "s2_with_lags.wild_bootstrap.absor.p", 0.151, 0.002),
        ("S2 d_hip b", "s2_with_lags.coefs.d_hip.b", 0.021, 0.001),
        ("S2 d_hip wild-p", "s2_with_lags.wild_bootstrap.d_hip.p", 0.5513, 0.002),
        ("S2 d_renta b", "s2_with_lags.coefs.d_renta.b", 0.039, 0.001),
        ("S2 d_renta wild-p", "s2_with_lags.wild_bootstrap.d_renta.p", 0.4643, 0.002),
        ("S2 d_coh b", "s2_with_lags.coefs.d_coh.b", 2.168, 0.001),
        ("S2 d_coh wild-p", "s2_with_lags.wild_bootstrap.d_coh.p", 0.3707, 0.002),
        ("S2 L_absor b", "s2_with_lags.coefs.L_absor.b", -0.162, 0.001),
        ("S2 L_absor wild-p", "s2_with_lags.wild_bootstrap.L_absor.p", 0.04, 0.002),
        ("S2 L_d_hip b", "s2_with_lags.coefs.L_d_hip.b", -0.003, 0.001),
        ("S2 L_d_hip wild-p", "s2_with_lags.wild_bootstrap.L_d_hip.p", 0.8593, 0.002),
        ("S2 L_d_renta b", "s2_with_lags.coefs.L_d_renta.b", -0.09, 0.001),
        ("S2 L_d_renta wild-p", "s2_with_lags.wild_bootstrap.L_d_renta.p", 0.259, 0.002),
        ("S2 n", "s2_with_lags.n", 133, 0),
        ("S3 absor b", "s3_with_migration.coefs.absor.b", -0.114, 0.001),
        ("S3 absor wild-p", "s3_with_migration.wild_bootstrap.absor.p", 0.095, 0.002),
        ("S3 d_hip b", "s3_with_migration.coefs.d_hip.b", 0.014, 0.001),
        ("S3 d_hip wild-p", "s3_with_migration.wild_bootstrap.d_hip.p", 0.6977, 0.002),
        ("S3 d_renta b", "s3_with_migration.coefs.d_renta.b", 0.015, 0.001),
        ("S3 d_renta wild-p", "s3_with_migration.wild_bootstrap.d_renta.p", 0.7843, 0.002),
        ("S3 d_coh b", "s3_with_migration.coefs.d_coh.b", 3.46, 0.001),
        ("S3 d_coh wild-p", "s3_with_migration.wild_bootstrap.d_coh.p", 0.1157, 0.002),
        ("S3 d_inmig b", "s3_with_migration.coefs.d_inmig.b", 0.005, 0.001),
        ("S3 d_inmig wild-p", "s3_with_migration.wild_bootstrap.d_inmig.p", 0.8927, 0.002),
        ("S3 n", "s3_with_migration.n", 119, 0),
    ):
        got = _json_path(pa, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] panel_adjusted: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 38
    print(f"{total - failures}/{total} claims hold")
    fresh_failures = check_freshness()
    total += len(MODEL_FRESHNESS)
    print(f"{len(MODEL_FRESHNESS) - fresh_failures}/{len(MODEL_FRESHNESS)} model outputs fresh")
    return 1 if (failures or fresh_failures) else 0


if __name__ == "__main__":
    sys.exit(main())
