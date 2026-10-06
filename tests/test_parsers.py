"""Offline parser/join-rule tests. No network, no data/ dependency."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_marts import CPRO_CCAA, N  # noqa: E402
from fetch_ecp import parse_hog as parse_ecp_hog  # noqa: E402
from fetch_ecp import parse_pob as parse_ecp_pob  # noqa: E402
from fetch_ipv import parse as parse_ipv  # noqa: E402
from fetch_padron import parse as parse_padron  # noqa: E402
from spanish_housing import ine_api  # noqa: E402


def test_norm_matches_all_parque_province_names():
    parque_names = [
        "Araba/Álava",
        "Albacete",
        "Alicante/Alacant",
        "Almería",
        "Ávila",
        "Badajoz",
        "Balears, Illes",
        "Barcelona",
        "Burgos",
        "Cáceres",
        "Cádiz",
        "Castellón/Castelló",
        "Ciudad Real",
        "Córdoba",
        "Coruña, A",
        "Cuenca",
        "Girona",
        "Granada",
        "Guadalajara",
        "Gipuzkoa",
        "Huelva",
        "Huesca",
        "Jaén",
        "León",
        "Lleida",
        "Rioja, La",
        "Lugo",
        "Madrid",
        "Málaga",
        "Murcia",
        "Navarra",
        "Ourense",
        "Asturias",
        "Palencia",
        "Palmas, Las",
        "Pontevedra",
        "Salamanca",
        "Santa Cruz de Tenerife",
        "Cantabria",
        "Segovia",
        "Sevilla",
        "Soria",
        "Tarragona",
        "Teruel",
        "Toledo",
        "Valencia/València",
        "Valladolid",
        "Bizkaia",
        "Zamora",
        "Zaragoza",
    ]
    assert len(parque_names) == 50
    # every MIVAU province name must hit the CPRO map via build lookup order
    assert len({N(n) for n in parque_names}) == 50


def test_cpro_ccaa_covers_all_50_provinces():
    assert len(CPRO_CCAA) == 50
    assert set(CPRO_CCAA) == {f"{i:02d}" for i in range(1, 51)}


def test_ipv_parse_keeps_index_levels_only():
    payload = [
        {
            "COD": "X1",
            "Nombre": "Nacional. Media anual. General. ",
            "Data": [{"Anyo": 2020, "Valor": 70.0}],
        },
        {
            "COD": "X2",
            "Nombre": "Nacional. Variación anual. General. ",
            "Data": [{"Anyo": 2020, "Valor": 1.5}],
        },
        {
            "COD": "X3",
            "Nombre": "Madrid, Comunidad de. Media anual. Vivienda nueva. ",
            "Data": [{"Anyo": 2020, "Valor": 80.0}],
        },
    ]
    rows, skipped = parse_ipv(payload)
    assert len(rows) == 2
    assert len(skipped) == 1 and "Variación" in skipped[0]
    assert rows[1]["territorio"] == "Madrid, Comunidad de"


def test_padron_parse_keeps_total_habitantes_only():
    payload = [
        {
            "COD": "D1",
            "Nombre": "Albacete. Total. Total habitantes. Personas. ",
            "Data": [{"Anyo": 2021, "Valor": 386464.0}],
        },
        {
            "COD": "D2",
            "Nombre": "Albacete. Total. Nacidos en el municipio. Personas. ",
            "Data": [{"Anyo": 2021, "Valor": 1.0}],
        },
    ]
    rows, skipped = parse_padron(payload)
    assert len(rows) == 1 and rows[0]["poblacion"] == 386464
    assert len(skipped) == 1


def test_ine_split_nombre():
    assert ine_api.split_nombre("Albacete. Total. Total habitantes. Personas. ") == [
        "Albacete",
        "Total",
        "Total habitantes",
        "Personas",
    ]


def test_ecp_pob_keeps_january_totals_only():
    payload = [
        {
            "COD": "E1",
            "Nombre": "Total. Todas las edades. Andalucía. Población. Número. ",
            "Data": [
                {"Anyo": 2022, "FK_Periodo": 19, "Valor": 8000000.0},
                {"Anyo": 2022, "FK_Periodo": 20, "Valor": 8010000.0},
            ],
        },
        {
            "COD": "E2",
            "Nombre": "Hombres. Todas las edades. Andalucía. Población. Número. ",
            "Data": [{"Anyo": 2022, "FK_Periodo": 19, "Valor": 3900000.0}],
        },
        {
            "COD": "E3",
            "Nombre": "Total Nacional. Todas las edades. Total. Población. Número. ",
            "Data": [{"Anyo": 2022, "FK_Periodo": 19, "Valor": 47000000.0}],
        },
        {
            "COD": "E4",
            "Nombre": "Total. 40 años. Andalucía. Población. Número. ",
            "Data": [{"Anyo": 2022, "FK_Periodo": 19, "Valor": 1.0}],
        },
    ]
    rows, skipped = parse_ecp_pob(payload)
    assert len(rows) == 2  # quarterly point + sex/age detail excluded
    assert rows[0] == {
        "territorio": "Andalucía",
        "anyo": 2022,
        "poblacion": 8000000,
        "serie_cod": "E1",
    }
    assert len(skipped) == 2


def test_ecp_hog_keeps_household_totals_only():
    payload = [
        {
            "COD": "H1",
            "Nombre": "Madrid. Total. Hogares en viviendas familiares. Número. ",
            "Data": [
                {"Anyo": 2023, "FK_Periodo": 19, "Valor": 2600000.0},
                {"Anyo": 2023, "FK_Periodo": 21, "Valor": 2610000.0},
            ],
        },
        {
            "COD": "H2",
            "Nombre": "Madrid. 1. Hogares en viviendas familiares. Número. ",
            "Data": [{"Anyo": 2023, "FK_Periodo": 19, "Valor": 700000.0}],
        },
    ]
    rows, skipped = parse_ecp_hog(payload)
    assert len(rows) == 2  # Total + tamaño detail both kept
    assert [r for r in rows if r["tamano"] == "Total"][0]["hogares"] == 2600000
    assert skipped == []


def test_annualize_valor_mean_andprovenance():
    from build_marts import annualize_valor

    rows = [
        {
            "Año": "2020",
            "Trimestre": "1",
            "Valor": "1000.0",
            "Régimen": "Libre",
            "CPRO": "8",
            "Provincia": "Barcelona",
            "Comunidad_Autónoma": "Cataluña",
            "CODAUTO": "9",
        },
        {
            "Año": "2020",
            "Trimestre": "2",
            "Valor": "1100.0",
            "Régimen": "Libre",
            "CPRO": "8",
            "Provincia": "Barcelona",
            "Comunidad_Autónoma": "Cataluña",
            "CODAUTO": "9",
        },
        {
            "Año": "2020",
            "Trimestre": "3",
            "Valor": "",
            "Régimen": "Libre",
            "CPRO": "8",
            "Provincia": "Barcelona",
            "Comunidad_Autónoma": "Cataluña",
            "CODAUTO": "9",
        },
        {
            "Año": "2020",
            "Trimestre": "1",
            "Valor": "2000.0",
            "Régimen": "Libre",
            "CPRO": "null",
            "Provincia": "Total CCAA",
            "Comunidad_Autónoma": "Cataluña",
            "CODAUTO": "9",
        },
        {
            "Año": "2020",
            "Trimestre": "1",
            "Valor": "",
            "Régimen": "Protegida",
            "CPRO": "",
            "Provincia": "",
            "Comunidad_Autónoma": "Total CCAA",
            "CODAUTO": "",
        },
    ]
    out = annualize_valor(rows)
    assert out[("P08", 2020, "Libre")] == {"eur_m2": 1050.0, "n_trim": 2}
    assert out[("CCATALUNA", 2020, "Libre")] == {"eur_m2": 2000.0, "n_trim": 1}
    assert len(out) == 2  # unpublished quarters never zero-filled


def test_renta_parse_lags_survey_year():
    from fetch_renta import parse as parse_renta

    payload = [
        {
            "COD": "R1",
            "Nombre": "Madrid, Comunidad de. Renta neta media por hogar. Base 2013. ",
            "Data": [{"Anyo": 2025, "Valor": 47375.0}],
        },
        {
            "COD": "R2",
            "Nombre": (
                "Madrid, Comunidad de. Renta media por hogar (con alquiler imputado). Base 2013. "
            ),
            "Data": [{"Anyo": 2025, "Valor": 54000.0}],
        },
    ]
    rows, skipped = parse_renta(payload)
    assert len(rows) == 2 and skipped == []
    neta = [r for r in rows if r["indicador"] == "neta"][0]
    assert neta["renta_anyo"] == 2024 and neta["encuesta_anyo"] == 2025


def test_edad_band_edges_and_grouped_elderly():
    from parse_edad import band

    assert band("Todas las edades") == "total"
    assert band("0 años") == "0-19" and band("1 año") == "0-19"
    assert band("19 años") == "0-19" and band("20 años") == "20-34"
    assert band("34 años") == "20-34" and band("35 años") == "35-49"
    assert band("49 años") == "35-49" and band("50 años") == "50-64"
    assert band("64 años") == "50-64" and band("65 años") == "65+"
    assert band("84 años") == "65+"
    assert band("85 y más años") == "65+"
    assert band("100 y más años") == "65+"
    assert band("De 0 a 15 años") is None


def test_hipotecas_classify_both_layouts():
    from fetch_hipotecas import classify

    # CCAA layout: nature. terr. medida
    assert classify("Viviendas. Andalucía. Número de hipotecas. Base nueva. Mensual.") == (
        "count",
        "Andalucía",
        "Número de hipotecas",
    )
    # Provincia layout: nature. medida. terr (swapped)
    assert classify("Viviendas. Número de hipotecas. Albacete. Base nueva. Mensual.") == (
        "count",
        "Albacete",
        "Número de hipotecas",
    )
    assert classify("Viviendas. Importe de hipotecas. Madrid. Base nueva. Mensual.") == (
        "count",
        "Madrid",
        "Importe de hipotecas",
    )
    # Rates: national only
    assert classify(
        "Viviendas. Tipo de interés medio. Total Nacional. Base nueva. Mensual. Fijo."
    ) == ("rates", "Total Nacional", "Fijo")
    # Skips: other natures, non-national rates, short names
    assert classify("Solares. Andalucía. Número de hipotecas. Base nueva. Mensual.") is None
    assert (
        classify("Viviendas. Tipo de interés medio. Andalucía. Base nueva. Mensual. Fijo.") is None
    )


def test_muni_key_unifies_publishers():
    from spanish_housing.muni_names import muni_key

    assert muni_key("El Bruc") == muni_key("Bruc, El") == "BRUC"
    assert muni_key("L'Ametlla del Vallès") == "AMETLLA DEL VALLES"
    assert muni_key("Rozas de Madrid (Las)") == muni_key("Rozas de Madrid, Las")
    assert (
        muni_key("Barcelona (provincia)") == muni_key("Barcelona") == muni_key("Barcelona (ciudad)")
    )
    assert muni_key("Hospitalet de Llobregat") == muni_key("Hospitalet de Llobregat")
    assert muni_key("Santa Coloma de Gramenet") != muni_key("Santa Coloma de Cervelló")


def test_muni_key_trailing_articles():
    from spanish_housing.muni_names import muni_key

    assert muni_key("Masnou, El") == muni_key("El Masnou") == "MASNOU"
    assert muni_key("Hospitalet de Llobregat, L'") == muni_key("Hospitalet de Llobregat")
    assert muni_key("Ametlla del Vallès, L'") == muni_key("L'Ametlla del Vallès")
    assert muni_key("Bruc, El") == muni_key("El Bruc")


def test_ecp_hog_keeps_all_sizes():
    from fetch_ecp import parse_hog as parse_ecp_hog

    payload = [
        {
            "COD": "H1",
            "Nombre": "Madrid. Total. Hogares en viviendas familiares. Número. ",
            "Data": [{"Anyo": 2023, "FK_Periodo": 19, "Valor": 2600000.0}],
        },
        {
            "COD": "H2",
            "Nombre": "Madrid. 1. Hogares en viviendas familiares. Número. ",
            "Data": [{"Anyo": 2023, "FK_Periodo": 19, "Valor": 700000.0}],
        },
        {
            "COD": "H3",
            "Nombre": "Madrid. 4 y más. Hogares en viviendas familiares. Número. ",
            "Data": [{"Anyo": 2023, "FK_Periodo": 19, "Valor": 500000.0}],
        },
    ]
    rows, skipped = parse_ecp_hog(payload)
    assert len(rows) == 3 and skipped == []
    assert {r["tamano"] for r in rows} == {"Total", "1", "4 y más"}


def test_transmisiones_strip_code():
    from fetch_transmisiones import strip_code

    assert strip_code("01 Andalucía") == "Andalucía"
    assert strip_code("18 Ceuta") == "Ceuta"
    assert strip_code("") == ""
    assert strip_code("Total Nacional") == "Total Nacional"


def test_tenencia_num_markers():
    from fetch_censo2011_tenencia import num

    assert num("18.083.692") == 18083692
    assert num("") is None and num("..") is None and num(".") is None
