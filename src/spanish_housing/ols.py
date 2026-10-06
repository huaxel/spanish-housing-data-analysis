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
    return [solve(_copy(a), [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]


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
