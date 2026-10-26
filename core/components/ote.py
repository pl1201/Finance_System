"""[E6] OTE — vùng hồi 62–79% của nhịp sau SHIFT (plan_ket_hop_ict_indicator.md §3.4; luồng: kien_truc_luong_ict.md §4.4).

Mô tả cho nhịp tăng (sau ``SHIFT_UP`` ở nến d); nhịp giảm đối xứng.

* **Nhịp:** đáy X = cực trị cú quét của SHIFT; đỉnh H = high[d], cập nhật ``H = max(H, high[t])`` SAU mỗi nến t
  (bước 12b) cho tới khi kết thúc → nến t chỉ dùng H của nến t − 1 (một nến vừa lập đỉnh mới vừa hồi sâu không tự vào
  OTE của chính nó). L = H − X.
* **Vùng:** [H − ``frac_hi``·L, H − ``frac_lo``·L] (mặc định 62–79%, điểm ngọt 70,5%). Chỉ có hiệu lực khi
  L ≥ ``min_leg_atr`` × ATR[t−1] (``min_leg_atr = 0``: không lọc, không cần ATR).
* **Bước 3b của nến t > d:** ``low[t] < X`` → ``fail`` (đáy nhịp bị thủng; xét trước); vùng có hiệu lực và
  ``low[t] ≤ H − frac_lo·L`` → ``entry`` (độ sâu = (H − low[t]) / L ∈ [frac_lo, 1]; = 1 khi low chạm đúng X mà không
  thủng); chưa vào mà ``t ≥ d + han`` → ``expired_time``.
* **Một nhịp đang chờ tại một thời điểm:** SHIFT mới (bước 6c) thay nhịp đang chờ — ngược chiều → ``expired_shift``;
  cùng chiều → ``replaced`` (chỗ plan chưa nói, chọn khi cài: nhịp mới là nhịp ICT đang xét).

Thành phần chỉ giữ trạng thái; thuật toán phát sự kiện (``OTE_ENTRY_*``, ``OTE_FAIL_*``, ``OTE_EXPIRED``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.types import Bar

#: Kết cục → chữ ngắn (details / thống kê). Khoá cũng là danh sách mọi kết cục.
END_TEXT_VI = {"entry": "giá vào vùng OTE", "fail": "đáy/đỉnh nhịp bị thủng", "expired_time": "hết hạn",
               "expired_shift": "SHIFT ngược chiều", "replaced": "SHIFT mới cùng chiều thay nhịp"}


@dataclass
class OteLeg:
    direction: str                     # "up" (nhịp tăng, hồi xuống) | "down"
    x: float                           # gốc nhịp (cực trị cú quét)
    h: float                           # đầu nhịp (cập nhật tới khi kết thúc)
    anchor: int                        # d
    anchor_id: str                     # sự kiện SHIFT ở d
    deadline: int
    ended: Optional[str] = None
    depth: Optional[float] = None      # độ sâu hồi thật ở nến vào (entry)

    @property
    def leg(self) -> float:
        return abs(self.h - self.x)

    def level(self, frac: float) -> float:
        """Mức hồi ``frac`` (0 = đầu nhịp H, 1 = gốc X)."""
        return self.h - frac * (self.h - self.x)

    def bounds(self, frac_lo: float, frac_hi: float) -> tuple[float, float]:
        """(mép dưới, mép trên) của vùng hồi [frac_lo, frac_hi]."""
        a, b = self.level(frac_lo), self.level(frac_hi)
        return min(a, b), max(a, b)

    def brief(self, frac_lo: float, frac_hi: float, anchor_key: str = "shift") -> dict[str, Any]:
        lo, hi = self.bounds(frac_lo, frac_hi)
        return {"chieu": self.direction, "x": self.x, "h": self.h, "nhip": self.leg, "vung_lo": lo, "vung_hi": hi,
                "diem_ngot": self.level((frac_lo + frac_hi) / 2.0), "nen_neo": self.anchor, anchor_key: self.anchor_id,
                "han_nen": self.deadline}


class OteTracker:
    def __init__(self, frac_lo: float = 0.62, frac_hi: float = 0.79, min_leg_atr: float = 2.0, expiry: int = 96,
                 anchor_key: str = "shift") -> None:
        if not 0.0 < frac_lo < frac_hi <= 1.0:
            raise ValueError("OTE: cần 0 < ote_tu < ote_den ≤ 1 (nhận %s, %s)" % (frac_lo, frac_hi))
        if min_leg_atr < 0 or expiry < 1:
            raise ValueError("OTE: ote_nhip_min_atr phải ≥ 0, ote_han phải ≥ 1")
        self.frac_lo, self.frac_hi = frac_lo, frac_hi
        self.min_leg_atr = min_leg_atr
        self.expiry = expiry
        self.anchor_key = anchor_key      # khoá của sự kiện neo trong brief: "shift" (0.5.0) | "mss" (0.10.0)
        self.reset()

    def reset(self) -> None:
        self.pending: Optional[OteLeg] = None
        self.counts = dict.fromkeys(END_TEXT_VI, 0)
        self.counts["nhip"] = 0
        self.depths: list[float] = []

    def zone(self, leg: OteLeg, atr: Optional[float]) -> Optional[tuple[float, float]]:
        """(mép dưới, mép trên) của vùng OTE nếu nhịp đủ lớn so với ``atr``; None nếu chưa (hoặc chưa có ATR khi có lọc)."""
        if leg.leg <= 0 or (self.min_leg_atr > 0 and (atr is None or leg.leg < self.min_leg_atr * atr)):
            return None
        return leg.bounds(self.frac_lo, self.frac_hi)

    def start(self, direction: str, x: float, h: float, d: int, anchor_id: str) -> Optional[OteLeg]:
        """Bước 6c: SHIFT ở d mở nhịp mới. Trả nhịp cũ đang chờ bị thay (``ended`` đã ghi) hoặc None."""
        old = self.pending
        if old is not None:
            self._end(old, "replaced" if old.direction == direction else "expired_shift")
        self.pending = OteLeg(direction, x, h, d, anchor_id, d + self.expiry)
        self.counts["nhip"] += 1
        return old

    def on_bar(self, bar: Bar, atr_prev: Optional[float]) -> Optional[OteLeg]:
        """Bước 3b của nến t: hỏng / vào / hết hạn của nhịp đang chờ (H, X của nến trước). Trả nhịp vừa kết thúc."""
        leg = self.pending
        if leg is None:
            return None
        up = leg.direction == "up"
        if (bar.low < leg.x) if up else (bar.high > leg.x):
            self._end(leg, "fail")
        else:
            near = leg.level(self.frac_lo)
            if ((bar.low <= near) if up else (bar.high >= near)) and self.zone(leg, atr_prev) is not None:
                leg.depth = ((leg.h - bar.low) if up else (bar.high - leg.h)) / leg.leg
                self.depths.append(leg.depth)
                self._end(leg, "entry")
            elif bar.index >= leg.deadline:
                self._end(leg, "expired_time")
            else:
                return None
        self.pending = None
        return leg

    def after_bar(self, bar: Bar) -> None:
        """Bước 12b: nhịp còn chờ → H theo cực trị của nến t (dùng từ nến t + 1)."""
        leg = self.pending
        if leg is not None:
            leg.h = max(leg.h, bar.high) if leg.direction == "up" else min(leg.h, bar.low)

    def _end(self, leg: OteLeg, kind: str) -> None:
        leg.ended = kind
        self.counts[kind] += 1
