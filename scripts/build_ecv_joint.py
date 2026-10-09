"""Own descriptive ECV age-poverty-tenure aggregates; no quintile inference.

Suppression/coverage rules were fixed in docs/ecv_joint_scope.md before
inspecting empirical joint outcomes. No original-design intervals are inferred.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assess_ecv_benchmarks as ecv  # noqa: E402

YEAR = 2025
MIN_PERSONS = 50
MIN_HOUSEHOLDS = 30
MAX_MISSING_FRACTION = 0.05
AGES = {
    "TOTAL": "Todas las edades",
    "Y_LT18": "Menores de 18 años",
    "Y18-24": "18–24 años",
    "Y25-29": "25–29 años",
    "Y30-64": "30–64 años",
    "Y_GE65": "65 años o más",
}
POVERTY = {
    "TOTAL": "Toda la población",
    "B_60": "Por debajo del umbral de pobreza",
    "A_60": "En el umbral de pobreza o por encima",
}
TENURE = {
    "TOTAL": "Todos los regímenes",
    "OWN_L": "Propiedad con hipoteca",
    "OWN_NL": "Propiedad sin hipoteca",
    "RENT_MKT": "Alquiler a precio de mercado",
    "RENT_FR": "Alquiler reducido o cesión gratuita",
}


def cohort(age: int) -> str:
    if age == -1:
        age = 0
    if age < 0:
        raise ValueError("Unknown reference age")
    if age < 18:
        return "Y_LT18"
    if age <= 24:
        return "Y18-24"
    if age <= 29:
        return "Y25-29"
    if age <= 64:
        return "Y30-64"
    return "Y_GE65"


def new_cell() -> dict:
    return {
        "target_persons": 0,
        "valid_persons": 0,
        "target_households": set(),
        "valid_households": set(),
        "target_weight": 0.0,
        "valid_weight": 0.0,
        "burden_weight": 0.0,  # INTERNAL only: never included in exported fields.
        "imputed_income_persons": 0,
        "imputed_allowance_persons": 0,
    }


def present(cell: dict) -> dict:
    """Apply immutable project gates; never return a suppressed rate/numerator."""
    target, valid = cell["target_weight"], cell["valid_weight"]
    missing_fraction = (target - valid) / target if target else None
    if missing_fraction is not None and not -1e-10 <= missing_fraction <= 1 + 1e-10:
        raise ValueError("Invalid weighted coverage")
    if missing_fraction is not None:
        missing_fraction = min(1.0, max(0.0, missing_fraction))
    reasons = []
    if cell["target_persons"] == 0:
        status = "empty"
    elif cell["valid_persons"] == 0:
        status = "no_valid_cost"
    else:
        if cell["valid_persons"] < MIN_PERSONS:
            reasons.append("less_than_50_valid_persons")
        if len(cell["valid_households"]) < MIN_HOUSEHOLDS:
            reasons.append("less_than_30_valid_households")
        if missing_fraction is not None and missing_fraction > MAX_MISSING_FRACTION + 1e-12:
            reasons.append("over_5pct_weighted_cost_loss")
        status = "suppressed" if reasons else "available"
    return {
        "sample_target_persons": cell["target_persons"],
        "sample_valid_persons": cell["valid_persons"],
        "sample_target_households": len(cell["target_households"]),
        "sample_valid_households": len(cell["valid_households"]),
        "weighted_target_persons": target,
        "weighted_valid_persons": valid,
        "weighted_missing_cost_loss_pct": 100 * missing_fraction
        if missing_fraction is not None
        else None,
        "known_imputed_income_target_persons": cell["imputed_income_persons"],
        "known_imputed_allowance_target_persons": cell["imputed_allowance_persons"],
        "rate_pct": 100 * cell["burden_weight"] / valid if status == "available" else None,
        "status": status,
        "suppression_reasons": ";".join(reasons),
    }


def release(cell: dict, coordinates: tuple[str, str, str]) -> dict:
    result = present(cell)
    # Only disjoint leaves may carry outcomes. Overlapping own marginals would
    # turn other rates and denominators into subtraction equations for hidden cells.
    if "TOTAL" in coordinates and result["status"] in {"available", "suppressed"}:
        result["rate_pct"] = None
        result["status"] = "marginal_not_published"
        result["suppression_reasons"] = ";".join(
            filter(None, [result["suppression_reasons"], "overlapping_marginal_rate_not_published"])
        )
    return result


def flag_summary(tables: dict[str, list[dict]]) -> dict:
    from collections import Counter

    population = ecv.prepare_population(tables, YEAR)
    summary = {}
    for table, fields, unit in [
        ("d", ["DB090_F"], "sample_households"),
        ("h", ["HY020_F", "HY070G_F", "HH070_F", "HH021_F"], "sample_households"),
        ("r", ["RB050_F", "RB081_F", "RB090_F"], "sample_persons"),
    ]:
        for field in fields:
            summary[field] = {
                "unit": unit,
                "full_validated_flag_counts": dict(
                    sorted(Counter(row[field] for row in population[table].values()).items())
                ),
            }
    return summary


def derive(tables: dict[str, list[dict]], year: int = YEAR) -> list[dict]:
    if year != YEAR:
        raise ValueError("Only the reviewed 2025 release is supported")
    population = ecv.prepare_population(tables, year)
    households, persons = population["h"], population["r"]
    cells = {key: new_cell() for key in itertools.product(AGES, POVERTY, TENURE)}
    for pid, person in persons.items():
        hid = pid // 100
        household = households[hid]
        weight = ecv.number(person["RB050"])
        age = cohort(int(person["RB081"]))
        poverty = "B_60" if population["equivalents"][hid] < population["poverty_cut"] else "A_60"
        tenure = ecv.TENURES[household["HH021"]]
        valid = household["HH070_F"] == "1"
        outcome = (
            ecv.burden(*(ecv.number(household[f]) for f in ("HH070", "HY020", "HY070G")))
            if valid
            else None
        )
        for key in itertools.product(("TOTAL", age), ("TOTAL", poverty), ("TOTAL", tenure)):
            cell = cells[key]
            cell["target_persons"] += 1
            cell["target_households"].add(hid)
            cell["target_weight"] += weight
            cell["imputed_income_persons"] += household["HY020_F"].startswith("5")
            cell["imputed_allowance_persons"] += household["HY070G_F"].startswith("5")
            if valid:
                cell["valid_persons"] += 1
                cell["valid_households"].add(hid)
                cell["valid_weight"] += weight
                cell["burden_weight"] += weight * outcome
    return [
        {
            "survey_year": year,
            "income_year": year - 1,
            "geo": "ES",
            "age_code": age,
            "age_label": AGES[age],
            "poverty_code": poverty,
            "poverty_label": POVERTY[poverty],
            "tenure_code": tenure,
            "tenure_label": TENURE[tenure],
            **release(cell, (age, poverty, tenure)),
        }
        for (age, poverty, tenure), cell in cells.items()
    ]


# Storage is separate from Eurostat's sidecar and all central estimator inputs.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import manifest  # noqa: E402
from spanish_housing.data_paths import PROCESSED, RAW, ROOT  # noqa: E402

ARCHIVE = RAW / "ine_ecv_2025.zip"
PARQUET = RAW / "parquet/ecv_joint_burden.parquet"
DATABASE = PROCESSED / "ecv_joint_burden.duckdb"
BENCHMARKS = PROCESSED / "housing_access.duckdb"
URL = "https://www.ine.es/ftp/microdatos/ecv/ecv_b2013/datos_2025.zip"


def benchmark_gate(tables):
    import duckdb

    import verify_housing_overburden

    verify_housing_overburden.main()
    with duckdb.connect(str(BENCHMARKS), read_only=True) as con:
        values = con.execute(
            "SELECT breakdown,group_code,rate_pct,status FROM overburden "
            "WHERE survey_year=2025 AND breakdown IN ('age','tenure') "
            "UNION ALL SELECT 'age_poverty',age_code || ':' || poverty_code,rate_pct,status "
            "FROM overburden_age_poverty WHERE survey_year=2025"
        ).fetchall()
    if len(values) != 20 or len({(r[0], r[1]) for r in values}) != 20:
        raise ValueError("Incomplete relevant benchmark selection")
    rows = [
        dict(zip(("breakdown", "group_code", "rate_pct", "status"), r, strict=True)) for r in values
    ]
    report = ecv.compare(ecv.calculate(tables, YEAR), rows)
    if not report["all_benchmarks_match_rounding"]:
        raise ValueError("Relevant benchmark gate failed; no joint output written")
    return report


def pinned_inputs():
    man = manifest.load()
    paths = [ARCHIVE, BENCHMARKS]
    expected = {}
    for path in paths:
        rel = str(path.relative_to(ROOT))
        if rel not in man.get("sha256", {}):
            raise ValueError(f"Unpinned ECV input: {rel}")
        expected[rel] = man["sha256"][rel]
    missing, changed = manifest.check(expected)
    if missing or changed:
        raise ValueError(f"ECV inputs missing={missing}, changed={changed}")
    return expected


def proof(inputs, tables):
    return {
        "inputs": inputs,
        "code_sha256": {
            str(Path(__file__).relative_to(ROOT)): manifest.sha256(Path(__file__)),
            str(Path(ecv.__file__).relative_to(ROOT)): manifest.sha256(Path(ecv.__file__)),
        },
        "survey_year": YEAR,
        "income_year": YEAR - 1,
        "geo": "ES",
        "estimate_kind": "own_descriptive_complete_case_person_weighted",
        "poverty_factor": 0.60,
        "poverty_reference": "national income-valid persons, before cost exclusions",
        "min_valid_persons": MIN_PERSONS,
        "min_valid_households": MIN_HOUSEHOLDS,
        "max_weighted_cost_loss_fraction": MAX_MISSING_FRACTION,
        "benchmark_cells": 20,
        "rate_release": "disjoint non-total age-poverty-tenure leaves only; own margins withheld",
        "flag_summary": flag_summary(tables),
        "quintiles": "excluded; official QPB population unresolved",
        "uncertainty": "No original strata/PSUs; no design-correct intervals or significance",
    }


def schema():
    import pyarrow as pa

    strings = [
        "geo",
        "age_code",
        "age_label",
        "poverty_code",
        "poverty_label",
        "tenure_code",
        "tenure_label",
        "status",
        "suppression_reasons",
    ]
    integers = [
        "survey_year",
        "income_year",
        "sample_target_persons",
        "sample_valid_persons",
        "sample_target_households",
        "sample_valid_households",
        "known_imputed_income_target_persons",
        "known_imputed_allowance_target_persons",
    ]
    doubles = [
        "weighted_target_persons",
        "weighted_valid_persons",
        "weighted_missing_cost_loss_pct",
        "rate_pct",
    ]
    return pa.schema(
        [(s, pa.string()) for s in strings]
        + [(s, pa.int64()) for s in integers]
        + [(s, pa.float64()) for s in doubles]
    )


def canonical(rows):
    return sorted(
        rows, key=lambda r: (r["survey_year"], r["age_code"], r["poverty_code"], r["tenure_code"])
    )


def verify(rows, metadata):
    import json

    import duckdb
    import pyarrow.parquet as pq

    man = manifest.load()
    expected = {}
    for path in [PARQUET, DATABASE]:
        rel = str(path.relative_to(ROOT))
        if rel not in man.get("sha256", {}):
            raise ValueError(f"Unpinned ECV output: {rel}")
        expected[rel] = man["sha256"][rel]
    missing, changed = manifest.check(expected)
    if missing or changed:
        raise ValueError(f"ECV outputs missing={missing}, changed={changed}")
    stored = pq.read_table(PARQUET)
    if stored.schema != schema() or canonical(stored.to_pylist()) != canonical(rows):
        raise ValueError("ECV parquet stale vs exact derivation")
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        data = con.execute("SELECT * FROM joint_burden").to_arrow_table().to_pylist()
        metas = con.execute("SELECT value FROM metadata WHERE key='proof'").fetchall()
    if canonical(data) != canonical(rows):
        raise ValueError("ECV database stale vs exact derivation")
    if len(metas) != 1 or json.loads(metas[0][0]) != metadata:
        raise ValueError("ECV proof stale vs source/method/code")
    print(f"ECV joint: {len(rows)} exact cells and proof verified")


def save(rows, metadata):
    import json
    import tempfile
    from datetime import date

    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq

    if any(set(row) != set(schema().names) for row in rows):
        raise ValueError("Unexpected aggregate output fields")
    table = pa.Table.from_pylist(rows, schema=schema())
    with tempfile.TemporaryDirectory(prefix="ecv-joint-", dir=PROCESSED) as directory:
        directory = Path(directory)
        db = directory / "joint.duckdb"
        parquet = directory / "joint.parquet"
        pq.write_table(table, parquet)
        with duckdb.connect(str(db)) as con:
            con.register("input", table)
            con.execute("CREATE TABLE joint_burden AS SELECT * FROM input")
            con.execute("CREATE TABLE metadata(key VARCHAR,value VARCHAR)")
            con.execute(
                "INSERT INTO metadata VALUES ('proof', ?)",
                [json.dumps(metadata, sort_keys=True, allow_nan=False)],
            )
        PARQUET.parent.mkdir(parents=True, exist_ok=True)
        parquet.replace(PARQUET)
        db.replace(DATABASE)
    for path in [PARQUET, DATABASE]:
        manifest.record(
            str(path.relative_to(ROOT)),
            {
                "publisher": "Own descriptive estimates from INE ECV 2025",
                "accessed": date.today().isoformat(),
                "note": "Own poverty-age-tenure; project suppression; no design intervals",
            },
        )


def main():
    import argparse
    import shutil
    import tempfile
    import urllib.request
    from datetime import date

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adopt-archive", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.adopt_archive and (args.offline or args.check):
        parser.error("Archive adoption cannot bypass an offline/check pin")
    if args.adopt_archive or (not ARCHIVE.exists() and not (args.offline or args.check)):
        with tempfile.TemporaryDirectory(prefix="ecv-input-", dir=RAW) as directory:
            candidate = Path(directory) / "source.zip"
            if args.adopt_archive:
                if args.adopt_archive.stat().st_size > ecv.MAX_MEMBER:
                    raise ValueError("Oversized input archive")
                shutil.copyfile(args.adopt_archive, candidate)
            else:
                with urllib.request.urlopen(URL, timeout=120) as response:
                    contents = response.read(ecv.MAX_MEMBER + 1)
                if len(contents) > ecv.MAX_MEMBER:
                    raise ValueError("Oversized input archive")
                candidate.write_bytes(contents)
            tables = ecv.load_archive(candidate, YEAR)
            benchmark_gate(tables)  # Validate before replacing/pinning any input.
            if ARCHIVE.exists() and manifest.sha256(candidate) != manifest.sha256(ARCHIVE):
                raise ValueError(
                    "Existing release differs; use a separately reviewed source revision"
                )
            candidate.replace(ARCHIVE)
        manifest.record(
            str(ARCHIVE.relative_to(ROOT)),
            {
                "url": URL,
                "publisher": "INE ECV transversal, base 2013",
                "accessed": date.today().isoformat(),
                "note": "Anonymised release; only D/H/R and layouts read; no bundled code",
            },
        )
    inputs = pinned_inputs()
    tables = ecv.load_archive(ARCHIVE, YEAR)
    benchmark_gate(tables)
    rows, metadata = derive(tables), proof(inputs, tables)
    if args.check:
        verify(rows, metadata)
    else:
        save(rows, metadata)
        verify(rows, metadata)


if __name__ == "__main__":
    main()
