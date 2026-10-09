"""Offline contracts for the separate municipal 2021 profile."""

import importlib.util
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
META = (
    "<h1>Censo de Población y Viviendas 2021</h1>"
    "<h2>Hogares por municipios y tamaño del hogar</h2><p>Unidades: hogares</p>"
)
HEADER = "Total Nacional\tMunicipios\tTamaño del hogar\tTotal\n"


@pytest.fixture
def source():
    spec = importlib.util.spec_from_file_location(
        "municipal2021", ROOT / "scripts/build_sevilla_2021.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cell(label="41091 Sevilla", size="Total (tamaño del hogar)", value="1.234"):
    return f"Total Nacional\t{label}\t{size}\t{value}\n"


def hh():
    return {
        "41091": {"codigo": "41091", "municipio": "Sevilla", "hogares": 12},
        "41002": {"codigo": "41002", "municipio": "Alcalá del Río", "hogares": None},
    }


def stock(measure="Viviendas totales", value=20, code="41091", name="Sevilla"):
    return {
        "codigo": code,
        "municipio": name,
        "provincia_cod": "41",
        "medida": measure,
        "valor": value,
    }


def rent(value=7.5, year=2021, measure="ALQM2_LV_M_VC", code="41091", name="Sevilla"):
    return {
        "codigo": code,
        "municipio": name,
        "cpro": "41",
        "anyo": year,
        "medida": measure,
        "valor": value,
    }


def test_published_household_total_not_sum_of_categories(source):
    output = source.households(
        HEADER + cell() + cell(size="1 persona", value="300") + cell(label="", value="18.539.223"),
        META,
    )
    assert output == {"41091": {"codigo": "41091", "municipio": "Sevilla", "hogares": 1234}}


@pytest.mark.parametrize(
    "value,expected", [("0", 0), ("..", None), (".", None), ("", None), ("1.234.567", 1234567)]
)
def test_household_zero_and_suppression_distinct(source, value, expected):
    assert source.households(HEADER + cell(value=value), META)["41091"]["hogares"] == expected


@pytest.mark.parametrize("value", ["-1", "1.5", "1,5", "NaN", "1.23.456"])
def test_invalid_household_counts(source, value):
    with pytest.raises(ValueError):
        source.households(HEADER + cell(value=value), META)


@pytest.mark.parametrize(
    "payload",
    [
        HEADER + cell() + cell(),
        HEADER + cell(label="Sevilla"),
        HEADER + cell(label="41999 Resto de Sevilla"),
        HEADER + cell(size="Total viviendas"),
        "A\tB\n1\t2\n",
    ],
)
def test_bad_household_keys_and_schema(source, payload):
    with pytest.raises(ValueError):
        source.households(payload, META)


@pytest.mark.parametrize(
    "metadata",
    [
        META.replace("2021", "2022"),
        META.replace("hogares</p>", "personas</p>"),
        "<script>" + META + "</script>",
    ],
)
def test_metadata_year_unit_and_visible_definition(source, metadata):
    with pytest.raises(ValueError):
        source.households(HEADER + cell(), metadata)


def test_outer_universe_exact_year_measure_and_zero_vacancy(source):
    profiles, excluded = source.derive(
        hh(),
        [stock(), stock("Viviendas vacías", 0)],
        [rent(), rent(99, year=2022), rent(88, measure="ALQM2_LV_M_VU")],
    )
    assert profiles[0] == (
        "41002",
        "Alcalá del Río",
        None,
        None,
        None,
        None,
        "missing",
        "missing",
        False,
    )
    assert profiles[1] == ("41091", "Sevilla", 12, 20, 0, 7.5, "valid", "valid", True)
    assert excluded == []


@pytest.mark.parametrize("kind", ["stock", "rent"])
def test_duplicate_selected_key_excludes_source_not_whole_universe(source, kind):
    sr, rr = [stock()], [rent()]
    if kind == "stock":
        sr.append(stock(value=21))
    else:
        rr.append(rent(value=8.0))
    profiles, _ = source.derive(hh(), sr, rr)
    row = profiles[1]
    assert not row[-1]
    if kind == "stock":
        assert row[3:5] == (None, None) and row[6] == "duplicate"
    else:
        assert row[5] is None and row[7] == "duplicate"


def test_label_mismatch_and_benign_accents(source):
    profiles, _ = source.derive(
        hh(), [stock(name="Sevilla (provincia)")], [rent(name="Another municipality")]
    )
    assert profiles[1][5] is None and profiles[1][7] == "label_mismatch"
    assert profiles[1][3] is None and profiles[1][6] == "label_mismatch"
    # Code decides identity; normalizer merely tolerates benign spelling.
    profiles, _ = source.derive(hh(), [stock(code="41002", name="ALCALA DEL RIO")], [])
    assert profiles[0][3] == 20


def test_resto_preserved_never_allocated(source):
    rows = [
        stock(code="41999", name="Resto de Sevilla", value=2502),
        stock("Viviendas vacías", 465, "41999", "Resto de Sevilla"),
    ]
    profiles, excluded = source.derive(hh(), rows, [])
    assert len(profiles) == 2 and all(r[3] is None for r in profiles)
    assert len(excluded) == 2 and excluded[0][4] == "2502"


@pytest.mark.parametrize("value", [None, 0, -1])
def test_unpublished_or_nonpositive_rent_not_zero_supply(source, value):
    profiles, _ = source.derive(hh(), [stock()], [rent(value=value)])
    assert profiles[1][5] is None and not profiles[1][-1]


@pytest.mark.parametrize(
    "record",
    [
        stock(value=-1),
        stock(value=1.5),
        stock(value=float("nan")),
        stock(code="28079"),
        stock(code="41001"),
        rent(value=float("inf")),
    ],
)
def test_invalid_counts_codes_and_prices_fail_closed(source, record):
    sr, rr = ([record], []) if "provincia_cod" in record else ([], [record])
    with pytest.raises(ValueError):
        source.derive(hh(), sr, rr)


def test_vacancy_not_above_total(source):
    with pytest.raises(ValueError):
        source.derive(hh(), [stock(), stock("Viviendas vacías", 21)], [])


def test_exact_rows_and_meta_verified(source, tmp_path, monkeypatch):
    profiles, excluded = source.derive(hh(), [stock()], [rent()])
    path = tmp_path / "profile.duckdb"
    monkeypatch.setattr(source, "DATABASE", path)
    monkeypatch.setattr(source, "inputs", lambda: (profiles, excluded, {"test": "pin"}, []))
    with duckdb.connect(str(path)) as con:
        con.execute(
            "create table perfiles(codigo varchar,municipio varchar,hogares bigint,"
            "viviendas bigint,"
            "vacias_consumo bigint,renta_vc double,estado_stock varchar,estado_renta varchar,"
            "perfil_completo boolean)"
        )
        con.executemany("insert into perfiles values (?,?,?,?,?,?,?,?,?)", profiles)
        con.execute(
            "create table agregados_excluidos(fuente varchar,codigo varchar,municipio varchar,"
            "medida varchar,valor_publicado varchar)"
        )
        con.execute(
            "create table tenencia_contexto(codigo varchar,municipio varchar,principales bigint,"
            "propiedad bigint,alquiler bigint,otro bigint,estado varchar)"
        )
        con.execute("create table profile_meta(key varchar,value varchar)")
        con.execute("insert into profile_meta values ('test','pin')")
    source.verify()
    with duckdb.connect(str(path)) as con:
        con.execute(
            "insert into tenencia_contexto values ('41091','Sevilla',1,1,0,0,'celdas_completas')"
        )
    with pytest.raises(ValueError, match="Tenure context differs"):
        source.verify()
    with duckdb.connect(str(path)) as con:
        con.execute("delete from tenencia_contexto")
        con.execute("insert into profile_meta values ('test','pin')")
    with pytest.raises(ValueError, match="Stale"):
        source.verify()
    with duckdb.connect(str(path)) as con:
        con.execute("delete from profile_meta")
        con.execute("insert into profile_meta values ('test','pin')")
        con.execute("update perfiles set hogares=13 where codigo='41091'")
    with pytest.raises(ValueError, match="profiles differ"):
        source.verify()


def test_page_and_source_dates_not_availability():
    text = (ROOT / "evidence/pages/stock-2021.md").read_text()
    for token in [
        "1 de enero de 2021",
        "ejercicio fiscal 2021",
        "2020",
        "no es oferta disponible",
        "establecimientos colectivos",
        "Resto de Sevilla",
        "alignment.perfiles",
    ]:
        assert token in text
    assert "--check" in (ROOT / "Makefile").read_text()
    assert "stock-2021/index.html" in (ROOT / "scripts/fix_build_meta.py").read_text()


def test_unpinned_input_rejected(source, monkeypatch):
    monkeypatch.setattr(source.manifest, "load", lambda: {"sha256": {}})
    with pytest.raises(ValueError, match="Unpinned"):
        source.inputs()


def test_modified_input_rejected(source, monkeypatch):
    pins = {str(p.relative_to(source.ROOT)): "hash" for p in source.INPUTS.values()}
    monkeypatch.setattr(source.manifest, "load", lambda: {"sha256": pins})
    monkeypatch.setattr(source.manifest, "check", lambda pins: ([], ["changed"]))
    with pytest.raises(ValueError, match="missing/changed"):
        source.inputs()
