"""Minimal OLS + cluster-robust (CR1V) covariance in pure stdlib.

Small-panel helper for the adjusted-description explorer: no numpy/pandas
in this repo by design, and k stays tiny (year dummies + a few regressors
after within-CCAA demeaning), so Gauss-Jordan is plenty.
"""

from __future__ import annotations


def _copy(m: list[list[float]]) -> list[list[float]]:
    return [row[:] for row in m]


def solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve Ax = b by Gauss-Jordan with partial pivoting. Raises on singular."""
    n = len(a)
    m = [a[i][:] + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            raise ValueError("singular design matrix")
        m[col], m[piv] = m[piv], m[col]
        piv_val = m[col][col]
        m[col] = [v / piv_val for v in m[col]]
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                factor = m[r][col]
                m[r] = [rv - factor * cv for rv, cv in zip(m[r], m[col], strict=True)]
    return [m[i][n] for i in range(n)]


def invert(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    cols = [solve(_copy(a), [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    # solve() returns columns of the inverse; transpose into rows.
    return [list(row) for row in zip(*cols, strict=True)]


def xtx(x: list[list[float]]) -> list[list[float]]:
    k = len(x[0])
    out = [[0.0] * k for _ in range(k)]
    for row in x:
        for i in range(k):
            for j in range(i, k):
                out[i][j] += row[i] * row[j]
    for i in range(k):
        for j in range(i):
            out[i][j] = out[j][i]
    return out


def wild_bootstrap_t(
    x: list[list[float]],
    y: list[float],
    clusters: list[str | int],
    j: int,
    reps: int = 4999,
    seed: int = 20261006,
) -> dict:
    """Wild cluster bootstrap-t (Rademacher, null-imposed) for beta[j].

    Restricted fit drops column j; bootstrap DGP is y* = X0 b0 + v_g e0 with
    Rademacher v_g per cluster; each replicate refits the full model and
    records t*_j = b*_j / se*_j (CR1V). Returns the observed t, the
    bootstrap two-sided p-value, and the 2.5/97.5 percentiles of t*.
    Deterministic for a fixed seed."""
    import random

    rng = random.Random(seed)
    k = len(x[0])
    keep = [c for c in range(k) if c != j]
    x0 = [[row[c] for c in keep] for row in x]
    fit0 = ols_cluster(x0, y, clusters)
    b0 = fit0["beta"]
    fitted0 = predict(x0, b0)
    e0 = [yi - fh for yi, fh in zip(y, fitted0, strict=True)]
    groups: dict[str | int, list[int]] = {}
    for i, g in enumerate(clusters):
        groups.setdefault(g, []).append(i)
    keys = list(groups)
    full = ols_cluster(x, y, clusters)
    t_obs = full["beta"][j] / full["se"][j] if full["se"][j] > 0 else 0.0
    t_stars = []
    for _ in range(reps):
        v = {g: 1.0 if rng.random() < 0.5 else -1.0 for g in keys}
        y_star = [fitted0[i] + v[clusters[i]] * e0[i] for i in range(len(y))]
        fb = ols_cluster(x, y_star, clusters)
        t_stars.append(fb["beta"][j] / fb["se"][j] if fb["se"][j] > 0 else 0.0)
    t_stars.sort()
    p = sum(1 for t in t_stars if abs(t) >= abs(t_obs)) / reps

    def q(p_: float) -> float:
        return t_stars[min(reps - 1, int(p_ * reps))]

    return {
        "t_obs": round(t_obs, 3),
        "p": round(p, 4),
        "t_star_ci95": [round(q(0.025), 3), round(q(0.975), 3)],
        "reps": reps,
        "seed": seed,
    }


def predict(x: list[list[float]], beta: list[float]) -> list[float]:
    return [sum(b * xij for b, xij in zip(beta, row, strict=True)) for row in x]


def xty(x: list[list[float]], y: list[float]) -> list[float]:
    k = len(x[0])
    out = [0.0] * k
    for row, yi in zip(x, y, strict=True):
        for i in range(k):
            out[i] += row[i] * yi
    return out


def ols_cluster(x: list[list[float]], y: list[float], clusters: list[str | int]) -> dict:
    """OLS with CR1V cluster-robust covariance.

    V = c * bread @ meat @ bread, meat = sum_g s_g s_g' with scores
    s_g = X_g' e_g, c = G/(G-1) * (N-1)/(N-k). With one observation per
    cluster this coincides exactly with White HC1.
    """
    n, k = len(x), len(x[0])
    bread = invert(xtx(x))
    beta = solve(xtx(x), xty(x, y))
    resid = [yi - yh for yi, yh in zip(y, predict(x, beta), strict=True)]
    groups: dict[str | int, list[int]] = {}
    for i, g in enumerate(clusters):
        groups.setdefault(g, []).append(i)
    g = len(groups)
    meat = [[0.0] * k for _ in range(k)]
    for idx in groups.values():
        s = [0.0] * k
        for i in idx:
            for j in range(k):
                s[j] += x[i][j] * resid[i]
        for i in range(k):
            for j in range(k):
                meat[i][j] += s[i] * s[j]
    tmp = [[sum(bread[i][m] * meat[m][j] for m in range(k)) for j in range(k)] for i in range(k)]
    cov = [[sum(tmp[i][m] * bread[m][j] for m in range(k)) for j in range(k)] for i in range(k)]
    c = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    cov = [[v * c for v in row] for row in cov]
    ybar = sum(y) / n
    sst = sum((yi - ybar) ** 2 for yi in y)
    r2 = 1 - sum(e * e for e in resid) / sst if sst else 0.0
    return {
        "beta": beta,
        "se": [(cov[i][i] if cov[i][i] > 0 else 0.0) ** 0.5 for i in range(k)],
        "n": n,
        "k": k,
        "clusters": g,
        "r2": r2,
    }


def _mat_vec(m: list[list[float]], v: list[float]) -> list[float]:
    return [sum(row[j] * v[j] for j in range(len(v))) for row in m]


def _project(x: list[list[float]], y: list[float]) -> list[float]:
    """OLS fitted values of y on X (no SEs)."""
    return predict(x, solve(xtx(x), xty(x, y)))


def tsls(
    y: list[float],
    d: list[float],
    w: list[list[float]],
    z: list[list[float]],
    clusters: list[str | int],
) -> dict:
    """2SLS for y = D*tau + W*gamma with excluded instruments Z.

    Single endogenous regressor; W holds exogenous controls (include a
    constant / FE dummies explicitly). Cluster-robust (CR1V) SEs from 2SLS
    residuals with bread = inv(X'Pz X). With Z == [D] this reduces to OLS.
    """
    n = len(y)
    zw = [zi + wi for zi, wi in zip(z, w, strict=True)]
    x = [[di] + wi for di, wi in zip(d, w, strict=True)]
    zt_x = [
        [sum(a * b for a, b in zip(zr, xc, strict=True)) for xc in zip(*x, strict=True)]
        for zr in zip(*zw, strict=True)
    ]
    zt_y = [sum(a * b for a, b in zip(zr, y, strict=True)) for zr in zip(*zw, strict=True)]
    bread = invert(zt_x)
    beta = _mat_vec(bread, zt_y)
    resid = [yi - yh for yi, yh in zip(y, predict(x, beta), strict=True)]
    k = len(x[0])
    groups: dict[str | int, list[int]] = {}
    for i, g in enumerate(clusters):
        groups.setdefault(g, []).append(i)
    g = len(groups)
    meat = [[0.0] * k for _ in range(k)]
    for idx in groups.values():
        s = [0.0] * k
        for i in idx:
            for j in range(k):
                s[j] += zw[i][j] * resid[i]
        for i in range(k):
            for j in range(k):
                meat[i][j] += s[i] * s[j]
    tmp = [[sum(bread[i][m] * meat[m][j] for m in range(k)) for j in range(k)] for i in range(k)]
    cov = [[sum(tmp[i][m] * bread[m][j] for m in range(k)) for j in range(k)] for i in range(k)]
    c = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    cov = [[v * c for v in row] for row in cov]
    return {
        "tau": beta[0],
        "se": (cov[0][0] if cov[0][0] > 0 else 0.0) ** 0.5,
        "beta": beta,
        "n": n,
        "k": k,
        "clusters": g,
    }


def first_stage_f(
    d: list[float],
    w: list[list[float]],
    z: list[list[float]],
    clusters: list[str | int],
) -> dict:
    """Cluster-robust Wald F on the excluded instruments in D ~ Z + W."""
    zw = [zi + wi for zi, wi in zip(z, w, strict=True)]
    fit = ols_cluster(zw, d, clusters)
    kz = len(z[0])
    bread = invert(xtx(zw))
    n, k = fit["n"], fit["k"]
    resid = [di - yh for di, yh in zip(d, predict(zw, fit["beta"]), strict=True)]
    groups: dict[str | int, list[int]] = {}
    for i, g in enumerate(clusters):
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
    g = len(groups)
    c = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    # Full sandwich first, then the top-left kz block (block-wise products
    # would drop the cross terms).
    tmp = [[sum(bread[i][m] * meat[m][j] for m in range(k)) for j in range(k)] for i in range(k)]
    vfull = [
        [sum(tmp[i][m] * bread[m][j] for m in range(k)) * c for j in range(k)] for i in range(k)
    ]
    vz = [[vfull[i][j] for j in range(kz)] for i in range(kz)]
    delta = fit["beta"][:kz]
    try:
        wald = _mat_vec(invert(vz), delta)
        f = sum(di * wi for di, wi in zip(delta, wald, strict=True)) / kz
    except ValueError:
        f = 0.0
    return {"F": round(f, 2), "kz": kz, "clusters": g, "n": n}


def _wald_sub(y: list[float], x: list[list[float]], clusters: list[str | int], k_sel: int) -> float:
    """Cluster-robust (CR1V) Wald F for H0: first k_sel coefficients are 0."""
    n, k = len(x), len(x[0])
    bread = invert(xtx(x))
    beta = solve(xtx(x), xty(x, y))
    resid = [yi - yh for yi, yh in zip(y, predict(x, beta), strict=True)]
    groups: dict[str | int, list[int]] = {}
    for i, g in enumerate(clusters):
        groups.setdefault(g, []).append(i)
    g = len(groups)
    meat = [[0.0] * k for _ in range(k)]
    for idx in groups.values():
        s = [0.0] * k
        for i in idx:
            for j in range(k):
                s[j] += x[i][j] * resid[i]
        for i in range(k):
            for j in range(k):
                meat[i][j] += s[i] * s[j]
    c = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    tmp = [[sum(bread[i][m] * meat[m][j] for m in range(k)) for j in range(k)] for i in range(k)]
    vfull = [
        [sum(tmp[i][m] * bread[m][j] for m in range(k)) * c for j in range(k)] for i in range(k)
    ]
    vz = [[vfull[i][j] for j in range(k_sel)] for i in range(k_sel)]
    delta = beta[:k_sel]
    try:
        wald = _mat_vec(invert(vz), delta)
        return sum(di * wi for di, wi in zip(delta, wald, strict=True)) / k_sel
    except ValueError:
        return 0.0


def ar_ci(
    y: list[float],
    d: list[float],
    w: list[list[float]],
    z: list[list[float]],
    clusters: list[str | int],
    lo: float,
    hi: float,
    steps: int = 101,
    f_crit: float = 10.0,
) -> dict:
    """Anderson-Rubin confidence set for tau (single endogenous regressor).

    Inverts the cluster-robust Wald test of excluded instruments in
    e(b0) = y - D*b0 on [Z, W]: keeps b0 with F < f_crit. Default critical
    value is a placeholder — calibrate by wild bootstrap for the real
    application (F( kz, G-1 ) quantiles are optimistic with few clusters).
    Returns the grid and the acceptance mask (possibly disjoint/empty).
    """
    kz = len(z[0])
    grid, keep = [], []
    for s in range(steps):
        b0 = lo + (hi - lo) * s / (steps - 1) if steps > 1 else lo
        e = [yi - di * b0 for yi, di in zip(y, d, strict=True)]
        x = [zi + wi for zi, wi in zip(z, w, strict=True)]
        f = _wald_sub(e, x, clusters, kz)
        grid.append(round(b0, 4))
        keep.append(f < f_crit)
    return {"grid": grid, "keep": keep, "kz": kz, "f_crit": f_crit}
