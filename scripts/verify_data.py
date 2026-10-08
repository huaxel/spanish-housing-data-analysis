"""Verify pinned inputs and mart integrity. Fails loudly; never imputes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import duckdb  # noqa: E402

from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import MANIFEST, MARTS_DB, PROCESSED  # noqa: E402


def main() -> int:
    if not MANIFEST.exists():
        print("no data/input_manifest.json — run make fetch")
        return 1
    man = manifest.load()
    missing, mismatched = manifest.check(man.get("sha256", {}))
    if missing or mismatched:
        print(f"FAIL missing={missing} mismatched={mismatched}")
        return 1
    print(f"manifest OK: {len(man['sha256'])} pinned files")
    age = manifest.snapshot_age_days(man)
    warn_days = int(os.environ.get("MANIFEST_WARN_DAYS", "90"))
    if age is None:
        print("WARNING: manifest snapshot_date missing/unparseable")
    else:
        print(f"manifest snapshot: {man['snapshot_date']} ({age}d old)")
        if age > warn_days:
            print(
                f"WARNING: snapshot is {age}d old (> {warn_days}d) — "
                "re-run make fetch to refresh (upstream tables get revised)"
            )
    if not MARTS_DB.exists():
        print("marts.duckdb absent — run make build")
        return 1
    con = duckdb.connect(str(MARTS_DB), read_only=True)
    prov = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT cpro), MIN(anyo), MAX(anyo), "
        "SUM(CASE WHEN poblacion IS NULL OR viviendas_total IS NULL "
        "THEN 1 ELSE 0 END) FROM mart_provincia_anual"
    ).fetchone()
    ccaa = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT ccaa), MIN(anyo), MAX(anyo) FROM mart_ccaa_anual"
    ).fetchone()
    null_ipv = con.execute(
        "SELECT COUNT(*) FROM mart_ccaa_anual WHERE ipv_general IS NULL"
    ).fetchone()[0]
    neg = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE poblacion <= 0 OR viviendas_total <= 0"
    ).fetchone()[0]
    print(
        f"mart_provincia_anual: rows={prov[0]} cpro={prov[1]} "
        f"years={prov[2]}–{prov[3]} nulls={prov[4]}"
    )
    srcs = con.execute("SELECT DISTINCT pop_source FROM mart_ccaa_anual").fetchall()
    hog = con.execute(
        "SELECT COUNT(*), SUM(CASE WHEN hogares IS NULL THEN 1 ELSE 0 END) FROM mart_ccaa_anual"
    ).fetchone()
    pre_hog = con.execute(
        "SELECT COUNT(*) FROM mart_ccaa_anual WHERE anyo < 2021 AND hogares IS NOT NULL"
    ).fetchone()[0]
    print(
        f"mart_ccaa_anual: rows={ccaa[0]} ccaa={ccaa[1]} years={ccaa[2]}–{ccaa[3]} "
        f"null_ipv={null_ipv} sources={sorted(s[0] for s in srcs)} "
        f"hog_null={hog[1]}/{hog[0]}"
    )
    assert prov[1] == 51, f"expected 50 provinces + Ceuta y Melilla, got {prov[1]}"
    assert prov[4] == 0 and neg == 0, "null/non-positive cells in provincia mart"
    assert {s[0] for s in srcs} == {"padron", "ecp"}, f"pop splice broken: {srcs}"
    assert ccaa[2] == 2007 and ccaa[3] == 2025, f"ccaa years drifted: {ccaa[2:4]}"
    assert pre_hog == 0 or set(
        r[0]
        for r in con.execute(
            "SELECT DISTINCT anyo FROM mart_ccaa_anual WHERE anyo < 2021 AND hogares IS NOT NULL"
        ).fetchall()
    ) <= {2011, 2014, 2015, 2016, 2017, 2018, 2019, 2020}, (
        "pre-2021 hogares allowed only for census-2011 + ECH 2014-2020"
    )
    ech_null = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual "
        "WHERE anyo BETWEEN 2014 AND 2020 AND hogares IS NULL"
    ).fetchone()[0]
    assert ech_null == 0, "ECH households must be complete (51 x 7)"
    vt = con.execute(
        "SELECT COUNT(*), SUM(CASE WHEN eur_m2_libre IS NULL THEN 1 ELSE 0 END), "
        "MIN(anyo), MAX(anyo) FROM mart_ccaa_anual"
    ).fetchone()
    vt_srcs = con.execute("SELECT DISTINCT vt_source FROM mart_provincia_anual").fetchall()
    print(f"valor tasado: ccaa rows={vt[0]} null_eur={vt[1]} years={vt[2]}–{vt[3]} ")
    print(f"prov vt sources: {sorted(s[0] for s in vt_srcs if s[0])}")
    prov_null = con.execute(
        "SELECT cpro, MIN(anyo), MAX(anyo), COUNT(*) FROM mart_provincia_anual "
        "WHERE eur_m2_libre IS NULL GROUP BY 1"
    ).fetchall()
    print(f"prov cells without valor (upstream unpublished): {prov_null}")
    null_cells = con.execute(
        "SELECT ccaa, MIN(anyo), MAX(anyo) FROM mart_ccaa_anual "
        "WHERE eur_m2_libre IS NULL GROUP BY 1"
    ).fetchall()
    print(f"ccaa cells without valor: {null_cells}")
    assert {s[0] for s in vt_srcs if s[0]} <= {"prov_direct", "ccaa_direct", "ccaa_fill"}
    # CCAA mart excludes Ceuta y Melilla (aggregated stock); every other
    # cell must have valor tasado (single-province CCAA fall back to prov_fill).
    assert null_cells == [], f"unexpected valor gaps: {null_cells}"
    aff = con.execute(
        "SELECT COUNT(*), SUM(CASE WHEN renta_hogar_neta IS NULL THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN afford_90m2_years IS NULL THEN 1 ELSE 0 END) "
        "FROM mart_ccaa_anual"
    ).fetchone()
    aff_2025 = con.execute(
        "SELECT COUNT(*) FROM mart_ccaa_anual WHERE anyo = 2025 AND renta_hogar_neta IS NOT NULL"
    ).fetchone()[0]
    print(f"affordability: rows={aff[0]} null_renta={aff[1]} null_afford={aff[2]}")
    # Renta runs to 2024 (ECV lag) while the mart runs to 2025: only 2025 may lack it.
    assert aff[1] == 18 and aff_2025 == 0, f"renta gaps outside 2025: null={aff[1]}"
    young = con.execute(
        "SELECT COUNT(*), SUM(CASE WHEN pob_20_34 IS NULL THEN 1 ELSE 0 END) FROM mart_ccaa_anual"
    ).fetchone()
    print(f"young cohort 20-34: rows={young[0]} null={young[1]}")
    assert young[1] == 0, "pob_20_34 must be complete 2007-2025"
    solo = con.execute(
        "SELECT SUM(CASE WHEN hog_1persona IS NULL THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN hog_1persona > hogares THEN 1 ELSE 0 END) "
        "FROM mart_ccaa_anual WHERE anyo >= 2021"
    ).fetchone()
    print(f"solo households 2021+: null={solo[0]} over-total={solo[1]}")
    assert solo == (0, 0), "solo-household cells broken"
    hip = con.execute(
        "SELECT SUM(CASE WHEN hip_viv_num IS NULL THEN 1 ELSE 0 END) FROM mart_ccaa_anual"
    ).fetchone()[0]
    hip_prov_pre = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE anyo < 2003 AND hip_viv_num IS NOT NULL"
    ).fetchone()[0]
    hip_prov_post = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE anyo >= 2003 AND hip_viv_num IS NULL"
    ).fetchone()[0]
    print(
        f"mortgages: ccaa null={hip}, prov null-pre2003={hip_prov_pre}, "
        f"prov null-post2003={hip_prov_post}"
    )
    # Mortgages start 2003; the CCAA mart starts 2007, so it must be complete.
    assert hip == 0, "ccaa mortgages must be complete 2007-2025"
    assert hip_prov_pre == 0 and hip_prov_post == 0, "prov mortgages must cover 2003-2025"
    tur_cc = con.execute(
        "SELECT COUNT(*) FROM mart_ccaa_anual WHERE anyo >= 2020 AND viv_turisticas IS NULL"
    ).fetchone()[0]
    tur_cc_pre = con.execute(
        "SELECT COUNT(*) FROM mart_ccaa_anual WHERE anyo < 2020 AND viv_turisticas IS NOT NULL"
    ).fetchone()[0]
    tur_pr = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE anyo >= 2020 AND viv_turisticas IS NULL"
    ).fetchone()[0]
    print(
        f"tourist dwellings: ccaa null-post2020={tur_cc}, ccaa pre2020-leak={tur_cc_pre}, "
        f"prov null-post2020={tur_pr}"
    )
    assert tur_cc == 0 and tur_cc_pre == 0, "ccaa tourist must cover 2020-2025 only"
    assert tur_pr == 0, "prov tourist must cover 2020-2025"
    mun = con.execute(
        "SELECT COUNT(DISTINCT municipio), MIN(anyo), MAX(anyo) FROM valor_municipal_madrid"
    ).fetchone()
    mun_cap = con.execute(
        "SELECT COUNT(*), MIN(anyo), MAX(anyo) FROM valor_municipal_madrid WHERE codigo = '0796'"
    ).fetchone()
    print(
        f"municipal madrid: municipios={mun[0]} years={mun[1]}-{mun[2]}; "
        f"capital years={mun_cap[1]}-{mun_cap[2]} ({mun_cap[0]} rows)"
    )
    assert mun_cap[0] == mun_cap[2] - mun_cap[1] + 1, "capital must be complete"
    bar = con.execute("SELECT MIN(anyo), MAX(anyo), COUNT(*) FROM barrios_madrid").fetchone()
    bar_city = con.execute(
        "SELECT eur_m2 FROM barrios_madrid WHERE distrito='Ciudad de Madrid' "
        "AND barrio='Ciudad de Madrid' AND anyo=2025 AND tipo='Total'"
    ).fetchone()[0]
    bar_top = con.execute(
        "SELECT barrio, eur_m2 FROM barrios_madrid WHERE anyo=2025 AND tipo='Total' "
        "ORDER BY eur_m2 DESC LIMIT 1"
    ).fetchone()
    print(
        f"barrios_madrid: years={bar[0]}-{bar[1]} rows={bar[2]}; "
        f"city 2025={bar_city}; top={bar_top}"
    )
    assert (bar[0], bar[1]) == (2007, 2025), f"barrio window broken: {bar}"
    assert bar_city == 5285.72, f"barrio city drifted: {bar_city}"
    assert bar_top[0] == "041. Recoletos", f"barrio top moved: {bar_top}"
    sevbar = con.execute(
        "SELECT COUNT(DISTINCT idg), MIN(anyo), MAX(anyo), COUNT(*) FROM barrios_sevilla"
    ).fetchone()
    sevbar_anchor = con.execute(
        "SELECT ipra_eur_m2 FROM barrios_sevilla WHERE barrio='ALFALFA' AND anyo=2022"
    ).fetchone()[0]
    print(f"barrios_sevilla: barrios={sevbar[0]} years={sevbar[1]}-{sevbar[2]} rows={sevbar[3]}")
    assert sevbar == (108, 2016, 2022, 756), f"Sevilla IPRA coverage broken: {sevbar}"
    assert sevbar_anchor == 6.8, f"Sevilla IPRA anchor drifted: {sevbar_anchor}"
    sev_compra = con.execute(
        "SELECT COUNT(*), COUNT(*) FILTER (WHERE compra_unifamiliar_eur_m2 IS NULL), "
        "MIN(compra_colectiva_eur_m2), MAX(compra_colectiva_eur_m2) "
        "FROM barrios_sevilla_compra"
    ).fetchone()
    assert sev_compra == (108, 31, 796, 2585), (
        f"Sevilla SIM purchase coverage drifted: {sev_compra}"
    )
    sev_offer = con.execute(
        "SELECT COUNT(*), MIN(anyo), MAX(anyo), MIN(precio_oferta_eur_m2), "
        "MAX(precio_oferta_eur_m2) FROM sevilla_oferta_zona"
    ).fetchone()
    offer_areas = con.execute(
        "SELECT provider, COUNT(DISTINCT zona) FROM sevilla_oferta_zona "
        "GROUP BY provider ORDER BY provider"
    ).fetchall()
    assert sev_offer == (336, 2024, 2024, 665.0, 3876.0), (
        f"Sevilla offer-price coverage drifted: {sev_offer}"
    )
    assert offer_areas == [("Fotocasa", 11), ("Idealista", 17)], (
        f"Sevilla offer-price geographies drifted: {offer_areas}"
    )
    sev_pob_hog = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT idg), MIN(anyo), MAX(anyo), "
        "COUNT(*) FILTER (WHERE poblacion IS NULL), "
        "COUNT(*) FILTER (WHERE hogares IS NULL) "
        "FROM sevilla_sim_poblacion_hogares"
    ).fetchone()
    assert sev_pob_hog == (756, 108, 2015, 2021, 0, 0), (
        f"Sevilla SIM population/household coverage drifted: {sev_pob_hog}"
    )
    sev_pob_anchor = con.execute(
        "SELECT poblacion, hogares FROM sevilla_sim_poblacion_hogares "
        "WHERE barrio='ALFALFA' AND anyo=2015"
    ).fetchone()
    assert sev_pob_anchor == (4479, 1972), f"SIM 2015 Alfalfa anchor drifted: {sev_pob_anchor}"
    sev_housing = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT idg), "
        "COUNT(*) FILTER (WHERE rehabilitacion_estimada IS NULL), "
        "COUNT(*) FILTER (WHERE deshabitadas IS NULL), "
        "COUNT(*) FILTER (WHERE unifamiliares IS NULL) "
        "FROM sevilla_sim_vivienda"
    ).fetchone()
    assert sev_housing == (108, 108, 6, 7, 30), (
        f"Sevilla SIM housing snapshot coverage drifted: {sev_housing}"
    )
    sev_housing_anchor = con.execute(
        "SELECT deshabitadas_pct, rehabilitacion_estimada_pct "
        "FROM sevilla_sim_vivienda WHERE barrio='ALFALFA'"
    ).fetchone()
    assert sev_housing_anchor == (7, 4), f"SIM Alfalfa housing anchor drifted: {sev_housing_anchor}"
    sev_tourism = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT idg), "
        "COUNT(*) FILTER (WHERE vft_2022_02_pct IS NULL) "
        "FROM sevilla_sim_turismo"
    ).fetchone()
    assert sev_tourism == (108, 108, 70), (
        f"Sevilla SIM tourism snapshot coverage drifted: {sev_tourism}"
    )
    sev_tourism_anchor = con.execute(
        "SELECT vft_2008, vft_2022_02 FROM sevilla_sim_turismo WHERE barrio='ALFALFA'"
    ).fetchone()
    assert sev_tourism_anchor == (557, 482), (
        f"SIM Alfalfa tourist-housing anchor drifted: {sev_tourism_anchor}"
    )
    print(
        "Sevilla SIM context: 108 barrios; population/households 2015–2021; "
        f"undated housing snapshot nulls={sev_housing[2:5]}; "
        f"tourism 2022-02 pressure nulls={sev_tourism[2]}"
    )
    bcn_anual = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT codi), MIN(anyo), MAX(anyo), "
        "COUNT(*) FILTER (WHERE ambit='barri' AND contractes IS NULL), "
        "COUNT(*) FILTER (WHERE ambit='barri' AND anyo < 2013 AND contractes IS NOT NULL) "
        "FROM barrios_bcn_lloguer_anual"
    ).fetchone()
    assert bcn_anual == (2184, 84, 2000, 2025, 949, 0), (
        f"Barcelona INCASÒL annual coverage drifted: {bcn_anual}"
    )
    bcn_anchor = con.execute(
        "SELECT contractes, ROUND(lloguer_m2, 2) FROM barrios_bcn_lloguer_anual "
        "WHERE codi='BCN' AND anyo=2024"
    ).fetchone()
    assert bcn_anchor == (32903, 16.13), f"Barcelona 2024 anchor drifted: {bcn_anchor}"
    bcn_barri_anchor = con.execute(
        "SELECT ROUND(lloguer_m2, 2) FROM barrios_bcn_lloguer_anual "
        "WHERE nom='la Barceloneta' AND anyo=2025"
    ).fetchone()
    assert bcn_barri_anchor == (22.70,), f"Barceloneta 2025 anchor drifted: {bcn_barri_anchor}"
    bcn_trim = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT codi), MIN(anyo), MAX(anyo) "
        "FROM barrios_bcn_lloguer_trimestral"
    ).fetchone()
    assert bcn_trim == (4984, 84, 2000, 2026), (
        f"Barcelona INCASÒL quarterly coverage drifted: {bcn_trim}"
    )
    print(
        "Barcelona INCASÒL: city+10 districts 2000–, 73 barris (annual 2013–, "
        "quarterly 2014–); filed contracts, <6-contract cells null"
    )
    bcn_compra = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT codi), MIN(anyo), MAX(anyo), "
        "COUNT(*) FILTER (WHERE eur_m2_total IS NULL) "
        "FROM barrios_bcn_compraventes"
    ).fetchone()
    assert bcn_compra == (2520, 84, 2018, 2026, 128), (
        f"Barcelona compravendes coverage drifted: {bcn_compra}"
    )
    bcn_compra_anchor = con.execute(
        "SELECT trx_total, eur_m2_total FROM barrios_bcn_compraventes "
        "WHERE codi='BCN' AND anyo=2024 AND trimestre=4"
    ).fetchone()
    assert bcn_compra_anchor == (4368, 4622.43), (
        f"Barcelona 2024Q4 sales anchor drifted: {bcn_compra_anchor}"
    )
    print(
        "Barcelona Registradores: city+10 districts+73 barris quarterly; "
        "zero prices stored as null (<3 contracts); city total non-additive"
    )
    serp_dist = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT distrito), "
        "COUNT(DISTINCT codigo), MIN(anyo), MAX(anyo) "
        "FROM serpavi_distritos"
    ).fetchone()
    assert serp_dist == (1099206, 9680, 7332, 2011, 2024), (
        f"SERPAVI district coverage drifted: {serp_dist}"
    )
    salamanca = con.execute(
        "SELECT ROUND(valor, 2) FROM serpavi_distritos WHERE distrito='2807904' "
        "AND anyo=2024 AND medida='ALQM2_LV_M_VC'"
    ).fetchone()
    assert salamanca == (18.31,), f"Salamanca 2024 anchor drifted: {salamanca}"
    print("SERPAVI distritos: 9,680 districts with data (codes only, no names)")
    desah = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT provincia), MIN(anyo), MAX(anyo), "
        "SUM(lanz_total) FILTER (WHERE anyo=2025), "
        "SUM(lanz_total) FILTER (WHERE anyo=2020 AND trimestre=2) "
        "FROM desahucios_provincia"
    ).fetchone()
    assert desah == (3850, 50, 2007, 2026, 24540, 1383), f"CGPJ launch coverage drifted: {desah}"
    # Upstream off-by-one in a single cell (Almería 2022Q4: total 252 vs 89+136+28);
    # pinned so any new mismatch fails loudly instead of passing silently.
    desah_add = con.execute(
        "SELECT provincia, anyo, trimestre FROM desahucios_provincia "
        "WHERE lanz_hipoteca + lanz_lau + lanz_otros != lanz_total"
    ).fetchall()
    assert desah_add == [("Almería", 2022, 4)], f"launch split drifted: {desah_add}"
    desah_anchor = con.execute(
        "SELECT lanz_total FROM desahucios_provincia "
        "WHERE provincia='Cádiz' AND anyo=2024 AND trimestre=4"
    ).fetchone()
    assert desah_anchor == (141,), f"Cádiz 2024Q4 launch anchor drifted: {desah_anchor}"
    print("CGPJ launches: 50 provinces, 2013Q1–2026Q1; foreclosures 2007Q1–")
    serp_prov = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT provincia), MIN(anyo), MAX(anyo) FROM serpavi_provincial"
    ).fetchone()
    assert serp_prov == (13620, 52, 2011, 2024), f"SERPAVI provincial coverage drifted: {serp_prov}"
    bcn_prov = con.execute(
        "SELECT ROUND(valor, 2) FROM serpavi_provincial WHERE provincia='Barcelona' "
        "AND anyo=2024 AND medida='ALQM2_LV_M_VC'"
    ).fetchone()
    assert bcn_prov == (10.98,), f"Barcelona provincial anchor drifted: {bcn_prov}"
    muni = con.execute(
        "SELECT COUNT(DISTINCT municipio), MIN(anyo), MAX(anyo) FROM muni_madrid"
    ).fetchone()
    print(f"muni_madrid join: municipios={muni[0]} years={muni[1]}-{muni[2]}")
    assert muni[0] >= 20, f"too few joined municipios: {muni[0]}"
    cen = con.execute("SELECT COUNT(DISTINCT municipio) FROM censo2011_mad").fetchone()[0]
    cen_bad = con.execute("SELECT COUNT(*) FROM censo2011_mad WHERE viviendas_2011 < 0").fetchone()[
        0
    ]
    print(f"censo2011_mad: municipios={cen} negatives={cen_bad}")
    assert cen >= 20 and cen_bad == 0, "censo2011 join broken"
    cen_b = con.execute("SELECT COUNT(DISTINCT municipio) FROM censo2011_bcn").fetchone()[0]
    # Census display names (INE article order) — keys already asserted in build.
    for focus in (
        "Barcelona",
        "Hospitalet de Llobregat, L'",
        "Badalona",
        "Santa Coloma de Gramenet",
    ):
        n = con.execute(
            "SELECT COUNT(*) FROM censo2011_bcn WHERE municipio = ?", [focus]
        ).fetchone()[0]
        assert n == 7, f"censo2011_bcn missing {focus}: {n} rows"
    print(f"censo2011_bcn: municipios={cen_b} (focus cities complete)")
    trx_c = con.execute(
        "SELECT SUM(CASE WHEN trx_total IS NULL THEN 1 ELSE 0 END) FROM mart_ccaa_anual"
    ).fetchone()[0]
    trx_p = con.execute(
        "SELECT SUM(CASE WHEN trx_total IS NULL THEN 1 ELSE 0 END) FROM mart_provincia_anual"
    ).fetchone()[0]
    trx_p_ok = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE anyo < 2007 AND trx_total IS NOT NULL"
    ).fetchone()[0]
    trx_p_bad = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE anyo >= 2007 AND trx_total IS NULL"
    ).fetchone()[0]
    print(
        f"transactions: ccaa null={trx_c}, prov null={trx_p} "
        f"(pre2007-leak={trx_p_ok}, post2007-gap={trx_p_bad})"
    )
    assert trx_c == 0, "ccaa transactions must be complete 2007-2025"
    assert trx_p_ok == 0 and trx_p_bad == 0, "prov transactions must cover 2007-2025"
    vin = con.execute(
        "SELECT SUM(CASE WHEN tipo='vacia' AND vintage='De 2002 a 2011' "
        "THEN viviendas END), SUM(CASE WHEN tipo='vacia' AND vintage='Total' "
        "THEN viviendas END) FROM censo2011_vintage WHERE ccaa = '' AND provincia = ''"
    ).fetchone()
    print(f"vintage: new-vacant share nacional={vin[0] / vin[1]:.3f}")
    ten = con.execute(
        "SELECT SUM(hogares) FROM censo2011_tenencia WHERE ccaa = '' AND provincia = '' "
        "AND tamano = 'Total (tamaño del hogar)' "
        "AND tenencia = 'Propia, por compra, con pagos pendientes (hipotecas)'"
    ).fetchone()[0]
    print(f"tenencia: mortgaged households nacional 2011={ten}")
    assert ten == 5940928, f"mortgaged anchor drifted: {ten}"
    assert vin[0] is not None and vin[1] is not None, "vintage nacional missing"
    cen_v = con.execute("SELECT COUNT(DISTINCT municipio) FROM censo2011_val").fetchone()[0]
    print(f"censo2011_val: municipios={cen_v}")
    assert cen_v == 9, f"valencia focus incomplete: {cen_v}"
    bcn = con.execute(
        "SELECT COUNT(DISTINCT municipio), MIN(anyo), MAX(anyo) FROM muni_bcn"
    ).fetchone()
    bcn_city = con.execute(
        "SELECT MIN(anyo), MAX(anyo) FROM muni_bcn "
        "WHERE municipio = 'Barcelona' AND sale_eur_m2 IS NOT NULL"
    ).fetchone()
    print(
        f"muni_bcn: municipios={bcn[0]} years={bcn[1]}-{bcn[2]}; "
        f"city sale window={bcn_city[0]}-{bcn_city[1]}"
    )
    assert bcn_city == (2013, 2024), "barcelona city sale window broken"
    sc = con.execute(
        "SELECT SUM(starts) FROM muni_bcn WHERE municipio='Santa Coloma de Gramenet'"
        " AND anyo BETWEEN 2012 AND 2024"
    ).fetchone()[0]
    print(f"santa coloma starts 2012-24: {sc}")
    assert sc == 514, f"santa coloma starts drifted: {sc}"
    vlc = con.execute(
        "SELECT COUNT(DISTINCT municipio), MIN(anyo), MAX(anyo) FROM muni_vlc"
    ).fetchone()
    vlc_rent = con.execute(
        "SELECT MIN(anyo), MAX(anyo) FROM muni_vlc WHERE rent_eur_m2 IS NOT NULL"
    ).fetchone()
    vlc_city = con.execute(
        "SELECT poblacion FROM muni_vlc WHERE municipio = 'València' AND anyo = 2025"
    ).fetchone()[0]
    vlc_city_rent = con.execute(
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_vlc WHERE municipio = 'València' AND anyo = 2024"
    ).fetchone()[0]
    print(
        f"muni_vlc: municipios={vlc[0]} years={vlc[1]}-{vlc[2]}; "
        f"rent window={vlc_rent[0]}-{vlc_rent[1]}; "
        f"Valencia city 2025={vlc_city}, rent 2024={vlc_city_rent}"
    )
    assert vlc == (266, 1996, 2025), f"valencia coverage broken: {vlc}"
    assert vlc_rent == (2011, 2024), f"valencia rent window broken: {vlc_rent}"
    assert vlc_city == 840792, f"valencia city pop drifted: {vlc_city}"
    assert vlc_city_rent == 8.18, f"valencia city rent drifted: {vlc_city_rent}"
    sev = con.execute(
        "SELECT COUNT(DISTINCT municipio), MIN(anyo), MAX(anyo) FROM muni_sev"
    ).fetchone()
    sev_rent = con.execute(
        "SELECT MIN(anyo), MAX(anyo) FROM muni_sev WHERE rent_eur_m2 IS NOT NULL"
    ).fetchone()
    sev_city = con.execute(
        "SELECT poblacion FROM muni_sev WHERE municipio = 'Sevilla (ciudad)' AND anyo = 2025"
    ).fetchone()[0]
    sev_city_rent = con.execute(
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_sev "
        "WHERE municipio = 'Sevilla (ciudad)' AND anyo = 2024"
    ).fetchone()[0]
    print(
        f"muni_sev: municipios={sev[0]} years={sev[1]}-{sev[2]}; "
        f"rent window={sev_rent[0]}-{sev_rent[1]}; "
        f"Sevilla city 2025={sev_city}, rent 2024={sev_city_rent}"
    )
    assert sev == (106, 1996, 2025), f"sevilla coverage broken: {sev}"
    assert sev_rent == (2011, 2024), f"sevilla rent window broken: {sev_rent}"
    assert sev_city == 689423, f"sevilla city pop drifted: {sev_city}"
    assert sev_city_rent == 9.17, f"sevilla city rent drifted: {sev_city_rent}"
    mall = con.execute(
        "SELECT COUNT(DISTINCT (cpro, municipio)), MIN(anyo), MAX(anyo) FROM muni_all"
    ).fetchone()
    mall_rent = con.execute(
        "SELECT MIN(anyo), MAX(anyo) FROM muni_all WHERE rent_eur_m2 IS NOT NULL"
    ).fetchone()
    mall_mad = con.execute(
        "SELECT poblacion FROM muni_all WHERE municipio = 'Madrid (ciudad)' AND anyo = 2025"
    ).fetchone()[0]
    mall_mad_rent = con.execute(
        "SELECT ROUND(rent_eur_m2, 2) FROM muni_all "
        "WHERE municipio = 'Madrid (ciudad)' AND anyo = 2024"
    ).fetchone()[0]
    print(
        f"muni_all: municipios={mall[0]} years={mall[1]}-{mall[2]}; "
        f"rent window={mall_rent[0]}-{mall_rent[1]}; "
        f"Madrid city 2025={mall_mad}, rent 2024={mall_mad_rent}"
    )
    assert mall == (8136, 1996, 2025), f"national coverage broken: {mall}"
    assert mall_rent == (2011, 2024), f"national rent window broken: {mall_rent}"
    assert mall_mad == 3506730, f"madrid city pop drifted: {mall_mad}"
    assert mall_mad_rent == 13.97, f"madrid city rent drifted: {mall_mad_rent}"
    hog11 = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE anyo=2011 AND hogares IS NULL"
    ).fetchone()[0]
    assert hog11 == 0, "2011 census households must be complete (51 provincias)"
    px01 = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE anyo=2001 AND hogares_2001_proxy IS NULL"
    ).fetchone()[0]
    assert px01 == 0, "2001 proxy households must be complete (51 provincias)"
    assert (PROCESSED / "coverage.json").exists(), "coverage.json missing"
    print("verify OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
