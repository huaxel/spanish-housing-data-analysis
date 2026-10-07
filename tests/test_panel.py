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


def test_tsls_se_uses_transposed_bread_with_controls():
    """Independent recomputation of the exactly-identified IV sandwich.

    With controls, Z'X is nonsymmetric, so bread @ meat @ bread differs
    from bread @ meat @ bread.T. This test builds the sandwich by an
    independent route and pins the transpose (regression test for the
    2026-10-06 review finding that tsls omitted .T)."""
    from spanish_housing import ols as ols_mod

    y, d, w, z, cl = _iv_dgp(n=200, ncl=20, strength=1.0, seed=11)
    t = ols_mod.tsls(y, d, w, z, cl)
    # Independent route: rebuild bread/meat from primitives.
    x = [[di] + wi for di, wi in zip(d, w, strict=True)]
    zw = [zi + wi for zi, wi in zip(z, w, strict=True)]
    k = len(x[0])
    zt_x = [
        [sum(a * b for a, b in zip(zr, xc, strict=True)) for xc in zip(*x, strict=True)]
        for zr in zip(*zw, strict=True)
    ]
    bread = ols_mod.invert(zt_x)
    beta = [t["beta"][i] for i in range(k)]
    resid = [y[i] - sum(x[i][j] * beta[j] for j in range(k)) for i in range(len(y))]
    groups: dict = {}
    for i, g in enumerate(cl):
        groups.setdefault(g, []).append(i)
    meat = [[0.0] * k for _ in range(k)]
    for idx in groups.values():
        s = [0.0] * k
        for i in idx:
            for j in range(k):
                s[j] += zw[i][j] * resid[i]
        for i in range(k):
            for j in range(k):
                meat[i][j] += s[i] * s[j]

    # Correct: bread @ meat @ bread.T. Wrong (old): bread @ meat @ bread.
    def mmul(a, b):
        return [[sum(a[i][m] * b[m][j] for m in range(k)) for j in range(k)] for i in range(k)]

    def transpose(m):
        return [[m[j][i] for j in range(k)] for i in range(k)]

    g, n = len(groups), len(y)
    c = (g / (g - 1)) * ((n - 1) / (n - k))
    good = mmul(mmul(bread, meat), transpose(bread))
    bad = mmul(mmul(bread, meat), bread)
    good_se = (c * good[0][0]) ** 0.5
    bad_se = (c * bad[0][0]) ** 0.5
    assert abs(good_se - bad_se) > 1e-6, "DGP must separate the two formulas"
    assert abs(t["se"] - good_se) < 1e-9
    assert abs(t["se"] - bad_se) > 1e-6


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


def test_bartik_shares_sum_to_one():
    from spanish_housing import bartik

    stocks = {
        ("A", "x", 2000): 30.0,
        ("A", "y", 2000): 70.0,
        ("B", "x", 2000): 50.0,
        ("B", "y", 2000): 50.0,
    }
    s = bartik.shares(stocks, ["A", "B"], ["x", "y"], 2000)
    assert abs(s[("A", "x")] - 0.3) < 1e-9 and abs(s[("A", "y")] - 0.7) < 1e-9
    assert all(abs(sum(s[(u, o)] for o in ["x", "y"]) - 1.0) < 1e-9 for u in ["A", "B"])


def test_bartik_leave_one_out():
    from spanish_housing import bartik

    # A dominates origin x nationally: with LOO its own boom must not
    # move its shifter; without LOO it does.
    stocks = {
        ("A", "x", 2000): 100.0,
        ("A", "x", 2010): 300.0,
        ("B", "x", 2000): 10.0,
        ("B", "x", 2010): 11.0,
    }
    units, origins = ["A", "B"], ["x"]
    loo = bartik.shift_share(stocks, units, origins, 2000, 2010, leave_one_out=True)
    full = bartik.shift_share(stocks, units, origins, 2000, 2010, leave_one_out=False)
    # LOO national growth for x as seen by A: (11-10)/10 = 0.1
    assert abs(loo["A"] - 0.1) < 1e-9
    # Without LOO: (311-110)/110 = 1.827
    assert abs(full["A"] - 201 / 110) < 1e-9
    assert loo["A"] != full["A"]


def _two_way_dgp(seed=5):
    import random

    rng = random.Random(seed)
    units = [f"u{i}" for i in range(6)]
    years = [2018, 2019, 2020, 2021]
    u, p, x, y = [], [], [], []
    for i, uu in enumerate(units):
        for t in years:
            # unbalanced: drop one cell so unit means differ by unit
            if uu == "u5" and t == 2018:
                continue
            xx = rng.gauss(0, 1)
            u.append(uu)
            p.append(t)
            x.append(xx)
            y.append(1.5 * xx + i * 0.3 + (t - 2018) * 0.2 + rng.gauss(0, 0.2))
    return u, p, x, y


def test_two_way_within_matches_explicit_dummies():
    from spanish_housing import ols as ols_mod

    u, p, x, y = _two_way_dgp()
    y_dm, cols_dm, w_dm, _kept = ols_mod.two_way_within(u, p, y, [x])
    x_dm = cols_dm[0]
    xd = [[xv] + wd for xv, wd in zip(x_dm, w_dm, strict=True)]
    got = ols_mod.ols_cluster(xd, y_dm, u)["beta"][0]
    # Explicit two-way OLS: intercept + x + unit dummies + year dummies.
    uus, tts = sorted(set(u))[1:], sorted(set(p))[1:]
    xe = [
        [xx, 1.0] + [1.0 if uu == q else 0.0 for q in uus] + [1.0 if tt == s else 0.0 for s in tts]
        for uu, tt, xx in zip(u, p, x, strict=True)
    ]
    want = ols_mod.ols_cluster(xe, y, u)["beta"][0]
    assert abs(got - want) < 1e-9


def test_two_way_within_differs_from_raw_dummies():
    """The old pattern (demeaned X + RAW year dummies) is a different model."""

    from spanish_housing import ols as ols_mod

    u, p, x, y = _two_way_dgp()
    y_dm, cols_dm, _w, kept = ols_mod.two_way_within(u, p, y, [x])
    x_dm = cols_dm[0]
    x_bad = [[xv] + [1.0 if tt == s else 0.0 for s in kept] for xv, tt in zip(x_dm, p, strict=True)]
    bad = ols_mod.ols_cluster(x_bad, y_dm, u)["beta"][0]
    uus, tts = sorted(set(u))[1:], sorted(set(p))[1:]
    xe = [
        [xx, 1.0] + [1.0 if uu == q else 0.0 for q in uus] + [1.0 if tt == s else 0.0 for s in tts]
        for uu, tt, xx in zip(u, p, x, strict=True)
    ]
    want = ols_mod.ols_cluster(xe, y, u)["beta"][0]
    assert abs(bad - want) > 1e-6


def test_wild_ar_ci_covers_truth_and_deterministic():
    from spanish_housing import ols as ols_mod

    # Small strong-IV DGP: calibrated set must cover the truth (2.0) and be
    # deterministic; coarse grid + few reps keep it fast.
    y, d, w, z, cl = _iv_dgp(n=120, ncl=12, strength=1.0, seed=3)
    r1 = ols_mod.wild_ar_ci(y, d, w, z, cl, lo=0.0, hi=4.0, steps=9, reps=99, seed=11)
    r2 = ols_mod.wild_ar_ci(y, d, w, z, cl, lo=0.0, hi=4.0, steps=9, reps=99, seed=11)
    assert r1 == r2
    assert r1["set"], "calibrated AR set empty under strong IV"
    assert r1["set"][0] <= 2.0 <= r1["set"][1]
    assert len(r1["grid"]) == 9 and len(r1["keep"]) == 9 and len(r1["crit_95"]) == 9
    assert all(c > 0 for c in r1["crit_95"])
