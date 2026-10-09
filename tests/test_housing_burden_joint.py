"""Direct published age-poverty rates, not reconstructed subgroup intersections."""

import copy
import re
from pathlib import Path

import duckdb
import pytest

from test_housing_overburden import burden, fixture

ROOT = Path(__file__).resolve().parents[1]


def payload(reverse=False):
    p = fixture("ilc_lvho07a", reverse=reverse)
    cat = p["dimension"]["rskpovth"]["category"]
    cat["index"] = {"TOTAL": 0, "A_60": 1, "B_60": 2}
    cat["label"] = {k: k for k in cat["index"]}
    p["size"][p["id"].index("rskpovth")] = 3
    p["value"] = {"0": 0}  # an observed marginal, independent of the joint cells
    p["status"] = {}
    return p


def index(p, **coords):
    result = 0
    for dim, size in zip(p["id"], p["size"], strict=True):
        positions = p["dimension"][dim]["category"]["index"]
        selected = coords.get(dim, next(iter(positions)))
        result = result * size + positions[selected]
    return str(result)


@pytest.mark.parametrize("reverse", [False, True])
def test_direct_coordinates_total_sex_and_flags(reverse):
    p = payload(reverse)
    selected = index(p, age="Y18-24", sex="T", rskpovth="B_60", time="2025")
    p["value"][selected], p["status"][selected] = 11.2, "b e"
    p["value"][index(p, age="Y18-24", sex="F", rskpovth="B_60", time="2025")] = 99
    rows = burden.parse_age_poverty(p)
    assert len(rows) == 5 * 2 * 2
    wanted = next(
        r
        for r in rows
        if (r["age_code"], r["poverty_code"], r["survey_year"]) == ("Y18-24", "B_60", 2025)
    )
    assert wanted["rate_pct"] == 11.2 and wanted["status"] == "b e"
    assert not any(r["rate_pct"] == 99 for r in rows)
    assert {r["poverty_code"] for r in rows} == {"A_60", "B_60"}
    assert all(r["geo"] == "ES" for r in rows)


def test_true_zero_and_missing_cells_not_confused():
    p = payload()
    p["value"][index(p, age="Y25-29", rskpovth="A_60", time="2025")] = 0
    rows = burden.parse_age_poverty(p)
    assert any(r["rate_pct"] == 0 for r in rows)
    assert any(r["rate_pct"] is None for r in rows)


def test_dense_values_and_list_category_indices_agree():
    p = payload()
    sparse = burden.parse_age_poverty(p)
    dense = copy.deepcopy(p)
    size = 1
    for n in p["size"]:
        size *= n
    dense["value"] = [None] * size
    dense["value"][0] = 0
    for dim in dense["dimension"].values():
        dim["category"]["index"] = list(dim["category"]["index"])
    assert burden.parse_age_poverty(dense) == sparse


@pytest.mark.parametrize("bad", [-1, 101, float("inf"), float("nan"), True, "11.2"])
def test_invalid_joint_rates_rejected(bad):
    p = payload()
    p["value"][index(p, age="Y18-24", rskpovth="B_60")] = bad
    with pytest.raises(ValueError):
        burden.parse_age_poverty(p)


def test_missing_poverty_category_rejected():
    with pytest.raises(ValueError, match="poverty/total-sex"):
        burden.parse_age_poverty(fixture("ilc_lvho07a"))


def test_no_marginal_reconstruction_when_joint_missing():
    p = payload()
    p["value"][index(p, age="Y18-24", rskpovth="TOTAL", time="2025")] = 55
    rows = burden.parse_age_poverty(p)
    assert all(r["rate_pct"] is None for r in rows)


def test_latest_year_query_does_not_backfill_subgroup():
    text = (ROOT / "evidence/pages/acceso.md").read_text()
    query = re.search(r"```sql sobrecarga_edad_pobreza\n(.*?)\n```", text, re.S).group(1)
    with duckdb.connect() as c:
        c.execute("create schema access")
        c.execute("create table access.overburden(survey_year integer,rate_pct double)")
        c.execute("insert into access.overburden values (2025,7)")
        c.execute(
            "create table access.overburden_age_poverty(age_code varchar,age_label varchar,"
            "poverty_code varchar,poverty_label varchar,survey_year integer,"
            "rate_pct double,status varchar)"
        )
        c.execute(
            "insert into access.overburden_age_poverty values "
            "('Y18-24','Young','B_60','Below',2024,30,''),"
            "('Y18-24','Young','B_60','Below',2025,NULL,'u')"
        )
        rows = c.execute(query).fetchall()
    assert len(rows) == 1 and rows[0][4:] == (2025, None, "u")


def test_page_retains_conditional_national_person_denominator():
    text = (ROOT / "evidence/pages/acceso.md").read_text()
    for phrase in [
        "celdas conjuntas publicadas directamente",
        "personas de cada combinación",
        "No identifica jóvenes inquilinos de bajos ingresos",
        "No es el primer quintil",
    ]:
        assert phrase in text


@pytest.mark.parametrize("bad", [0, False, 1])
def test_invalid_joint_status_rejected(bad):
    p = payload()
    p["status"][index(p, age="Y18-24", rskpovth="B_60")] = bad
    with pytest.raises(ValueError, match="status"):
        burden.parse_age_poverty(p)


@pytest.mark.parametrize("target", ["database", "parquet"])
def test_exact_joint_derivation_detects_tampering(target, tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq

    import verify_housing_overburden as verify

    original = burden.parse(payload(), "ilc_lvho07a")
    joint = burden.parse_age_poverty(payload())
    marginal_path = tmp_path / "marginal.parquet"
    joint_path = tmp_path / "joint.parquet"
    db_path = tmp_path / "burden.duckdb"
    marginal_table = pa.Table.from_pylist(original, schema=burden.SCHEMA)
    joint_table = pa.Table.from_pylist(joint, schema=burden.JOINT_SCHEMA)
    pq.write_table(marginal_table, marginal_path)
    pq.write_table(joint_table, joint_path)
    with duckdb.connect(str(db_path)) as c:
        c.register("m", marginal_table)
        c.register("j", joint_table)
        c.execute("create table overburden as select * from m")
        c.execute("create table overburden_age_poverty as select * from j")
    monkeypatch.setattr(verify, "ROOT", tmp_path)
    monkeypatch.setattr(verify, "PARQUET", marginal_path)
    monkeypatch.setattr(verify, "JOINT_PARQUET", joint_path)
    monkeypatch.setattr(verify, "DATABASE", db_path)
    monkeypatch.setattr(verify, "pinned_rows", lambda: original)
    monkeypatch.setattr(verify, "pinned_joint_rows", lambda: joint)
    pins = {p.name: "pin" for p in [marginal_path, joint_path, db_path]}
    monkeypatch.setattr(verify.manifest, "load", lambda: {"sha256": pins})
    monkeypatch.setattr(verify.manifest, "check", lambda expected: ([], []))
    verify.main()
    if target == "database":
        with duckdb.connect(str(db_path)) as c:
            c.execute("update overburden_age_poverty set rate_pct=9 where age_code='Y18-24'")
    else:
        changed = copy.deepcopy(joint)
        changed[0]["rate_pct"] = 9
        pq.write_table(pa.Table.from_pylist(changed, schema=burden.JOINT_SCHEMA), joint_path)
    with pytest.raises(SystemExit, match="Joint burden .* stale"):
        verify.main()
