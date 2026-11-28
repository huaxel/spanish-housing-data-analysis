"""The analysis pipeline's stage order must respect its artifact edges.

`scripts/run_analysis.py` runs the 45 estimators in four stages so that
independent ones run concurrently. That is only safe while every producer of
an artifact used downstream sits in an earlier stage. The edges are declared
there as `DEPENDENCIES`; this module proves the stage list honours them, and
that no *undeclared* pair of scripts touches the same artifact — a new
estimator reading another's output would otherwise race on a parallel run.

Artifacts are found by the paths a script mentions, so a coupling expressed
through a path constant is caught too (that is how `invert_tourist` reads the
tourist panel).
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_analysis  # noqa: E402

ARTIFACT = re.compile(r"(?:artifacts|explorations)/[\w.]+\.json")
# Path constants spell the same thing as `ROOT / "artifacts" / "name.json"`.
JOINED = re.compile(r'"(artifacts|explorations)"\s*/\s*"([\w.]+\.json)"')


def _mentions(script: str) -> set[str]:
    src = (ROOT / script).read_text(encoding="utf-8")
    return set(ARTIFACT.findall(src)) | {f"{folder}/{name}" for folder, name in JOINED.findall(src)}


def _stage_of() -> dict[str, int]:
    return {script: index for index, stage in enumerate(run_analysis.STAGES) for script in stage}


def test_every_listed_script_exists_and_appears_once():
    scripts = [script for stage in run_analysis.STAGES for script in stage]
    assert len(scripts) == len(set(scripts))
    missing = [script for script in scripts if not (ROOT / script).exists()]
    assert not missing


def test_the_ledger_runs_last_and_alone():
    assert run_analysis.STAGES[-1] == run_analysis.LEDGER
    assert len(run_analysis.LEDGER) == 1


def test_each_declared_edge_is_real_and_ordered():
    stage = _stage_of()
    for artifact, producer, consumers in run_analysis.DEPENDENCIES:
        assert artifact in _mentions(producer), f"{producer} does not mention {artifact}"
        for consumer in consumers:
            assert artifact in _mentions(consumer), f"{consumer} does not mention {artifact}"
            assert stage[producer] < stage[consumer], (
                f"{consumer} reads {artifact} but runs in stage {stage[consumer]}, "
                f"not after its producer {producer} (stage {stage[producer]})"
            )


def test_no_undeclared_pair_of_scripts_touches_the_same_artifact():
    declared = {
        (artifact, script)
        for artifact, producer, consumers in run_analysis.DEPENDENCIES
        for script in [producer, *consumers]
    }
    by_artifact: dict[str, set[str]] = {}
    for script in _stage_of():
        for artifact in _mentions(script):
            by_artifact.setdefault(artifact, set()).add(script)

    undeclared = {
        artifact: sorted(scripts)
        for artifact, scripts in by_artifact.items()
        if len(scripts) > 1 and any((artifact, script) not in declared for script in scripts)
    }
    assert not undeclared, (
        f"scripts touch the same artifact without a declared dependency: {undeclared}; "
        "add the edge to DEPENDENCIES in scripts/run_analysis.py"
    )


def test_the_instrument_is_a_stage_of_its_own_first():
    assert run_analysis.STAGES[0] == run_analysis.INSTRUMENT
    assert run_analysis.INSTRUMENT == ["explorations/bartik_predict.py"]
