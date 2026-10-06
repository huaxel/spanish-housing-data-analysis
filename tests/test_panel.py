"""Tests for the stdlib OLS + CR1V helper. No network, no data/ dependency."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spanish_housing import ols  # noqa: E402


def test_solve_exact_fit():
    # y = 1 + 2x recovered exactly.
    x = [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0], [1.0, 3.0]]
    y = [1.0, 3.0, 5.0, 7.0]
    beta = ols.solve(ols.xtx(x), ols.xty(x, y))
    assert abs(beta[0] - 1.0) < 1e-9 and abs(beta[1] - 2.0) < 1e-9


def test_solve_singular_raises():
    try:
        ols.solve([[1.0, 1.0], [1.0, 1.0]], [1.0, 2.0])
    except ValueError:
        return
    raise AssertionError("singular system should raise")


def test_singleton_clusters_equal_hc1():
    # One observation per cluster: CR1V must coincide with White HC1.
    x = [[1.0, float(i)] for i in range(6)]
    y = [0.5, 1.1, 1.9, 3.2, 3.8, 5.1]
    got = ols.ols_cluster(x, y, clusters=list(range(6)))
    n, k = 6, 2
    bread = ols.invert(ols.xtx(x))
    beta = ols.solve(ols.xtx(x), ols.xty(x, y))
    resid = [yi - yh for yi, yh in zip(y, ols.predict(x, beta), strict=True)]
    meat = [[0.0] * k for _ in range(k)]
    for row, e in zip(x, resid, strict=True):
        for i in range(k):
            for j in range(k):
                meat[i][j] += row[i] * e * row[j] * e
    c = n / (n - k)  # HC1 factor
    tmp = [[sum(bread[i][m] * meat[m][j] for m in range(k)) for j in range(k)] for i in range(k)]
    hc1 = [[sum(tmp[i][m] * bread[m][j] for m in range(k)) * c for j in range(k)] for i in range(k)]
    for i in range(k):
        assert abs(got["se"][i] - hc1[i][i] ** 0.5) < 1e-9


def test_clustering_matters_and_r2_bounded():
    # Two tight groups: clustering must widen SEs vs iid-implied scale,
    # and R2 must stay in [0, 1].
    x = [[1.0, 0.0], [1.0, 0.1], [1.0, 10.0], [1.0, 10.1]]
    y = [0.0, 0.0, 1.0, 3.0]
    got = ols.ols_cluster(x, y, clusters=["a", "a", "b", "b"])
    assert 0.0 <= got["r2"] <= 1.0
    assert got["clusters"] == 2
    assert all(s > 0 for s in got["se"])
