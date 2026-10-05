"""Verify pinned inputs and mart integrity. Fails loudly; never imputes."""

from __future__ import annotations

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
    assert pre_hog == 0, "hogares must be NULL before 2021"
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
        "SELECT COUNT(DISTINCT municipio), MIN(anyo), MAX(anyo) "
        "FROM valor_municipal_madrid"
    ).fetchone()
    mun_cap = con.execute(
        "SELECT COUNT(*), MIN(anyo), MAX(anyo) FROM valor_municipal_madrid "
        "WHERE codigo = '0796'"
    ).fetchone()
    print(f"municipal madrid: municipios={mun[0]} years={mun[1]}-{mun[2]}; "
          f"capital years={mun_cap[1]}-{mun_cap[2]} ({mun_cap[0]} rows)")
    assert mun_cap[0] == mun_cap[2] - mun_cap[1] + 1, "capital must be complete"
    muni = con.execute(
        "SELECT COUNT(DISTINCT municipio), MIN(anyo), MAX(anyo) FROM muni_madrid"
    ).fetchone()
    print(f"muni_madrid join: municipios={muni[0]} years={muni[1]}-{muni[2]}")
    assert muni[0] >= 20, f"too few joined municipios: {muni[0]}"
    assert (PROCESSED / "coverage.json").exists(), "coverage.json missing"
    print("verify OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
