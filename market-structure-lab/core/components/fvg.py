"""[P2] FVG ba nến (plan_ict_structure §4.4) và vòng đời chạm → lấp.

* Tăng: ``low[t] > high[t−2]``, vùng ``[high[t−2], low[t]]``; giảm: ``high[t] < low[t−2]``, vùng
  ``[high[t], low[t−2]]``. Gắn tại t (vẽ ở nến giữa t−1), biết khi t đóng.
* Loại nếu ba nến vắt qua khoảng trống (đó là khoảng trống mở phiên, không phải FVG). Ngưỡng
  ``fvg_min_atr`` × ATR[t−1] (mặc định 0 = không lọc).
* ``from_displacement``: nến giữa là displacement cùng chiều.
* Vòng đời (từ nến sau lúc biết): **chạm** khi giá tới mép gần lần đầu, **lấp** khi tới mép xa. Có thể
  cùng một nến. «Đã lấp» chỉ là mốc mô tả, không phải tín hiệu.

FVG đang mở nằm trong heap theo mép → mỗi FVG chuyển trạng thái tối đa hai lần, tổng chi phí
O(N log N) dù có hàng chục nghìn FVG chưa lấp.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, Optional

from core.types import Bar


@dataclass
class Fvg:
    seq: int
    direction: str            # "up" | "down"
    lo: float
    hi: float
    index: int                # nến thứ 3 (lúc biết)
    mid_index: int            # nến giữa
    from_displacement: bool
    event_id: str = ""
    touched_at: Optional[int] = None
    filled_at: Optional[int] = None


class FvgTracker:
    def __init__(self, min_atr: float = 0.0) -> None:
        if min_atr < 0:
            raise ValueError("fvg_min_atr phải >= 0")
        self.min_atr = min_atr
        self.reset()

    def reset(self) -> None:
        self._seq = 0
        self._up_touch: list[tuple] = []     # (-hi, seq, fvg): chạm khi low ≤ hi
        self._up_fill: list[tuple] = []      # (-lo, seq, fvg): lấp khi low ≤ lo
        self._dn_touch: list[tuple] = []     # (lo, seq, fvg): chạm khi high ≥ lo
        self._dn_fill: list[tuple] = []      # (hi, seq, fvg): lấp khi high ≥ hi
        self.counts = {"tao": 0, "tu_displacement": 0, "bo_vi_khoang_trong": 0, "bo_vi_nho": 0,
                       "cham": 0, "lap": 0}
        self.open = {"up": 0, "down": 0}

    def update_open(self, bar: Bar) -> list[tuple[str, Fvg]]:
        """Chạm / lấp của các FVG đã biết TRƯỚC nến này. Trả [(“touched”|“filled”, fvg)] theo thứ tự tạo."""
        out: list[tuple[str, Fvg]] = []
        while self._up_touch and -self._up_touch[0][0] >= bar.low:
            _k, _s, f = heapq.heappop(self._up_touch)
            f.touched_at = bar.index
            out.append(("touched", f))
            heapq.heappush(self._up_fill, (-f.lo, f.seq, f))
        while self._up_fill and -self._up_fill[0][0] >= bar.low:
            _k, _s, f = heapq.heappop(self._up_fill)
            f.filled_at = bar.index
            out.append(("filled", f))
            self.open["up"] -= 1
        while self._dn_touch and self._dn_touch[0][0] <= bar.high:
            _k, _s, f = heapq.heappop(self._dn_touch)
            f.touched_at = bar.index
            out.append(("touched", f))
            heapq.heappush(self._dn_fill, (f.hi, f.seq, f))
        while self._dn_fill and self._dn_fill[0][0] <= bar.high:
            _k, _s, f = heapq.heappop(self._dn_fill)
            f.filled_at = bar.index
            out.append(("filled", f))
            self.open["down"] -= 1
        out.sort(key=lambda x: (x[1].seq, 0 if x[0] == "touched" else 1))
        for kind, _f in out:
            self.counts["cham" if kind == "touched" else "lap"] += 1
        return out

    def detect(self, b1: Bar, b2: Bar, b3: Bar, gap_in_window: bool, atr_prev: Optional[float],
               mid_disp: Optional[str]) -> Optional[Fvg]:
        """FVG với nến 3 = ``b3``; ghi vào heap (chạm/lấp xét từ nến sau)."""
        if b3.low > b1.high:
            direction, lo, hi = "up", b1.high, b3.low
        elif b3.high < b1.low:
            direction, lo, hi = "down", b3.high, b1.low
        else:
            return None
        if gap_in_window:
            self.counts["bo_vi_khoang_trong"] += 1
            return None
        if self.min_atr > 0 and (atr_prev is None or hi - lo < self.min_atr * atr_prev):
            self.counts["bo_vi_nho"] += 1
            return None
        f = Fvg(self._seq, direction, lo, hi, b3.index, b2.index, mid_disp == direction)
        self._seq += 1
        self.counts["tao"] += 1
        if f.from_displacement:
            self.counts["tu_displacement"] += 1
        self.open[direction] += 1
        if direction == "up":
            heapq.heappush(self._up_touch, (-hi, f.seq, f))
        else:
            heapq.heappush(self._dn_touch, (lo, f.seq, f))
        return f

    def nearest(self) -> dict[str, Any]:
        """FVG chưa chạm gần giá nhất mỗi chiều (mép gần)."""
        up = self._up_touch[0][2] if self._up_touch else None
        dn = self._dn_touch[0][2] if self._dn_touch else None
        return {
            "up": None if up is None else {"lo": up.lo, "hi": up.hi, "nen": up.mid_index},
            "down": None if dn is None else {"lo": dn.lo, "hi": dn.hi, "nen": dn.mid_index},
        }
