"""Shift-share (Bartik) instrument constructor in pure stdlib.

Given base-year local shares by origin group and national group growth
rates, builds predicted local shocks with optional leave-one-out
national growth (recommended: a province's own flow must not move its
own shifter). No data bundled, no estimates — pair with ols.tsls and
the AR machinery when a design is commissioned. See identification.md.
"""

from __future__ import annotations


def national_growth(
    stocks: dict[tuple[str, str, int], float],
    origins: list[str],
    units: list[str],
    t0: int,
    t1: int,
    leave_out: str | None = None,
) -> dict[str, float]:
    """National growth rate per origin between t0 and t1.

    stocks[(unit, origin, year)] -> level. leave_out excludes one unit
    from the national aggregates (use the unit being instrumented).
    """
    out = {}
    for o in origins:
        b = sum(stocks.get((u, o, t0), 0.0) for u in units if u != leave_out)
        e = sum(stocks.get((u, o, t1), 0.0) for u in units if u != leave_out)
        out[o] = (e - b) / b if b else 0.0
    return out


def shares(
    stocks: dict[tuple[str, str, int], float],
    units: list[str],
    origins: list[str],
    t0: int,
) -> dict[tuple[str, str], float]:
    """Base-year origin shares per unit (sum to 1 over listed origins)."""
    out = {}
    for u in units:
        denom = sum(stocks.get((u, o, t0), 0.0) for o in origins)
        for o in origins:
            out[(u, o)] = stocks.get((u, o, t0), 0.0) / denom if denom else 0.0
    return out


def shift_share(
    stocks: dict[tuple[str, str, int], float],
    units: list[str],
    origins: list[str],
    t0: int,
    t1: int,
    leave_one_out: bool = True,
) -> dict[str, float]:
    """Predicted shock per unit: sum_o share[u,o,t0] * g[o,t0->t1]."""
    out = {}
    for u in units:
        g = national_growth(stocks, origins, units, t0, t1, leave_out=u if leave_one_out else None)
        s = shares(stocks, units, origins, t0)
        out[u] = sum(s[(u, o)] * g[o] for o in origins)
    return out
