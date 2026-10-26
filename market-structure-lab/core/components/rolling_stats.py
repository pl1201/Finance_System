"""Thống kê trượt dùng chung của lớp nhận diện (``price_band``, ``state_clock``): phân vị nội suy, tỷ lệ an toàn, cửa sổ
trượt đã sắp, điểm Brier của một xác suất nhị phân so với B0."""
from __future__ import annotations

import bisect
from collections import deque
from typing import Any, Optional


def quantile(xs: list[float], q: float, lo: int = 0) -> float:
    """Phân vị nội suy tuyến tính trên ``xs[lo:]`` (đã sắp), vị trí (n − 1)·q — không cắt danh sách."""
    pos = (len(xs) - lo - 1) * q
    i = lo + int(pos)
    j = min(i + 1, len(xs) - 1)
    return xs[i] + (xs[j] - xs[i]) * (pos - int(pos))


def ratio(a: float, n: int) -> Optional[float]:
    return a / n if n else None


class SortedWindow:
    """Cửa sổ trượt cỡ ``cap`` giữ bản đã sắp (phân vị, số / tỷ lệ ≥ x trong O(log n))."""

    __slots__ = ("cap", "fifo", "xs")

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.fifo: deque[float] = deque()
        self.xs: list[float] = []

    def add(self, x: float) -> None:
        self.fifo.append(x)
        bisect.insort(self.xs, x)
        if len(self.fifo) > self.cap:
            del self.xs[bisect.bisect_left(self.xs, self.fifo.popleft())]

    def __len__(self) -> int:
        return len(self.xs)

    def count_at_least(self, x: float) -> int:
        return len(self.xs) - bisect.bisect_left(self.xs, x)

    def at_least(self, x: float) -> float:
        return self.count_at_least(x) / len(self.xs)


class BrierTally:
    """Điểm thật của một xác suất nhị phân: số lần chấm, số lần xảy ra, tổng (p − y)² và (p0 − y)² của B0."""

    __slots__ = ("n", "hit", "brier", "brier0")

    def __init__(self) -> None:
        self.n = self.hit = 0
        self.brier = self.brier0 = 0.0

    def add(self, p: float, p0: float, hit: bool) -> None:
        self.n += 1
        self.hit += hit
        self.brier += (p - hit) ** 2
        self.brier0 += (p0 - hit) ** 2

    def summary(self) -> dict[str, Any]:
        return {"n": self.n, "ty_le": ratio(self.hit, self.n), "brier": ratio(self.brier, self.n),
                "brier_b0": ratio(self.brier0, self.n)}
