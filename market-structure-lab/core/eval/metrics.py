"""Các đại lượng đánh giá: F1, percentile, mật độ, khoảng giá/ATR."""
from __future__ import annotations

import math
from typing import Optional, Sequence


def f1_score(precision: Optional[float], recall: Optional[float]) -> Optional[float]:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return None
    return 2.0 * precision * recall / (precision + recall)


def ratio(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return num / den


def percentile_nearest_rank(values: Sequence[float], p: float) -> Optional[float]:
    """Percentile nearest-rank: chỉ số 1-based ``ceil(p/100 * n)``.

    ``p`` trong [0, 100]. Danh sách rỗng → ``None``.
    """
    if not values:
        return None
    if p < 0 or p > 100:
        raise ValueError("percentile p phải trong [0, 100], nhận %s" % p)
    xs = sorted(float(v) for v in values)
    n = len(xs)
    k = max(1, min(n, math.ceil(p / 100.0 * n)))
    return xs[k - 1]


def median(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    xs = sorted(float(v) for v in values)
    n = len(xs)
    mid = n // 2
    if n % 2:
        return xs[mid]
    return (xs[mid - 1] + xs[mid]) / 2.0


def lag_histogram(values: Sequence[int], *, bin_width: int = 4, max_edge: int = 40) -> list[dict]:
    """Histogram độ trễ (nến). Bin cuối gộp mọi giá trị ≥ max_edge."""
    if bin_width < 1 or max_edge < 1:
        raise ValueError("bin_width và max_edge phải >= 1")
    edges = list(range(0, max_edge, bin_width))
    counts = [0] * (len(edges) + 1)
    for v in values:
        x = int(v)
        if x < 0:
            x = 0
        if x >= max_edge:
            counts[-1] += 1
            continue
        counts[x // bin_width] += 1
    out = []
    for i, start in enumerate(edges):
        end = start + bin_width - 1
        out.append({"from": start, "to": end, "count": counts[i]})
    out.append({"from": max_edge, "to": None, "count": counts[-1]})
    return out
