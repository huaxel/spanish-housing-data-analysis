"""Wild-cluster bootstrap-t inversion grid, outside the estimator core.

Deliberately NOT added to spanish_housing/ols.py: ols.py is a freshness key
for every model artifact, so a new helper there would invalidate all 18
committed outputs and force a full analysis re-run. This module imports the
existing pure-stdlib routines and adds only the candidate-coefficient
inversion used by scripts/invert_tourist.py.
"""

from __future__ import annotations

from spanish_housing import ols


def wild_bootstrap_t_grid(
    x: list[list[float]],
    y: list[float],
    clusters: list[str | int],
    j: int,
    grid: list[float],
    reps: int = 1999,
    seed: int = 20261006,
    alpha: float = 0.05,
) -> dict:
    """Wild-cluster bootstrap-t inversion over candidate beta_j values.

    For every candidate c the null H0: beta_j = c is imposed by recentering
    y_c = y - c*x_j and running the SAME restricted-fit wild bootstrap as the
    existing zero-null routine in ols.wild_bootstrap_t (Rademacher per
    cluster, refit the full model each replicate, finite-rep
    (count+1)/(reps+1) two-sided p). Draws are generated once and reused for
    every candidate, so p-values are comparable under common random numbers;
    candidate c = 0.0 with the same seed/reps reproduces the legacy routine
    exactly.

    Returns the grid, per-candidate p, the acceptance mask at the nominal
    alpha level, and boundary/resolution warnings. The mask is a set of
    TESTED POINTS only: it is not a continuous confidence interval, and the
    warnings flag when the accepted set touches the grid edges (so it may
    extend beyond) or no candidate was accepted at this resolution.
    """
    import random

    rng = random.Random(seed)
    k = len(x[0])
    keep_cols = [c for c in range(k) if c != j]
    x0 = [[row[c] for c in keep_cols] for row in x]
    xj = [row[j] for row in x]
    groups: dict[str | int, list[int]] = {}
    for i, g in enumerate(clusters):
        groups.setdefault(g, []).append(i)
    keys = list(groups)
    # Common random numbers: one Rademacher matrix shared by all candidates,
    # drawn in the same per-rep/per-cluster order as ols.wild_bootstrap_t.
    n = len(x)
    bread = ols.invert(ols.xtx(x))
    wj = [sum(bread[j][m] * x[i][m] for m in range(k)) for i in range(n)]
    g_count = len(groups)
    c_scale = (g_count / (g_count - 1)) * ((n - 1) / (n - k)) if g_count > 1 and n > k else 1.0
    draws = [[1.0 if rng.random() < 0.5 else -1.0 for _ in keys] for _ in range(reps)]
    group_items = list(groups.values())
    Z_g = [[sum(wj[i] * x[i][m] for i in idxs) for m in range(k)] for idxs in group_items]
    out = {"grid": [], "p": [], "keep": [], "warnings": []}
    for c in grid:
        y_c = [yi - c * xji for yi, xji in zip(y, xj, strict=True)]
        fit0 = ols.ols_cluster(x0, y_c, clusters)
        fitted0 = ols.predict(x0, fit0["beta"])
        e0 = [yi - fh for yi, fh in zip(y_c, fitted0, strict=True)]
        full = ols.ols_cluster(x, y_c, clusters)
        t_obs = full["beta"][j] / full["se"][j] if full["se"][j] > 0 else 0.0
        xty0 = ols.xty(x, fitted0)
        s0_g = [[sum(x[i][m] * e0[i] for i in idxs) for m in range(k)] for idxs in group_items]
        q_g = [sum(wj[i] * fitted0[i] for i in idxs) for idxs in group_items]
        r_g = [sum(wj[i] * e0[i] for i in idxs) for idxs in group_items]
        t_stars = []
        for rep in range(reps):
            v = draws[rep]
            xty_star = [
                xty0[m] + sum(v[grp_idx] * s0_g[grp_idx][m] for grp_idx in range(g_count))
                for m in range(k)
            ]
            beta_star = [sum(bread[r][m] * xty_star[m] for m in range(k)) for r in range(k)]
            v_jj = (
                sum(
                    (
                        q_g[grp_idx]
                        - sum(Z_g[grp_idx][m] * beta_star[m] for m in range(k))
                        + v[grp_idx] * r_g[grp_idx]
                    )
                    ** 2
                    for grp_idx in range(g_count)
                )
                * c_scale
            )
            se_star = (v_jj**0.5) if v_jj > 0 else 0.0
            t_stars.append(beta_star[j] / se_star if se_star > 0 else 0.0)
        p = (sum(1 for t in t_stars if abs(t) >= abs(t_obs)) + 1) / (reps + 1)
        out["grid"].append(round(c, 4))
        out["p"].append(round(p, 4))
        out["keep"].append(p >= alpha)
    kept = out["keep"]
    if not any(kept):
        out["warnings"].append("no_candidate_accepted_at_this_resolution")
    if kept and kept[0]:
        out["warnings"].append("accepted_set_may_extend_below_grid")
    if kept and kept[-1]:
        out["warnings"].append("accepted_set_may_extend_above_grid")
    if any(kept):
        # With a t-statistic inversion the accepted set is an interval in c;
        # a gap would indicate an error in the implementation or draws.
        first = kept.index(True)
        last = len(kept) - 1 - kept[::-1].index(True)
        if any(not kept[s] for s in range(first, last + 1)):
            out["warnings"].append("disjoint_accepted_set")
    return out
