"""[P3] Displacement (plan_ict_structure §4.3).

Nến t là displacement tăng khi ``close > open``, ``high − low ≥ k_disp × ATR[t−1]`` và
``|close − open| ≥ body_min × (high − low)``; giảm đối xứng. Mặc định 1.5 và 0.6 (≈ 7% nến M15 —
survey-v2 §2.3, do lab chọn). Không xét nến đầu sau khoảng trống; ATR chưa có → không xét.
"""
from __future__ import annotations

from typing import Any, Optional

from core.types import Bar


class Displacement:
    def __init__(self, k_disp: float, body_min: float) -> None:
        if k_disp <= 0 or not 0 <= body_min <= 1:
            raise ValueError("k_disp phải > 0 và body_min trong [0, 1]")
        self.k_disp = k_disp
        self.body_min = body_min

    def check(self, bar: Bar, atr_prev: Optional[float], after_gap: bool) -> Optional[dict[str, Any]]:
        if after_gap or atr_prev is None or atr_prev <= 0:
            return None
        rng = bar.high - bar.low
        body = abs(bar.close - bar.open)
        if rng <= 0 or rng < self.k_disp * atr_prev or body < self.body_min * rng:
            return None
        if bar.close > bar.open:
            direction = "up"
        elif bar.close < bar.open:
            direction = "down"
        else:
            return None
        return {
            "dir": direction,
            "bien_do_atr": rng / atr_prev,
            "than_ty_le": body / rng,
            "atr": atr_prev,
            "nguong_vi": "biên độ ≥ %s × ATR và thân ≥ %s × biên độ" % (self.k_disp, self.body_min),
        }
