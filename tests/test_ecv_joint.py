"""Synthetic joint contracts; no empirical microdata/outcomes in offline tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "ecv_joint", Path(__file__).parents[1] / "scripts/build_ecv_joint.py"
)
assert SPEC and SPEC.loader
joint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(joint)


def cell(persons=50, households=30, target=100, valid=95, outcome=0):
    result = joint.new_cell()
    result.update(
        target_persons=persons,
        valid_persons=persons,
        target_households=set(range(households)),
        valid_households=set(range(households)),
        target_weight=target,
        valid_weight=valid,
        burden_weight=outcome,
    )
    return result


def test_presentation_exact_boundaries_and_true_zero():
    result = joint.present(cell())
    assert result["status"] == "available"
    assert result["rate_pct"] == 0
    assert result["weighted_missing_cost_loss_pct"] == pytest.approx(5)
    assert "burden_weight" not in result
    assert not any(isinstance(v, set) for v in result.values())


@pytest.mark.parametrize(
    ("persons", "households", "valid", "reason"),
    [
        (49, 30, 95, "less_than_50_valid_persons"),
        (50, 29, 95, "less_than_30_valid_households"),
        (50, 30, 94.999, "over_5pct_weighted_cost_loss"),
    ],
)
def test_each_suppression_gate(persons, households, valid, reason):
    result = joint.present(cell(persons, households, valid=valid, outcome=10))
    assert result["rate_pct"] is None
    assert result["status"] == "suppressed"
    assert reason in result["suppression_reasons"]


def test_multiple_reasons_and_empty_no_cost_states():
    result = joint.present(cell(1, 1, valid=50, outcome=10))
    assert len(result["suppression_reasons"].split(";")) == 3
    assert result["rate_pct"] is None
    empty = joint.present(joint.new_cell())
    assert empty["status"] == "empty" and empty["rate_pct"] is None
    assert empty["weighted_missing_cost_loss_pct"] is None
    missing = cell(0, 0, valid=0)
    missing["target_persons"] = 2
    missing["target_households"] = {1}
    no_cost = joint.present(missing)
    assert no_cost["status"] == "no_valid_cost"
    assert no_cost["rate_pct"] is None
    assert no_cost["weighted_missing_cost_loss_pct"] == 100


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (-1, "Y_LT18"),
        (17, "Y_LT18"),
        (18, "Y18-24"),
        (24, "Y18-24"),
        (25, "Y25-29"),
        (29, "Y25-29"),
        (30, "Y30-64"),
        (64, "Y30-64"),
        (65, "Y_GE65"),
    ],
)
def test_disjoint_cohorts(age, expected):
    assert joint.cohort(age) == expected


def population():
    data = {"d": [], "h": [], "r": []}
    for hid in range(1, 31):
        data["d"].append(
            {"DB010": "2025", "DB020": "ES", "DB030": str(hid), "DB090": "1", "DB090_F": "1"}
        )
        data["h"].append(
            {
                "HB010": "2025",
                "HB020": "ES",
                "HB030": str(hid),
                "HX040": "2",
                "HY020": "10000",
                "HY020_F": "51",
                "HY070G": "0",
                "HY070G_F": "15",
                "HH070": "0",
                "HH070_F": "1",
                "HH021": "3",
                "HH021_F": "1",
            }
        )
        for ordinal in (1, 2):
            data["r"].append(
                {
                    "RB010": "2025",
                    "RB020": "ES",
                    "RB030": str(hid * 100 + ordinal),
                    "RB050": "2",
                    "RB050_F": "1",
                    "RB081": "20",
                    "RB081_F": "1",
                    "RB090": "1",
                    "RB090_F": "1",
                }
            )
    return data


def test_complete_grid_conservation_households_and_imputation():
    rows = joint.derive(population())
    assert len(rows) == 90
    keyed = {(r["age_code"], r["poverty_code"], r["tenure_code"]): r for r in rows}
    assert len(keyed) == 90
    total = keyed["TOTAL", "TOTAL", "TOTAL"]
    assert total["sample_valid_persons"] == 60
    assert total["sample_valid_households"] == 30
    assert total["weighted_valid_persons"] == 120
    assert total["known_imputed_income_target_persons"] == 60
    assert total["rate_pct"] is None
    assert total["status"] == "marginal_not_published"
    assert keyed["Y18-24", "A_60", "RENT_MKT"]["rate_pct"] == 0
    for dimension, codes in enumerate([joint.AGES, joint.POVERTY, joint.TENURE]):
        keys = [
            tuple(code if i == dimension else "TOTAL" for i in range(3))
            for code in codes
            if code != "TOTAL"
        ]
        assert sum(keyed[k]["sample_target_persons"] for k in keys) == 60
        assert sum(keyed[k]["weighted_target_persons"] for k in keys) == 120
    assert keyed["Y_GE65", "B_60", "OWN_L"]["status"] == "empty"
    assert all("burden_weight" not in row and "RB030" not in row for row in rows)


def test_missing_cost_never_becomes_zero():
    data = population()
    data["h"][0].update(HH070="", HH070_F="-1")
    total = next(
        r
        for r in joint.derive(data)
        if (r["age_code"], r["poverty_code"], r["tenure_code"]) == ("TOTAL", "TOTAL", "TOTAL")
    )
    assert total["sample_target_persons"] == 60
    assert total["sample_valid_persons"] == 58
    assert total["sample_valid_households"] == 29
    assert total["rate_pct"] is None
    assert "less_than_30_valid_households" in total["suppression_reasons"]


def test_exact_storage_and_repinned_tamper_fail(tmp_path, monkeypatch):
    import hashlib

    import duckdb

    class Pins:
        def __init__(self):
            self.pins = {}

        def load(self):
            return {"sha256": self.pins}

        def record(self, rel, source):
            self.pins[rel] = hashlib.sha256((tmp_path / rel).read_bytes()).hexdigest()

        def check(self, expected):
            missing, changed = [], []
            for rel, digest in expected.items():
                p = tmp_path / rel
                if not p.exists():
                    missing.append(rel)
                elif hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                    changed.append(rel)
            return missing, changed

    pins = Pins()
    processed = tmp_path / "processed"
    processed.mkdir()
    monkeypatch.setattr(joint, "ROOT", tmp_path)
    monkeypatch.setattr(joint, "PROCESSED", processed)
    monkeypatch.setattr(joint, "PARQUET", tmp_path / "raw/joint.parquet")
    monkeypatch.setattr(joint, "DATABASE", processed / "joint.duckdb")
    monkeypatch.setattr(joint, "manifest", pins)
    rows = joint.derive(population())
    metadata = {"test": "synthetic"}
    joint.save(rows, metadata)
    joint.verify(rows, metadata)
    with duckdb.connect(str(joint.DATABASE)) as c:
        c.execute(
            "UPDATE joint_burden SET rate_pct=99 WHERE age_code='TOTAL' "
            "AND poverty_code='TOTAL' AND tenure_code='TOTAL'"
        )
    pins.record("processed/joint.duckdb", {})
    with pytest.raises(ValueError, match="exact derivation"):
        joint.verify(rows, metadata)
    joint.save(rows, metadata)
    with duckdb.connect(str(joint.DATABASE)) as c:
        c.execute("UPDATE metadata SET value='{}'")
    pins.record("processed/joint.duckdb", {})
    with pytest.raises(ValueError, match="proof stale"):
        joint.verify(rows, metadata)


def test_export_fields_and_suppression_cannot_be_bypassed():
    rows = joint.derive(population())
    assert all(set(r) == set(joint.schema().names) for r in rows)
    assert not any("burden_weight" in name for name in joint.schema().names)
    with pytest.raises(ValueError, match="2025"):
        joint.derive(population(), 2024)


def test_no_own_marginal_rates_and_hidden_household_mutation():
    data = population()
    data["d"].append({**data["d"][-1], "DB030": "31"})
    data["h"].append({**data["h"][-1], "HB030": "31"})
    data["r"].extend([{**data["r"][-1], "RB030": str(pid)} for pid in (3101, 3102)])
    for person in data["r"][:2]:
        person["RB081"] = "25"
    before = joint.derive(data)
    data["h"][0]["HH070"] = "2000"
    after = joint.derive(data)
    assert before == after  # Hidden outcome change cannot affect any released outcome.
    assert all(
        r["rate_pct"] is None
        for r in after
        if "TOTAL" in (r["age_code"], r["poverty_code"], r["tenure_code"])
    )
    released = [r for r in after if r["rate_pct"] is not None]
    assert released and all(
        "TOTAL" not in (r["age_code"], r["poverty_code"], r["tenure_code"]) for r in released
    )


def test_flag_proof_retains_modes_and_source_counts_by_unit():
    data = population()
    data["h"][0]["HY020_F"] = "21"
    result = joint.flag_summary(data)
    assert result["HY020_F"] == {
        "unit": "sample_households",
        "full_validated_flag_counts": {"21": 1, "51": 29},
    }
    assert result["HY070G_F"]["full_validated_flag_counts"] == {"15": 30}
    assert result["RB050_F"] == {"unit": "sample_persons", "full_validated_flag_counts": {"1": 60}}
    assert not any("burden" in k or "030" in k for k in result)


def test_shared_household_extremes_remain_a_documented_presentation_limit():
    # A visible all-zero adult outcome can logically imply a hidden child outcome.
    # This is NOT a confidentiality mechanism, even with disjoint age leaves.
    data = population()
    for hid in range(1, 31):
        data["h"][hid - 1]["HX040"] = "3"
        data["r"].append({**data["r"][0], "RB030": str(hid * 100 + 3), "RB081": "10"})
    keyed = {(r["age_code"], r["poverty_code"], r["tenure_code"]): r for r in joint.derive(data)}
    adult = keyed["Y18-24", "A_60", "RENT_MKT"]
    child = keyed["Y_LT18", "A_60", "RENT_MKT"]
    assert adult["rate_pct"] == 0 and adult["status"] == "available"
    assert child["rate_pct"] is None and child["status"] == "suppressed"
    assert adult["sample_valid_households"] == child["sample_valid_households"] == 30
    page = (Path(__file__).parents[1] / "evidence/pages/acceso.md").read_text()
    assert "Incluso los propios agregados" in page
    assert "por compartir hogares" in page
