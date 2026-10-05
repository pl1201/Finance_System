"""[S2] Thứ tự đỉnh/đáy và mức được bảo vệ (plan_ict_structure.md §4.5).

Khi một swing cấu trúc mới có hiệu lực, so với swing cùng phía liền trước, dung sai
``eq_tol_atr × ATR`` (ATR của khung **lúc xác nhận** — giá trị của nến trước nến xác nhận):

* ``hh`` ∈ {+1, 0, −1} giữa hai đỉnh, ``hl`` ∈ {+1, 0, −1} giữa hai đáy (0 = bằng giá trong dung sai);
* ``order`` = +1 khi ``hh = hl = +1``; −1 khi ``hh = hl = −1``; 0 (lẫn lộn) mọi trường hợp còn lại;
  ``None`` khi chưa đủ hai so sánh. **Chỉ đổi khi có swing mới**, không đổi vì close vượt mức.
* ATR chưa có → chưa so (``hh``/``hl`` = None, không ép dung sai 0).

Mức được bảo vệ — một định nghĩa: ``order`` +1 → đáy gần nhất; −1 → đỉnh gần nhất; 0 → không có.
``protected_broken``: đã có close vượt (nghiêm ngặt) mức kể từ khi nó thành mức được bảo vệ; xoá khi
mức đổi. **Không** phát sự kiện, **không** đổi ``order``. Không có BOS/CHoCH/MSS (quyết định B1).
"""
from __future__ import annotations

from typing import Any, Optional

from core.components.swing_source import Pivot
from core.types import Bar

LABELS = {
    ("high", 1): "HH", ("high", -1): "LH", ("high", 0): "EQH",
    ("low", 1): "HL", ("low", -1): "LL", ("low", 0): "EQL",
}
ORDER_TEXT_VI = {1: "tăng (HH + HL)", -1: "giảm (LH + LL)", 0: "lẫn lộn", None: "chưa đủ swing"}


class StructureOrder:
    def __init__(self, eq_tol_atr: float) -> None:
        if eq_tol_atr < 0:
            raise ValueError("eq_tol_atr phải >= 0")
        self.eq_tol_atr = eq_tol_atr
        self.reset()

    def reset(self) -> None:
        self.last: dict[str, Optional[Pivot]] = {"high": None, "low": None}
        self.cmp: dict[str, Optional[int]] = {"high": None, "low": None}
        self.order: Optional[int] = None
        self.protected: Optional[Pivot] = None
        self.broken = False
        self.broken_at: Optional[int] = None

    def check_close(self, bar: Bar) -> bool:
        """Close của ``bar`` so với mức được bảo vệ đã biết TRƯỚC nến này. True nếu vừa bị vượt."""
        p = self.protected
        if p is None or self.broken:
            return False
        if (p.side == "low" and bar.close < p.price) or (p.side == "high" and bar.close > p.price):
            self.broken = True
            self.broken_at = bar.index
            return True
        return False

    def on_swing(self, pivot: Pivot, atr: Optional[float]) -> dict[str, Any]:
        """Swing cấu trúc mới (đã xác nhận). Trả chi tiết so sánh để ghi vào ``details``."""
        side = pivot.side
        prev = self.last[side]
        cmp: Optional[int] = None
        tol: Optional[float] = None
        diff: Optional[float] = None
        if prev is not None and atr is not None:
            tol = self.eq_tol_atr * atr
            diff = pivot.price - prev.price
            cmp = 1 if diff > tol else (-1 if diff < -tol else 0)
        self.last[side] = pivot
        self.cmp[side] = cmp
        hh, hl = self.cmp["high"], self.cmp["low"]
        if hh is None or hl is None:
            order = None
        elif hh == 1 and hl == 1:
            order = 1
        elif hh == -1 and hl == -1:
            order = -1
        else:
            order = 0
        self.order = order
        new_protected = self.last["low"] if order == 1 else (self.last["high"] if order == -1 else None)
        if _key(new_protected) != _key(self.protected):
            self.protected = new_protected
            self.broken = False
            self.broken_at = None
        return {
            "so_sanh": cmp,
            "nhan": LABELS.get((side, cmp)) if cmp is not None else None,
            "gia_truoc": prev.price if prev is not None else None,
            "nen_truoc": prev.bar_index if prev is not None else None,
            "chenh_lech": diff,
            "dung_sai": tol,
            "atr_luc_xac_nhan": atr,
            "ly_do_chua_so": (
                None if cmp is not None else ("swing đầu tiên cùng phía" if prev is None else "ATR chưa đủ nến")
            ),
            "order_sau": order,
            "order_sau_vi": ORDER_TEXT_VI[order],
            "muc_bao_ve_sau": self.protected.price if self.protected else None,
        }

    def snapshot(self) -> dict[str, Any]:
        p = self.protected
        return {
            "order": self.order,
            "order_vi": ORDER_TEXT_VI[self.order],
            "hh": self.cmp["high"],
            "hl": self.cmp["low"],
            "dinh_gan_nhat": _brief(self.last["high"]),
            "day_gan_nhat": _brief(self.last["low"]),
            "muc_bao_ve": None if p is None else dict(_brief(p), phia=p.side),
            "muc_bao_ve_bi_vuot": self.broken,
            "bi_vuot_tai_nen": self.broken_at,
        }


def _key(p: Optional[Pivot]) -> Optional[tuple]:
    return None if p is None else (p.side, p.level, p.bar_index, p.confirmed_index)


def _brief(p: Optional[Pivot]) -> Optional[dict[str, Any]]:
    if p is None:
        return None
    return {"gia": p.price, "nen": p.bar_index, "xac_nhan_tai": p.confirmed_index}
