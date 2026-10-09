"""Wild-bootstrap inversion grid: equivalence, common numbers, fixtures."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spanish_housing import (
    ols,  # noqa: E402
    wild_grid,  # noqa: E402
)


def fixture_panel():
    """Clustered panel: 24 units x 4 periods, one regressor + unit/year FE."""
    rng = random.Random(7)
    units, periods, y, z = [], [], [], []
    for u in range(24):
        for p in range(4):
            units.append(f"u{u}")
            periods.append(2000 + p)
            z.append(rng.uniform(0, 1))
            y.append(2.0 + 0.7 * z[-1] + (u - 3) * 0.05 + rng.uniform(-0.2, 0.2))
    ydm, cols_dm, w, _kept = ols.two_way_within(units, periods, y, [z])
    x = [[c[i] for c in cols_dm] + w[i] for i in range(len(y))]
    return x, ydm, units


def test_grid_c_zero_matches_legacy_zero_null_exactly():
    x, y, cl = fixture_panel()
    legacy = ols.wild_bootstrap_t(x, y, cl, j=0, reps=199, seed=99)
    grid = wild_grid.wild_bootstrap_t_grid(x, y, cl, j=0, grid=[-1.0, 0.0, 1.0], reps=199, seed=99)
    assert grid["p"][1] == legacy["p"]
    assert grid["keep"][1] == (legacy["p"] >= 0.05)


def test_common_random_numbers_candidate_order_invariance():
    x, y, cl = fixture_panel()
    a = wild_grid.wild_bootstrap_t_grid(x, y, cl, j=0, grid=[0.0, 1.0], reps=199, seed=5)
    b = wild_grid.wild_bootstrap_t_grid(x, y, cl, j=0, grid=[1.0, 0.0], reps=199, seed=5)
    assert a["p"][0] == b["p"][1] and a["p"][1] == b["p"][0]
    assert a["keep"] == b["keep"][::-1]
    assert a["warnings"] == b["warnings"]


def test_fit_point_is_accepted_and_far_values_rejected_on_direct_fit():
    x, y, cl = fixture_panel()
    fit = ols.ols_cluster(x, y, cl)
    b = fit["beta"][0]
    grid = [b - 4 * fit["se"][0], b, b + 4 * fit["se"][0]]
    result = wild_grid.wild_bootstrap_t_grid(x, y, cl, j=0, grid=grid, reps=199, seed=11)
    assert result["p"][1] == 1.0  # t_obs is ~0 at the fitted value
    assert result["keep"][1] is True
    assert result["keep"][0] is False and result["keep"][2] is False


def test_p_is_monotone_away_from_the_fit():
    x, y, cl = fixture_panel()
    fit = ols.ols_cluster(x, y, cl)
    b = fit["beta"][0]
    grid = [
        b - 3 * fit["se"][0],
        b - 2 * fit["se"][0],
        b - fit["se"][0],
        b,
        b + fit["se"][0],
        b + 2 * fit["se"][0],
        b + 3 * fit["se"][0],
    ]
    p = wild_grid.wild_bootstrap_t_grid(x, y, cl, j=0, grid=grid, reps=199, seed=13)["p"]
    assert p[3] == 1.0
    assert p[0] < p[1] < p[2] < p[3] and p[3] > p[4] > p[5] > p[6]


def test_boundary_and_resolution_warnings():
    x, y, cl = fixture_panel()
    fit = ols.ols_cluster(x, y, cl)
    b = fit["beta"][0]
    one_side = wild_grid.wild_bootstrap_t_grid(
        x, y, cl, j=0, grid=[b - 1.5 * fit["se"][0], b - 0.5 * fit["se"][0]], reps=199, seed=17
    )
    assert one_side["keep"][0] is True
    assert "accepted_set_may_extend_below_grid" in one_side["warnings"]
    far = wild_grid.wild_bootstrap_t_grid(
        x, y, cl, j=0, grid=[b + 6 * fit["se"][0], b + 7 * fit["se"][0]], reps=199, seed=19
    )
    assert "no_candidate_accepted_at_this_resolution" in far["warnings"]
    # With finite reps the (count+1)/(reps+1) floor keeps p strictly positive.
    assert all(0 < p <= 1 for p in far["p"])
    # A normal centered grid yields a contiguous interval with no warnings.
    clean = wild_grid.wild_bootstrap_t_grid(
        x, y, cl, j=0, grid=[b - 4 * fit["se"][0], b, b + 4 * fit["se"][0]], reps=199, seed=31
    )
    assert clean["keep"] == [False, True, False]
    assert clean["warnings"] == []
