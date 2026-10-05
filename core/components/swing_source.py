"""[P1] Nguồn swing: pivot strict left/right (STH/STL khi 1/1).

Pivot đỉnh tại nến ``c``: ``high[c]`` lớn hơn (nghiêm ngặt) mọi high trong ``left`` nến trước và
``right`` nến sau; biết khi nến ``c + right`` đóng. Đáy đối xứng. Nến bằng giá → không phải pivot.
Outside bar có thể vừa là đỉnh vừa là đáy. Cùng quy tắc với ``swing_pivot`` / ``swing_hierarchy``.

Chặn gap (mặc định bật, plan_ict_structure D1): cửa sổ ``c-left .. c+right`` có khoảng trống giữa
hai nến liên tiếp bất kỳ → không xét pivot ở ``c`` (đếm vào ``blocked``). Mức đã có vẫn giữ.

Nguồn swing phải thay được (AGENTS.md §4.3): thuật toán tổ hợp chỉ dùng ``update`` → danh sách
``Pivot`` — nguồn khác (vd DC theo close) chỉ cần trả cùng kiểu.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from core.types import Bar


@dataclass(frozen=True)
class Pivot:
    """Một swing đã xác nhận ở một cấp."""

    side: str                 # "high" | "low"
    level: int                # 1 = STH/STL, 2 = ITH/ITL, 3 = LTH/LTL
    price: float
    bar: Bar                  # nến cực trị
    pos: int                  # thứ tự nến cực trị trong luồng (0 = nến đầu tiên đã nạp)
    confirmed_bar: Bar        # nến làm swing được biết
    event_id: str = ""
    members: tuple["Pivot", ...] = field(default=(), compare=False)   # ba swing cấp dưới (cấp ≥ 2)

    @property
    def bar_index(self) -> int:
        return self.bar.index

    @property
    def confirmed_index(self) -> int:
        return self.confirmed_bar.index


class PivotSource:
    def __init__(self, left: int = 1, right: int = 1, block_gaps: bool = True) -> None:
        if left < 1 or right < 1:
            raise ValueError("left/right phải >= 1")
        self.left = left
        self.right = right
        self.block_gaps = block_gaps
        self.reset()

    def reset(self) -> None:
        n = self.left + self.right + 1
        self._win: deque[Bar] = deque(maxlen=n)
        self._gap_before: deque[bool] = deque(maxlen=n)
        self._n = 0                       # số nến đã nạp
        self.blocked = {"high": 0, "low": 0}

    def update(self, bar: Bar, gap_before: bool) -> list[Pivot]:
        """Nạp nến ``bar`` (``gap_before``: có khoảng trống giữa nến trước và nến này)."""
        self._win.append(bar)
        self._gap_before.append(bool(gap_before))
        self._n += 1
        if len(self._win) < self.left + self.right + 1:
            return []
        win = list(self._win)
        c = win[self.left]
        others = win[: self.left] + win[self.left + 1:]
        is_high = all(b.high < c.high for b in others)
        is_low = all(b.low > c.low for b in others)
        if not (is_high or is_low):
            return []
        # khoảng trống giữa hai nến liên tiếp trong cửa sổ = cờ gap_before của nến thứ 2..cuối
        if self.block_gaps and any(list(self._gap_before)[1:]):
            if is_high:
                self.blocked["high"] += 1
            if is_low:
                self.blocked["low"] += 1
            return []
        pos = self._n - 1 - self.right
        out = []
        if is_high:
            out.append(Pivot("high", 1, c.high, c, pos, bar))
        if is_low:
            out.append(Pivot("low", 1, c.low, c, pos, bar))
        return out

    def snapshot(self) -> dict[str, Any]:
        return {
            "cho_xac_nhan": [b.index for b in list(self._win)[self.left:]] if self._win else [],
            "bi_chan_vi_gap": dict(self.blocked),
        }


def with_event_id(p: Pivot, event_id: str) -> Pivot:
    return Pivot(p.side, p.level, p.price, p.bar, p.pos, p.confirmed_bar, event_id, p.members)
