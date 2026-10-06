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
    assert hip_prov_pre == 0 and hip_prov_post == 0, "prov mortgages must cover 2003-2021"
    tur_cc = con.execute(
        "SELECT COUNT(*) FROM mart_ccaa_anual WHERE anyo >= 2020 AND viv_turisticas IS NULL"
    ).fetchone()[0]
    tur_cc_pre = con.execute(
        "SELECT COUNT(*) FROM mart_ccaa_anual WHERE anyo < 2020 AND viv_turisticas IS NOT NULL"
    ).fetchone()[0]
    tur_pr = con.execute(
        "SELECT COUNT(*) FROM mart_provincia_anual WHERE anyo IN (2020, 2021) "
        "AND viv_turisticas IS NULL"
    ).fetchone()[0]
    print(
        f"tourist dwellings: ccaa null-post2020={tur_cc}, ccaa pre2020-leak={tur_cc_pre}, "
        f"prov null-2020/21={tur_pr}"
    )
    assert tur_cc == 0 and tur_cc_pre == 0, "ccaa tourist must cover 2020-2025 only"
    assert tur_pr == 0, "prov tourist must cover 2020-2021"
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
    assert trx_p_ok == 0 and trx_p_bad == 0, "prov transactions must cover 2007-2021 only"
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
