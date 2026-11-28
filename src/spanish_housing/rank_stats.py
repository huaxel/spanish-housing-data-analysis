"""Rank correlation with mean ranks for ties, including exact decimal ratios."""

import statistics


def midranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        for i in order[start:end]:
            ranks[i] = (start + 1 + end) / 2
        start = end
    return ranks


def spearman(x, y, *, digits):
    if len(x) != len(y):
        raise ValueError("Rank correlation requires paired values")
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return round(statistics.correlation(midranks(x), midranks(y)), digits)
