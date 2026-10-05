"""[S1] Phân cấp swing (Larry Williams): cấp k+1 lọc trên chuỗi swing cấp k đã xác nhận.

Ba đỉnh cấp k liên tiếp ``P_trai, P_giua, P_phai``: ``P_giua`` là đỉnh cấp k+1 khi cao hơn
(nghiêm ngặt) cả hai. Đáy đối xứng. Xác nhận **khi đỉnh cấp k bên phải được xác nhận** — không gắn
về lúc đỉnh giữa hình thành. Cùng quy tắc với ``swing_hierarchy`` (cấp 2 trên cấp 1).

Đọc swing của **bất kỳ** nguồn nào (pivot, DC…), không biết nến.
"""
from __future__ import annotations

from typing import Any, Optional

from core.components.swing_source import Pivot


class HierarchyLevel:
    def __init__(self, level: int) -> None:
        if level < 2:
            raise ValueError("Cấp phân cấp phải >= 2")
        self.level = level
        self.reset()

    def reset(self) -> None:
        self._seq: dict[str, list[Pivot]] = {"high": [], "low": []}
        self.count = {"high": 0, "low": 0}

    def update(self, pivot: Pivot) -> Optional[Pivot]:
        """Nạp một swing cấp ``level - 1`` vừa xác nhận; trả swing cấp ``level`` nếu có."""
        if pivot.level != self.level - 1:
            raise ValueError("HierarchyLevel(%d) nhận swing cấp %d" % (self.level, pivot.level))
        seq = self._seq[pivot.side]
        seq.append(pivot)
        if len(seq) > 3:
            del seq[0]
        if len(seq) < 3:
            return None
        left, mid, right = seq
        if pivot.side == "high":
            ok = mid.price > left.price and mid.price > right.price
        else:
            ok = mid.price < left.price and mid.price < right.price
        if not ok:
            return None
        self.count[pivot.side] += 1
        return Pivot(pivot.side, self.level, mid.price, mid.bar, mid.pos, pivot.confirmed_bar,
                     members=(left, mid, right))

    def snapshot(self) -> dict[str, Any]:
        def tail(side: str) -> list[dict[str, Any]]:
            return [{"gia": p.price, "nen": p.bar_index, "xac_nhan_tai": p.confirmed_index}
                    for p in self._seq[side]]
        return {"cap": self.level, "cap_duoi_gan_nhat": {"high": tail("high"), "low": tail("low")},
                "so_luong": dict(self.count)}
