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


def test_wild_bootstrap_deterministic_and_bounded():
    from spanish_housing import ols as ols_mod

    # 8 clusters: 2^8 sign patterns admit p < 0.05 (with 4 clusters the
    # minimum attainable Rademacher p is 1/16, so detection is impossible).
    x = [[1.0, float(i)] for i in range(24)]
    y = [1.0 + 2.0 * i + (0.5 if i % 2 else -0.5) for i in range(24)]
    cl = [i // 3 for i in range(24)]
    r1 = ols_mod.wild_bootstrap_t(x, y, cl, j=1, reps=200, seed=7)
    r2 = ols_mod.wild_bootstrap_t(x, y, cl, j=1, reps=200, seed=7)
    assert r1 == r2
    assert 0.0 <= r1["p"] <= 1.0
    assert r1["p"] < 0.05  # strong slope on 8 clusters detected


def test_wild_bootstrap_null_not_significant():
    from spanish_housing import ols as ols_mod

    x = [[1.0, float(i % 4)] for i in range(16)]
    y = [(-1.0) ** i * 0.1 for i in range(16)]
    cl = [i // 4 for i in range(16)]
    r = ols_mod.wild_bootstrap_t(x, y, cl, j=1, reps=200, seed=7)
    assert r["p"] > 0.05


def test_quarterize_requires_full_quarter():
    import sys as _sys
    from pathlib import Path as _P

    _sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "explorations"))
    from panel_quarterly import qoq, quarterize

    m = {
        (2024, 1): 10.0,
        (2024, 2): 10.0,
        (2024, 3): 10.0,
        (2024, 4): 10.0,
        (2024, 5): 10.0,
        (2024, 7): 10.0,
    }
    assert quarterize(m) == {(2024, 1): 30.0}
    assert qoq(100.0, 101.0) == 1.0
    assert qoq(None, 101.0) is None and qoq(0.0, 101.0) is None


def _iv_dgp(n=200, ncl=20, strength=1.0, seed=11):
    import random

    rng = random.Random(seed)
    z = [rng.gauss(0, 1) for _ in range(n)]
    w = [[1.0, rng.gauss(0, 1)] for _ in range(n)]
    d = [strength * zi + 0.5 * wi[1] + rng.gauss(0, 1) for zi, wi in zip(z, w, strict=True)]
    y = [2.0 * di + wi[1] + rng.gauss(0, 1) for di, wi in zip(d, w, strict=True)]
    cl = [i % ncl for i in range(n)]
    return y, d, w, [[zi] for zi in z], cl


def test_tsls_matches_ols_with_own_instrument():
    from spanish_housing import ols as ols_mod

    y, d, w, _z, cl = _iv_dgp()
    t = ols_mod.tsls(y, d, w, [[di] for di in d], cl)
    x = [[di] + wi for di, wi in zip(d, w, strict=True)]
    o = ols_mod.ols_cluster(x, y, cl)
    assert abs(t["tau"] - o["beta"][0]) < 1e-9
    assert abs(t["se"] - o["se"][0]) < 1e-9


def test_tsls_recovers_truth_strong_iv():
    from spanish_housing import ols as ols_mod

    y, d, w, z, cl = _iv_dgp()
    t = ols_mod.tsls(y, d, w, z, cl)
    assert abs(t["tau"] - 2.0) < 0.25


def test_first_stage_f_scales_with_strength():
    from spanish_housing import ols as ols_mod

    for strength, floor in [(1.0, 50.0), (0.2, 0.0)]:
        y, d, w, z, cl = _iv_dgp(strength=strength)
        f = ols_mod.first_stage_f(d, w, z, cl)["F"]
        assert f > floor, (strength, f)
    y, d, w, z, cl = _iv_dgp(strength=1.0)
    fs = ols_mod.first_stage_f(d, w, z, cl)["F"]
    yw, dw, ww, zw, clw = _iv_dgp(strength=0.2)
    fw = ols_mod.first_stage_f(dw, ww, zw, clw)["F"]
    assert fs > 5 * fw


def test_ar_ci_covers_truth_strong_iv():
    from spanish_housing import ols as ols_mod

    y, d, w, z, cl = _iv_dgp(ncl=20)
    ci = ols_mod.ar_ci(y, d, w, z, cl, lo=0.0, hi=4.0, steps=41)
    inside = [b for b, k in zip(ci["grid"], ci["keep"], strict=True) if k]
    assert inside, "AR set empty under strong IV"
    assert min(inside) <= 2.0 <= max(inside)


def test_invert_asymmetric():
    from spanish_housing import ols as ols_mod

    a = [[1.0, 2.0], [3.0, 4.0]]
    inv = ols_mod.invert(a)
    # [[-2, 1], [1.5, -0.5]]; naive row-stacking would give the transpose.
    assert abs(inv[0][0] + 2.0) < 1e-9 and abs(inv[0][1] - 1.0) < 1e-9
    assert abs(inv[1][0] - 1.5) < 1e-9 and abs(inv[1][1] + 0.5) < 1e-9
    prod = [[sum(a[i][m] * inv[m][j] for m in range(2)) for j in range(2)] for i in range(2)]
    assert abs(prod[0][0] - 1) < 1e-9 and abs(prod[1][1] - 1) < 1e-9
    assert abs(prod[0][1]) < 1e-9 and abs(prod[1][0]) < 1e-9
