"""Offline income source and descriptive partial-rank contracts."""

import copy
import importlib.util
import math
from pathlib import Path

import duckdb
import pytest

from test_stock_rent import QUERIES

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def source(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "income_source", ROOT / "scripts/fetch_sevilla_income.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def payloads():
    attrs = [
        {
            "IDG": f"01{i:03}",
            "ID_DIS": "01",
            "ID_BAR": f"{i:03}",
            "BAR": f"B{i}",
            "DIS": "D",
            **{f"ING_FAM_{y}": 10000 + i for y in range(15, 21)},
        }
        for i in range(1, 109)
    ]
    return (
        {"features": [{"attributes": a} for a in attrs]},
        {
            "id": 31,
            "name": "Income a escala Barrio",
            "fields": [
                {
                    "name": k,
                    "type": "esriFieldTypeInteger"
                    if k.startswith("ING_")
                    else "esriFieldTypeString",
                }
                for k in attrs[0]
            ],
        },
        {
            "widgets": {
                "widget_1389": {
                    "config": {
                        "text": (
                            "<p>Ingresos familiares declarados ejercicio AA "
                            "(Renta media neta €)</p>"
                        )
                    }
                }
            }
        },
    )


def test_source_preserves_null_income(source, payloads):
    payloads[0]["features"][0]["attributes"]["ING_FAM_16"] = None
    rows = source.parse(*payloads)
    assert len(rows) == 648
    assert rows[1] == ("01001", "B1", "D", 2016, None)


@pytest.mark.parametrize(
    "issue",
    [
        "duplicate",
        "conflict",
        "truncated",
        "missing",
        "definition",
        "grain",
        "negative",
        "nan",
        "boolean",
    ],
)
def test_source_rejects_unsafe_inputs(source, payloads, issue):
    q, m, d = copy.deepcopy(payloads)
    a = q["features"][0]["attributes"]
    if issue == "duplicate":
        q["features"][1] = copy.deepcopy(q["features"][0])
    elif issue == "conflict":
        a["ID_DIS"] = "02"
    elif issue == "truncated":
        q["exceededTransferLimit"] = True
    elif issue == "missing":
        q["features"].pop()
    elif issue == "definition":
        d["widgets"] = {}
    elif issue == "grain":
        m["id"] = 47
    else:
        a["ING_FAM_20"] = {"negative": -1, "nan": float("nan"), "boolean": True}[issue]
    with pytest.raises(ValueError):
        source.parse(q, m, d)


@pytest.fixture
def sample():
    with duckdb.connect() as con:
        con.execute("set threads=1")
        con.execute(
            "create table pairs(idg varchar,barrio varchar,distrito varchar,"
            "variable varchar,x double,y double)"
        )
        con.execute("create schema income")
        con.execute(
            "create table income.barrios_income(idg varchar,barrio varchar,"
            "distrito varchar,anyo int,renta_neta_eur double)"
        )
        yield con


def query(con, name):
    import analyze_stock_rent

    qs = {**QUERIES, "stock_renta_largo": "select * from pairs"}
    cur = con.execute(analyze_stock_rent.expand(qs[name], qs))
    return [dict(zip([c[0] for c in cur.description], row, strict=True)) for row in cur.fetchall()]


def insert(con, values, year=2019):
    for i, (x, y, z, d) in enumerate(values):
        con.execute("insert into pairs values (?,?,?,'v',?,?)", [str(i), str(i), d, x, y])
        con.execute(
            "insert into income.barrios_income values (?,?,?,?,?)", [str(i), str(i), d, year, z]
        )


def test_same_sample_baselines_and_missing_year(sample, source):
    insert(sample, [(1, 1, 10, "A"), (2, 3, 20, "A"), (3, 2, None, "A"), (4, 4, 30, "B")])
    coverage = query(sample, "cobertura_stock_ingreso")
    assert [(r["anyo_ingreso"], r["completos"], r["excluidos_ingreso"]) for r in coverage] == [
        (2019, 3, 1),
        (2020, 0, 4),
    ]
    rows = query(sample, "sensibilidad_stock_ingreso")
    assert len(rows) == 1 and rows[0]["n"] == 3
    assert rows[0]["spearman_misma_muestra"] == pytest.approx(1)


def test_ambiguous_or_mismatched_income_never_chosen(sample, source):
    insert(sample, [(1, 2, 10, "A"), (2, 1, 20, "A"), (3, 3, 30, "B")])
    sample.execute(
        "insert into income.barrios_income select * from income.barrios_income where idg='0'"
    )
    sample.execute("update income.barrios_income set barrio='Wrong' where idg='1'")
    row = query(sample, "cobertura_stock_ingreso")[0]
    assert (
        row["completos"] == 1
        and row["excluidos_ingreso"] == 2
        and row["claves_ingreso_ambiguas"] == 1
    )


def ranks(values):
    return [1 + sum(b < a for b in values) + (sum(b == a for b in values) - 1) / 2 for a in values]


def corr(x, y):
    x = [v - sum(x) / len(x) for v in x]
    y = [v - sum(y) / len(y) for v in y]
    return sum(a * b for a, b in zip(x, y, strict=True)) / math.sqrt(
        sum(v * v for v in x) * sum(v * v for v in y)
    )


def test_tied_global_partial_ranks_match_independent_correlation_identity(sample, source):
    values = [
        (1, 3, 10, "A"),
        (2, 1, 20, "A"),
        (2, 2, 20, "A"),
        (5, 4, 30, "A"),
        (3, 7, 40, "B"),
        (4, 6, 40, "B"),
        (6, 5, 50, "B"),
        (7, 8, 60, "B"),
    ]
    insert(sample, values)
    vectors = [ranks([v[j] for v in values]) for j in range(3)]
    centered = [
        [
            v - sum(w for w, row in zip(vec, values, strict=True) if row[3] == values[i][3]) / 4
            for i, v in enumerate(vec)
        ]
        for vec in vectors
    ]
    x, y, z = centered
    xy, xz, yz = corr(x, y), corr(x, z), corr(y, z)
    expected = (xy - xz * yz) / math.sqrt((1 - xz * xz) * (1 - yz * yz))
    row = query(sample, "sensibilidad_stock_ingreso")[0]
    assert row["distrito_misma_muestra"] == pytest.approx(xy)
    assert row["distrito_ingreso"] == pytest.approx(expected)


@pytest.mark.parametrize(
    "values",
    [
        [(1, 3, 10, "A"), (2, 1, 10, "A"), (3, 2, 10, "A")],
        [(1, 1, 10, "A"), (3, 2, 20, "A"), (2, 3, 30, "A"), (4, 4, 40, "A")],
        [(1, 1, 10, "A"), (2, 2, 20, "B")],
    ],
)
def test_constant_income_or_income_explained_outcome_is_null(sample, source, values):
    insert(sample, values)
    row = query(sample, "sensibilidad_stock_ingreso")[0]
    assert row["distrito_ingreso"] is None
    assert row["estado"] != "Asociación descriptiva"


def test_empty_sample_has_no_association(sample, source):
    assert query(sample, "sensibilidad_stock_ingreso") == []


def test_source_numeric_schema_change_rejected(source, payloads):
    for field in payloads[1]["fields"]:
        if field["name"] == "ING_FAM_20":
            field["type"] = "esriFieldTypeString"
    with pytest.raises(ValueError, match="numeric field types"):
        source.parse(*payloads)


def test_year_specific_samples_are_not_pooled(sample, source):
    insert(sample, [(1, 3, 10, "A"), (2, 2, 20, "A"), (3, 1, 30, "A")])
    sample.execute(
        "insert into income.barrios_income select idg,barrio,distrito,2020,renta_neta_eur "
        "from income.barrios_income where idg!='0'"
    )
    rows = query(sample, "sensibilidad_stock_ingreso")
    assert [(r["anyo_ingreso"], r["n"]) for r in rows] == [(2019, 3), (2020, 2)]
    assert [r["spearman_misma_muestra"] for r in rows] == pytest.approx([-1, -1])


def test_sidecar_verification_rejects_altered_rows_and_metadata(source, tmp_path, monkeypatch):
    path = tmp_path / "income.duckdb"
    rows = [("01001", "B", "D", 2019, 20000.0)]
    meta = {"raw": "hash"}
    monkeypatch.setattr(source, "DATABASE", path)
    monkeypatch.setattr(source, "inputs", lambda: (rows, meta))
    with pytest.raises(ValueError, match="Missing income"):
        source.verify()
    with duckdb.connect(str(path)) as con:
        con.execute(
            "create table barrios_income (idg varchar,barrio varchar,distrito varchar,"
            "anyo integer,renta_neta_eur double)"
        )
        con.executemany("insert into barrios_income values (?,?,?,?,?)", rows)
        con.execute("create table income_meta as select 'raw' as key,'hash' as value")
    source.verify()
    with duckdb.connect(str(path)) as con:
        con.execute("update barrios_income set renta_neta_eur=999")
    with pytest.raises(ValueError, match="differs from pinned source"):
        source.verify()
    with duckdb.connect(str(path)) as con:
        con.execute("update income_meta set value='wrong'")
    with pytest.raises(ValueError, match="Stale income"):
        source.verify()


def test_omissions_match_standalone_reduced_sample_refits(sample, source):
    import analyze_stock_rent

    values = [
        (1, 3, 10, "A"),
        (2, 1, 20, "A"),
        (2, 2, 20, "A"),
        (5, 4, 30, "A"),
        (3, 7, 40, "B"),
        (4, 6, 40, "B"),
        (6, 5, 50, "B"),
        (7, 8, 60, "B"),
        (4, 7, 25, "C"),
        (7, 5, 15, "C"),
        (8, 2, 45, "C"),
        (10, 9, 20, "C"),
        (6, 8, 30, "C"),
    ]
    insert(sample, values)
    omitted = query(sample, "omision_distrito_stock_ingreso")
    assert len(omitted) == 3
    for row in omitted:
        district = row["distrito_omitido"]
        qs = {**QUERIES, "stock_renta_largo": f"select * from pairs where distrito <> '{district}'"}
        cur = sample.execute(analyze_stock_rent.expand(qs["sensibilidad_stock_ingreso"], qs))
        reduced = dict(zip([c[0] for c in cur.description], cur.fetchone(), strict=True))
        for key in [
            "n",
            "distritos",
            "spearman_misma_muestra",
            "distrito_misma_muestra",
            "distrito_ingreso",
        ]:
            assert row[key] == pytest.approx(reduced[key])
        assert row["estado"] == reduced["estado"]
    # An independent rank/correlation calculation also differs from reusing old ranks.
    kept = [i for i, v in enumerate(values) if v[3] != "A"]

    def partial(vectors, group_rows):
        centered = []
        for vec in vectors:
            centered.append(
                [
                    v
                    - sum(
                        w for w, r in zip(vec, group_rows, strict=True) if r[3] == group_rows[i][3]
                    )
                    / sum(r[3] == group_rows[i][3] for r in group_rows)
                    for i, v in enumerate(vec)
                ]
            )
        x, y, z = centered
        xy, xz, yz = corr(x, y), corr(x, z), corr(y, z)
        return (xy - xz * yz) / math.sqrt((1 - xz * xz) * (1 - yz * yz))

    remaining = [values[i] for i in kept]
    fresh = [ranks([v[j] for v in remaining]) for j in range(3)]
    stale = [[ranks([v[j] for v in values])[i] for i in kept] for j in range(3)]
    expected = partial(fresh, remaining)
    row = next(r for r in omitted if r["distrito_omitido"] == "A")
    assert row["distrito_ingreso"] == pytest.approx(expected)
    assert abs(expected - partial(stale, remaining)) > 0.001


def test_omitting_only_district_retains_empty_null_summary(sample, source):
    insert(sample, [(1, 2, 10, "A"), (2, 1, 20, "A")])
    rows = query(sample, "omision_distrito_stock_ingreso")
    assert len(rows) == 1 and rows[0]["n"] == 0 and rows[0]["distritos"] == 0
    assert rows[0]["distrito_ingreso"] is None and rows[0]["estado"] == "Sin barrios completos"
    summary = query(sample, "resumen_omision_stock_ingreso")[0]
    assert (
        summary["omisiones"] == 1
        and summary["omisiones_validas"] == 0
        and summary["omisiones_nulas"] == 1
    )
    assert summary["asociacion_minima"] is None and summary["asociacion_maxima"] is None


def test_omission_districts_are_year_specific_complete_cases(sample, source):
    insert(sample, [(1, 3, 10, "A"), (2, 1, 20, "A"), (3, 2, 30, "B"), (4, 4, 40, "B")])
    sample.execute(
        "insert into income.barrios_income select idg,barrio,distrito,2020,renta_neta_eur "
        "from income.barrios_income where distrito='A'"
    )
    rows = query(sample, "omision_distrito_stock_ingreso")
    assert [(r["anyo_ingreso"], r["distrito_omitido"]) for r in rows] == [
        (2019, "A"),
        (2019, "B"),
        (2020, "A"),
    ]
    assert rows[-1]["n"] == 0 and rows[-1]["distrito_ingreso"] is None
    assert query(sample, "resumen_omision_stock_ingreso")[-1]["omisiones_nulas"] == 1


def test_omission_partitions_do_not_pool_stock_variables(sample, source):
    insert(
        sample,
        [
            (1, 3, 10, "A"),
            (2, 1, 20, "A"),
            (2, 2, 20, "A"),
            (5, 4, 30, "A"),
            (3, 7, 40, "B"),
            (4, 6, 40, "B"),
            (6, 5, 50, "B"),
            (7, 8, 60, "B"),
        ],
    )
    sample.execute("insert into pairs select idg,barrio,distrito,'reversed',100-x,y from pairs")
    rows = query(sample, "omision_distrito_stock_ingreso")
    for district in ["A", "B"]:
        a = next(r for r in rows if r["variable"] == "v" and r["distrito_omitido"] == district)
        b = next(
            r for r in rows if r["variable"] == "reversed" and r["distrito_omitido"] == district
        )
        assert a["n"] == b["n"] == 4
        if a["distrito_ingreso"] is None:
            assert b["distrito_ingreso"] is None
        else:
            assert a["distrito_ingreso"] == pytest.approx(-b["distrito_ingreso"])
    assert any(r["distrito_ingreso"] is not None for r in rows)
