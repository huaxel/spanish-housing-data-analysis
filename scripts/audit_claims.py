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
from spanish_housing.data_paths import PROCESSED, RAW  # noqa: E402

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
    (
        "deficit_vivienda",
        "artifacts/deficit_vivienda.json",
        "explorations/deficit_vivienda.py",
    ),
    # Policy evaluation + distributional microsimulation + claim ledger
    # (added 2026-11-27). The ledger hashes its upstream artifacts, so it
    # fails whenever catalonia/panel_tourist/tourist_rents moved under it.
    (
        "catalonia_rent_control",
        "artifacts/catalonia_rent_control.json",
        "explorations/catalonia_rent_control.py",
    ),
    (
        "ecv_microsim",
        "artifacts/ecv_microsim.json",
        "scripts/build_ecv_microsim.py",
    ),
    (
        "claim_ledger",
        "artifacts/claim_ledger.json",
        "scripts/build_claim_ledger.py",
    ),
    # INE statutory rent-update reference (IRAV), added 2026-11-27. Keyed to
    # the pinned monthly series, so a new INE release invalidates the pins.
    (
        "irav_index",
        "artifacts/irav.json",
        "scripts/build_irav_index.py",
    ),
    # IPVA vs SERPAVI municipal cross-check, added 2026-11-27.
    (
        "ipva_rent_index",
        "artifacts/ipva_rent_index.json",
        "explorations/ipva_rent_index.py",
    ),
    # INE household projection paired with the stock marts, added 2026-11-27.
    (
        "proh_households",
        "artifacts/proh_households.json",
        "explorations/proh_households.py",
    ),
    ("ecp_households", "artifacts/ecp_households.json", "explorations/ecp_households.py"),
    # Official tourist-dwelling stock (INE VTE municipal), added 2026-11-27.
    (
        "vut_stock",
        "artifacts/vut_stock.json",
        "explorations/vut_stock.py",
    ),
    (
        "vut_rent_overlap",
        "artifacts/vut_rent_overlap.json",
        "explorations/vut_rent_overlap.py",
    ),
    (
        "occupancy_catalonia",
        "artifacts/occupancy_catalonia.json",
        "explorations/occupancy_catalonia.py",
    ),
    (
        "serpavi_deposit_contrast",
        "artifacts/serpavi_deposit_contrast.json",
        "explorations/serpavi_deposit_contrast.py",
    ),
    (
        "vut_seasonal_deposits",
        "artifacts/vut_seasonal_deposits.json",
        "explorations/vut_seasonal_deposits.py",
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


def _ecp_households_sql(year: int) -> str:
    source = str(RAW / "parquet/ecp_hog_ccaa.parquet").replace("'", "''")
    return (
        f"(SELECT hogares FROM read_parquet('{source}') "
        f"WHERE territorio='Total Nacional' AND tamano='Total' AND anyo={year})"
    )


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


# SERPAVI published band, pivoted once: median/P25/P75 for vivienda colectiva in
# EUR/m2 and EUR/month, vivienda unifamiliar in EUR/m2, plus the surface median.
# Each measure is sparse, so MAX-over-CASE keeps the municipio-year grain.
_SERPAVI_BAND = (
    "(SELECT codigo, anyo,"
    " MAX(CASE WHEN medida='ALQM2_LV_M_VC' THEN valor END) m2_vc,"
    " MAX(CASE WHEN medida='ALQM2_LV_25_VC' THEN valor END) lo_vc,"
    " MAX(CASE WHEN medida='ALQM2_LV_75_VC' THEN valor END) hi_vc,"
    " MAX(CASE WHEN medida='ALQM2_LV_M_VU' THEN valor END) m2_vu,"
    " MAX(CASE WHEN medida='ALQM2_LV_25_VU' THEN valor END) lo_vu,"
    " MAX(CASE WHEN medida='ALQM2_LV_75_VU' THEN valor END) hi_vu,"
    " MAX(CASE WHEN medida='ALQTBID12_M_VC' THEN valor END) mo_vc,"
    " MAX(CASE WHEN medida='ALQTBID12_25_VC' THEN valor END) mo_lo_vc,"
    " MAX(CASE WHEN medida='ALQTBID12_75_VC' THEN valor END) mo_hi_vc,"
    " MAX(CASE WHEN medida='SLVM2_M_VC' THEN valor END) sf_vc"
    " FROM serpavi_municipal GROUP BY 1,2) b"
)
_VC_BAND_2024 = (
    f"FROM {_SERPAVI_BAND} WHERE anyo=2024 AND m2_vc>0 AND lo_vc IS NOT NULL AND hi_vc IS NOT NULL"
)


CLAIMS: list[tuple[str, str, str, float, float]] = [
    (
        "deficit",
        "national ECP households 1-Jan-2026",
        f"SELECT {_ecp_households_sql(2026)}",
        19_761_683,
        0,
    ),
    (
        "deficit",
        "national net household growth during calendar 2025",
        f"SELECT {_ecp_households_sql(2026)} - {_ecp_households_sql(2025)}",
        240_932,
        0,
    ),
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
        2512.0,
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
        "occupancy_barcelona_mediation",
        "Barcelona INCASÒL city contracts 2017",
        "SELECT contractes FROM barrios_bcn_lloguer_anual WHERE codi='BCN' AND anyo=2017",
        49953,
        0,
    ),
    (
        "occupancy_barcelona_mediation",
        "Barcelona INCASÒL city contracts 2025",
        "SELECT contractes FROM barrios_bcn_lloguer_anual WHERE codi='BCN' AND anyo=2025",
        30789,
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
        "occupancy_province_pilot",
        "03 2024 change in total stock",
        "SELECT b.viviendas_total - a.viviendas_total "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '03' AND a.anyo = 2023 AND b.anyo = 2024",
        6000,
        0,
    ),
    (
        "occupancy_province_pilot",
        "03 2024 change in primary stock",
        "SELECT b.viviendas_principales - a.viviendas_principales "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '03' AND a.anyo = 2023 AND b.anyo = 2024",
        -7343,
        0,
    ),
    (
        "occupancy_province_pilot",
        "03 2025 change in primary stock",
        "SELECT b.viviendas_principales - a.viviendas_principales "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '03' AND a.anyo = 2024 AND b.anyo = 2025",
        30433,
        0,
    ),
    (
        "occupancy_province_pilot",
        "03 2024 change in IRPF at owners disposal",
        "SELECT b.n_disposicion - a.n_disposicion "
        "FROM aeat_viviendas_uso a JOIN aeat_viviendas_uso b USING (cpro) "
        "WHERE cpro = '03' AND a.anyo = 2023 AND b.anyo = 2024",
        1374,
        0,
    ),
    (
        "occupancy_province_pilot",
        "08 2024 change in total stock",
        "SELECT b.viviendas_total - a.viviendas_total "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '08' AND a.anyo = 2023 AND b.anyo = 2024",
        10448,
        0,
    ),
    (
        "occupancy_province_pilot",
        "08 2024 change in primary stock",
        "SELECT b.viviendas_principales - a.viviendas_principales "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '08' AND a.anyo = 2023 AND b.anyo = 2024",
        -9209,
        0,
    ),
    (
        "occupancy_province_pilot",
        "08 2025 change in primary stock",
        "SELECT b.viviendas_principales - a.viviendas_principales "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '08' AND a.anyo = 2024 AND b.anyo = 2025",
        14985,
        0,
    ),
    (
        "occupancy_province_pilot",
        "08 2024 change in IRPF at owners disposal",
        "SELECT b.n_disposicion - a.n_disposicion "
        "FROM aeat_viviendas_uso a JOIN aeat_viviendas_uso b USING (cpro) "
        "WHERE cpro = '08' AND a.anyo = 2023 AND b.anyo = 2024",
        994,
        0,
    ),
    (
        "occupancy_province_pilot",
        "28 2024 change in total stock",
        "SELECT b.viviendas_total - a.viviendas_total "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '28' AND a.anyo = 2023 AND b.anyo = 2024",
        20608,
        0,
    ),
    (
        "occupancy_province_pilot",
        "28 2024 change in primary stock",
        "SELECT b.viviendas_principales - a.viviendas_principales "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '28' AND a.anyo = 2023 AND b.anyo = 2024",
        29457,
        0,
    ),
    (
        "occupancy_province_pilot",
        "28 2025 change in primary stock",
        "SELECT b.viviendas_principales - a.viviendas_principales "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '28' AND a.anyo = 2024 AND b.anyo = 2025",
        41660,
        0,
    ),
    (
        "occupancy_province_pilot",
        "28 2024 change in IRPF at owners disposal",
        "SELECT b.n_disposicion - a.n_disposicion "
        "FROM aeat_viviendas_uso a JOIN aeat_viviendas_uso b USING (cpro) "
        "WHERE cpro = '28' AND a.anyo = 2023 AND b.anyo = 2024",
        2224,
        0,
    ),
    (
        "occupancy_province_pilot",
        "46 2024 change in total stock",
        "SELECT b.viviendas_total - a.viviendas_total "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '46' AND a.anyo = 2023 AND b.anyo = 2024",
        4300,
        0,
    ),
    (
        "occupancy_province_pilot",
        "46 2024 change in primary stock",
        "SELECT b.viviendas_principales - a.viviendas_principales "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '46' AND a.anyo = 2023 AND b.anyo = 2024",
        40529,
        0,
    ),
    (
        "occupancy_province_pilot",
        "46 2025 change in primary stock",
        "SELECT b.viviendas_principales - a.viviendas_principales "
        "FROM mart_provincia_anual a JOIN mart_provincia_anual b USING (cpro) "
        "WHERE cpro = '46' AND a.anyo = 2024 AND b.anyo = 2025",
        10185,
        0,
    ),
    (
        "occupancy_province_pilot",
        "46 2024 change in IRPF at owners disposal",
        "SELECT b.n_disposicion - a.n_disposicion "
        "FROM aeat_viviendas_uso a JOIN aeat_viviendas_uso b USING (cpro) "
        "WHERE cpro = '46' AND a.anyo = 2023 AND b.anyo = 2024",
        -1983,
        0,
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
        # Baseline month only: the series grows with each publication, so
        # only the immutable first month is pinned; month-continuity and
        # per-month reconciliations are asserted in build_marts.
        "anchor",
        "rmdvp 2020-12 listed municipalities",
        "SELECT COUNT(*) FROM rmdvp_inscripciones WHERE yyyymm = '202012' AND grano = 'municipio'",
        518.0,
        1.0,
    ),
    (
        "anchor",
        "rmdvp 2020-12 solicitudes (municipio sum)",
        "SELECT SUM(solicitudes) FROM rmdvp_inscripciones "
        "WHERE yyyymm = '202012' AND grano = 'municipio'",
        257208.0,
        1.0,
    ),
    (
        "anchor",
        "rmdvp 2020-12 inscripciones (municipio sum)",
        "SELECT SUM(inscripciones) FROM rmdvp_inscripciones "
        "WHERE yyyymm = '202012' AND grano = 'municipio'",
        203128.0,
        1.0,
    ),
    (
        "anchor",
        "rmdvp 2020-12 activas (municipio sum)",
        "SELECT SUM(activas) FROM rmdvp_inscripciones "
        "WHERE yyyymm = '202012' AND grano = 'municipio'",
        64471.0,
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
        981528.0,
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
        161848.0,
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
    # Published rent reference band (docs/explorations/serpavi_reference_band.md).
    # The band is the within-municipio contract spread, not an uncertainty
    # interval; these pin its width, its coverage and its internal arithmetic.
    (
        "serpavi_reference_band",
        "municipios with a 2024 published colectiva median",
        "SELECT COUNT(*) FROM muni_all WHERE anyo=2024 AND rent_eur_m2 IS NOT NULL",
        2512,
        0,
    ),
    (
        "serpavi_reference_band",
        "share of municipios with a 2024 median",
        "SELECT ROUND(1.0*COUNT(*)/(SELECT COUNT(*) FROM muni_all WHERE anyo=2024),3)"
        " FROM muni_all WHERE anyo=2024 AND rent_eur_m2 IS NOT NULL",
        0.309,
        0.001,
    ),
    (
        "serpavi_reference_band",
        "share of national population covered by a 2024 median",
        "SELECT ROUND(SUM(poblacion)/(SELECT SUM(poblacion) FROM muni_all"
        " WHERE anyo=2024),3) FROM muni_all"
        " WHERE anyo=2024 AND rent_eur_m2 IS NOT NULL",
        0.913,
        0.001,
    ),
    (
        "serpavi_reference_band",
        "median relative inner band, colectiva EUR/m2, 2024",
        f"SELECT ROUND(MEDIAN((hi_vc-lo_vc)/m2_vc),3) {_VC_BAND_2024}",
        0.453,
        0.001,
    ),
    (
        "serpavi_reference_band",
        "share of municipios with relative inner band above 0.30, 2024",
        "SELECT ROUND(AVG(CASE WHEN (hi_vc-lo_vc)/m2_vc>0.30 THEN 1 ELSE 0 END),3)"
        f" {_VC_BAND_2024}",
        0.924,
        0.001,
    ),
    (
        "serpavi_reference_band",
        "median relative inner band, colectiva EUR/month, 2024",
        f"SELECT ROUND(MEDIAN((mo_hi_vc-mo_lo_vc)/mo_vc),3) FROM {_SERPAVI_BAND}"
        " WHERE anyo=2024 AND mo_vc>0 AND mo_lo_vc IS NOT NULL AND mo_hi_vc IS NOT NULL",
        0.334,
        0.001,
    ),
    (
        "serpavi_reference_band",
        "median relative inner band, unifamiliar EUR/m2, 2024",
        f"SELECT ROUND(MEDIAN((hi_vu-lo_vu)/m2_vu),3) FROM {_SERPAVI_BAND}"
        " WHERE anyo=2024 AND m2_vu>0 AND lo_vu IS NOT NULL AND hi_vu IS NOT NULL",
        0.672,
        0.001,
    ),
    (
        "serpavi_reference_band",
        "median EUR/month over EUR/m2 x surface median, 2024",
        f"SELECT ROUND(MEDIAN(mo_vc/(m2_vc*sf_vc)),3) FROM {_SERPAVI_BAND}"
        " WHERE anyo=2024 AND m2_vc>0 AND sf_vc>0 AND mo_vc IS NOT NULL",
        0.956,
        0.001,
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

# ---------------------------------------------------------------------------
# Catalonia rent-control evaluation, ECV 2025 microsimulation, and the public
# claim ledger (added 2026-11-27).
#
# Each artifact carries a _meta freshness key (MODEL_FRESHNESS below), so
# staleness is caught there; these claims answer the doc-side question: does
# the narrative still quote what the artifact says? Paths address rows by
# index, mirroring the artifact's own row order (deterministic by design).
POLICY_EVAL_CLAIMS: list[tuple[str, str, str, float, float]] = [
    # Design A (Wave 1 vs not-yet-treated Wave 2) — the cleanest control.
    ("politica", "A rent effect %", "did_summary.0.effect_display", -3.79, 0.005),
    ("politica", "A contracts effect %", "did_summary.1.effect_display", -12.61, 0.005),
    ("politica", "A seasonal share pp", "did_summary.2.effect_display", 1.42, 0.005),
    ("politica", "A rent wild p", "did_summary.0.wild_p", 0.001, 0.0),
    ("politica", "A seasonal wild p", "did_summary.2.wild_p", 0.005, 0.0),
    ("politica", "A rent placebo t", "did_summary.0.placebo_t", -0.968, 0.0005),
    ("politica", "A contracts placebo t", "did_summary.1.placebo_t", -0.901, 0.0005),
    # Design B (Wave 1 vs never-treated active markets, open horizon).
    ("politica", "B rent effect %", "did_summary.3.effect_display", -6.19, 0.005),
    ("politica", "B contracts effect %", "did_summary.4.effect_display", -17.1, 0.005),
    ("politica", "B seasonal share pp", "did_summary.5.effect_display", 1.91, 0.005),
    ("politica", "B rent placebo t", "did_summary.3.placebo_t", 2.06, 0.0005),
    ("politica", "B contracts placebo t", "did_summary.4.placebo_t", -0.999, 0.0005),
    # Design C (Wave 2 vs never-treated): contracts null, seasonal null.
    ("politica", "C rent effect %", "did_summary.6.effect_display", -5.55, 0.005),
    ("politica", "C contracts effect %", "did_summary.7.effect_display", -7.0, 0.005),
    ("politica", "C contracts wild p", "did_summary.7.wild_p", 0.068, 0.0),
    ("politica", "C seasonal share pp", "did_summary.8.effect_display", 0.73, 0.005),
    ("politica", "C seasonal wild p", "did_summary.8.wild_p", 0.154, 0.0),
    ("politica", "C rent placebo t", "did_summary.6.placebo_t", 1.447, 0.0005),
    ("politica", "C contracts placebo t", "did_summary.7.placebo_t", -1.362, 0.0005),
    # Design D (within-comarca FE).
    ("politica", "D rent effect %", "did_summary.9.effect_display", -5.3, 0.005),
    ("politica", "D contracts effect %", "did_summary.10.effect_display", -10.66, 0.005),
    ("politica", "D seasonal share pp", "did_summary.11.effect_display", 0.89, 0.005),
    ("politica", "D seasonal wild p", "did_summary.11.wild_p", 0.035, 0.0),
    ("politica", "D contracts placebo t", "did_summary.10.placebo_t", 0.627, 0.0005),
    # Sample and pre-trend diagnostics quoted in the doc's caveat section.
    ("politica", "active Wave 1 municipalities", "meta.active_munis_by_wave.1", 139, 0),
    ("politica", "active Wave 2 municipalities", "meta.active_munis_by_wave.2", 124, 0),
    ("politica", "active never-treated municipalities", "meta.active_munis_by_wave.0", 64, 0),
    ("politica", "A rent max pre-lead |t|", "pretrends.A_w1_vs_w2_rent.max_abs_t", 2.23, 0.005),
    ("politica", "A rent significant pre-leads", "pretrends.A_w1_vs_w2_rent.sig_pre_leads", 1, 0),
    (
        "politica",
        "B contracts significant pre-leads",
        "pretrends.B_w1_vs_never_contracts.sig_pre_leads",
        3,
        0,
    ),
]

MICROSIM_CLAIMS: list[tuple[str, str, str, float, float]] = [
    # Baseline overburden (Eurostat >40% rule, market renters).
    ("microsimulacion", "valid households", "meta.valid_households", 29263, 0),
    ("microsimulacion", "valid market renters", "meta.valid_market_renter_hh", 3660, 0),
    ("microsimulacion", "baseline over40 all", "scenarios.0.overburden_40_all_pct", 7.17, 0.005),
    ("microsimulacion", "baseline over40 market", "scenarios.0.overburden_40_mkt_pct", 26.8, 0.005),
    ("microsimulacion", "baseline effort30 market", "scenarios.0.effort_30_mkt_pct", 44.02, 0.005),
    # Bono Alquiler Joven, 0% and 50% pass-through.
    ("microsimulacion", "bono0 over40 market", "scenarios.1.overburden_40_mkt_pct", 21.46, 0.005),
    ("microsimulacion", "bono0 households lifted", "scenarios.1.hh_lifted_out_40", 202337, 0),
    ("microsimulacion", "bono0 fiscal cost M€", "scenarios.1.fiscal_cost_meur", 1796.3, 0.5),
    ("microsimulacion", "bono0 € per lifted hh", "scenarios.1.fiscal_eur_per_hh_lifted", 8878, 0),
    ("microsimulacion", "bono0 relief to Q1-Q2 %", "scenarios.1.relief_to_q1_q2_pct", 90.0, 0.05),
    ("microsimulacion", "bono0 eligible hh", "scenarios.1.eligible_hh", 600114, 0),
    ("microsimulacion", "bono50 over40 market", "scenarios.2.overburden_40_mkt_pct", 23.6, 0.005),
    ("microsimulacion", "bono50 households lifted", "scenarios.2.hh_lifted_out_40", 114314, 0),
    ("microsimulacion", "bono50 € per lifted hh", "scenarios.2.fiscal_eur_per_hh_lifted", 15714, 0),
    # Income-targeted Q1-Q2 subsidy.
    (
        "microsimulacion",
        "targeted over40 market",
        "scenarios.3.overburden_40_mkt_pct",
        14.75,
        0.005,
    ),
    ("microsimulacion", "targeted households lifted", "scenarios.3.hh_lifted_out_40", 480349, 0),
    ("microsimulacion", "targeted fiscal cost M€", "scenarios.3.fiscal_cost_meur", 5115.7, 0.5),
    (
        "microsimulacion",
        "targeted € per lifted hh",
        "scenarios.3.fiscal_eur_per_hh_lifted",
        10650,
        0,
    ),
    # Broad -5% rent cap (calibrated to the Catalonia Design B range).
    ("microsimulacion", "cap -5% over40 market", "scenarios.4.overburden_40_mkt_pct", 24.47, 0.005),
    ("microsimulacion", "cap -5% households lifted", "scenarios.4.hh_lifted_out_40", 89550, 0),
    ("microsimulacion", "cap -5% tenant relief M€", "scenarios.4.tenant_relief_meur", 1533.5, 0.5),
    ("microsimulacion", "cap -5% relief to Q1-Q2 %", "scenarios.4.relief_to_q1_q2_pct", 47.3, 0.05),
    # Progressive 30% effort shield.
    (
        "microsimulacion",
        "effort shield over40 market",
        "scenarios.5.overburden_40_mkt_pct",
        10.05,
        0.005,
    ),
    (
        "microsimulacion",
        "effort shield households lifted",
        "scenarios.5.hh_lifted_out_40",
        666040,
        0,
    ),
    (
        "microsimulacion",
        "effort shield fiscal cost M€",
        "scenarios.5.fiscal_cost_meur",
        3865.8,
        0.5,
    ),
    (
        "microsimulacion",
        "effort shield € per lifted hh",
        "scenarios.5.fiscal_eur_per_hh_lifted",
        5804,
        0,
    ),
]

# (doc, description, claim_id, definition substring, expected, tol). The
# ledger re-derives each bridge from the marts, so pinning the bridge value
# catches a doc quoting a definition the artifact no longer reports.
LEDGER_CLAIMS: list[tuple[str, str, str, str, float, float]] = [
    (
        "afirmaciones",
        "deficit net stock 2021-2024",
        "C1_deficit_600k",
        "parque neto MIVAU (2021\u20132024)",
        600471,
        0,
    ),
    (
        "afirmaciones",
        "deficit vs completions 2021-2024",
        "C1_deficit_600k",
        "terminadas",
        606955,
        0,
    ),
    ("afirmaciones", "deficit net stock 2021-2025", "C1_deficit_600k", "2021\u20132025", 746612, 0),
    (
        "afirmaciones",
        "Madrid dwellings per 1000 2025",
        "C5_flat_stock_ratio",
        "Madrid (2025)",
        429.41,
        0.01,
    ),
    (
        "afirmaciones",
        "Galicia dwellings per 1000 2025",
        "C5_flat_stock_ratio",
        "Galicia (2025)",
        652.85,
        0.01,
    ),
    (
        "afirmaciones",
        "IPV fall 2007-2013",
        "C7_bust_oversupply_only",
        "Caída del IPV",
        -35.7,
        0.05,
    ),
    (
        "afirmaciones",
        "mortgage fall 2007-2013",
        "C7_bust_oversupply_only",
        "Caída de hipotecas",
        -83.9,
        0.05,
    ),
    (
        "afirmaciones",
        "declared rental contracts Barcelona 2024",
        "C8_rentals_disappearing",
        "Contratos de alquiler declarados",
        143159,
        0,
    ),
    (
        "afirmaciones",
        "deposit entries Barcelona 2024",
        "C8_rentals_disappearing",
        "Altas de fianza",
        32903,
        0,
    ),
    (
        "afirmaciones",
        "negative deposit balance Barcelona 2020",
        "C8_rentals_disappearing",
        "Saldo neto de fianzas",
        -4820,
        0,
    ),
    ("afirmaciones", "census vacant dwellings", "C2_empty_homes_3_8m", "vac\u00edas", 3828307, 0),
    (
        "afirmaciones",
        "census sporadic-use dwellings",
        "C2_empty_homes_3_8m",
        "espor\u00e1dico",
        2517628,
        0,
    ),
    (
        "afirmaciones",
        "Galicia vs Madrid vacancy gap pp",
        "C2_empty_homes_3_8m",
        "Galicia",
        22.47,
        0.005,
    ),
    (
        "afirmaciones",
        "real valoration vs 2007 %",
        "C4_harder_than_2007",
        "Valor tasado",
        -27.5,
        0.05,
    ),
    (
        "afirmaciones",
        "90m2 affordability gap years",
        "C4_harder_than_2007",
        "90 m\u00b2",
        1.99,
        0.005,
    ),
]

# INE rent-update reference index (IRAV): the statutory ceiling for updating an
# existing lease, national and monthly. Path-based against artifacts/irav.json,
# like the policy/microsim lists. INE publishes a rolling 24-month window, so
# these pins move with each release: `make fetch` and this list are updated
# together (the audit fails loudly instead of drifting).
# Catalan mediation, seasonal deposits and INCASÒL balances (2026-11-28).
# Same grain as the notes: the artifact recomputes every quoted figure from the
# pinned workbooks, so a publisher reissue fails here instead of leaving the
# prose on a superseded vintage. Signed changes are claimed as stored; where the
# prose states a loss as a magnitude ("229 fewer"), the doc audit matches the
# magnitude and the signed value stays pinned here.
OCCUPANCY_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("occupancy", "city mediated rentals 2024", "mediation_flow.barcelona_city.2024", 202, 0),
    ("occupancy", "city mediated rentals 2025", "mediation_flow.barcelona_city.2025", 176, 0),
    ("occupancy", "city mediated rentals 2017", "mediation_flow.barcelona_city.2017", 178, 0),
    (
        "occupancy",
        "rest of demarcation rentals 2024",
        "mediation_flow.rest_demarcation.2024",
        488,
        0,
    ),
    (
        "occupancy",
        "rest of demarcation rentals 2025",
        "mediation_flow.rest_demarcation.2025",
        375,
        0,
    ),
    (
        "occupancy",
        "demarcation rentals 2024",
        "mediation_flow.barcelona_demarcation.2024",
        690,
        0,
    ),
    (
        "occupancy",
        "demarcation rentals 2025",
        "mediation_flow.barcelona_demarcation.2025",
        551,
        0,
    ),
    ("occupancy", "Catalonia mediated rentals 2024", "mediation_flow.catalonia.2024", 1133, 0),
    ("occupancy", "Catalonia mediated rentals 2025", "mediation_flow.catalonia.2025", 910, 0),
    ("occupancy", "city active contracts 2024", "mediation_active.barcelona_city.2024", 1246, 0),
    ("occupancy", "city active contracts 2025", "mediation_active.barcelona_city.2025", 1301, 0),
    (
        "occupancy",
        "rest of demarcation active 2024",
        "mediation_active.rest_demarcation.2024",
        4028,
        0,
    ),
    (
        "occupancy",
        "rest of demarcation active 2025",
        "mediation_active.rest_demarcation.2025",
        3912,
        0,
    ),
    (
        "occupancy",
        "demarcation active 2024",
        "mediation_active.barcelona_demarcation.2024",
        5274,
        0,
    ),
    (
        "occupancy",
        "demarcation active 2025",
        "mediation_active.barcelona_demarcation.2025",
        5213,
        0,
    ),
    ("occupancy", "Catalonia active contracts 2024", "mediation_active.catalonia.2024", 7790, 0),
    ("occupancy", "Catalonia active contracts 2025", "mediation_active.catalonia.2025", 7704, 0),
    ("occupancy", "city active change 2024-25", "latest_year.city_active_change", 55, 0),
    (
        "occupancy",
        "rest of demarcation active change 2024-25",
        "latest_year.rest_active_change",
        -116,
        0,
    ),
    (
        "occupancy",
        "municipalities with rentals 2024",
        "mediation_flow.municipalities.positive_first",
        150,
        0,
    ),
    (
        "occupancy",
        "municipalities with rentals 2025",
        "mediation_flow.municipalities.positive_last",
        158,
        0,
    ),
    (
        "occupancy",
        "rental change in places active both years",
        "mediation_flow.municipalities.change_both_positive",
        -229,
        0,
    ),
    (
        "occupancy",
        "rental change from municipalities switching",
        "mediation_flow.municipalities.change_switchers",
        6,
        0,
    ),
    (
        "occupancy",
        "net municipal rental change",
        "mediation_flow.municipalities.net_change",
        -223,
        0,
    ),
    (
        "occupancy",
        "municipalities with active contracts 2024",
        "mediation_active.municipalities.positive_first",
        294,
        0,
    ),
    (
        "occupancy",
        "municipalities with active contracts 2025",
        "mediation_active.municipalities.positive_last",
        298,
        0,
    ),
    (
        "occupancy",
        "active change in places positive both years",
        "mediation_active.municipalities.change_both_positive",
        -94,
        0,
    ),
    (
        "occupancy",
        "active change from municipalities switching",
        "mediation_active.municipalities.change_switchers",
        8,
        0,
    ),
    ("occupancy", "city active contracts 2017", "latest_year.city_active_first", 760, 0),
    ("occupancy", "city active contracts 2025 window", "latest_year.city_active_last", 1301, 0),
    (
        "occupancy",
        "rest of Catalonia active 2017",
        "latest_year.rest_active_first",
        7687,
        0,
    ),
    ("occupancy", "rest of Catalonia active 2025", "latest_year.rest_active_last", 6403, 0),
    (
        "occupancy",
        "city share of active contracts 2017",
        "latest_year.city_share_first_pct",
        9.0,
        0.05,
    ),
    (
        "occupancy",
        "city share of active contracts 2025",
        "latest_year.city_share_last_pct",
        16.9,
        0.05,
    ),
    ("occupancy", "city filings 2017", "scale_per_1000_filings.2017.city_filings", 49953, 0),
    (
        "occupancy",
        "city mediated rentals per 1,000 filings 2017",
        "scale_per_1000_filings.2017.city_per_1000",
        3.56,
        0.005,
    ),
    (
        "occupancy",
        "Catalonia filings 2017",
        "scale_per_1000_filings.2017.catalonia_filings",
        156936,
        0,
    ),
    (
        "occupancy",
        "Catalonia mediated rentals per 1,000 filings 2017",
        "scale_per_1000_filings.2017.catalonia_per_1000",
        9.02,
        0.005,
    ),
    ("occupancy", "city filings 2024", "scale_per_1000_filings.2024.city_filings", 32903, 0),
    (
        "occupancy",
        "city mediated rentals per 1,000 filings 2024",
        "scale_per_1000_filings.2024.city_per_1000",
        6.14,
        0.005,
    ),
    (
        "occupancy",
        "Catalonia filings 2024",
        "scale_per_1000_filings.2024.catalonia_filings",
        118626,
        0,
    ),
    (
        "occupancy",
        "Catalonia mediated rentals per 1,000 filings 2024",
        "scale_per_1000_filings.2024.catalonia_per_1000",
        9.55,
        0.005,
    ),
    ("occupancy", "city filings 2025", "scale_per_1000_filings.2025.city_filings", 30789, 0),
    (
        "occupancy",
        "city mediated rentals per 1,000 filings 2025",
        "scale_per_1000_filings.2025.city_per_1000",
        5.72,
        0.005,
    ),
    (
        "occupancy",
        "Catalonia filings 2025",
        "scale_per_1000_filings.2025.catalonia_filings",
        108057,
        0,
    ),
    (
        "occupancy",
        "Catalonia mediated rentals per 1,000 filings 2025",
        "scale_per_1000_filings.2025.catalonia_per_1000",
        8.42,
        0.005,
    ),
    (
        "occupancy",
        "city habitual plus seasonal filings 2024",
        "scale_per_1000_filings.2024.city_combined_filings",
        41309,
        0,
    ),
    (
        "occupancy",
        "city mediated rentals per 1,000 combined filings 2024",
        "scale_per_1000_filings.2024.city_combined_per_1000",
        4.89,
        0.005,
    ),
    (
        "occupancy",
        "Catalonia combined filings 2024",
        "scale_per_1000_filings.2024.catalonia_combined_filings",
        132143,
        0,
    ),
    (
        "occupancy",
        "Catalonia mediated rentals per 1,000 combined filings 2024",
        "scale_per_1000_filings.2024.catalonia_combined_per_1000",
        8.57,
        0.005,
    ),
    (
        "occupancy",
        "city habitual plus seasonal filings 2025",
        "scale_per_1000_filings.2025.city_combined_filings",
        39584,
        0,
    ),
    (
        "occupancy",
        "city mediated rentals per 1,000 combined filings 2025",
        "scale_per_1000_filings.2025.city_combined_per_1000",
        4.45,
        0.005,
    ),
    (
        "occupancy",
        "Catalonia combined filings 2025",
        "scale_per_1000_filings.2025.catalonia_combined_filings",
        121209,
        0,
    ),
    (
        "occupancy",
        "Catalonia mediated rentals per 1,000 combined filings 2025",
        "scale_per_1000_filings.2025.catalonia_combined_per_1000",
        7.51,
        0.005,
    ),
    (
        "occupancy",
        "city seasonal deposits 2024",
        "seasonal_deposits.barcelona_city.2024",
        8406,
        0,
    ),
    (
        "occupancy",
        "city seasonal deposits 2025",
        "seasonal_deposits.barcelona_city.2025",
        8795,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal deposits 2024",
        "seasonal_deposits.catalonia.2024",
        13517,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal deposits 2025",
        "seasonal_deposits.catalonia.2025",
        13152,
        0,
    ),
    (
        "occupancy",
        "city habitual new deposits 2024",
        "balances.annual.2024.barcelona_habitual.entries",
        32903,
        0,
    ),
    (
        "occupancy",
        "city habitual new deposits 2025",
        "balances.annual.2025.barcelona_habitual.entries",
        30789,
        0,
    ),
    (
        "occupancy",
        "city habitual cancellations 2024",
        "balances.annual.2024.barcelona_habitual.cancellations",
        30179,
        0,
    ),
    (
        "occupancy",
        "city habitual cancellations 2025",
        "balances.annual.2025.barcelona_habitual.cancellations",
        30255,
        0,
    ),
    (
        "occupancy",
        "city habitual net balance 2024",
        "balances.annual.2024.barcelona_habitual.balance",
        2724,
        0,
    ),
    (
        "occupancy",
        "city habitual net balance 2025",
        "balances.annual.2025.barcelona_habitual.balance",
        534,
        0,
    ),
    (
        "occupancy",
        "city habitual balance change",
        "balances.city_habitual_change.balance_change",
        -2190,
        0,
    ),
    (
        "occupancy",
        "city habitual entry change",
        "balances.city_habitual_change.entries_change",
        -2114,
        0,
    ),
    (
        "occupancy",
        "city habitual cancellation change",
        "balances.city_habitual_change.cancellations_change",
        76,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal balance 2024",
        "balances.annual.2024.catalonia_seasonal.balance",
        4186,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal balance 2025",
        "balances.annual.2025.catalonia_seasonal.balance",
        243,
        0,
    ),
    (
        "occupancy",
        "city habitual H1 2025 entries",
        "balances.first_half.2025.barcelona_habitual.entries",
        15026,
        0,
    ),
    (
        "occupancy",
        "city habitual H1 2026 entries",
        "balances.first_half.2026.barcelona_habitual.entries",
        16001,
        0,
    ),
    (
        "occupancy",
        "city habitual H1 2025 cancellations",
        "balances.first_half.2025.barcelona_habitual.cancellations",
        14255,
        0,
    ),
    (
        "occupancy",
        "city habitual H1 2026 cancellations",
        "balances.first_half.2026.barcelona_habitual.cancellations",
        15420,
        0,
    ),
    (
        "occupancy",
        "city habitual H1 2025 balance",
        "balances.first_half.2025.barcelona_habitual.balance",
        771,
        0,
    ),
    (
        "occupancy",
        "city habitual H1 2026 balance",
        "balances.first_half.2026.barcelona_habitual.balance",
        581,
        0,
    ),
    (
        "occupancy",
        "Catalonia habitual H1 2025 balance",
        "balances.first_half.2025.catalonia_habitual.balance",
        5429,
        0,
    ),
    (
        "occupancy",
        "Catalonia habitual H1 2026 balance",
        "balances.first_half.2026.catalonia_habitual.balance",
        5913,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal H1 2025 balance",
        "balances.first_half.2025.catalonia_seasonal.balance",
        1135,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal H1 2026 balance",
        "balances.first_half.2026.catalonia_seasonal.balance",
        -1065,
        0,
    ),
    (
        "occupancy",
        "Catalonia combined H1 2025 balance",
        "balances.first_half.2025.catalonia_combined.balance",
        6564,
        0,
    ),
    (
        "occupancy",
        "Catalonia combined H1 2026 balance",
        "balances.first_half.2026.catalonia_combined.balance",
        4848,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal balance 2025 Q4",
        "balances.seasonal_quarters.2025 4T.balance",
        -1233,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal balance 2026 Q1",
        "balances.seasonal_quarters.2026 1T.balance",
        -102,
        0,
    ),
    (
        "occupancy",
        "Catalonia seasonal balance 2026 Q2",
        "balances.seasonal_quarters.2026 2T.balance",
        -963,
        0,
    ),
    (
        "occupancy",
        "seasonal entries, three quarters to 2025 Q2",
        "balances.three_quarters.2024Q4_2025Q2.catalonia_seasonal.entries",
        10872,
        0,
    ),
    (
        "occupancy",
        "seasonal entries, three quarters to 2026 Q2",
        "balances.three_quarters.2025Q4_2026Q2.catalonia_seasonal.entries",
        5677,
        0,
    ),
    (
        "occupancy",
        "seasonal cancellations, three quarters to 2025 Q2",
        "balances.three_quarters.2024Q4_2025Q2.catalonia_seasonal.cancellations",
        7734,
        0,
    ),
    (
        "occupancy",
        "seasonal cancellations, three quarters to 2026 Q2",
        "balances.three_quarters.2025Q4_2026Q2.catalonia_seasonal.cancellations",
        7975,
        0,
    ),
    (
        "occupancy",
        "seasonal balance, three quarters to 2025 Q2",
        "balances.three_quarters.2024Q4_2025Q2.catalonia_seasonal.balance",
        3138,
        0,
    ),
    (
        "occupancy",
        "seasonal balance, three quarters to 2026 Q2",
        "balances.three_quarters.2025Q4_2026Q2.catalonia_seasonal.balance",
        -2298,
        0,
    ),
    (
        "occupancy",
        "habitual balance, three quarters to 2025 Q2",
        "balances.three_quarters.2024Q4_2025Q2.catalonia_habitual.balance",
        8499,
        0,
    ),
    (
        "occupancy",
        "habitual balance, three quarters to 2026 Q2",
        "balances.three_quarters.2025Q4_2026Q2.catalonia_habitual.balance",
        7795,
        0,
    ),
    (
        "occupancy",
        "habitual entries, three quarters to 2025 Q2",
        "balances.three_quarters.2024Q4_2025Q2.catalonia_habitual.entries",
        81886,
        0,
    ),
    (
        "occupancy",
        "habitual entries, three quarters to 2026 Q2",
        "balances.three_quarters.2025Q4_2026Q2.catalonia_habitual.entries",
        81459,
        0,
    ),
    (
        "occupancy",
        "city habitual deposits 2019",
        "balances.history.barcelona_habitual.2019.entries",
        51294,
        0,
    ),
    (
        "occupancy",
        "city habitual cancellations 2019",
        "balances.history.barcelona_habitual.2019.cancellations",
        47708,
        0,
    ),
    (
        "occupancy",
        "city habitual balance 2019",
        "balances.history.barcelona_habitual.2019.balance",
        3586,
        0,
    ),
    (
        "occupancy",
        "city habitual deposits 2020",
        "balances.history.barcelona_habitual.2020.entries",
        40416,
        0,
    ),
    (
        "occupancy",
        "city habitual cancellations 2020",
        "balances.history.barcelona_habitual.2020.cancellations",
        45236,
        0,
    ),
    (
        "occupancy",
        "city habitual balance 2020",
        "balances.history.barcelona_habitual.2020.balance",
        -4820,
        0,
    ),
    (
        "occupancy",
        "city habitual deposits 2021",
        "balances.history.barcelona_habitual.2021.entries",
        57158,
        0,
    ),
    (
        "occupancy",
        "city habitual cancellations 2021",
        "balances.history.barcelona_habitual.2021.cancellations",
        47497,
        0,
    ),
    (
        "occupancy",
        "city habitual balance 2021",
        "balances.history.barcelona_habitual.2021.balance",
        9661,
        0,
    ),
    (
        "occupancy",
        "city habitual deposits 2022",
        "balances.history.barcelona_habitual.2022.entries",
        47927,
        0,
    ),
    (
        "occupancy",
        "city habitual cancellations 2022",
        "balances.history.barcelona_habitual.2022.cancellations",
        38854,
        0,
    ),
    (
        "occupancy",
        "city habitual balance 2022",
        "balances.history.barcelona_habitual.2022.balance",
        9073,
        0,
    ),
    (
        "occupancy",
        "city habitual deposits 2023",
        "balances.history.barcelona_habitual.2023.entries",
        38683,
        0,
    ),
    (
        "occupancy",
        "city habitual cancellations 2023",
        "balances.history.barcelona_habitual.2023.cancellations",
        32173,
        0,
    ),
    (
        "occupancy",
        "city habitual balance 2023",
        "balances.history.barcelona_habitual.2023.balance",
        6510,
        0,
    ),
    (
        "occupancy",
        "Catalonia habitual balance 2023",
        "balances.history.catalonia_habitual.2023.balance",
        26845,
        0,
    ),
    (
        "occupancy",
        "Catalonia habitual balance 2025",
        "balances.history.catalonia_habitual.2025.balance",
        8895,
        0,
    ),
]

IRAV_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("politica", "IRAV published window (months)", "window.months", 24, 0),
    ("politica", "IRAV latest annual variation", "latest.irav_pct", 2.57, 0.005),
    ("politica", "IRAV window minimum", "bounds.min.irav_pct", 1.98, 0.005),
    ("politica", "IRAV window maximum", "bounds.max.irav_pct", 2.57, 0.005),
    ("politica", "IRAV 2025 mean annual variation", "annual_means.1.mean_pct", 2.15, 0.005),
    ("politica", "IRAV 2026 mean annual variation", "annual_means.2.mean_pct", 2.42, 0.005),
]

# IPVA vs SERPAVI: changes on code-matched municipalities, not independent sources.
IPVA_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("ipva_rent_index", "IPVA municipios published", "coverage.ipva_municipios", 718, 0),
    ("ipva_rent_index", "codes in SERPAVI (any year)", "coverage.matched", 718, 0),
    ("ipva_rent_index", "IPVA municipios unmatched", "coverage.unmatched", 0, 0),
    ("ipva_rent_index", "2013-2023 pairs", "windows.0.n", 697, 0),
    ("ipva_rent_index", "2013-2023 IPVA median change", "windows.0.ipva_median_pct", 15.82, 0.005),
    (
        "ipva_rent_index",
        "2013-2023 SERPAVI median change",
        "windows.0.serpavi_median_pct",
        32.51,
        0.005,
    ),
    ("ipva_rent_index", "2013-2023 Pearson", "windows.0.pearson", 0.634, 0.0005),
    ("ipva_rent_index", "2013-2023 Spearman", "windows.0.spearman", 0.679, 0.0005),
    ("ipva_rent_index", "2013-2023 median gap pp", "windows.0.gap_pp.median", -16.54, 0.005),
    ("ipva_rent_index", "2013-2023 gap p10 pp", "windows.0.gap_pp.p10", -27.59, 0.005),
    ("ipva_rent_index", "2019-2023 pairs", "windows.1.n", 702, 0),
    ("ipva_rent_index", "2019-2023 IPVA median change", "windows.1.ipva_median_pct", 8.03, 0.005),
    (
        "ipva_rent_index",
        "2019-2023 SERPAVI median change",
        "windows.1.serpavi_median_pct",
        16.15,
        0.005,
    ),
    ("ipva_rent_index", "2019-2023 Spearman", "windows.1.spearman", 0.703, 0.0005),
    ("ipva_rent_index", "2019-2023 median gap pp", "windows.1.gap_pp.median", -8.02, 0.005),
    (
        "ipva_rent_index",
        "2013-2023 weakest-quartile gap pp",
        "windows.0.quartiles_by_serpavi_change.0.median_gap_pp",
        -9.5,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2013-2023 strongest-quartile gap pp",
        "windows.0.quartiles_by_serpavi_change.3.median_gap_pp",
        -24.98,
        0.005,
    ),
    ("ipva_rent_index", "2019-2023 Pearson", "windows.1.pearson", 0.69, 0.0005),
    ("ipva_rent_index", "2019-2023 gap p10 pp", "windows.1.gap_pp.p10", -13.82, 0.005),
    ("ipva_rent_index", "2019-2023 gap p90 pp", "windows.1.gap_pp.p90", -4.36, 0.005),
    (
        "ipva_rent_index",
        "quartile 1 SERPAVI change",
        "windows.0.quartiles_by_serpavi_change.0.median_serpavi_pct",
        21.11,
        0.005,
    ),
    (
        "ipva_rent_index",
        "quartile 2 SERPAVI change",
        "windows.0.quartiles_by_serpavi_change.1.median_serpavi_pct",
        28.4,
        0.005,
    ),
    (
        "ipva_rent_index",
        "quartile 2 gap pp",
        "windows.0.quartiles_by_serpavi_change.1.median_gap_pp",
        -14.13,
        0.005,
    ),
    (
        "ipva_rent_index",
        "quartile 3 SERPAVI change",
        "windows.0.quartiles_by_serpavi_change.2.median_serpavi_pct",
        35.22,
        0.005,
    ),
    (
        "ipva_rent_index",
        "quartile 3 gap pp",
        "windows.0.quartiles_by_serpavi_change.2.median_gap_pp",
        -17.7,
        0.005,
    ),
    (
        "ipva_rent_index",
        "quartile 4 SERPAVI change",
        "windows.0.quartiles_by_serpavi_change.3.median_serpavi_pct",
        46.43,
        0.005,
    ),
    ("ipva_rent_index", "2013-2023 from", "windows.0.from", 2013, 0),
    ("ipva_rent_index", "2013-2023 to", "windows.0.to", 2023, 0),
    ("ipva_rent_index", "2013-2023 gap_pp.p90", "windows.0.gap_pp.p90", -7.73, 0.005),
    ("ipva_rent_index", "2019-2023 from", "windows.1.from", 2019, 0),
    ("ipva_rent_index", "2019-2023 to", "windows.1.to", 2023, 0),
    ("ipva_rent_index", "2019-2024 from", "windows.2.from", 2019, 0),
    ("ipva_rent_index", "2019-2024 to", "windows.2.to", 2024, 0),
    ("ipva_rent_index", "2019-2024 n", "windows.2.n", 701, 0),
    ("ipva_rent_index", "2019-2024 ipva_median_pct", "windows.2.ipva_median_pct", 11.62, 0.005),
    (
        "ipva_rent_index",
        "2019-2024 serpavi_median_pct",
        "windows.2.serpavi_median_pct",
        22.09,
        0.005,
    ),
    ("ipva_rent_index", "2019-2024 pearson", "windows.2.pearson", 0.753, 0.0005),
    ("ipva_rent_index", "2019-2024 spearman", "windows.2.spearman", 0.758, 0.0005),
    ("ipva_rent_index", "2019-2024 gap_pp.p10", "windows.2.gap_pp.p10", -18.3, 0.005),
    ("ipva_rent_index", "2019-2024 gap_pp.median", "windows.2.gap_pp.median", -10.64, 0.005),
    ("ipva_rent_index", "2019-2024 gap_pp.p90", "windows.2.gap_pp.p90", -6.26, 0.005),
    # Same eligible towns in the within- and between-province contrasts.
    (
        "ipva_rent_index",
        "2013-23 province-pair mean pct",
        "windows.0.pair_ordering.equal_province_pair_agreement_pct",
        74.68,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-23 province-pair mean pct",
        "windows.1.pair_ordering.equal_province_pair_agreement_pct",
        78.81,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-24 province-pair mean pct",
        "windows.2.pair_ordering.equal_province_pair_agreement_pct",
        81.40,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-24 comparable pairs across provinces",
        "windows.2.pair_ordering.between.comparable",
        230379,
        0,
    ),
    (
        "ipva_rent_index",
        "2019-24 tied pairs across provinces",
        "windows.2.pair_ordering.between.tied",
        0,
        0,
    ),
    ("ipva_rent_index", "2019-24 tied local pairs", "windows.2.pair_ordering.within.tied", 0, 0),
    (
        "ipva_rent_index",
        "2013-23 within pct",
        "windows.0.pair_ordering.within.agreement_pct",
        66.50,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2013-23 between pct",
        "windows.0.pair_ordering.between.agreement_pct",
        75.66,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2013-23 province mean pct",
        "windows.0.pair_ordering.equal_province_agreement_pct",
        66.32,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-23 within pct",
        "windows.1.pair_ordering.within.agreement_pct",
        73.53,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-23 between pct",
        "windows.1.pair_ordering.between.agreement_pct",
        76.84,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-23 province mean pct",
        "windows.1.pair_ordering.equal_province_agreement_pct",
        71.82,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-24 within pct",
        "windows.2.pair_ordering.within.agreement_pct",
        74.60,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-24 between pct",
        "windows.2.pair_ordering.between.agreement_pct",
        79.35,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-24 province mean pct",
        "windows.2.pair_ordering.equal_province_agreement_pct",
        74.87,
        0.005,
    ),
    (
        "ipva_rent_index",
        "2019-24 local pairs agreed",
        "windows.2.pair_ordering.within.agreed",
        8046,
        0,
    ),
    (
        "ipva_rent_index",
        "2019-24 comparable local pairs",
        "windows.2.pair_ordering.within.comparable",
        10786,
        0,
    ),
    ("ipva_rent_index", "2019-24 pair sample", "windows.2.pair_ordering.municipalities", 695, 0),
    (
        "ipva_rent_index",
        "2019-24 comparable provinces",
        "windows.2.pair_ordering.provinces_with_comparable_pairs",
        42,
        0,
    ),
]

# INE's own household projection (PROH) paired with the stock marts: the
# projection is an external input, so both its levels and the pairing with
# current dwellings per household are pinned.
PROH_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("proh_households", "projected households 2026", "national.households_first", 19759349, 0),
    ("proh_households", "projected households 2040", "national.households_last", 21867217, 0),
    ("proh_households", "projected change", "national.change", 2107868, 0),
    ("proh_households", "projected change pct", "national.change_pct", 10.67, 0.005),
    ("proh_households", "top-4 CCAA projected change", "concentration.top4_change", 1425007, 0),
    ("proh_households", "top-4 share of growth pct", "concentration.top4_share_pct", 67.75, 0.005),
    (
        "proh_households",
        "lean-stock median growth pct",
        "stock_pairing.lean_stock_growth_median_pct",
        11.9,
        0.005,
    ),
    (
        "proh_households",
        "fat-stock median growth pct",
        "stock_pairing.fat_stock_growth_median_pct",
        7.69,
        0.005,
    ),
    (
        "proh_households",
        "ratio vs growth Pearson",
        "stock_pairing.pearson_ratio_vs_growth",
        -0.316,
        0.0005,
    ),
    ("proh_households", "CCAA units", "stock_pairing.n_ccaa", 17, 0),
    ("proh_households", "Madrid projected change", "ccaa.0.change", 379306, 0),
    (
        "proh_households",
        "Madrid dwellings per household 2025",
        "ccaa.0.dwellings_per_household_2025",
        1.128,
        0.0005,
    ),
    (
        "proh_households",
        "ECP observed households 1-Jan-2026",
        "ecp_check.observed_2026",
        19761683,
        0,
    ),
    (
        "proh_households",
        "projection base minus observed ECP",
        "ecp_check.projection_minus_observed",
        -2334,
        0,
    ),
]

# INE VTE municipal estimates: platform-derived stock, not a licence register.
VUT_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("vut_stock", "tourist dwellings (Spain)", "national.viviendas_turisticas", 341001, 0),
    ("vut_stock", "tourist beds (Spain)", "national.plazas", 1714702, 0),
    ("vut_stock", "beds per tourist dwelling", "national.plazas_por_vivienda", 5.03, 0.005),
    ("vut_stock", "share of census dwellings pct", "national.pct_censadas", 1.28, 0.005),
    ("vut_stock", "first snapshot stock", "path.first_value", 321496, 0),
    ("vut_stock", "change since first snapshot pct", "path.change_pct", 6.07, 0.005),
    ("vut_stock", "top municipio stock", "concentration.top_municipio_vut", 10836, 0),
    (
        "vut_stock",
        "top-10 share of assigned stock pct",
        "concentration.top10_share_of_assigned_pct",
        18.47,
        0.005,
    ),
    ("vut_stock", "median municipal share pct", "shares.median_pct", 0.61, 0.005),
    ("vut_stock", "p90 municipal share pct", "shares.p90_pct", 3.38, 0.005),
    ("vut_stock", "max municipal share pct", "shares.max_pct", 33.33, 0.005),
    ("vut_stock", "municipios above 5 pct", "shares.share_above_5pct", 5.30, 0.005),
    ("vut_stock", "municipios with a published share", "shares.n_municipios", 5319, 0),
    ("vut_stock", "municipality stock rows", "coverage.municipio_rows", 8131, 0),
    ("vut_stock", "municipal codes matched to map", "coverage.matched_map_rows", 8131, 0),
    ("vut_stock", "unmapped municipality rows", "coverage.unassigned_rows", 0, 0),
    ("vut_stock", "unassigned stock", "coverage.unassigned_stock", 0, 0),
    ("vut_stock", "assigned stock", "coverage.assigned_stock", 341001, 0),
    (
        "vut_stock",
        "assigned share of national stock pct",
        "coverage.assigned_share_of_national_pct",
        100,
        0.005,
    ),
]


VUT_RENT_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("vut_rent_overlap", "2024 level sample", "levels_2024.n", 2555, 0),
    ("vut_rent_overlap", "2022 change sample", "changes_2022_2024.n", 2340, 0),
    ("vut_rent_overlap", "2020 change sample", "changes_2020_2024.n", 2122, 0),
    ("vut_rent_overlap", "2024 level rank correlation", "levels_2024.spearman", 0.206, 0.0005),
    (
        "vut_rent_overlap",
        "2022 change rank correlation",
        "changes_2022_2024.spearman",
        0.050,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 change rank correlation",
        "changes_2020_2024.spearman",
        0.007,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "levels on the 2022 change sample",
        "changes_2022_2024.end_levels_spearman_on_same_sample",
        0.224,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "levels on the 2020 change sample",
        "changes_2020_2024.end_levels_spearman_on_same_sample",
        0.241,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "municipalities covered in 2024 pct",
        "levels_2024.end_matched_municipalities_pct",
        31.42,
        0.005,
    ),
    (
        "vut_rent_overlap",
        "stock in 2024 level sample pct",
        "levels_2024.end_matched_stock_pct",
        95.29,
        0.005,
    ),
    (
        "vut_rent_overlap",
        "stock in 2022 change sample pct",
        "changes_2022_2024.end_matched_stock_pct",
        94.19,
        0.005,
    ),
    (
        "vut_rent_overlap",
        "stock in 2020 change sample pct",
        "changes_2020_2024.end_matched_stock_pct",
        92.97,
        0.005,
    ),
    # Hold the towns fixed when changing the rent measure.
    (
        "vut_rent_overlap",
        "2022–24 towns on common IPVA sample",
        "changes_2022_2024.common_ipva_sample.n",
        703,
        0,
    ),
    (
        "vut_rent_overlap",
        "2022–24 IPVA towns observed at both endpoints",
        "changes_2022_2024.common_ipva_sample.ipva_both_endpoints",
        703,
        0,
    ),
    (
        "vut_rent_overlap",
        "2022–24 August 2024 tourist stock pct on common sample",
        "changes_2022_2024.common_ipva_sample.end_matched_stock_pct",
        76.98,
        0.005,
    ),
    (
        "vut_rent_overlap",
        "2022–24 tourist share vs SERPAVI growth, common sample",
        "changes_2022_2024.common_ipva_sample.tourism_serpavi_spearman",
        0.12,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022–24 tourist share vs IPVA growth, common sample",
        "changes_2022_2024.common_ipva_sample.tourism_ipva_spearman",
        0.104,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022–24 SERPAVI vs IPVA growth, common sample",
        "changes_2022_2024.common_ipva_sample.serpavi_ipva_spearman",
        0.694,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020–24 towns on common IPVA sample",
        "changes_2020_2024.common_ipva_sample.n",
        701,
        0,
    ),
    (
        "vut_rent_overlap",
        "2020–24 IPVA towns observed at both endpoints",
        "changes_2020_2024.common_ipva_sample.ipva_both_endpoints",
        701,
        0,
    ),
    (
        "vut_rent_overlap",
        "2020–24 August 2024 tourist stock pct on common sample",
        "changes_2020_2024.common_ipva_sample.end_matched_stock_pct",
        76.96,
        0.005,
    ),
    (
        "vut_rent_overlap",
        "2020–24 tourist share vs SERPAVI growth, common sample",
        "changes_2020_2024.common_ipva_sample.tourism_serpavi_spearman",
        0.068,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020–24 tourist share vs IPVA growth, common sample",
        "changes_2020_2024.common_ipva_sample.tourism_ipva_spearman",
        0.032,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020–24 SERPAVI vs IPVA growth, common sample",
        "changes_2020_2024.common_ipva_sample.serpavi_ipva_spearman",
        0.747,
        0.0005,
    ),
    # Fixed housing denominator and the separately documented regional count revision.
    (
        "vut_rent_overlap",
        "2022 fixed base: all, n",
        "changes_2022_2024.fixed_2021_base.all.n",
        703,
        0,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: all, reported_serpavi",
        "changes_2022_2024.fixed_2021_base.all.reported_serpavi",
        0.12,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: all, fixed_serpavi",
        "changes_2022_2024.fixed_2021_base.all.fixed_serpavi",
        0.167,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: all, reported_ipva",
        "changes_2022_2024.fixed_2021_base.all.reported_ipva",
        0.104,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: all, fixed_ipva",
        "changes_2022_2024.fixed_2021_base.all.fixed_ipva",
        0.133,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: all, n",
        "changes_2020_2024.fixed_2021_base.all.n",
        701,
        0,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: all, reported_serpavi",
        "changes_2020_2024.fixed_2021_base.all.reported_serpavi",
        0.068,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: all, fixed_serpavi",
        "changes_2020_2024.fixed_2021_base.all.fixed_serpavi",
        0.113,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: all, reported_ipva",
        "changes_2020_2024.fixed_2021_base.all.reported_ipva",
        0.032,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: all, fixed_ipva",
        "changes_2020_2024.fixed_2021_base.all.fixed_ipva",
        0.069,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: outside_andalucia, n",
        "changes_2022_2024.fixed_2021_base.outside_andalucia.n",
        551,
        0,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: outside_andalucia, reported_serpavi",
        "changes_2022_2024.fixed_2021_base.outside_andalucia.reported_serpavi",
        0.088,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: outside_andalucia, fixed_serpavi",
        "changes_2022_2024.fixed_2021_base.outside_andalucia.fixed_serpavi",
        0.145,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: outside_andalucia, reported_ipva",
        "changes_2022_2024.fixed_2021_base.outside_andalucia.reported_ipva",
        0.041,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2022 fixed base: outside_andalucia, fixed_ipva",
        "changes_2022_2024.fixed_2021_base.outside_andalucia.fixed_ipva",
        0.076,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: outside_andalucia, n",
        "changes_2020_2024.fixed_2021_base.outside_andalucia.n",
        549,
        0,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: outside_andalucia, reported_serpavi",
        "changes_2020_2024.fixed_2021_base.outside_andalucia.reported_serpavi",
        0.045,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: outside_andalucia, fixed_serpavi",
        "changes_2020_2024.fixed_2021_base.outside_andalucia.fixed_serpavi",
        0.091,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: outside_andalucia, reported_ipva",
        "changes_2020_2024.fixed_2021_base.outside_andalucia.reported_ipva",
        0.017,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020 fixed base: outside_andalucia, fixed_ipva",
        "changes_2020_2024.fixed_2021_base.outside_andalucia.fixed_ipva",
        0.055,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "fixed August 2024 shares within rounding, 2022 sample",
        "changes_2022_2024.fixed_2021_base.all.end_shares_within_rounding",
        694,
        0,
    ),
    # Net change over the two earlier windows, without the middle count.
    (
        "vut_rent_overlap",
        "net timing serpavi rank correlation",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.spearman.serpavi",
        -0.023268,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing ipva rank correlation",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.spearman.ipva",
        -0.00422,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing decreased n",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.decreased.n",
        320,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing decreased median_change_per_100",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.decreased.median_change_per_100",
        -0.05272,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing decreased median serpavi rent growth",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.decreased.median_rent_growth_pct.serpavi",
        5.211647,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing decreased median ipva rent growth",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.decreased.median_rent_growth_pct.ipva",
        3.274595,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing unchanged n",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.unchanged.n",
        44,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing unchanged median_change_per_100",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.unchanged.median_change_per_100",
        0.0,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing unchanged median serpavi rent growth",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.unchanged.median_rent_growth_pct.serpavi",
        5.10002,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing unchanged median ipva rent growth",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.unchanged.median_rent_growth_pct.ipva",
        3.168573,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing increased n",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.increased.n",
        339,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing increased median_change_per_100",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.increased.median_change_per_100",
        0.072838,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing increased median serpavi rent growth",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.increased.median_rent_growth_pct.serpavi",
        5.427659,
        0,
    ),
    (
        "vut_rent_overlap",
        "net timing increased median ipva rent growth",
        "earlier_tourism_later_rents.net_two_year.2020_2022__2023_2024.by_direction.increased.median_rent_growth_pct.ipva",
        3.371754,
        0,
    ),
    # One fixed cohort for all strictly ordered one-year stock/rent comparisons.
    (
        "vut_rent_overlap",
        "fully observed later rent series",
        "earlier_tourism_later_rents.rent_complete",
        703,
        0,
    ),
    ("vut_rent_overlap", "balanced timing sample", "earlier_tourism_later_rents.n", 703, 0),
    (
        "vut_rent_overlap",
        "2020–2021 tourist change vs 2022–2023 serpavi growth",
        "earlier_tourism_later_rents.comparisons.2020_2021__2022_2023.serpavi",
        -0.045,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020–2021 tourist change vs 2022–2023 ipva growth",
        "earlier_tourism_later_rents.comparisons.2020_2021__2022_2023.ipva",
        -0.072,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020–2021 tourist change vs 2023–2024 serpavi growth",
        "earlier_tourism_later_rents.comparisons.2020_2021__2023_2024.serpavi",
        -0.104,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2020–2021 tourist change vs 2023–2024 ipva growth",
        "earlier_tourism_later_rents.comparisons.2020_2021__2023_2024.ipva",
        -0.098,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2021–2022 tourist change vs 2023–2024 serpavi growth",
        "earlier_tourism_later_rents.comparisons.2021_2022__2023_2024.serpavi",
        0.075,
        0.0005,
    ),
    (
        "vut_rent_overlap",
        "2021–2022 tourist change vs 2023–2024 ipva growth",
        "earlier_tourism_later_rents.comparisons.2021_2022__2023_2024.ipva",
        0.072,
        0.0005,
    ),
]


# October ECP remains separate from the December stock comparison.
ECP_HOUSEHOLD_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("deficit", "October 2026 household total", "latest.total", 19953529, 0),
    ("deficit", "October household change versus 2025", "latest.yoy.total_change", 244014, 0),
    (
        "deficit",
        "October change for one- and two-person households",
        "latest.yoy.small_change",
        220295,
        0,
    ),
    (
        "deficit",
        "share of net growth for one- and two-person households",
        "latest.yoy.small_share_of_net_change_pct",
        90.28,
        0.005,
    ),
    (
        "deficit",
        "October 2026 top four share of net household growth",
        "regional_october.2026-10-01.top4_share_pct",
        64.74,
        0.005,
    ),
    (
        "deficit",
        "October 2026 small-household share outside the top four",
        "regional_october.2026-10-01.rest_small_share_pct",
        98.34,
        0.005,
    ),
    (
        "deficit",
        "October 2026 territory count",
        "regional_october.2026-10-01.territories",
        19,
        0,
    ),
    (
        "deficit",
        "October 2026 territories with small-household majority of net growth",
        "regional_october.2026-10-01.small_majority",
        19,
        0,
    ),
    (
        "deficit",
        "minimum October territories with small-household majority of net growth",
        "regional_october_min_majority",
        18,
        0,
    ),
    (
        "deficit",
        "October 2021 small-household share",
        "small_share_first_to_last_october.start_share_pct",
        55.96,
        0.005,
    ),
    (
        "deficit",
        "October 2026 small-household share",
        "small_share_first_to_last_october.end_share_pct",
        57.77,
        0.005,
    ),
    (
        "deficit",
        "territories with rising small-household share from 2021 to 2026",
        "small_share_first_to_last_october.territories_with_rising_share",
        19,
        0,
    ),
    (
        "deficit",
        "within-territory contribution to small-household share shift",
        "small_share_first_to_last_october.within_territories_pp",
        1.84,
        0.005,
    ),
    (
        "deficit",
        "reweighting contribution to small-household share shift",
        "small_share_first_to_last_october.regional_reweighting_pp",
        -0.03,
        0.005,
    ),
    (
        "deficit",
        "October 2021 persons per household",
        "population_accounting.first_to_last_october.start_people_per_household",
        2.51,
        0.005,
    ),
    (
        "deficit",
        "October 2026 persons per household",
        "population_accounting.first_to_last_october.end_people_per_household",
        2.48,
        0.005,
    ),
    (
        "deficit",
        "2021–2026 household growth share from lower average size",
        "population_accounting.first_to_last_october.household_size_component_pct",
        19.16,
        0.005,
    ),
    (
        "deficit",
        "2025–2026 household growth share from lower average size",
        "population_accounting.october_yoy.2026-10-01.household_size_component_pct",
        30.28,
        0.005,
    ),
    (
        "deficit",
        "province and autonomous-city coverage",
        "local_family_accounting.first_to_last_october.territories",
        52,
        0,
    ),
    (
        "deficit",
        "lower average household size in 2021–2026",
        "local_family_accounting.first_to_last_october.territories_with_smaller_households",
        46,
        0,
    ),
    (
        "deficit",
        "local household gains with resident loss in 2021–2026",
        "local_family_accounting.first_to_last_october.households_rose_population_fell_count",
        5,
        0,
    ),
    (
        "deficit",
        "local household gains with resident loss in 2025–2026",
        "local_family_accounting.october_yoy.2026-10-01.households_rose_population_fell_count",
        2,
        0,
    ),
    (
        "deficit",
        "Zamora household count change in 2021–2026",
        "local_family_accounting.first_to_last_october.by_territory.Zamora.net_household_change",
        1457,
        0,
    ),
    (
        "deficit",
        "Zamora family-dwelling resident change in 2021–2026",
        "local_family_accounting.first_to_last_october.by_territory.Zamora.family_population_change",
        -2437,
        0,
    ),
    (
        "deficit",
        "2021–2025 matched stock territories",
        "aligned_stock_comparison.2021-2025.territories",
        51,
        0,
    ),
    (
        "deficit",
        "2021–2025 positive observed gaps",
        "aligned_stock_comparison.2021-2025.observed_gap_positive",
        49,
        0,
    ),
    (
        "deficit",
        "2021–2025 positive fixed-size gaps",
        "aligned_stock_comparison.2021-2025.fixed_size_gap_positive",
        27,
        0,
    ),
    (
        "deficit",
        "2021–2025 territories with fewer family-dwelling residents",
        "aligned_stock_comparison.2021-2025.fewer_residents",
        6,
        0,
    ),
    (
        "deficit",
        "2021–2025 positive household-and-stock gap despite fewer residents",
        "aligned_stock_comparison.2021-2025.fewer_residents_but_household_growth_exceeds_stock",
        5,
        0,
    ),
    (
        "deficit",
        "2021–2024 positive observed gaps",
        "aligned_stock_comparison.2021-2024.observed_gap_positive",
        50,
        0,
    ),
    (
        "deficit",
        "2021–2024 positive fixed-size gaps",
        "aligned_stock_comparison.2021-2024.fixed_size_gap_positive",
        24,
        0,
    ),
    (
        "deficit",
        "2021–2025 observed national stock gap",
        "aligned_stock_comparison.2021-2025.spain.observed_gap",
        746612,
        0,
    ),
    (
        "deficit",
        "2021–2025 national stock gap at fixed local household sizes",
        "aligned_stock_comparison.2021-2025.spain.fixed_local_size_gap",
        359113,
        0.5,
    ),
    (
        "deficit",
        "2021–2025 national stock gap at fixed pooled household size",
        "aligned_stock_comparison.2021-2025.spain.fixed_national_size_gap",
        368210,
        0.5,
    ),
    (
        "deficit",
        "2021-2024 observed top four share of positive gaps",
        "aligned_stock_comparison.2021-2024.positive_gap_concentration.observed.share_pct",
        43.18,
        0.005,
    ),
    (
        "deficit",
        "2021-2024 fixed_local_size top four share of positive gaps",
        "aligned_stock_comparison.2021-2024.positive_gap_concentration.fixed_local_size.share_pct",
        60.28,
        0.005,
    ),
    (
        "deficit",
        "2021-2025 observed top four share of positive gaps",
        "aligned_stock_comparison.2021-2025.positive_gap_concentration.observed.share_pct",
        42.1,
        0.005,
    ),
    (
        "deficit",
        "2021-2025 fixed_local_size top four share of positive gaps",
        "aligned_stock_comparison.2021-2025.positive_gap_concentration.fixed_local_size.share_pct",
        57.78,
        0.005,
    ),
    (
        "deficit",
        "2021–2025 observed top four positive gaps",
        "aligned_stock_comparison.2021-2025.positive_gap_concentration.observed.group_positive_gap",
        314532,
        0,
    ),
    (
        "deficit",
        "2021–2025 fixed_local_size top four positive gaps",
        "aligned_stock_comparison.2021-2025.positive_gap_concentration.fixed_local_size.group_positive_gap",
        249788,
        0.5,
    ),
    (
        "deficit",
        "Calendar 2025 household change",
        "aligned_stock_comparison.2025.spain.household_change",
        240932,
        0,
    ),
    (
        "deficit",
        "Calendar 2025 stock change",
        "aligned_stock_comparison.2025.spain.stock_change",
        94791,
        0,
    ),
    (
        "deficit",
        "Calendar 2025 observed gap",
        "aligned_stock_comparison.2025.spain.observed_gap",
        146141,
        0,
    ),
    (
        "deficit",
        "Calendar 2025 fixed local size gap",
        "aligned_stock_comparison.2025.spain.fixed_local_size_gap",
        86631,
        0.5,
    ),
    (
        "deficit",
        "Calendar 2025 territory coverage",
        "aligned_stock_comparison.2025.territories",
        51,
        0,
    ),
    (
        "deficit",
        "Calendar 2025 observed positive gaps",
        "aligned_stock_comparison.2025.observed_gap_positive",
        50,
        0,
    ),
    (
        "deficit",
        "Calendar 2025 fixed local size positive gaps",
        "aligned_stock_comparison.2025.fixed_size_gap_positive",
        43,
        0,
    ),
    (
        "deficit",
        "Calendar 2021 observed gap",
        "aligned_stock_comparison.2021.spain.observed_gap",
        186648,
        0,
    ),
    (
        "deficit",
        "Calendar 2021 fixed local size gap",
        "aligned_stock_comparison.2021.spain.fixed_local_size_gap",
        -66226,
        0.5,
    ),
    (
        "deficit",
        "Calendar 2022 observed gap",
        "aligned_stock_comparison.2022.spain.observed_gap",
        188926,
        0,
    ),
    (
        "deficit",
        "Calendar 2022 fixed local size gap",
        "aligned_stock_comparison.2022.spain.fixed_local_size_gap",
        139332,
        0.5,
    ),
    (
        "deficit",
        "Calendar 2023 observed gap",
        "aligned_stock_comparison.2023.spain.observed_gap",
        120905,
        0,
    ),
    (
        "deficit",
        "Calendar 2023 fixed local size gap",
        "aligned_stock_comparison.2023.spain.fixed_local_size_gap",
        116068,
        0.5,
    ),
    (
        "deficit",
        "Calendar 2024 observed gap",
        "aligned_stock_comparison.2024.spain.observed_gap",
        103992,
        0,
    ),
    (
        "deficit",
        "Calendar 2024 fixed local size gap",
        "aligned_stock_comparison.2024.spain.fixed_local_size_gap",
        94359,
        0.5,
    ),
    (
        "deficit",
        "2024–2025 annual observed gap increase",
        "annual_gap_change.2024-2025.observed_gap_change",
        42149,
        0,
    ),
    (
        "deficit",
        "2024–2025 slower stock growth contribution",
        "annual_gap_change.2024-2025.stock_contribution",
        7531,
        0,
    ),
    (
        "deficit",
        "2024–2025 population growth contribution at starting household sizes",
        "annual_gap_change.2024-2025.population_at_starting_size_contribution",
        -15260,
        0,
    ),
    (
        "deficit",
        "2024–2025 household-size residual contribution",
        "annual_gap_change.2024-2025.household_size_residual_contribution",
        49878,
        0,
    ),
    (
        "deficit",
        "2024–2025 territories with wider gaps",
        "annual_gap_change.2024-2025.territories_with_wider_gap",
        40,
        0,
    ),
    (
        "deficit",
        "2024–2025 Madrid observed gap increase",
        "annual_gap_change.2024-2025.by_territory.Madrid",
        12234,
        0,
    ),
    (
        "deficit",
        "2024 completions",
        "completion_crosscheck_2024_2025.by_year.2024.completions",
        100980,
        0,
    ),
    (
        "deficit",
        "2025 completions",
        "completion_crosscheck_2024_2025.by_year.2025.completions",
        93650,
        0,
    ),
    (
        "deficit",
        "2024 households minus completions",
        "completion_crosscheck_2024_2025.by_year.2024.households_minus_completions",
        105334,
        0,
    ),
    (
        "deficit",
        "2025 households minus completions",
        "completion_crosscheck_2024_2025.by_year.2025.households_minus_completions",
        147282,
        0,
    ),
    (
        "deficit",
        "2024–2025 increase in household-completion gap",
        "completion_crosscheck_2024_2025.completion_gap_change",
        41948,
        0,
    ),
    (
        "deficit",
        "2024 missing completion cells",
        "completion_crosscheck_2024_2025.by_year.2024.completion_cells_missing",
        0,
        0,
    ),
    (
        "deficit",
        "2025 missing completion cells",
        "completion_crosscheck_2024_2025.by_year.2025.completion_cells_missing",
        0,
        0,
    ),
    (
        "deficit",
        "areas with paired gaps",
        "completion_crosscheck_2024_2025.local.areas_with_paired_completion_gaps",
        51,
        0,
    ),
    (
        "deficit",
        "areas with matching change direction",
        "completion_crosscheck_2024_2025.local.areas_with_matching_direction",
        51,
        0,
    ),
    (
        "deficit",
        "areas where both gaps widened",
        "completion_crosscheck_2024_2025.local.areas_with_both_gaps_widening",
        40,
        0,
    ),
    (
        "deficit",
        "areas with different gap signs in 2025",
        "completion_crosscheck_2024_2025.local.areas_with_different_end_signs",
        1,
        0,
    ),
    (
        "deficit",
        "2025 Soria stock gap",
        "completion_crosscheck_2024_2025.local.by_territory.Soria.stock_gap_end",
        14,
        0,
    ),
    (
        "deficit",
        "2025 Soria completion gap",
        "completion_crosscheck_2024_2025.local.by_territory.Soria.completion_gap_end",
        -15,
        0,
    ),
    (
        "deficit",
        "areas with matching supply directions",
        "completion_crosscheck_2024_2025.local.areas_with_matching_supply_direction",
        50,
        0,
    ),
    (
        "deficit",
        "Toledo change in net stock growth",
        "completion_crosscheck_2024_2025.local.by_territory.Toledo.net_stock_growth_change",
        19,
        0,
    ),
    (
        "deficit",
        "Toledo change in completions",
        "completion_crosscheck_2024_2025.local.by_territory.Toledo.completion_flow_change",
        -41,
        0,
    ),
]


CONTRAST_CLAIMS: list[tuple[str, str, str, float, float]] = [
    (
        "contrast",
        "Barcelona declared rental contracts 2011",
        "barcelona_city.serpavi_contracts.2011.total",
        82608,
        0,
    ),
    (
        "contrast",
        "Barcelona declared rental contracts 2019",
        "barcelona_city.serpavi_contracts.2019.total",
        127241,
        0,
    ),
    (
        "contrast",
        "Barcelona declared rental contracts 2021",
        "barcelona_city.serpavi_contracts.2021.total",
        133074,
        0,
    ),
    (
        "contrast",
        "Barcelona declared rental contracts 2024",
        "barcelona_city.serpavi_contracts.2024.total",
        143159,
        0,
    ),
    (
        "contrast",
        "Barcelona collective-housing contracts 2024",
        "barcelona_city.serpavi_contracts.2024.collective",
        140872,
        0,
    ),
    (
        "contrast",
        "Barcelona single-family contracts 2024",
        "barcelona_city.serpavi_contracts.2024.single_family",
        2287,
        0,
    ),
    (
        "contrast",
        "declared contract growth 2011-2024 pct",
        "verdicts.contracts_growth_pct_2011_2024",
        73.3,
        0.05,
    ),
    (
        "contrast",
        "deposit entries in the overlap year",
        "barcelona_city.incasol_entries.2024",
        32903,
        0,
    ),
    (
        "contrast",
        "declared stock change 2019",
        "reconciliation.2019.declared_stock_change",
        2742,
        0,
    ),
    (
        "contrast",
        "balance minus stock change 2019",
        "reconciliation.2019.balance_minus_change",
        844,
        0,
    ),
    (
        "contrast",
        "declared stock change 2020",
        "reconciliation.2020.declared_stock_change",
        2414,
        0,
    ),
    (
        "contrast",
        "balance minus stock change 2020",
        "reconciliation.2020.balance_minus_change",
        -7234,
        0,
    ),
    (
        "contrast",
        "declared stock change 2021",
        "reconciliation.2021.declared_stock_change",
        3419,
        0,
    ),
    (
        "contrast",
        "balance minus stock change 2021",
        "reconciliation.2021.balance_minus_change",
        6242,
        0,
    ),
    (
        "contrast",
        "declared stock change 2022",
        "reconciliation.2022.declared_stock_change",
        2689,
        0,
    ),
    (
        "contrast",
        "balance minus stock change 2022",
        "reconciliation.2022.balance_minus_change",
        6384,
        0,
    ),
    (
        "contrast",
        "declared stock change 2023",
        "reconciliation.2023.declared_stock_change",
        4766,
        0,
    ),
    (
        "contrast",
        "balance minus stock change 2023",
        "reconciliation.2023.balance_minus_change",
        1744,
        0,
    ),
    (
        "contrast",
        "declared stock change 2024",
        "reconciliation.2024.declared_stock_change",
        2630,
        0,
    ),
    (
        "contrast",
        "balance minus stock change 2024",
        "reconciliation.2024.balance_minus_change",
        94,
        0,
    ),
    (
        "contrast",
        "municipalities in the spread check",
        "municipal_spread.n_municipios",
        308,
        0,
    ),
    (
        "contrast",
        "municipalities that rose",
        "municipal_spread.rising",
        308,
        0,
    ),
    (
        "contrast",
        "municipalities rising every year",
        "municipal_spread.monotone",
        295,
        0,
    ),
    (
        "contrast",
        "median municipal contract growth pct",
        "municipal_spread.median_growth_pct",
        59.4,
        0.05,
    ),
    (
        "contrast",
        "smallest municipal contract growth pct",
        "municipal_spread.min_growth_pct",
        17.9,
        0.05,
    ),
    (
        "contrast",
        "Madrid contracts 2015",
        "municipal_spread.largest.0.first",
        191435,
        0,
    ),
    (
        "contrast",
        "Madrid contracts 2024",
        "municipal_spread.largest.0.last",
        300447,
        0,
    ),
    (
        "contrast",
        "Madrid contract growth pct",
        "municipal_spread.largest.0.growth_pct",
        56.9,
        0.05,
    ),
    (
        "contrast",
        "Barcelona contracts 2015",
        "municipal_spread.largest.1.first",
        104971,
        0,
    ),
    (
        "contrast",
        "Barcelona contract growth pct",
        "municipal_spread.largest.1.growth_pct",
        34.2,
        0.05,
    ),
    (
        "contrast",
        "Valencia contracts 2015",
        "municipal_spread.largest.2.first",
        39267,
        0,
    ),
    (
        "contrast",
        "Valencia contracts 2024",
        "municipal_spread.largest.2.last",
        65742,
        0,
    ),
    (
        "contrast",
        "Valencia contract growth pct",
        "municipal_spread.largest.2.growth_pct",
        67.4,
        0.05,
    ),
    (
        "contrast",
        "closest reconciliation gap",
        "verdicts.reconciliation_closest_gap",
        94,
        0,
    ),
]


VUT_SEASONAL_CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("occupancy", "tourist dwellings peak", "verdicts.peak_value", 63199, 0),
    ("occupancy", "tourist dwellings trough", "verdicts.trough_value", 45709, 0),
    ("occupancy", "tourist dwellings latest", "verdicts.latest_value", 51305, 0),
    (
        "occupancy",
        "tourist dwellings same month prior",
        "verdicts.same_month_prior_value",
        56851,
        0,
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
    policy = _model_output("artifacts/catalonia_rent_control.json")
    for doc, desc, path, expected, tol in POLICY_EVAL_CLAIMS:
        got = _json_path(policy, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(POLICY_EVAL_CLAIMS)
    microsim = _model_output("artifacts/ecv_microsim.json")
    for doc, desc, path, expected, tol in MICROSIM_CLAIMS:
        got = _json_path(microsim, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(MICROSIM_CLAIMS)
    ledger = _model_output("artifacts/claim_ledger.json")
    for doc, desc, claim_id, needle, expected, tol in LEDGER_CLAIMS:
        hits = [
            r for r in ledger["bridges"] if r["claim_id"] == claim_id and needle in r["definition"]
        ]
        got = hits[0]["value_num"] if len(hits) == 1 else None
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        if got is None:
            print(f"    ({len(hits)} bridge rows match {claim_id} / {needle!r})")
        failures += not ok
    total += len(LEDGER_CLAIMS)
    irav = _model_output("artifacts/irav.json")
    for doc, desc, path, expected, tol in IRAV_CLAIMS:
        got = _json_path(irav, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(IRAV_CLAIMS)
    ipva = _model_output("artifacts/ipva_rent_index.json")
    for doc, desc, path, expected, tol in IPVA_CLAIMS:
        got = _json_path(ipva, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(IPVA_CLAIMS)
    proh = _model_output("artifacts/proh_households.json")
    for doc, desc, path, expected, tol in PROH_CLAIMS:
        got = _json_path(proh, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(PROH_CLAIMS)
    ecp = _model_output("artifacts/ecp_households.json")
    for doc, desc, path, expected, tol in ECP_HOUSEHOLD_CLAIMS:
        got = _json_path(ecp, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(ECP_HOUSEHOLD_CLAIMS)
    occupancy = _model_output("artifacts/occupancy_catalonia.json")
    for doc, desc, path, expected, tol in OCCUPANCY_CLAIMS:
        got = _json_path(occupancy, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(OCCUPANCY_CLAIMS)
    contrast = _model_output("artifacts/serpavi_deposit_contrast.json")
    for doc, desc, path, expected, tol in CONTRAST_CLAIMS:
        got = _json_path(contrast, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(CONTRAST_CLAIMS)
    tourist_seasonal = _model_output("artifacts/vut_seasonal_deposits.json")
    for doc, desc, path, expected, tol in VUT_SEASONAL_CLAIMS:
        got = _json_path(tourist_seasonal, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(VUT_SEASONAL_CLAIMS)
    vut = _model_output("artifacts/vut_stock.json")
    for doc, desc, path, expected, tol in VUT_CLAIMS:
        got = _json_path(vut, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(VUT_CLAIMS)
    vut_rent = _model_output("artifacts/vut_rent_overlap.json")
    for doc, desc, path, expected, tol in VUT_RENT_CLAIMS:
        got = _json_path(vut_rent, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] {doc}: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += len(VUT_RENT_CLAIMS)
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
        ("rent n 2024", "rent_geo_2024.n", 2512, 0),
        ("rent max level", "rent_geo_2024.max.rent", 14.63, 0.02),
        ("rent min level", "rent_geo_2024.min.rent", 1.84, 0.02),
        ("growth n", "rent_growth_2011_2024.n", 1676, 0),
        ("growth median pct", "rent_growth_2011_2024.median_pct", 29.0, 0.1),
        ("fastest growth pct", "rent_growth_2011_2024.fastest.growth_pct", 223.4, 0.1),
        ("rent-vac pearson", "rent_vs_vacancy.pearson", -0.393, 0.005),
        ("rent-vac spearman", "rent_vs_vacancy.spearman", -0.434, 0.005),
        ("rent-vac n", "rent_vs_vacancy.n", 1927, 0),
        ("pop-rent pearson", "pop_vs_rent_growth.pearson", 0.051, 0.005),
        ("pop-rent spearman", "pop_vs_rent_growth.spearman", 0.115, 0.005),
        ("pop-rent n", "pop_vs_rent_growth.n", 1676, 0),
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
    dv = _model_output("artifacts/deficit_vivienda.json")
    for desc, path, expected, tol in (
        ("deficit v2 2021-2024", "windows.2021-2024.national.deficit_v2", 606955, 0),
        ("deficit v2 2021-2025", "windows.2021-2025.national.deficit_v2", 754237, 0),
        ("deficit v3p 2021-2024", "windows.2021-2024.national.deficit_v3p", 551988, 0),
        ("deficit v3p 2021-2025", "windows.2021-2025.national.deficit_v3p", 745969, 0),
        ("deficit top5 share 2021-2024", "windows.2021-2024.national.top5_share", 0.4826, 0.00005),
        ("deficit benchmark v2 2021-2024", "windows.2021-2024.benchmark.caixabank_v2", 600000, 0),
        ("deficit benchmark v2 2021-2025", "windows.2021-2025.benchmark.caixabank_v2", 734000, 0),
        ("deficit delta v2 2021-2024", "windows.2021-2024.benchmark.delta", 6955, 0),
        ("deficit delta v2 2021-2025", "windows.2021-2025.benchmark.delta", 20237, 0),
    ):
        got = _json_path(dv, path)
        ok = got is not None and abs(got - expected) <= tol
        print(f"[{'OK' if ok else 'FAIL'}] deficit_vivienda: {desc} = {got} (doc: {expected})")
        failures += not ok
    total += 9
    # List-integrity checks (ranking order, exception set): verified and
    # printed, but intentionally outside the value-claim denominator — the
    # doc-number audit matches numeric expectations only.
    for desc, path, expected in (
        (
            "deficit top5 keys 2021-2024",
            "windows.2021-2024.national.top5_keys",
            ["28", "08", "46", "03", "30"],
        ),
        (
            "deficit negatives 2021-2024",
            "windows.2021-2024.national.negative_keys",
            ["42"],
        ),
    ):
        got = _json_path(dv, path)
        ok = got == expected
        print(f"[{'OK' if ok else 'FAIL'}] deficit_vivienda: {desc} = {got} (doc: {expected})")
        failures += not ok
    print(f"{total - failures}/{total} claims hold")
    fresh_failures = check_freshness()
    total += len(MODEL_FRESHNESS)
    print(f"{len(MODEL_FRESHNESS) - fresh_failures}/{len(MODEL_FRESHNESS)} model outputs fresh")
    return 1 if (failures or fresh_failures) else 0


if __name__ == "__main__":
    sys.exit(main())
