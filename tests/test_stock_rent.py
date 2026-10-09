"""Offline cross-snapshot association contracts; no production artifacts required."""

import importlib.util
import math
import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
QUERIES = dict(
    re.findall(r"```sql (\w+)\n(.*?)\n```", (ROOT / "evidence/pages/stock.md").read_text(), re.S)
)


@pytest.fixture
def analysis(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "stock_rent", ROOT / "scripts/analyze_stock_rent.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ranked(analysis):
    with duckdb.connect() as con:
        con.execute("create table pairs(variable varchar,distrito varchar,x double,y double)")
        queries = {**QUERIES, "stock_renta_largo": "select * from pairs"}
        yield con, queries, analysis


def execute(fixture, name):
    con, queries, analysis = fixture
    cursor = con.execute(analysis.expand(queries[name], queries))
    keys = [column[0] for column in cursor.description]
    return [dict(zip(keys, row, strict=True)) for row in cursor.fetchall()]


def test_district_centering_is_not_pooled_correlation(ranked):
    con, _, _ = ranked
    con.execute("insert into pairs values ('v','A',1,2),('v','A',2,1),('v','B',3,4),('v','B',4,3)")
    row = execute(ranked, "asociaciones_stock_renta")[0]
    assert row["n"] == 4 and row["distritos"] == 2
    assert row["spearman"] == pytest.approx(0.6)
    assert row["rangos_centrados_distrito"] == pytest.approx(-1)


def test_tied_values_get_average_ranks(ranked):
    con, _, _ = ranked
    con.execute("insert into pairs values ('v','A',1,1),('v','A',1,2),('v','A',3,3),('v','A',4,4)")
    row = execute(ranked, "asociaciones_stock_renta")[0]
    assert row["spearman"] == pytest.approx(math.sqrt(0.9))


def test_omission_recomputes_ranks_on_remaining_sample(ranked):
    con, _, _ = ranked
    con.execute(
        "insert into pairs values ('v','A',1,1),('v','A',2,3),"
        "('v','B',2,2),('v','B',4,4),('v','B',5,4),('v','B',7,5)"
    )
    rows = execute(ranked, "omision_distrito_stock_renta")
    a = next(row for row in rows if row["distrito_omitido"] == "A")
    assert a["n"] == 4 and a["spearman"] == pytest.approx(math.sqrt(0.9))


@pytest.mark.parametrize(
    "values", ["('v','A',1,1)", "('v','A',1,1),('v','A',1,2)", "('v','A',1,1),('v','B',2,2)"]
)
def test_no_rank_variation_or_district_peers_is_null_not_nan(ranked, values):
    con, _, _ = ranked
    con.execute("insert into pairs values " + values)
    row = execute(ranked, "asociaciones_stock_renta")[0]
    assert row["rangos_centrados_distrito"] is None
    assert all(
        value is None or not isinstance(value, float) or math.isfinite(value)
        for value in row.values()
    )


def test_ambiguous_and_mismatched_rent_keys_never_multiply_or_select_values(analysis):
    with duckdb.connect() as con:
        con.execute("create schema housing")
        con.execute("create table physical as select 'A' as idg,'Alpha' as barrio,'D' as distrito")
        con.execute(
            "create table housing.barrios_sevilla as select 'A' as idg, 'Alpha' as barrio,"
            "'D' as distrito,2022 as anyo,7.0::double as ipra_eur_m2"
        )
        queries = {**QUERIES, "stock_barrios": "select * from physical"}
        sql = analysis.expand(queries["stock_renta"], queries)
        assert con.execute(sql).fetchall() == [("A", "Alpha", "D", 1, 7.0)]
        con.execute("insert into housing.barrios_sevilla values ('A','Alpha','D',2022,100)")
        assert con.execute(sql).fetchall() == [("A", "Alpha", "D", 2, None)]
        con.execute("delete from housing.barrios_sevilla where ipra_eur_m2=100")
        con.execute("update housing.barrios_sevilla set barrio='Wrong geography'")
        assert con.execute(sql).fetchall() == [("A", "Alpha", "D", 1, None)]
        con.execute("update housing.barrios_sevilla set anyo=2021")
        assert con.execute(sql).fetchall() == [("A", "Alpha", "D", 0, None)]


def test_query_expansion_refuses_unknown_or_cyclic_references(analysis):
    with pytest.raises(ValueError):
        analysis.expand("${missing}", {})
    with pytest.raises(ValueError):
        analysis.expand("${a}", {"a": "${a}"})


def test_page_contract_discloses_selection_units_and_noncausal_sensitivity():
    page = (ROOT / "evidence/pages/stock.md").read_text()
    assert "supervivencia y modificaciones posteriores" in page
    assert "rango **global**" in page and "no un intervalo de" in page
    assert "no controla ingresos" in page
    assert "rank()" in QUERIES["omision_distrito_stock_renta"]


def test_omitting_the_only_district_retains_an_empty_null_result(ranked):
    con, _, _ = ranked
    con.execute("insert into pairs values ('v','A',1,1),('v','A',2,2)")
    rows = execute(ranked, "omision_distrito_stock_renta")
    assert rows == [{"variable": "v", "distrito_omitido": "A", "n": 0, "spearman": None}]


def test_report_cli_rejects_missing_changed_results_and_metadata(analysis, tmp_path, monkeypatch):
    import json

    output = tmp_path / "report.json"
    payload = {"meta": {"page": "original"}, "results": {"coefficient": None}}
    monkeypatch.setattr(analysis, "OUTPUT", output)
    monkeypatch.setattr(analysis, "report", lambda: payload)
    monkeypatch.setattr("sys.argv", ["analyze_stock_rent.py", "--check"])
    with pytest.raises(SystemExit, match="missing or stale"):
        analysis.main()
    monkeypatch.setattr("sys.argv", ["analyze_stock_rent.py"])
    analysis.main()
    monkeypatch.setattr("sys.argv", ["analyze_stock_rent.py", "--check"])
    analysis.main()
    modified = json.loads(output.read_text())
    modified["results"]["coefficient"] = 0.5
    output.write_text(json.dumps(modified))
    with pytest.raises(SystemExit, match="missing or stale"):
        analysis.main()
    output.write_text(json.dumps(payload))
    payload["meta"]["page"] = "changed"
    with pytest.raises(SystemExit, match="missing or stale"):
        analysis.main()


@pytest.fixture
def summary(analysis):
    with duckdb.connect() as con:
        con.execute("create table baseline(variable varchar,n integer,spearman double)")
        con.execute(
            "create table adjusted(variable varchar,anyo_ingreso integer,n integer,"
            "distrito_ingreso double)"
        )
        queries = {
            **QUERIES,
            "asociaciones_stock_renta": "select * from baseline",
            "sensibilidad_stock_ingreso": "select * from adjusted",
        }
        yield con, queries, analysis


def test_reader_summary_passes_both_years_and_counts_without_selecting_variant(summary):
    con, _, _ = summary
    con.execute("insert into baseline values ('v',4,0.6)")
    con.execute("insert into adjusted values ('v',2019,4,-0.3),('v',2020,4,0.4),('v',2021,99,0.99)")
    assert execute(summary, "lectura_stock_renta") == [
        {
            "variable": "v",
            "n_sin_ajuste": 4,
            "rho_sin_ajuste": 0.6,
            "n_ingreso_2019": 4,
            "rho_ingreso_2019": -0.3,
            "n_ingreso_2020": 4,
            "rho_ingreso_2020": 0.4,
            "lectura": "Misma muestra; asociación descriptiva",
        }
    ]


def test_reader_summary_retains_missing_and_degenerate_adjustments(summary):
    con, _, _ = summary
    con.execute("insert into baseline values ('v',4,0.6)")
    con.execute("insert into adjusted values ('v',2019,3,null)")
    row = execute(summary, "lectura_stock_renta")[0]
    assert row["n_ingreso_2019"] == 3 and row["rho_ingreso_2019"] is None
    assert row["n_ingreso_2020"] is None and row["rho_ingreso_2020"] is None
    assert row["lectura"] == "Algún ajuste no está definido"


def test_reader_summary_warns_about_different_sample_sizes_and_keeps_zero(summary):
    con, _, _ = summary
    con.execute("insert into baseline values ('v',4,0.6)")
    con.execute("insert into adjusted values ('v',2019,3,0.0),('v',2020,2,0.4)")
    row = execute(summary, "lectura_stock_renta")[0]
    assert row["n_sin_ajuste"] == 4 and row["n_ingreso_2019"] == 3 and row["n_ingreso_2020"] == 2
    assert row["rho_ingreso_2019"] == 0
    assert row["lectura"] == "Muestras distintas: consulte cobertura"


def test_reader_summary_variables_never_cross_join(summary):
    con, _, _ = summary
    con.execute("insert into baseline values ('a',4,0.6),('b',5,-0.2)")
    con.execute("insert into adjusted values ('a',2019,4,0.3),('b',2020,5,-0.4)")
    rows = execute(summary, "lectura_stock_renta")
    assert len(rows) == 2
    assert rows[0]["rho_ingreso_2019"] == 0.3 and rows[0]["rho_ingreso_2020"] is None
    assert rows[1]["rho_ingreso_2019"] is None and rows[1]["rho_ingreso_2020"] == -0.4


def test_reader_summary_contract_separates_density_availability_and_causality():
    page = (ROOT / "evidence/pages/stock.md").read_text()
    assert "Stock declarado ≠ vivienda disponible; correlación ≠ efecto de" in page
    assert "Más\ncontroles sobre estas instantáneas no reconstruyen" in page
    assert page.index("```sql lectura_stock_renta") < page.index("## Qué cuenta cada fila")
