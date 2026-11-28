"""Run the deterministic analysis pipeline, parallelising independent scripts.

`make analysis` used to run its 45 estimators serially — measured at ~6 min
on a 32-core machine, dominated by wild_ar_bust (~2.5 min) and iv_migration
(~2 min); staging them takes ~3 min. Almost every estimator reads the marts
and writes its own artifact, so they are independent; only a handful of
artifact edges force an order, and those edges are the stage boundaries
below:

  bartik_predict            -> iv_migration, panel_saiz, wild_ar_bust
  panel_saiz_madrid         -> panel_saiz_madrid_vacancy
  panel_tourist             -> invert_tourist, export_inference
  invert_tourist            -> export_inference (via tourist_inversion.json)
  deficit_vivienda          -> export_deficit
  catalonia_rent_control, panel_tourist, tourist_rents -> build_claim_ledger

`scripts/build_claim_ledger.py` stays alone in the last stage: it hashes both
marts plus those three artifacts, so it must see every producer.

Every script is still a separate process that writes bytes-identical output to
a serial run — the pipeline is deterministic, so parallel execution changes
wall clock only, not results. Verify that with `--serial` on a clean tree if a
new estimator looks order-sensitive.

Usage: python scripts/run_analysis.py [--serial] [--jobs N]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Stage 0: the instrument every IV/WILD script reads.
INSTRUMENT = ["explorations/bartik_predict.py"]

# Stage 1: everything that reads the marts and writes only its own outputs.
INDEPENDENT = [
    "explorations/iv_migration.py",
    "explorations/panel_saiz.py",
    "explorations/panel_provincial.py",
    "explorations/panel_adjusted.py",
    "explorations/panel_tourist.py",
    "explorations/panel_quarterly.py",
    "explorations/ratio_ccaa.py",
    "explorations/serpavi_analysis.py",
    "explorations/tourist_rents.py",
    "explorations/panel_saiz_municipal.py",
    "explorations/panel_saiz_madrid.py",
    "explorations/wild_ar_bust.py",
    "explorations/test_absorption_hypothesis.py",
    "explorations/municipios_nacional.py",
    "explorations/barrios_bcn_yield.py",
    "explorations/desahucios_renta.py",
    "scripts/analyze_stock_rent.py",
    "explorations/cadastre_eras.py",
    "explorations/cadastre_age_rent.py",
    "explorations/cadastre_era_rehab.py",
    "explorations/cadastre_era_quality.py",
    "explorations/cadastre_era_surface.py",
    "explorations/cadastre_vacancy_alignment.py",
    "explorations/cadastre_household_alignment.py",
    "explorations/cadastre_capitals.py",
    "explorations/cadastre_province.py",
    "explorations/cadastre_malaga_barrios.py",
    "explorations/cadastre_granada_distritos.py",
    "explorations/censo_vintage.py",
    "explorations/deficit_vivienda.py",
    "explorations/catalonia_rent_control.py",
    "scripts/build_ecv_microsim.py",
    "scripts/build_irav_index.py",
    "explorations/ipva_rent_index.py",
    "explorations/proh_households.py",
    "explorations/ecp_households.py",
    "explorations/occupancy_catalonia.py",
    "explorations/vut_stock.py",
    "explorations/vut_rent_overlap.py",
]

# Stage 2: consumers of stage-1 artifacts.
DEPENDENT = [
    "explorations/panel_saiz_madrid_vacancy.py",
    "scripts/export_deficit.py",
    "scripts/invert_tourist.py",
]

# Stage 3: export_inference reads the inversion that invert_tourist writes, so
# it cannot share stage 2 with it.
DERIVED = ["scripts/export_inference.py"]

# Stage 4: hashes the producers above.
LEDGER = ["scripts/build_claim_ledger.py"]

# The artifact edges behind the staging, as data so tests/test_run_analysis.py
# can prove the stage order (a consumer must run after its producer) and so an
# undeclared coupling between two scripts fails instead of racing.
DEPENDENCIES: list[tuple[str, str, list[str]]] = [
    (
        "artifacts/bartik_predicted.json",
        "explorations/bartik_predict.py",
        [
            "explorations/iv_migration.py",
            "explorations/panel_saiz.py",
            "explorations/wild_ar_bust.py",
        ],
    ),
    (
        "explorations/saiz_municipal_mad.json",
        "explorations/panel_saiz_madrid.py",
        ["explorations/panel_saiz_madrid_vacancy.py"],
    ),
    (
        "artifacts/panel_tourist.json",
        "explorations/panel_tourist.py",
        [
            "scripts/invert_tourist.py",
            "scripts/export_inference.py",
            "scripts/build_claim_ledger.py",
        ],
    ),
    (
        "artifacts/tourist_inversion.json",
        "scripts/invert_tourist.py",
        ["scripts/export_inference.py"],
    ),
    (
        "artifacts/tourist_rents.json",
        "explorations/tourist_rents.py",
        ["scripts/build_claim_ledger.py"],
    ),
    (
        "artifacts/catalonia_rent_control.json",
        "explorations/catalonia_rent_control.py",
        ["scripts/build_claim_ledger.py"],
    ),
    (
        "artifacts/deficit_vivienda.json",
        "explorations/deficit_vivienda.py",
        ["scripts/export_deficit.py"],
    ),
]

STAGES = [INSTRUMENT, INDEPENDENT, DEPENDENT, DERIVED, LEDGER]

# 8 lanes keeps the 39 independent estimators inside a modest RAM budget
# (each opens the marts read-only) while pointing the floor at wild_ar_bust.
DEFAULT_JOBS = 8


def _short(script: str) -> str:
    return Path(script).stem


def _stream(script: str) -> tuple[int, float]:
    """Run one estimator, streaming its output prefixed with its name."""
    started = time.monotonic()
    proc = subprocess.Popen(
        [sys.executable, script],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(f"  [{_short(script)}] {line.rstrip()}", flush=True)
    code = proc.wait()
    return code, time.monotonic() - started


def _run_stage(stage: list[str], jobs: int, width: int, counter: list[int]) -> list[str]:
    """Run one stage. Returns the scripts that failed (empty list on success)."""
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(jobs, len(stage)))) as pool:
        futures = {}
        for script in stage:
            counter[0] += 1
            print(f"[analysis {counter[0]}/{width}] {_short(script)} — start", flush=True)
            futures[pool.submit(_stream, script)] = script
        for future in as_completed(futures):
            script = futures[future]
            try:
                code, seconds = future.result()
            except Exception as exc:  # a crashed child must not hide the stage
                print(f"[analysis] {_short(script)} — runner error: {exc}", flush=True)
                failed.append(script)
                continue
            state = "done" if code == 0 else f"FAILED (exit {code})"
            print(f"[analysis] {_short(script)} — {state} in {seconds:.1f}s", flush=True)
            if code != 0:
                failed.append(script)
    return failed


def _run_serial(stages: list[list[str]], width: int) -> list[str]:
    failed: list[str] = []
    counter = [0]
    for stage in stages:
        for script in stage:
            counter[0] += 1
            print(f"[analysis {counter[0]}/{width}] {_short(script)}", flush=True)
            code, seconds = _stream(script)
            print(f"[analysis] {_short(script)} — done in {seconds:.1f}s", flush=True)
            if code != 0:
                failed.append(script)
                return failed
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--serial", action="store_true", help="run every stage serially")
    parser.add_argument(
        "--jobs",
        type=int,
        default=int(os.environ.get("ANALYSIS_JOBS", DEFAULT_JOBS)),
        help=f"concurrent estimators per stage (default {DEFAULT_JOBS})",
    )
    args = parser.parse_args(argv)

    width = sum(len(stage) for stage in STAGES)
    missing = [s for stage in STAGES for s in stage if not (ROOT / s).exists()]
    if missing:
        print(f"analysis: missing scripts: {missing}", file=sys.stderr)
        return 2

    started = time.monotonic()
    if args.serial:
        failed = _run_serial(STAGES, width)
    else:
        failed = []
        counter = [0]
        for stage in STAGES:
            failed = _run_stage(stage, args.jobs, width, counter)
            if failed:
                break
    elapsed = time.monotonic() - started

    if failed:
        print(
            f"analysis: {len(failed)} script(s) failed after {elapsed / 60:.1f} min: "
            + ", ".join(_short(s) for s in failed),
            file=sys.stderr,
        )
        return 1
    print(f"analysis: {width} scripts in {elapsed / 60:.1f} min", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
