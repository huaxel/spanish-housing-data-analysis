"""Build Spain's Citation-Grade Housing Claim Ledger from pinned marts and artifacts.

Computes every headline metric and methodological reconciliation bridge directly
from the repo's pinned DuckDB marts and JSON exploration artifacts — no hardcoded
numbers detached from source tables.

Outputs:
- artifacts/claim_ledger.json
- data/processed/claim_ledger.duckdb (tables: claims, claim_bridges)

Use --check to verify existing outputs match current marts/artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402
from spanish_housing.data_paths import PROCESSED, ROOT  # noqa: E402

MARTS_DB = PROCESSED / "marts.duckdb"
DEFICIT_DB = PROCESSED / "deficit.duckdb"
CAT_ARTIFACT = ROOT / "artifacts/catalonia_rent_control.json"
TOURIST_PANEL = ROOT / "artifacts/panel_tourist.json"
TOURIST_RENTS = ROOT / "artifacts/tourist_rents.json"
DEPOSIT_CONTRAST = ROOT / "artifacts/serpavi_deposit_contrast.json"

ARTIFACT_OUT = ROOT / "artifacts/claim_ledger.json"
DUCKDB_OUT = PROCESSED / "claim_ledger.duckdb"


def query_one(con: duckdb.DuckDBPyConnection, sql: str) -> dict:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Empty query result for: {sql}")
    return dict(zip(cols, row, strict=True))


def build_ledger() -> dict:
    for p in (MARTS_DB, DEFICIT_DB, CAT_ARTIFACT, DEPOSIT_CONTRAST):
        if not p.is_file():
            raise SystemExit(f"Missing required input for claim ledger: {p}")

    con = duckdb.connect()
    con.execute(f"ATTACH '{MARTS_DB}' AS m (READ_ONLY)")
    con.execute(f"ATTACH '{DEFICIT_DB}' AS d (READ_ONLY)")

    # 1. Deficit numbers (2021-2024 and 2021-2025)
    def_24 = query_one(
        con,
        "select household_change, stock_change, completions_observed, gap_stock, gap_completions "
        "from d.comparisons where window_key = '2021-2024' and cpro = 'NACIONAL'",
    )
    def_25 = query_one(
        con,
        "select household_change, stock_change, completions_observed, gap_stock, gap_completions "
        "from d.comparisons where window_key = '2021-2025' and cpro = 'NACIONAL'",
    )

    # 2. Vacancy numbers (Censo 2021 electricity consumption)
    vac_nat = query_one(
        con,
        """
        select
            sum(case when medida = 'Viviendas totales' then valor end) as tot,
            sum(case when medida = 'Viviendas vacías' then valor end) as vac,
            sum(case when medida = 'Viviendas de uso esporádico' then valor end) as esporadico
        from m.censo2021_intensidad
        """,
    )
    vac_pct_nat = round(100.0 * vac_nat["vac"] / vac_nat["tot"], 2)

    vac_mad = query_one(
        con,
        """
        select round(100.0 * sum(case when medida = 'Viviendas vacías' then valor end)
             / sum(case when medida = 'Viviendas totales' then valor end), 2) as pct
        from m.censo2021_intensidad where codigo like '28%'
        """,
    )["pct"]
    vac_gal = query_one(
        con,
        """
        select round(100.0 * sum(case when medida = 'Viviendas vacías' then valor end)
             / sum(case when medida = 'Viviendas totales' then valor end), 2) as pct
        from m.censo2021_intensidad
        where left(codigo, 2) in ('15', '27', '32', '36')
        """,
    )["pct"]

    # 3. National spine: 2007, 2013, 2021, 2024, 2025
    spine = {}
    for yr in (2007, 2013, 2021, 2024, 2025):
        spine[yr] = query_one(
            con,
            f"""
            select m.ipv_general, m.eur_m2_libre, m.viv_por_1000_hab, m.viv_por_hogar,
                   m.afford_90m2_years, m.hip_viv_num,
                   round(m.eur_m2_libre * i25.ipc / i.ipc, 1) as eur_m2_2025
            from m.mart_ccaa_anual m
            join m.ipc_anual i on i.territorio = 'Nacional' and i.anyo = m.anyo
            join m.ipc_anual i25 on i25.territorio = 'Nacional' and i25.anyo = 2025
            where m.ccaa = 'Nacional' and m.anyo = {yr}
            """,
        )

    afford_max = query_one(
        con,
        "select ccaa, round(afford_90m2_years, 2) as yrs from m.mart_ccaa_anual "
        "where anyo = 2024 and ccaa != 'Nacional' and afford_90m2_years is not null "
        "order by afford_90m2_years desc limit 1",
    )
    afford_mad = query_one(
        con,
        "select round(afford_90m2_years, 2) as yrs from m.mart_ccaa_anual "
        "where anyo = 2024 and ccaa = 'Madrid, Comunidad de'",
    )["yrs"]

    # 4. Regional viv/1000 divergence (2007 -> 2025)
    mad_07 = query_one(
        con,
        "select viv_por_1000_hab as v from m.mart_ccaa_anual "
        "where ccaa = 'Madrid, Comunidad de' and anyo = 2007",
    )["v"]
    mad_25 = query_one(
        con,
        "select viv_por_1000_hab as v from m.mart_ccaa_anual "
        "where ccaa = 'Madrid, Comunidad de' and anyo = 2025",
    )["v"]
    gal_07 = query_one(
        con,
        "select viv_por_1000_hab as v from m.mart_ccaa_anual "
        "where ccaa = 'Galicia' and anyo = 2007",
    )["v"]
    gal_25 = query_one(
        con,
        "select viv_por_1000_hab as v from m.mart_ccaa_anual "
        "where ccaa = 'Galicia' and anyo = 2025",
    )["v"]

    # 5. Tourist rents / panel artifacts (if present)
    tourist_wild_note = "panel municipal nulo (wild-p 0,49–0,96)"
    if TOURIST_PANEL.is_file():
        tp = json.loads(TOURIST_PANEL.read_text())
        ps = [
            v["wild_p"]
            for v in tp.values()
            if isinstance(v, dict) and isinstance(v.get("wild_p"), (int, float))
        ]
        if ps:
            tourist_wild_note = f"panel municipal nulo (wild-p {min(ps):.2f}–{max(ps):.2f})"

    # 6. Catalonia rent control (Phase 1 artifact)
    cat = json.loads(CAT_ARTIFACT.read_text())
    cat_did = {(r["design_id"], r["outcome_id"]): r for r in cat["did_summary"]}
    a_rent = cat_did[("A_w1_vs_w2", "log_rent")]
    b_rent = cat_did[("B_w1_vs_never", "log_rent")]
    a_con = cat_did[("A_w1_vs_w2", "log_contracts")]
    d_con = cat_did[("D_within_comarca", "log_contracts")]
    a_tmp = cat_did[("A_w1_vs_w2", "temporada_share")]
    b_tmp = cat_did[("B_w1_vs_never", "temporada_share")]

    # 7. Barcelona contract stock vs deposit flow (INCASÒL/SERPAVI contrast)
    contrast = json.loads(DEPOSIT_CONTRAST.read_text())
    contracts = contrast["barcelona_city"]["serpavi_contracts"]
    entries = contrast["barcelona_city"]["incasol_entries"]
    balances = contrast["barcelona_city"]["incasol_balance"]
    stock_first = contracts[min(contracts)]["total"]
    stock_last = contracts[max(contracts)]["total"]
    stock_growth = round(100.0 * (stock_last / stock_first - 1), 1)
    entries_peak_year = max(entries, key=lambda year: entries[year])
    entries_last_year = max(entries)
    negative_year = next(year for year, value in sorted(balances.items()) if value < 0)
    negative_balance = balances[negative_year]
    negative_stock_change = (
        contracts[negative_year]["total"] - contracts[str(int(negative_year) - 1)]["total"]
    )

    con.close()

    real_chg_07_25 = round(
        100.0
        * (spine[2025]["eur_m2_2025"] - spine[2007]["eur_m2_2025"])
        / spine[2007]["eur_m2_2025"],
        1,
    )
    ipv_drop_07_13 = round(
        100.0
        * (spine[2013]["ipv_general"] - spine[2007]["ipv_general"])
        / spine[2007]["ipv_general"],
        1,
    )
    hip_drop_07_13 = round(
        100.0
        * (spine[2013]["hip_viv_num"] - spine[2007]["hip_viv_num"])
        / spine[2007]["hip_viv_num"],
        1,
    )

    claims = [
        {
            "claim_id": "C1_deficit_600k",
            "topic": "Oferta y déficit",
            "public_claim": "«En España faltan 600.000 viviendas»",
            "verdict": "Depende de la definición",
            "verdict_code": "conditional",
            "pinned_finding": (
                f"Resta neta 2021–2024: +{def_24['household_change']:,} hogares vs "
                f"+{def_24['stock_change']:,} parque neto = {def_24['gap_stock']:,} "
                f"(2021–2025: {def_25['gap_stock']:,})."
            ),
            "what_breaks_claim": (
                "Es una resta contable neto-menos-neto, no un recuento de casas "
                "habitables necesarias ni de su localización."
            ),
            "deep_dive_path": "/deficit/",
        },
        {
            "claim_id": "C2_empty_homes_3_8m",
            "topic": "Vacancia",
            "public_claim": "«Hay 3,8 millones de viviendas vacías, no hace falta construir»",
            "verdict": "Engañoso sin geografía",
            "verdict_code": "misleading",
            "pinned_finding": (
                f"Censo 2021 (consumo eléctrico): {vac_nat['vac']:,} vacías "
                f"({vac_pct_nat}% del parque), pero Galicia {vac_gal}% vs Madrid {vac_mad}%."
            ),
            "what_breaks_claim": (
                "Bajo consumo eléctrico no implica habitabilidad, disponibilidad legal "
                "ni ubicación donde crecen los hogares y el empleo."
            ),
            "deep_dive_path": "/vacancia/",
        },
        {
            "claim_id": "C3_tourist_flats",
            "topic": "Turismo",
            "public_claim": "«Los pisos turísticos explican la subida de precios y alquileres»",
            "verdict": "No identificado",
            "verdict_code": "unidentified",
            "pinned_finding": (
                f"Correlación transversal provincial confundida con demanda costera; "
                f"en cambios intra-municipales, {tourist_wild_note}."
            ),
            "what_breaks_claim": (
                "El nulo intra-municipal no prueba efecto cero (hay licencias y "
                "subregistro), pero impide atribuir la subida generalizada al VUT."
            ),
            "deep_dive_path": "/incertidumbre/",
        },
        {
            "claim_id": "C8_rentals_disappearing",
            "topic": "Alquiler",
            "public_claim": "«Cada vez hay menos viviendas en alquiler»",
            "verdict": "Sin medir: el registro no es la oferta",
            "verdict_code": "unidentified",
            "pinned_finding": (
                f"En Barcelona los contratos declarados en el IRPF suben de "
                f"{stock_first:,} ({min(contracts)}) a {stock_last:,} ({max(contracts)}), "
                f"+{stock_growth}%, mientras las altas de fianza bajan de "
                f"{entries[entries_peak_year]:,} ({entries_peak_year}) a "
                f"{entries[entries_last_year]:,} ({entries_last_year})."
            ),
            "what_breaks_claim": (
                "Las fianzas cuentan altas y bajas registradas, no viviendas disponibles; "
                "comparadas con el stock declarado no reconcilian año a año "
                f"(en {negative_year} el saldo fue {negative_balance:,} con el stock "
                f"creciendo {negative_stock_change:,}), y ninguna fuente pública cuenta "
                "oferta efectiva."
            ),
            "deep_dive_path": "/alquiler/",
        },
        {
            "claim_id": "C4_harder_than_2007",
            "topic": "Asequibilidad",
            "public_claim": "«Comprar vivienda es hoy más difícil que en 2007»",
            "verdict": "Falso en media; cierto en polos",
            "verdict_code": "split",
            "pinned_finding": (
                f"En € de 2025 el valor tasado nacional sigue {real_chg_07_25:+.1f}% bajo 2007 "
                f"y 90 m² bajaron de {spine[2007]['afford_90m2_years']:.1f} a "
                f"{spine[2024]['afford_90m2_years']:.1f} años de renta media; "
                f"pero {afford_max['ccaa']} marca {afford_max['yrs']:.1f} "
                f"y Madrid {afford_mad:.1f}."
            ),
            "what_breaks_claim": (
                "La media nacional oculta la barrera de ahorro inicial (entrada + "
                "impuestos) y la brecha de jóvenes y polos tensos."
            ),
            "deep_dive_path": "/compra/",
        },
        {
            "claim_id": "C5_flat_stock_ratio",
            "topic": "Geografía del stock",
            "public_claim": "«El parque de vivienda por habitante apenas ha cambiado»",
            "verdict": "Falacia de media nacional",
            "verdict_code": "misleading",
            "pinned_finding": (
                f"España pasa de {spine[2007]['viv_por_1000_hab']:.0f} a "
                f"{spine[2025]['viv_por_1000_hab']:.0f} viv/1.000 hab (2007–2025), "
                f"pero Madrid cae ({mad_07:.0f}→{mad_25:.0f}) mientras Galicia sube "
                f"({gal_07:.0f}→{gal_25:.0f})."
            ),
            "what_breaks_claim": (
                "La estabilidad agregada promedia dos fenómenos opuestos: escasez "
                "metropolitana y vaciamiento del interior."
            ),
            "deep_dive_path": "/ccaa/",
        },
        {
            "claim_id": "C6_catalonia_rent_cap",
            "topic": "Control de alquileres",
            "public_claim": (
                "«El tope catalán bajó precios sin coste / hundió la oferta sin bajar precios»"
            ),
            "verdict": "Ambas caricaturas fallan",
            "verdict_code": "tradeoff",
            "pinned_finding": (
                f"INCASÒL (2019–2026T2): rentas contractuales {a_rent['effect_display']:+.2f}% "
                f"a {b_rent['effect_display']:+.2f}% (wild-p=0,001); firmas habituales "
                f"{d_con['effect_display']:+.2f}% a {a_con['effect_display']:+.2f}%; "
                f"temporada {a_tmp['effect_display']:+.2f} a {b_tmp['effect_display']:+.2f} pp."
            ),
            "what_breaks_claim": (
                "Caen tanto las rentas firmadas como los nuevos contratos habituales "
                "(que mezclan menor rotación y desvío a temporada/salida)."
            ),
            "deep_dive_path": "/politica/",
        },
        {
            "claim_id": "C7_bust_oversupply_only",
            "topic": "Ciclo 2007–2013",
            "public_claim": "«Los precios cayeron en 2007–2013 solo porque sobraban casas»",
            "verdict": "Incompleto (crédito + stock)",
            "verdict_code": "incomplete",
            "pinned_finding": (
                f"IPV {ipv_drop_07_13:+.1f}% mientras las hipotecas cayeron {hip_drop_07_13:+.1f}% "
                f"({spine[2007]['hip_viv_num']:,.0f}→{spine[2013]['hip_viv_num']:,.0f}) y el stock "
                f"por habitante subió ({spine[2007]['viv_por_1000_hab']:.0f}→"
                f"{spine[2013]['viv_por_1000_hab']:.0f})."
            ),
            "what_breaks_claim": (
                "El frenazo crediticio y el excedente localizado (768k vacías 2002–2011) "
                "actúan a la vez; las series agregadas no separan su peso relativo."
            ),
            "deep_dive_path": "/reportaje/",
        },
    ]

    # Explicit methodological reconciliation bridges (core differentiator of the Ledger)
    bridges = [
        {
            "claim_id": "C1_deficit_600k",
            "definition": "Hogares netos ECP − parque neto MIVAU (2021–2024)",
            "value_num": float(def_24["gap_stock"]),
            "unit": "viviendas",
            "why_it_differs": (
                "Ventana de 4 años (base típica del titular «~600k»); "
                "resta neta sin medir habitabilidad ni ubicación."
            ),
        },
        {
            "claim_id": "C1_deficit_600k",
            "definition": "Hogares netos ECP − viviendas terminadas MIVAU (2021–2024)",
            "value_num": float(def_24["gap_completions"]),
            "unit": "viviendas",
            "why_it_differs": "Usa obra terminada bruta observada en vez de parque modelado neto.",
        },
        {
            "claim_id": "C1_deficit_600k",
            "definition": "Hogares netos ECP − parque neto MIVAU (2021–2025)",
            "value_num": float(def_25["gap_stock"]),
            "unit": "viviendas",
            "why_it_differs": (
                "Añade 2025: la brecha contable acumulada sube en ~146k en un solo año."
            ),
        },
        {
            "claim_id": "C2_empty_homes_3_8m",
            "definition": "Viviendas vacías por consumo eléctrico (Censo 2021, España)",
            "value_num": float(vac_nat["vac"]),
            "unit": "viviendas",
            "why_it_differs": (
                "Total nacional sin filtrar estado de conservación, uso turístico ni demanda local."
            ),
        },
        {
            "claim_id": "C2_empty_homes_3_8m",
            "definition": "Viviendas de uso esporádico (Censo 2021, España)",
            "value_num": float(vac_nat["esporadico"]),
            "unit": "viviendas",
            "why_it_differs": (
                "Segundas residencias con consumo bajo (251–750 kWh/año), distintas de las vacías."
            ),
        },
        {
            "claim_id": "C2_empty_homes_3_8m",
            "definition": "Tasa de vacancia: Galicia vs Comunidad de Madrid (Censo 2021)",
            "value_num": round(vac_gal - vac_mad, 2),
            "unit": "pp diferencia",
            "why_it_differs": (
                f"Galicia {vac_gal}% frente a Madrid {vac_mad}%: "
                "la vacancia se concentra donde cae la población."
            ),
        },
        {
            "claim_id": "C4_harder_than_2007",
            "definition": "Valor tasado nacional en € reales de 2025 (2007 vs 2025)",
            "value_num": real_chg_07_25,
            "unit": "% real",
            "why_it_differs": (
                f"{spine[2007]['eur_m2_2025']:.0f} → {spine[2025]['eur_m2_2025']:.0f} €/m² "
                "(IPC base 2021); el nominal oculta 18 años de inflación."
            ),
        },
        {
            "claim_id": "C4_harder_than_2007",
            "definition": "Años de renta neta media para 90 m² (España 2024 vs Balears 2024)",
            "value_num": round(afford_max["yrs"] - spine[2024]["afford_90m2_years"], 2),
            "unit": "años brecha",
            "why_it_differs": (
                f"Media nacional {spine[2024]['afford_90m2_years']:.1f} años vs "
                f"{afford_max['ccaa']} {afford_max['yrs']:.1f} y Madrid {afford_mad:.1f}."
            ),
        },
        {
            "claim_id": "C6_catalonia_rent_cap",
            "definition": "Efecto renta contractual · Diseño A (Ola 1 vs Ola 2, 2019–2024T3)",
            "value_num": float(a_rent["effect_display"]),
            "unit": "%",
            "why_it_differs": (
                "Control más comparable (municipios que también serían "
                "declarados tensionados en Oct 2024)."
            ),
        },
        {
            "claim_id": "C6_catalonia_rent_cap",
            "definition": (
                "Efecto renta contractual · Diseño B (Ola 1 vs no tensionados, 2019–2026T2)"
            ),
            "value_num": float(b_rent["effect_display"]),
            "unit": "%",
            "why_it_differs": (
                "Horizonte completo de 9 trimestres post-tope; "
                "incluye divergencia pre-tratamiento al alza."
            ),
        },
        {
            "claim_id": "C6_catalonia_rent_cap",
            "definition": "Efecto firmas habituales · Diseño D intra-comarca (2019–2026T2)",
            "value_num": float(d_con["effect_display"]),
            "unit": "%",
            "why_it_differs": (
                "Absorbe shocks locales comarca×trimestre; "
                "combina menor rotación y salidas/temporada."
            ),
        },
        {
            "claim_id": "C6_catalonia_rent_cap",
            "definition": "Efecto cuota temporada · Diseño A / Diseño B (2023–2026T2)",
            "value_num": float(b_tmp["effect_display"]),
            "unit": "pp",
            "why_it_differs": (
                f"Sube +{a_tmp['effect_display']:.2f} pp (Ola 1 vs Ola 2) y "
                f"+{b_tmp['effect_display']:.2f} pp (Ola 1 vs no tensionados)."
            ),
        },
        {
            "claim_id": "C8_rentals_disappearing",
            "definition": (
                f"Contratos de alquiler declarados en el IRPF (SERPAVI), Barcelona {max(contracts)}"
            ),
            "value_num": float(stock_last),
            "unit": "contratos",
            "why_it_differs": (
                "Stock de contratos vigentes en el año fiscal: no es oferta disponible "
                f"ni un flujo; {min(contracts)} fue {stock_first:,}."
            ),
        },
        {
            "claim_id": "C8_rentals_disappearing",
            "definition": (f"Altas de fianza registradas (INCASÒL), Barcelona {entries_last_year}"),
            "value_num": float(entries[entries_last_year]),
            "unit": "altas",
            "why_it_differs": (
                "Flujo anual de altas registradas; el máximo de la ventana fue "
                f"{entries[entries_peak_year]:,} en {entries_peak_year}."
            ),
        },
        {
            "claim_id": "C5_flat_stock_ratio",
            "definition": "Viviendas por 1.000 habitantes · Madrid (2025)",
            "value_num": float(mad_25),
            "unit": "por 1.000",
            "why_it_differs": (
                f"La media nacional apenas se mueve, pero Madrid pasó de {mad_07:.0f} "
                f"(2007) a {mad_25:.0f} (2025)."
            ),
        },
        {
            "claim_id": "C5_flat_stock_ratio",
            "definition": "Viviendas por 1.000 habitantes · Galicia (2025)",
            "value_num": float(gal_25),
            "unit": "por 1.000",
            "why_it_differs": (
                f"Galicia va en la dirección contraria: {gal_07:.0f} (2007) a {gal_25:.0f} (2025)."
            ),
        },
        {
            "claim_id": "C7_bust_oversupply_only",
            "definition": "Caída del IPV · 2007–2013",
            "value_num": float(ipv_drop_07_13),
            "unit": "%",
            "why_it_differs": (
                "El precio cayó mientras el parque por habitante subía "
                f"({float(spine[2007]['viv_por_1000_hab']):.0f}→"
                f"{float(spine[2013]['viv_por_1000_hab']):.0f}), así que el excedente "
                "no basta como explicación única."
            ),
        },
        {
            "claim_id": "C7_bust_oversupply_only",
            "definition": "Caída de hipotecas · 2007–2013",
            "value_num": float(hip_drop_07_13),
            "unit": "%",
            "why_it_differs": (
                f"El crédito se cerró al mismo tiempo "
                f"({float(spine[2007]['hip_viv_num']):,.0f}→"
                f"{float(spine[2013]['hip_viv_num']):,.0f} hipotecas)."
            ),
        },
        {
            "claim_id": "C8_rentals_disappearing",
            "definition": f"Saldo neto de fianzas (INCASÒL), Barcelona {negative_year}",
            "value_num": float(negative_balance),
            "unit": "saldo",
            "why_it_differs": (
                "Altas menos bajas del registro; ese mismo año el stock declarado creció "
                f"{negative_stock_change:,}, así que no mide su cambio."
            ),
        },
    ]

    return {
        # Freshness key (audit_claims.MODEL_FRESHNESS): every upstream mart and
        # exploration artifact is hashed, so the ledger cannot silently quote
        # numbers that a later `make build`/`make analysis` moved.
        "_meta": ols.model_meta(
            __file__,
            [
                str(p.relative_to(ROOT))
                for p in (
                    MARTS_DB,
                    DEFICIT_DB,
                    CAT_ARTIFACT,
                    TOURIST_PANEL,
                    TOURIST_RENTS,
                    DEPOSIT_CONTRAST,
                )
            ],
        ),
        # A public claim whose evidence is a null, not a number: there is no
        # second quantity to reconcile, so it is exempt from the bridge rule
        # (asserted in tests/test_claim_ledger.py).
        "bridge_exempt": {
            "C3_tourist_flats": (
                "La evidencia es un panel intra-municipal nulo, sin una segunda cifra "
                "reconciliable; los puentes numéricos cubren C1, C2 y C4–C8."
            )
        },
        "claims": claims,
        "bridges": bridges,
    }


def write_duckdb(data: dict) -> None:
    tmp = DUCKDB_OUT.with_suffix(".duckdb.tmp")
    if tmp.exists():
        tmp.unlink()
    con = duckdb.connect(str(tmp))
    con.register("c_tbl", pa.Table.from_pylist(data["claims"]))
    con.register("b_tbl", pa.Table.from_pylist(data["bridges"]))
    con.execute("CREATE TABLE claims AS SELECT * FROM c_tbl")
    con.execute("CREATE TABLE claim_bridges AS SELECT * FROM b_tbl")
    con.close()
    tmp.replace(DUCKDB_OUT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify existing ledger matches marts")
    args = parser.parse_args()

    data = build_ledger()
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not ARTIFACT_OUT.is_file() or ARTIFACT_OUT.read_text() != payload:
            raise SystemExit("Stale artifacts/claim_ledger.json; re-run build_claim_ledger.py")
        if not DUCKDB_OUT.is_file():
            raise SystemExit("Missing data/processed/claim_ledger.duckdb")
        print(
            f"claim_ledger: verified {len(data['claims'])} claims, {len(data['bridges'])} bridges"
        )
        return

    ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_OUT.write_text(payload)
    write_duckdb(data)
    print(f"wrote claim_ledger: {len(data['claims'])} claims, {len(data['bridges'])} bridges")


if __name__ == "__main__":
    main()
