"""Offline export contracts: existing normal ranges are not bootstrap CIs."""

import copy
import json
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_inference as inference  # noqa: E402


def payload():
    source = {}
    for key, (_, _, y, spec) in inference.MODELS.items():
        source[key] = {
            "y": y,
            "spec": spec,
            "n": 100,
            "clusters": 10,
            "coefs": {"d_tour": {"b": 0.0, "se": 0.1, "ci95": [-0.196, 0.196]}},
            "wild_bootstrap": {"d_tour": {"p": 0.6, "reps": 1999, "t_star_ci95": [-999, 999]}},
        }
    source["_meta"] = {"fixture": "current"}
    return source


def test_normal_endpoints_not_replaced_by_null_statistic_quantiles():
    rows = inference.parse(payload())
    assert len(rows) == 4
    assert {row["model_key"] for row in rows} == set(inference.MODELS)
    assert all(row["normal_lo"] == -0.196 and row["normal_hi"] == 0.196 for row in rows)
    assert all(row["wild_p_zero"] == 0.6 for row in rows)
    assert all("t_star_ci95" not in row for row in rows)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("b", float("nan")),
        ("se", -1),
        ("se", True),
        ("ci95", [1, -1]),
        ("ci95", [0]),
        ("ci95", [-2, 2]),
    ],
)
def test_malformed_or_changed_normal_interval_fails(field, bad):
    source = payload()
    source["sale_tour_only"]["coefs"]["d_tour"][field] = bad
    with pytest.raises(ValueError):
        inference.parse(source)


@pytest.mark.parametrize("p", [0, -0.1, 1.1, float("inf"), True])
def test_invalid_bootstrap_p_fails(p):
    source = payload()
    source["sale_tour_only"]["wild_bootstrap"]["d_tour"]["p"] = p
    with pytest.raises(ValueError):
        inference.parse(source)


@pytest.mark.parametrize("n,clusters", [(0, 10), (100, 1), (10, 11), (100, 2.5)])
def test_invalid_sample_cluster_counts_fail(n, clusters):
    source = payload()
    source["sale_tour_only"].update(n=n, clusters=clusters)
    with pytest.raises(ValueError):
        inference.parse(source)


def test_source_model_set_and_definition_must_match():
    source = payload()
    del source["rent_with_pop"]
    with pytest.raises(ValueError, match="model set"):
        inference.parse(source)
    source = payload()
    source["sale_tour_only"]["spec"] = ["something_else"]
    with pytest.raises(ValueError, match="definition"):
        inference.parse(source)


def test_independently_rounded_source_endpoints_are_preserved():
    source = payload()
    source["sale_tour_only"]["coefs"]["d_tour"] = {
        "b": -0.2107,
        "se": 0.3092,
        "ci95": [-0.8168, 0.3955],
    }
    row = inference.parse(source)[0]
    assert (row["normal_lo"], row["normal_hi"]) == (-0.8168, 0.3955)
    assert row["normal_lo"] != row["b"] - 1.96 * row["se"]


def test_source_rows_reject_stale_meta_and_pin_current_bytes(tmp_path, monkeypatch):
    artifact = tmp_path / "fixture.json"
    source = payload()
    artifact.write_text(json.dumps(source))
    monkeypatch.setattr(inference, "ARTIFACT", artifact)
    monkeypatch.setattr(inference.ols, "model_meta", lambda *args: {"fixture": "current"})
    rows, metadata = inference.source_rows()
    assert len(rows) == 4
    assert metadata["source_artifact_sha"] == inference.ols.sha_file(str(artifact))
    assert metadata["export_script_sha"] == inference.ols.sha_file(inference.__file__)
    source["_meta"] = {"fixture": "old"}
    artifact.write_text(json.dumps(source))
    with pytest.raises(ValueError, match="stale"):
        inference.source_rows()


def inv_payload():
    return {
        "grid": [-0.5, 0.0, 0.5],
        "reps": 1999,
        "seed": 20261006,
        "alpha": 0.05,
        "models": {
            key: {
                "y": y,
                "spec": spec,
                "n": 100,
                "clusters": 10,
                "b": 0.0,
                "se": 0.1,
                "p": [0.02, 0.6, 0.02],
                "keep": [False, True, False],
                "warnings": [],
            }
            for key, (_, _, y, spec) in inference.MODELS.items()
        },
        "_meta": {"fixture": "inversion"},
    }


def test_parse_inversion_candidate_and_summary_rows():
    candidates, summaries = inference.parse_inversion(inv_payload())
    assert len(candidates) == 12  # 4 models x 3 candidates
    assert all(row["model_key"] in inference.MODELS for row in candidates)
    assert all(row["candidate_c"] in (-0.5, 0.0, 0.5) for row in candidates)
    kept = {row["model_key"] for row in candidates if row["keep_95"]}
    assert kept == set(inference.MODELS)
    assert all(
        (s["accepted_min_c"], s["accepted_max_c"], s["accepted_count"]) == (0.0, 0.0, 1)
        for s in summaries
    )
    assert all(s["warnings"] == "" for s in summaries)


@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda d: d.update(grid=[0.0, 0.0]), "increasing"),
        (lambda d: d.update(reps=299), "reps/seed"),
        (lambda d: d.update(alpha=0.1), "alpha"),
        (lambda d: d["models"]["sale_tour_only"].update(keep=[True, True]), "keep mask"),
        (lambda d: d["models"]["sale_tour_only"].update(p=[0.0, 0.6, 0.02]), "candidate p"),
        (lambda d: d["models"].pop("rent_with_pop"), "model set"),
        (lambda d: d["models"]["sale_tour_only"].update(se=0.0), "nonpositive"),
    ],
)
def test_malformed_inversion_artifact_fails(mutate, message):
    source = inv_payload()
    mutate(source)
    with pytest.raises(ValueError, match=message):
        inference.parse_inversion(source)


def test_empty_acceptance_requires_resolution_warning():
    source = inv_payload()
    source["models"]["sale_tour_only"]["p"] = [0.02, 0.02, 0.02]
    source["models"]["sale_tour_only"]["keep"] = [False, False, False]
    with pytest.raises(ValueError, match="warnings inconsistent"):
        inference.parse_inversion(source)
    source["models"]["sale_tour_only"]["warnings"] = ["no_candidate_accepted_at_this_resolution"]
    candidates, summaries = inference.parse_inversion(source)
    sale = next(s for s in summaries if s["model_key"] == "sale_tour_only")
    assert sale["accepted_count"] == 0 and sale["accepted_min_c"] is None


def test_exact_sidecar_derivation_and_metadata_are_verified(tmp_path, monkeypatch):
    database = tmp_path / "inference.duckdb"
    monkeypatch.setattr(inference, "DATABASE", database)
    rows = inference.parse(payload())
    inv_rows, inv_meta_rows = inference.parse_inversion(inv_payload())
    metadata = {"source_artifact_sha": "fixture-source", "export_script_sha": "fixture-code"}
    inv_metadata = {
        "inversion_script_sha": "fixture-inv-script",
        "inversion_artifact_sha": "fixture-inv-artifact",
        "inversion_meta": '{"fixture": "inversion"}',
    }
    with duckdb.connect(str(database)) as con:
        con.register("fixture", pa.Table.from_pylist(rows, schema=inference.SCHEMA))
        con.execute("create table tourism_panel as select * from fixture")
        con.register("inv", pa.Table.from_pylist(inv_rows, schema=inference.INV_SCHEMA))
        con.execute("create table tourism_inversion as select * from inv")
        con.register(
            "inv_meta", pa.Table.from_pylist(inv_meta_rows, schema=inference.INV_META_SCHEMA)
        )
        con.execute("create table tourism_inversion_meta as select * from inv_meta")
        con.execute("create table export_meta (key varchar, value varchar)")
        con.executemany(
            "insert into export_meta values (?, ?)",
            list({**metadata, **inv_metadata}.items()),
        )
    inference.verify(rows, metadata, inv_rows, inv_meta_rows, inv_metadata)
    old_metadata = copy.deepcopy(metadata)
    old_metadata["source_artifact_sha"] = "old"
    with pytest.raises(ValueError, match="stale or changed"):
        inference.verify(rows, old_metadata, inv_rows, inv_meta_rows, inv_metadata)
    with duckdb.connect(str(database)) as con:
        con.execute("update tourism_panel set wild_p_zero = 0.9")
    with pytest.raises(ValueError, match="stale or changed"):
        inference.verify(rows, metadata, inv_rows, inv_meta_rows, inv_metadata)
    with duckdb.connect(str(database)) as con:
        con.execute("update tourism_panel set wild_p_zero = 0.494")
        con.execute("update tourism_inversion set keep_95 = not keep_95 where candidate_c = 0.0")
    with pytest.raises(ValueError, match="stale or changed"):
        inference.verify(rows, metadata, inv_rows, inv_meta_rows, inv_metadata)


def test_missing_sidecar_fails_with_rebuild_guidance(tmp_path, monkeypatch):
    monkeypatch.setattr(inference, "DATABASE", tmp_path / "missing.duckdb")
    inv_rows, inv_meta_rows = inference.parse_inversion(inv_payload())
    with pytest.raises(ValueError, match="make inference"):
        inference.verify(
            inference.parse(payload()),
            {},
            inv_rows,
            inv_meta_rows,
            {"inversion_script_sha": "x", "inversion_artifact_sha": "y", "inversion_meta": "{}"},
        )


@pytest.mark.parametrize(
    "mutate,message",
    [
        (
            lambda d: d["models"]["sale_tour_only"].update(keep=[True, True, False]),
            "keep mask inconsistent",
        ),
        (
            lambda d: d["models"]["sale_tour_only"].update(warnings=["disjoint_accepted_set"]),
            "warnings inconsistent",
        ),
        (
            lambda d: d["models"]["sale_tour_only"].update(
                warnings=["accepted_set_may_extend_below_grid"]
            ),
            "warnings inconsistent",
        ),
        (
            lambda d: d["models"]["sale_tour_only"].update(keep=[True, False, False]),
            "keep mask inconsistent",
        ),
    ],
)
def test_inversion_mask_and_warning_consistency_enforced(mutate, message):
    source = inv_payload()
    mutate(source)
    with pytest.raises(ValueError, match=message):
        inference.parse_inversion(source)


def test_inversion_mask_alpha_and_contiguous_warnings_pass_when_consistent():
    source = inv_payload()
    # Keep mask matches p >= alpha; edge-accepted warnings follow the mask.
    source["models"]["sale_tour_only"].update(
        p=[0.9, 0.02, 0.02],
        keep=[True, False, False],
        warnings=["accepted_set_may_extend_below_grid"],
    )
    candidates, summaries = inference.parse_inversion(source)
    sale = next(s for s in summaries if s["model_key"] == "sale_tour_only")
    assert sale["accepted_min_c"] == -0.5 and sale["accepted_count"] == 1
    assert sale["warnings"] == "accepted_set_may_extend_below_grid"
