"""Bộ nhận diện cấu trúc ICT phân tầng — giai đoạn 1 (``ict_structure`` v0.1.0).

Đặc tả: ``docs/algorithms/thuat_toan_ict_structure.md`` (lập từ ``docs/plans/plan_ict_structure.md``,
quyết định D1–D15 duyệt 04/10/2026). Giai đoạn 1 gồm:

* **[G]** lịch phiên khai báo + phân loại khoảng trống → ``ICT_GAP``;
* **[A]** ATR Wilder (seed theo close trước); giá trị của nến TRƯỚC làm ngưỡng cho nến hiện tại;
* **[P1]** STH/STL — pivot strict ``pivot_left``/``pivot_right`` (1/1), chặn cửa sổ vắt qua gap (D1);
* **[S1]** ITH/ITL (cấp 2), tuỳ chọn LTH/LTL (cấp 3);
* **[S2]** thứ tự đỉnh/đáy ``order`` + mức được bảo vệ + ``protected_broken`` (không phát sự kiện);
* **[S4]** dealing range, premium / discount.

Thứ tự trong một nến t (cố định, plan §3.1 phần thuộc giai đoạn 1):

1. kiểm nến; phân loại khoảng trống trước t → ``ICT_GAP``;
2. ATR[t−1] dùng cho mọi ngưỡng của nến t;
3. [S2] close[t] so với mức được bảo vệ đã biết **trước** t;
4. [S4] mở rộng dealing range theo high/low của t;
5. [P1] pivot xác nhận tại t → [S1] cấp 2 → cấp 3 → [S2] thứ tự/mức được bảo vệ và [S4] mốc mới
   theo swing cấp cấu trúc — có hiệu lực từ t+1 (không so close[t] với mức vừa biết ở t);
6. cập nhật ATR[t].

Không có BOS/CHoCH/MSS (B1); sweep, shift, FVG, khung lớn, DOL thuộc giai đoạn 2–3.
"""
from __future__ import annotations

import functools
import math
from datetime import timedelta
from typing import Any, Optional

from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.components.dealing_range import DealingRange
from core.components.hierarchy import HierarchyLevel
from core.components.session_gap import GAP_KINDS, GAP_TEXT_VI, GapClassifier
from core.components.structure_order import ORDER_TEXT_VI, StructureOrder
from core.components.swing_source import Pivot, PivotSource, with_event_id
from core.data.session_calendar import (
    CAL_AUTO,
    CAL_NONE,
    CUOI_TUAN,
    DEFAULT_FOR_SYMBOL,
    NGHI_LE,
    NGHI_PHIEN,
    THIEU_TRONG_PHIEN,
    SessionCalendar,
)
from core.indicators import WilderATRPrevClose
from core.types import TIMEFRAME_SECONDS, Bar, ReasonCode, StructureEvent, StructureType

SPEC = "docs/algorithms/thuat_toan_ict_structure.md"
CALENDARS = (CAL_AUTO,) + tuple(sorted(set(DEFAULT_FOR_SYMBOL.values()))) + (CAL_NONE,)
GAP_BLOCK = "giu_muc_chan_cua_so"
GAP_NO_BLOCK = "giu_muc_khong_chan"

_TYPES = {
    (1, "high"): (StructureType.SWING_HIGH, ReasonCode.PIVOT_HIGH_STRICT, "STH"),
    (1, "low"): (StructureType.SWING_LOW, ReasonCode.PIVOT_LOW_STRICT, "STL"),
    (2, "high"): (StructureType.SWING_HIGH_L2, ReasonCode.PIVOT_HIGH_L2, "ITH"),
    (2, "low"): (StructureType.SWING_LOW_L2, ReasonCode.PIVOT_LOW_L2, "ITL"),
    (3, "high"): (StructureType.SWING_HIGH_L3, ReasonCode.PIVOT_HIGH_L3, "LTH"),
    (3, "low"): (StructureType.SWING_LOW_L3, ReasonCode.PIVOT_LOW_L3, "LTL"),
}
_GAP_REASON = {
    NGHI_PHIEN: ReasonCode.GAP_NGHI_PHIEN,
    CUOI_TUAN: ReasonCode.GAP_CUOI_TUAN,
    NGHI_LE: ReasonCode.GAP_NGHI_LE,
    THIEU_TRONG_PHIEN: ReasonCode.GAP_THIEU_TRONG_PHIEN,
    "ngoai_lich": ReasonCode.GAP_NGOAI_LICH,
    "khong_ro_lich": ReasonCode.GAP_KHONG_RO_LICH,
    "lech_buoc": ReasonCode.GAP_THIEU_TRONG_PHIEN,
}
MAX_ABNORMAL_LISTED = 50


@functools.lru_cache(maxsize=8)
def _calendar(name: str) -> SessionCalendar:
    return SessionCalendar.load(name)


class IctStructureAlgorithm(StructureAlgorithm):
    name = "ict_structure"
    display_name_vi = "Cấu trúc ICT phân tầng (giai đoạn 1)"
    version = "0.1.0"
    emits_types = (
        StructureType.SWING_HIGH, StructureType.SWING_LOW,
        StructureType.SWING_HIGH_L2, StructureType.SWING_LOW_L2,
        StructureType.SWING_HIGH_L3, StructureType.SWING_LOW_L3,
        StructureType.ICT_GAP,
    )
    description_vi = (
        "Giai đoạn 1 của bộ nhận diện ICT: STH/STL (pivot 1/1) → ITH/ITL (cấp 2) → thứ tự đỉnh/đáy, "
        "mức được bảo vệ, dealing range; khoảng trống phân loại theo lịch phiên khai báo. Không có "
        "BOS/CHoCH. Sweep, shift, FVG, khung lớn ở giai đoạn sau."
    )

    @classmethod
    def param_specs(cls) -> tuple[ParamSpec, ...]:
        return (
            ParamSpec("timeframe", "Khung của dataset", "choice", "M15", choices=tuple(TIMEFRAME_SECONDS),
                      help_vi="Tự điền theo dataset; dùng để biết bước nến khi phân loại khoảng trống."),
            ParamSpec("session_calendar", "Lịch phiên", "choice", CAL_AUTO, choices=CALENDARS,
                      help_vi=(
                          "auto = theo mã của dataset (XAUUSD → cme_globex_metals, EURUSD → fx_spot); run lưu "
                          "tên lịch cụ thể. none = không phân biệt nghỉ phiên với thiếu dữ liệu."
                      )),
            ParamSpec("pivot_left", "Số nến trái (STH/STL)", "int", 1, min=1, max=10, step=1,
                      help_vi="Pivot strict: high lớn hơn mọi high trong cửa sổ. Mặc định 1/1 (plan §4.1)."),
            ParamSpec("pivot_right", "Số nến phải (STH/STL)", "int", 1, min=1, max=10, step=1,
                      help_vi="Pivot chỉ biết khi nến thứ «phải» sau nó đóng."),
            ParamSpec("structure_level", "Cấp cấu trúc", "int", 2, min=1, max=3, step=1,
                      help_vi=(
                          "Cấp swing dùng cho thứ tự đỉnh/đáy, mức được bảo vệ, dealing range: 1 = STH/STL, "
                          "2 = ITH/ITL (mặc định, D2), 3 = LTH/LTL (trễ trung vị ~23 nến M15)."
                      )),
            ParamSpec("atr_period", "Chu kỳ ATR (Wilder)", "int", 14, min=2, max=500, step=1,
                      help_vi="ATR seed = trung bình period TR đầu có close trước."),
            ParamSpec("eq_tol_atr", "Dung sai bằng giá (× ATR)", "float", 0.1, min=0.0, max=5.0, step=0.05,
                      help_vi="Hai đỉnh (đáy) cấu trúc chênh trong dung sai → EQH/EQL (so sánh = 0). Do lab chọn."),
            ParamSpec("gap_policy", "Chính sách khoảng trống", "choice", GAP_BLOCK,
                      choices=(GAP_BLOCK, GAP_NO_BLOCK),
                      help_vi=(
                          "Giữ mức qua mọi khoảng trống; chặn cửa sổ pivot vắt qua khoảng trống (D1). "
                          "«không chặn» chỉ để đối chiếu với swing_pivot / swing_hierarchy."
                      )),
        )

    @classmethod
    def check_dataset(cls, timeframe: str, params: dict[str, Any]) -> None:
        if (timeframe or "").upper() != params.get("timeframe"):
            raise ValueError(
                "ict_structure: tham số timeframe=%s không khớp dataset %s. Chọn lại khung trong form "
                "(dùng để phân loại khoảng trống)." % (params.get("timeframe"), timeframe)
            )

    @classmethod
    def manifest_info(cls, params: dict[str, Any]) -> dict[str, Any]:
        cal = params.get("session_calendar") or CAL_AUTO
        cal_info: dict[str, Any] = {"ten": cal}
        if cal not in (CAL_AUTO, CAL_NONE):
            meta = _calendar(cal).meta
            cal_info.update({k: meta.get(k) for k in ("nguon", "nguon_ngoai_le", "timezone", "so_phien", "created")})
        return {
            "spec": SPEC,
            "giai_doan": "1 — [G] lịch phiên/khoảng trống, [P1] STH/STL, [S1] ITH/ITL (cấp 3 tuỳ chọn), "
                         "[S2] thứ tự + mức được bảo vệ, [S4] dealing range",
            "lich_phien": cal_info,
            "chinh_sach_khoang_trong": params.get("gap_policy"),
            "atr": "Wilder, seed SMA của period TR đầu có close trước (WilderATRPrevClose); ngưỡng ở nến t dùng ATR[t-1]",
            "khong_co": "BOS/CHoCH/MSS (quyết định B1 — đổi hướng chỉ đến từ shift ở giai đoạn 2)",
        }

    def __init__(self, **params: Any) -> None:
        p = self.validate_params(params)
        self.params = p
        self.left = p["pivot_left"]
        self.right = p["pivot_right"]
        self.structure_level = p["structure_level"]
        self.step = timedelta(seconds=TIMEFRAME_SECONDS[p["timeframe"]])
        cal = p["session_calendar"]
        self.calendar_name = cal
        self.calendar: Optional[SessionCalendar] = None if cal in (CAL_AUTO, CAL_NONE) else _calendar(cal)
        self.reset()

    def reset(self) -> None:
        self._prev: Optional[Bar] = None
        self._atr = WilderATRPrevClose(self.params["atr_period"])
        self._gaps = GapClassifier(self.step, self.calendar)
        self._pivots = PivotSource(self.left, self.right, block_gaps=self.params["gap_policy"] == GAP_BLOCK)
        self._l2 = HierarchyLevel(2)
        self._l3 = HierarchyLevel(3) if self.structure_level >= 3 else None
        self._order = StructureOrder(self.params["eq_tol_atr"])
        self._range = DealingRange()
        self._highs: list[float] = []
        self._lows: list[float] = []
        self._gap_now: Optional[dict[str, Any]] = None
        self._emitted: set[str] = set()
        # thống kê theo nến (đọc ở run_stats / pending_state)
        self._n = 0
        self._days: set[Any] = set()
        self._outside = 0
        self._gap_count = dict.fromkeys(GAP_KINDS, 0)
        self._abnormal: list[dict[str, Any]] = []
        self._order_bars = {"1": 0, "-1": 0, "0": 0, "none": 0}
        self._protected_bars = 0
        self._broken_bars = 0

    def warmup_bars(self) -> int:
        return self.left + self.right + 1

    # ------------------------------------------------------------------ on_bar

    def _validate(self, bar: Bar) -> None:
        vals = (bar.open, bar.high, bar.low, bar.close)
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals):
            raise ValueError("Nến #%d có giá không hữu hạn (NaN/inf)." % bar.index)
        if not bar.is_valid_ohlc():
            raise ValueError("Nến #%d vi phạm quan hệ OHLC (low ≤ open/close ≤ high)." % bar.index)
        span = (bar.close_time - bar.bar_time).total_seconds()
        if span not in (0, self.step.total_seconds()):
            raise ValueError("Nến #%d không phải khung %s (bar_time→close_time = %ds)."
                             % (bar.index, self.params["timeframe"], span))
        prev = self._prev
        if prev is not None:
            if bar.index <= prev.index:
                raise ValueError("Nến phải nạp theo index tăng dần: nhận #%d sau #%d." % (bar.index, prev.index))
            if bar.bar_time <= prev.bar_time:
                raise ValueError("Timestamp trùng hoặc lùi tại nến #%d (%s ≤ %s). Không tự sắp lại."
                                 % (bar.index, bar.bar_time.isoformat(), prev.bar_time.isoformat()))

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        self._validate(bar)
        out: list[StructureEvent] = []
        prev = self._prev
        # 1. khoảng trống trước nến này
        gap = self._gaps.classify(prev, bar) if prev is not None else None
        self._gap_now = gap
        if gap is not None:
            self._gap_count[gap["loai"]] += 1
            if gap["bat_thuong"] and len(self._abnormal) < MAX_ABNORMAL_LISTED:
                self._abnormal.append({"nen": bar.index, "tu": gap["tu"], "den": gap["den"],
                                       "loai": gap["loai"], "so_o_trong_phien": gap["so_o_trong_phien"]})
            out.append(self._gap_event(bar, prev, gap))
        # 2. ngưỡng của nến t dùng ATR[t-1]
        atr_prev = self._atr.value
        # 3. close[t] so với mức được bảo vệ đã biết trước t
        self._order.check_close(bar)
        # 4. dealing range gồm cả nến t
        self._range.on_bar(bar)
        self._highs.append(bar.high)
        self._lows.append(bar.low)
        # 5. swing xác nhận tại t
        for p in self._pivots.update(bar, gap_before=gap is not None):
            out.extend(self._on_swing(p, atr_prev))
        # 6. ATR[t]
        self._atr.update(bar.high, bar.low, bar.close)
        self._prev = bar
        self._count_bar(bar)
        return out

    def _on_swing(self, p: Pivot, atr_prev: Optional[float]) -> list[StructureEvent]:
        stype, reason, short = _TYPES[(p.level, p.side)]
        is_high = p.side == "high"
        details: dict[str, Any] = {"cap": p.level, "ten": short}
        if p.level == 1:
            details.update({
                "trai": self.left, "phai": self.right,
                "quy_tac": ("high[pivot] > mọi high trong cửa sổ" if is_high else "low[pivot] < mọi low trong cửa sổ"),
                "chan_cua_so_qua_gap": self.params["gap_policy"] == GAP_BLOCK,
            })
        else:
            left, mid, right = p.members
            details.update({
                "basis": [left.event_id, mid.event_id, right.event_id],
                "gia_trai": left.price, "gia_giua": mid.price, "gia_phai": right.price,
                "nen_trai": left.bar_index, "nen_giua": mid.bar_index, "nen_phai": right.bar_index,
                "quy_tac": (
                    "đỉnh cấp %d ở giữa > hai đỉnh cấp %d liền trước và liền sau" % (p.level - 1, p.level - 1)
                    if is_high else
                    "đáy cấp %d ở giữa < hai đáy cấp %d liền trước và liền sau" % (p.level - 1, p.level - 1)
                ),
                "xac_nhan_khi": "swing cấp %d bên phải vừa xác nhận" % (p.level - 1),
            })
        if p.level == self.structure_level:
            details["cap_cau_truc"] = True
            details.update(self._order.on_swing(p, atr_prev))
            seq = self._highs if is_high else self._lows
            extreme = max(seq[p.pos:]) if is_high else min(seq[p.pos:])
            self._range.on_swing(p, extreme)
        ev = self._event(stype, p.price, p.bar, p.confirmed_bar, reason, "up" if is_high else "down",
                         reference=(p.members[1].event_id if p.members else None), details=details)
        p = with_event_id(p, ev.event_id)
        out = [ev]
        nxt = None
        if p.level == 1:
            nxt = self._l2.update(p)
        elif p.level == 2 and self._l3 is not None:
            nxt = self._l3.update(p)
        if nxt is not None:
            out.extend(self._on_swing(nxt, atr_prev))
        return out

    def _gap_event(self, bar: Bar, prev: Bar, gap: dict[str, Any]) -> StructureEvent:
        details = dict(gap)
        details.update({
            "nen_truoc": prev.index,
            "lich_phien": self.calendar_name,
            "chinh_sach": (
                "giữ mức swing/vùng; chặn cửa sổ pivot vắt qua khoảng trống"
                if self.params["gap_policy"] == GAP_BLOCK else "giữ mức; không chặn cửa sổ (chỉ để đối chiếu)"
            ),
        })
        return self._event(StructureType.ICT_GAP, bar.open, bar, bar, _GAP_REASON[gap["loai"]], None,
                           details=details)

    def _event(self, stype: str, price: float, event_bar: Bar, confirming: Bar, reason: str,
               direction: Optional[str], reference: Optional[str] = None,
               details: Optional[dict[str, Any]] = None) -> StructureEvent:
        if stype == StructureType.ICT_GAP:
            event_id = "ict:%s@%d" % (stype, event_bar.index)
        else:
            event_id = "ict:%s@%d>%d" % (stype, event_bar.index, confirming.index)
        if event_id in self._emitted:  # pragma: no cover - phòng vệ
            raise RuntimeError("Trùng event_id: %s" % event_id)
        self._emitted.add(event_id)
        return StructureEvent(
            event_id=event_id, structure_type=stype, price=float(price),
            event_bar_index=event_bar.index, event_time=event_bar.bar_time, event_close_time=event_bar.close_time,
            confirmed_bar_index=confirming.index, confirmed_at=confirming.close_time,
            algorithm=self.name, algorithm_version=self.version, reason_code=reason, direction=direction,
            reference_event_id=reference, details=details or {},
        )

    def _count_bar(self, bar: Bar) -> None:
        self._n += 1
        if self.calendar is not None:
            s = self.calendar.session_at(bar.bar_time)
            if s is None:
                self._outside += 1
            else:
                self._days.add(s.trading_day)
        else:
            self._days.add(bar.bar_time.date())
        o = self._order
        self._order_bars["none" if o.order is None else str(o.order)] += 1
        if o.protected is not None:
            self._protected_bars += 1
            if o.broken:
                self._broken_bars += 1

    # ------------------------------------------------------------------ hiển thị

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        o = self._order
        r = self._range.snapshot(bar.close)
        p = o.protected
        return {
            "order": o.order,
            "protected": p.price if p else None,
            "protected_side": p.side if p else None,
            "protected_id": ("%s%d" % (p.side[0], p.bar_index)) if p else None,
            "protected_broken": o.broken if p else None,
            "dealing_hi": r["hi"],
            "dealing_lo": r["lo"],
            "dealing_eq": r["eq"],
            "dealing_id": r["id"],
            "zone": r["zone"],
            "range_pos": r["range_pos"],
            "atr": self._atr.value,
            "gap": self._gap_now["loai"] if self._gap_now else None,
        }

    def pending_state(self) -> dict[str, Any]:
        last_close = self._prev.close if self._prev is not None else None
        return {
            "ict": True,
            "giai_doan": 1,
            "lich_phien": self.calendar_name,
            "cap_cau_truc": self.structure_level,
            "atr_hien_tai": self._atr.value,
            "cau_truc": self._order.snapshot(),
            "dealing_range": self._range.snapshot(last_close) if last_close is not None else None,
            "pivot": self._pivots.snapshot(),
            "cap2": self._l2.snapshot(),
            "cap3": self._l3.snapshot() if self._l3 else None,
            "khoang_trong": {k: v for k, v in self._gap_count.items() if v},
            "khoang_trong_truoc_nen_nay": self._gap_now,
            "so_nen": self._n,
            "ghi_chu_vi": (
                "Thứ tự chỉ đổi khi có swing cấu trúc mới; close vượt mức được bảo vệ chỉ bật cờ, "
                "không phát sự kiện (không có BOS/CHoCH)."
            ),
        }

    def run_stats(self, events: list[StructureEvent]) -> Optional[dict[str, Any]]:
        by_type: dict[str, int] = {}
        for e in events:
            by_type[e.structure_type] = by_type.get(e.structure_type, 0) + 1
        n_days = len(self._days)

        def per_day(n: int) -> Optional[float]:
            return (n / n_days) if n_days else None

        levels = {}
        for (lvl, side), (stype, _r, short) in _TYPES.items():
            levels[short] = {"so": by_type.get(stype, 0), "moi_ngay": per_day(by_type.get(stype, 0)), "cap": lvl}
        n = self._n or 1
        return {
            "giai_doan": 1,
            "lich_phien": self.calendar_name,
            "cap_cau_truc": self.structure_level,
            "so_nen": self._n,
            "so_ngay_giao_dich": n_days,
            "ngay_tinh_theo": "lịch phiên (ngày giao dịch)" if self.calendar is not None else "ngày UTC của nến",
            "nen_ngoai_phien": self._outside,
            "swing": levels,
            "ty_le_thoi_gian_order": {k: v / n for k, v in self._order_bars.items()},
            # Trạng thái SAU mỗi nến (như timeline). Survey-v2 đếm trước khi áp swing xác nhận ở nến đó
            # → cao hơn ~1 điểm %; cùng logic (xem đặc tả §9).
            "ty_le_muc_bao_ve_bi_vuot_tren_tong_nen": (self._broken_bars / self._n) if self._n else None,
            "ty_le_muc_bao_ve_bi_vuot_khi_co_muc": (
                (self._broken_bars / self._protected_bars) if self._protected_bars else None),
            "so_nen_co_muc_bao_ve": self._protected_bars,
            "khoang_trong": dict(self._gap_count),
            "khoang_trong_bat_thuong": list(self._abnormal),
            "pivot_bi_chan_vi_gap": dict(self._pivots.blocked),
            "ghi_chu_vi": (
                "Mật độ tính trên ngày giao dịch. «order» lẫn lộn là trạng thái hợp lệ (range hoặc chuyển "
                "tiếp), không phải lỗi. Đây là mô tả hành vi, không phải accuracy — cần nhãn tham chiếu (D8)."
            ),
            "loai_khoang_trong_vi": GAP_TEXT_VI,
            "order_vi": {str(k) if k is not None else "none": v for k, v in ORDER_TEXT_VI.items()},
        }
