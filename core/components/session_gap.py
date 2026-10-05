"""[G] Phân loại khoảng trống giữa hai nến liên tiếp theo lịch phiên KHAI BÁO.

Khoảng trống = ``bar_time`` của nến sau − nến trước khác đúng một bước khung. Loại:

* ``nghi_phien`` / ``cuoi_tuan`` / ``nghi_le`` — mọi ô thiếu nằm ngoài phiên theo lịch;
* ``thieu_trong_phien`` — có ô thiếu nằm TRONG phiên: thiếu dữ liệu, **bất thường**;
* ``ngoai_lich`` — khoảng trống nằm ngoài phạm vi lịch (không phân loại được);
* ``khong_ro_lich`` — không chọn lịch phiên;
* ``lech_buoc`` — khoảng cách không phải bội số của bước khung (dữ liệu sai mốc), bất thường.

Lịch không được suy từ dữ liệu (AGENTS.md §2.2); gap bất thường không được gộp thành Range /
Uncertain — chỉ phân loại và ghi lại.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from core.data.session_calendar import (
    CUOI_TUAN,
    NGHI_LE,
    NGHI_PHIEN,
    THIEU_TRONG_PHIEN,
    SessionCalendar,
)
from core.types import Bar

NGOAI_LICH = "ngoai_lich"
KHONG_RO_LICH = "khong_ro_lich"
LECH_BUOC = "lech_buoc"
GAP_KINDS = (NGHI_PHIEN, CUOI_TUAN, NGHI_LE, THIEU_TRONG_PHIEN, NGOAI_LICH, KHONG_RO_LICH, LECH_BUOC)
ABNORMAL = frozenset({THIEU_TRONG_PHIEN, LECH_BUOC})
GAP_TEXT_VI = {
    NGHI_PHIEN: "nghỉ hằng ngày",
    CUOI_TUAN: "cuối tuần",
    NGHI_LE: "nghỉ lễ",
    THIEU_TRONG_PHIEN: "thiếu dữ liệu trong phiên",
    NGOAI_LICH: "ngoài phạm vi lịch",
    KHONG_RO_LICH: "chưa chọn lịch",
    LECH_BUOC: "lệch bước khung",
}


class GapClassifier:
    """Phân loại khoảng trống trước mỗi nến. ``calendar`` = None → mọi gap là ``khong_ro_lich``."""

    def __init__(self, step: timedelta, calendar: Optional[SessionCalendar]) -> None:
        self.step = step
        self.calendar = calendar

    def classify(self, prev: Bar, bar: Bar) -> Optional[dict[str, Any]]:
        """None nếu hai nến liền nhau; ngược lại mô tả khoảng trống ``[prev + bước, bar)``."""
        gap = bar.bar_time - prev.bar_time
        if gap == self.step:
            return None
        first_missing = prev.bar_time + self.step
        step_s = self.step.total_seconds()
        n_slots = int(round(gap.total_seconds() / step_s)) - 1
        out: dict[str, Any] = {
            "tu": first_missing.isoformat(),
            "den": bar.bar_time.isoformat(),
            "khoang_cach_phut": gap.total_seconds() / 60.0,
            "so_o_thieu": n_slots,
            "so_o_trong_phien": None,
        }
        if gap.total_seconds() % step_s:
            kind = LECH_BUOC
        elif self.calendar is None:
            kind = KHONG_RO_LICH
        elif not (self.calendar.covers(first_missing) and self.calendar.covers(bar.bar_time - self.step)):
            kind = NGOAI_LICH
        else:
            kind, n_in = self.calendar.classify_gap(first_missing, bar.bar_time, self.step)
            out["so_o_trong_phien"] = n_in
        out["loai"] = kind
        out["loai_vi"] = GAP_TEXT_VI[kind]
        out["bat_thuong"] = kind in ABNORMAL
        return out
