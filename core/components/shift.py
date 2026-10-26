"""[E3] Shift = sweep → displacement ngược chiều (plan_ict_structure §4.7, thay BOS/CHoCH/MSS — B1).

Sau một sweep tại r (nến lấy b), cực trị cú quét ``X = max(high[b..r])`` (quét BSL) hoặc
``min(low[b..r])`` (quét SSL). **Shift giảm** (sau quét BSL) tại d = nến **đầu tiên** trong
``[r, r + shift_window]`` thoả cả bốn:

1. d là displacement giảm;
2. ``close[d] <`` mức bị quét;
3. không có khoảng trống trong (r, d];
4. không nến nào trong (r, d] có ``high > X`` — nếu có, cú quét đã bị vượt → **huỷ**, không tìm tiếp.

Shift tăng đối xứng. Nhiều sweep cùng dẫn tới một d → **một** shift (thuật toán gom theo chiều).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.types import Bar


def overrun(direction: str, extreme: float, bar: Bar) -> bool:
    """Cú quét đã bị vượt ở ``bar``: high > X (sau quét BSL, chiều "down") / low < X (sau quét SSL); bằng X không tính — chung cho
    shift và MSS (``core/components/mss.py``)."""
    return bar.high > extreme if direction == "down" else bar.low < extreme


@dataclass
class ShiftCandidate:
    direction: str                # "down" (sau quét BSL) | "up" (sau quét SSL)
    level: float                  # mức bị quét
    extreme: float                # X
    r: int                        # nến sweep
    deadline: int                 # r + shift_window
    sweep_event_id: str
    group_id: str
    tier: str
    pools: list[dict[str, Any]] = field(default_factory=list)
    taken_index: Optional[int] = None


class ShiftTracker:
    def __init__(self, window: int) -> None:
        if window < 0:
            raise ValueError("shift_window phải >= 0")
        self.window = window
        self.reset()

    def reset(self) -> None:
        self.pending: list[ShiftCandidate] = []
        self.counts = {"ung_vien": 0, "huy_vuot_cuc_tri": 0, "huy_khoang_trong": 0, "het_cua_so": 0,
                       "thanh_shift": 0}

    def add(self, c: ShiftCandidate) -> None:
        self.pending.append(c)
        self.counts["ung_vien"] += 1

    def on_bar(self, bar: Bar, disp: Optional[dict[str, Any]], gap_before: bool) -> dict[str, list[ShiftCandidate]]:
        """Xét nến t cho mọi ứng viên (kể cả ứng viên vừa thêm ở chính t). Trả {chiều: [ứng viên thành shift]}."""
        t = bar.index
        ok: dict[str, list[ShiftCandidate]] = {}
        still: list[ShiftCandidate] = []
        for c in self.pending:
            if t > c.r:
                if gap_before:
                    self.counts["huy_khoang_trong"] += 1
                    continue
                if overrun(c.direction, c.extreme, bar):
                    self.counts["huy_vuot_cuc_tri"] += 1
                    continue
            hit = (disp is not None and disp["dir"] == c.direction
                   and (bar.close < c.level if c.direction == "down" else bar.close > c.level))
            if hit:
                ok.setdefault(c.direction, []).append(c)
                self.counts["thanh_shift"] += 1
            elif t >= c.deadline:
                self.counts["het_cua_so"] += 1
            else:
                still.append(c)
        self.pending = still
        return ok
