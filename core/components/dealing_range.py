"""[S4] Dealing range, premium / discount (plan_ict_structure.md §4.8).

``range_hi`` = max(đỉnh cấu trúc gần nhất, high cao nhất từ nến cực trị của đỉnh đó tới nến hiện
tại); ``range_lo`` đối xứng với đáy. Cập nhật dần theo từng nến — nhân quả. Vì gồm cả nến hiện tại,
dealing range **luôn chứa giá** nên ``zone`` (premium > EQ > discount) luôn xác định khi đã có cả
hai mốc. ``range_pos`` = (close − lo) / (hi − lo) ∈ [0, 1].
"""
from __future__ import annotations

from typing import Any, Optional

from core.components.swing_source import Pivot
from core.types import Bar


class DealingRange:
    def reset(self) -> None:
        self.hi_anchor: Optional[Pivot] = None
        self.lo_anchor: Optional[Pivot] = None
        self.hi: Optional[float] = None
        self.lo: Optional[float] = None

    def __init__(self) -> None:
        self.reset()

    def on_bar(self, bar: Bar) -> None:
        """Mở rộng theo nến hiện tại (gọi trước khi đặt mốc mới ở cùng nến)."""
        if self.hi is not None and bar.high > self.hi:
            self.hi = bar.high
        if self.lo is not None and bar.low < self.lo:
            self.lo = bar.low

    def on_swing(self, pivot: Pivot, extreme_since: float) -> None:
        """Mốc mới. ``extreme_since``: high cao nhất (đỉnh) / low thấp nhất (đáy) từ nến cực trị của
        swing tới nến hiện tại, gồm cả hai đầu."""
        if pivot.side == "high":
            self.hi_anchor = pivot
            self.hi = max(pivot.price, extreme_since)
        else:
            self.lo_anchor = pivot
            self.lo = min(pivot.price, extreme_since)

    def ready(self) -> bool:
        return self.hi is not None and self.lo is not None

    def snapshot(self, close: float) -> dict[str, Any]:
        if not self.ready():
            return {"hi": None, "lo": None, "eq": None, "zone": None, "range_pos": None, "id": None}
        hi, lo = float(self.hi), float(self.lo)
        eq = (hi + lo) / 2.0
        zone = "premium" if close > eq else ("discount" if close < eq else "eq")
        pos = (close - lo) / (hi - lo) if hi > lo else 0.5
        return {
            "hi": hi, "lo": lo, "eq": eq, "zone": zone, "range_pos": pos,
            "id": "%d-%d" % (self.hi_anchor.bar_index, self.lo_anchor.bar_index),
        }
