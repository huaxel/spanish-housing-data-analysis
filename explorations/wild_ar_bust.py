"""Wild-bootstrap-calibrated AR set for the bust-spec IV (one-off calibration).

Answers whether the bust-era tau (+0.46) survives AR inference once the
critical value is bootstrapped instead of the F<10 placeholder (covers
zero) or the optimistic F(1,G-1) approximation (excludes zero).
Writes artifacts/wild_ar_bust.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import importlib.util

from spanish_housing import ols  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "ivmod", str(Path(__file__).resolve().parent / "iv_migration.py")
)
ivmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ivmod)  # deterministic re-run; refreshes committed outputs

from spanish_housing.data_paths import ROOT  # noqa: E402

y, d, w, z, cl, rows = ivmod.build(None, 2002, 2013)
out = ols.wild_ar_ci(y, d, w, z, cl, lo=-2.0, hi=5.0, steps=29, reps=299, seed=20261007)
out["spec"] = "bust_2002_2013"
out["_meta"] = ols.model_meta(
    __file__, ["data/processed/marts.duckdb", "artifacts/bartik_predicted.json"]
)
(ROOT / "artifacts" / "wild_ar_bust.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps({k: out[k] for k in ("spec", "set", "reps", "seed")}, indent=1))
