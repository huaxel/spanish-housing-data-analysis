"""Offline checks for publisher layout changes and fetch-step ordering."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_municipios_mad  # noqa: E402
import fetch_parque  # noqa: E402
from build_marts import pivot_parque  # noqa: E402

PARQUE_HEADER = "COD_CCAA;NOM_CCAA;COD_PROV;NOM_PROV;ANIO;CATEGORIA_PARQUE;NUM_VIVIENDAS"


def parque_csv(*rows: str, header: str = PARQUE_HEADER) -> str:
    return "\r\n".join([header, *rows]) + "\r\n"


def test_parque_new_layout_feeds_build_marts():
    text = parque_csv(
        *(
            f"09;Cataluña;08;Barcelona;2025;{tipo};{value}"
            for tipo, value in (("Principal", 70), ("No_Principal", 30), ("Totales", 100))
        )
    )
    rows = fetch_parque.parse(text)
    assert (rows[0]["CODAUTO"], rows[0]["CPRO"]) == ("9", "8")
    assert pivot_parque(rows) == {("08", 2025): {"principal": 70, "no_principal": 30, "total": 100}}


def test_parque_blank_province_code_stays_blank():
    (row,) = fetch_parque.parse(parque_csv("00;Ceuta y Melilla;;;2001;Totales;45381"))
    assert (row["CODAUTO"], row["CPRO"], row["Provincia"]) == ("0", "", "")


@pytest.mark.parametrize(
    "text",
    [
        parque_csv(header="CODAUTO;Comunidad_Autónoma;CPRO;Provincia;Año;Tipo_Vivienda;Valor"),
        parque_csv("09;Cataluña;08;Barcelona;2025;Otra;1"),
        parque_csv("09;Cataluña;xx;Barcelona;2025;Totales;1"),
        parque_csv("09;Cataluña;08;Barcelona;2025;Totales"),
        parque_csv(),
        "",
    ],
)
def test_parque_rejects_unexpected_layouts(text):
    with pytest.raises(ValueError, match="parque"):
        fetch_parque.parse(text)


def test_madrid_decodes_utf8_with_or_without_bom():
    text = (
        ";".join(fetch_municipios_mad.HEADER)
        + "\r\n2005;Municipios;0014;Acebeda (La);1500;Euros/m2;\r\n"
    )
    for encoding in ("utf-8", "utf-8-sig"):
        assert fetch_municipios_mad.decode(text.encode(encoding)) == text


@pytest.mark.parametrize("body", ["", "2005;Municipios;0014;A;-;;\r\n", "2005;short\r\n"])
def test_madrid_rejects_empty_valueless_or_ragged_files(body):
    text = ";".join(fetch_municipios_mad.HEADER) + "\r\n" + body
    with pytest.raises(ValueError, match="municipios madrid"):
        fetch_municipios_mad.decode(text.encode("utf-8"))


def parque_grid():
    return [
        {"CPRO": cpro, "Año": str(year), "Tipo_Vivienda": tipo, "Valor": "1"}
        for cpro in ["", *(str(n) for n in range(1, 51))]
        for year in range(2001, 2026)
        for tipo in fetch_parque.TIPOS.values()
    ]


def test_parque_coverage_rejects_gaps_duplicates_and_short_range():
    fetch_parque.validate_coverage(parque_grid())
    for rows in (
        parque_grid()[1:],
        parque_grid() + parque_grid()[:1],
        [r for r in parque_grid() if r["CPRO"] != "28"],
        [r for r in parque_grid() if r["Año"] != "2025"],
    ):
        with pytest.raises(ValueError, match="parque"):
            fetch_parque.validate_coverage(rows)


def test_parque_rejects_nonnumeric_value():
    with pytest.raises(ValueError, match="non-numeric value"):
        fetch_parque.parse(parque_csv("09;Cataluña;08;Barcelona;2025;Totales;abc"))


def test_failed_parque_validation_keeps_the_saved_file(tmp_path, monkeypatch):
    saved = tmp_path / "parque_viviendas.csv"
    saved.write_text("previous")
    bad = parque_csv("09;Cataluña;08;Barcelona;2025;Totales;1").encode()
    monkeypatch.setattr(fetch_parque, "RAW", tmp_path)
    monkeypatch.setattr(fetch_parque, "RAW_CSV", saved)
    monkeypatch.setattr(fetch_parque, "RAW_PARQUET", tmp_path / "parquet" / "p.parquet")
    monkeypatch.setattr(fetch_parque.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(bad))
    with pytest.raises(ValueError, match="parque"):
        fetch_parque.main()
    assert saved.read_text() == "previous"
    assert {p.name for p in tmp_path.iterdir()} == {"parquet", "parque_viviendas.csv"}


def test_madrid_rejects_other_encoding_or_header():
    header = ";".join(fetch_municipios_mad.HEADER)
    with pytest.raises(UnicodeDecodeError):
        fetch_municipios_mad.decode(header.encode("cp1252"))
    with pytest.raises(ValueError, match="unexpected header"):
        fetch_municipios_mad.decode(b"a;b\n1;2\n")


def test_cadastre_province_runs_after_the_database_it_reads():
    recipe = (ROOT / "Makefile").read_text().split("\nfetch:\n", 1)[1].split("\n\n", 1)[0]
    steps = [line.split()[3] for line in recipe.splitlines()]
    assert steps.index("scripts/build_sevilla_2021.py") < steps.index(
        "scripts/fetch_cadastre_province.py"
    )
