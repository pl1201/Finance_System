"""Thuật toán Swing Pivot + HH/HL/LH/LL + BOS / CHoCH.

Đặc tả đầy đủ: ``docs/thuat_toan_swing_pivot.md``.
Tóm tắt quy tắc (phiên bản 1.1.0):

**1. Pivot**

Với cửa sổ ``left`` nến trái và ``right`` nến phải, nến tại chỉ số ``c`` là
swing high khi và chỉ khi::

    high[c] > high[j]  với mọi j thuộc [c-left, c-1] và [c+1, c+right]

So sánh là LỚN HƠN TUYỆT ĐỐI. Nếu có bất kỳ nến nào trong cửa sổ bằng
``high[c]`` thì KHÔNG nhận pivot (quy ước phiên bản đầu). Swing low đối xứng
với ``low[c] < low[j]``.

Pivot chỉ được xác nhận khi nến bên phải CUỐI CÙNG đã đóng, tức tại nến
``i = c + right``. Do đó::

    event_bar_index     = c
    confirmed_bar_index = c + right
    confirmation_lag_bars = right

**2. Nhãn HH/LH/EQH và HL/LL/EQL**

So sánh swing high vừa xác nhận với swing high ĐÃ XÁC NHẬN liền trước:

* ``price > prev + tol``  -> ``HH``
* ``price < prev - tol``  -> ``LH``
* còn lại (bằng nhau trong dung sai) -> ``EQH`` (nhãn riêng, không ép về HH/LH)

Swing low đối xứng: ``HL`` / ``LL`` / ``EQL``. Swing đầu tiên của mỗi phía
không có mốc so sánh nên không sinh nhãn.

**3. Phá vỡ theo close (phát hiện như v1.0.0, phân loại ở 1.1.0)**

* Chiều LÊN: ``close[i] > level_high + buffer`` với ``level_high`` là swing
  high ĐÃ XÁC NHẬN, CHƯA BỊ PHÁ, có chỉ số xác nhận lớn nhất (mức active).
* Chiều XUỐNG: ``close[i] < level_low - buffer`` (đối xứng).
* Chống phát lặp: khi phá lên tại giá ``p``, MỌI mức swing high chưa bị phá
  thoả ``p > level + buffer`` đều được đánh dấu ĐÃ PHÁ, nhưng chỉ phát ra
  ĐÚNG MỘT sự kiện tham chiếu tới mức mới nhất.
* Phân loại 1.1.0 (khi ``enable_choch``): BOS chính / BOS nội bộ / CHoCH
  dựa trên bias HH+HL hoặc LH+LL và mức cực trị chưa bị phá. Khi
  ``bias is none`` hoặc ``enable_choch=false`` → ``BOS_UP``/``BOS_DOWN``.

**4. Thứ tự xử lý trong cùng một nến ``i``**

::

    A. Xác nhận pivot tại c = i - right (nếu đủ điều kiện)
    B. Sinh nhãn HH/LH/EQH hoặc HL/LL/EQL cho pivot vừa xác nhận
    C. Đăng ký mức giá của pivot vào danh sách mức đang hoạt động
    D. Kiểm tra phá vỡ bằng close[i] trên các mức đang hoạt động
       (phân loại theo bias snapshot đầu bước D)

Thứ tự A→D và D→A cho kết quả GIỐNG NHAU ở bước phát hiện pivot-vs-BOS.
Chứng minh v1.0.0 vẫn đúng: nến vừa xác nhận swing high không phá chính
swing đó. CHoCH/BOS nội bộ chỉ là nhãn của cùng phép so close.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Any, Optional

from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.types import Bar, ReasonCode, StructureEvent, StructureType


@dataclass
class _Level:
    """Một mức swing đã xác nhận, dùng cho kiểm tra BOS."""

    event_id: str
    price: float
    bar_index: int
    confirmed_index: int
    broken: bool = False


class SwingPivotAlgorithm(StructureAlgorithm):
    name = "swing_pivot"
    display_name_vi = "Swing Pivot + HH/HL/LH/LL + BOS/CHoCH"
    version = "1.1.0"
    emits_types = (
        StructureType.SWING_HIGH, StructureType.SWING_LOW,
        StructureType.HH, StructureType.LH, StructureType.EQH,
        StructureType.HL, StructureType.LL, StructureType.EQL,
        StructureType.BOS_UP, StructureType.BOS_DOWN,
        StructureType.BOS_INTERNAL_UP, StructureType.BOS_INTERNAL_DOWN,
        StructureType.CHOCH_UP, StructureType.CHOCH_DOWN,
    )
    description_vi = (
        "Nhận diện đỉnh/đáy swing bằng cửa sổ trái/phải, gắn nhãn "
        "HH/LH/EQH và HL/LL/EQL, phát hiện phá vỡ theo close, và phân loại "
        "BOS chính / BOS nội bộ / CHoCH khi đã có bias HH+HL hoặc LH+LL."
    )

    @classmethod
    def param_specs(cls) -> tuple[ParamSpec, ...]:
        return (
            ParamSpec(
                name="left",
                label_vi="Số nến bên trái",
                type="int",
                default=3,
                min=1,
                max=50,
                step=1,
                help_vi=(
                    "Số nến phía trước nến pivot phải có high thấp hơn "
                    "(hoặc low cao hơn) nến pivot."
                ),
            ),
            ParamSpec(
                name="right",
                label_vi="Số nến bên phải",
                type="int",
                default=3,
                min=1,
                max=50,
                step=1,
                help_vi=(
                    "Số nến phía sau nến pivot. Pivot chỉ được xác nhận khi "
                    "nến bên phải cuối cùng đã đóng, nên đây cũng chính là "
                    "độ trễ xác nhận tính bằng nến."
                ),
            ),
            ParamSpec(
                name="label_eq_tolerance",
                label_vi="Dung sai 'bằng giá' (đơn vị giá)",
                type="float",
                default=0.0,
                min=0.0,
                step=0.01,
                help_vi=(
                    "Hai swing cùng phía chênh nhau không quá giá trị này thì "
                    "gắn nhãn EQH/EQL. Mặc định 0.0 nghĩa là phải bằng tuyệt đối."
                ),
            ),
            ParamSpec(
                name="bos_buffer",
                label_vi="Biên phá vỡ BOS (đơn vị giá)",
                type="float",
                default=0.0,
                min=0.0,
                step=0.01,
                help_vi=(
                    "Giá đóng cửa phải vượt mức swing thêm ít nhất giá trị này "
                    "mới tính là phá vỡ. Đặt 0.0 để dùng quy tắc vượt thuần tuý."
                ),
            ),
            ParamSpec(
                name="enable_bos",
                label_vi="Bật phát hiện phá vỡ (BOS/CHoCH)",
                type="bool",
                default=True,
                help_vi="Tắt để chỉ xem pivot và nhãn HH/HL/LH/LL.",
            ),
            ParamSpec(
                name="enable_choch",
                label_vi="Phân loại CHoCH và BOS nội bộ",
                type="bool",
                default=True,
                help_vi=(
                    "Bật: phá vỡ được gắn BOS chính, BOS nội bộ hoặc CHoCH "
                    "tuỳ bias. Tắt: mọi phá vỡ đều là BOS_UP/BOS_DOWN như v1.0.0."
                ),
            ),
        )

    def __init__(self, **params: Any) -> None:
        p = self.validate_params(params)
        self.left: int = p["left"]
        self.right: int = p["right"]
        self.label_eq_tolerance: float = p["label_eq_tolerance"]
        self.bos_buffer: float = p["bos_buffer"]
        self.enable_bos: bool = p["enable_bos"]
        self.enable_choch: bool = p["enable_choch"]
        self.params: dict[str, Any] = p
        self.reset()

    # ------------------------------------------------------------------
    # Vòng đời
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self._bars: list[Bar] = []
        self._high_levels: list[_Level] = []
        self._low_levels: list[_Level] = []
        self._last_swing_high: Optional[StructureEvent] = None
        self._last_swing_low: Optional[StructureEvent] = None
        self._last_high_label: Optional[str] = None
        self._last_low_label: Optional[str] = None
        self._last_hh_id: Optional[str] = None
        self._last_hl_id: Optional[str] = None
        self._last_lh_id: Optional[str] = None
        self._last_ll_id: Optional[str] = None
        self._bias: str = "none"  # none | bullish | bearish
        self._emitted_ids: set[str] = set()
        # Chỉ mục cho mức swing (thay quét tuyến tính toàn bộ danh sách — kết quả giống hệt):
        # theo event_id; mức CHƯA bị phá theo thứ tự xác nhận; mức chưa phá xếp theo giá.
        self._high_by_id: dict[str, _Level] = {}
        self._low_by_id: dict[str, _Level] = {}
        self._high_unbroken: dict[str, _Level] = {}
        self._low_unbroken: dict[str, _Level] = {}
        self._high_by_price: list[tuple[float, int, str]] = []
        self._low_by_price: list[tuple[float, int, str]] = []
        self._level_seq: int = 0

    def warmup_bars(self) -> int:
        """Cần ``left + right + 1`` nến mới có thể xác nhận pivot đầu tiên."""
        return self.left + self.right + 1

    # ------------------------------------------------------------------
    # Xử lý từng nến
    # ------------------------------------------------------------------

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        if self._bars and bar.index <= self._bars[-1].index:
            raise ValueError(
                "Nến phải được nạp theo thứ tự tăng dần: nhận index=%s sau index=%s"
                % (bar.index, self._bars[-1].index)
            )
        self._bars.append(bar)
        events: list[StructureEvent] = []

        # --- Bước A + B + C: xác nhận pivot, gắn nhãn, đăng ký mức ---
        events.extend(self._confirm_pivot(bar))

        # --- Bước D: kiểm tra BOS bằng close của nến hiện tại ---
        if self.enable_bos:
            events.extend(self._check_bos(bar))

        return events

    # ------------------------------------------------------------------

    def _confirm_pivot(self, bar: Bar) -> list[StructureEvent]:
        """Xác nhận pivot tại c = i - right khi nến phải cuối cùng đã đóng."""
        i = len(self._bars) - 1  # vị trí trong bộ đệm nội bộ
        c = i - self.right
        if c < self.left:
            return []  # chưa đủ warm-up

        window_left = self._bars[c - self.left : c]
        window_right = self._bars[c + 1 : c + 1 + self.right]
        pivot = self._bars[c]
        events: list[StructureEvent] = []

        is_high = all(b.high < pivot.high for b in window_left) and all(
            b.high < pivot.high for b in window_right
        )
        is_low = all(b.low > pivot.low for b in window_left) and all(
            b.low > pivot.low for b in window_right
        )

        if is_high:
            events.extend(self._emit_swing(pivot, bar, side="high"))
        if is_low:
            events.extend(self._emit_swing(pivot, bar, side="low"))
        return events

    def _emit_swing(self, pivot: Bar, confirming: Bar, side: str) -> list[StructureEvent]:
        is_high = side == "high"
        price = pivot.high if is_high else pivot.low
        stype = StructureType.SWING_HIGH if is_high else StructureType.SWING_LOW
        reason = (
            ReasonCode.PIVOT_HIGH_STRICT if is_high else ReasonCode.PIVOT_LOW_STRICT
        )

        swing = self._make_event(
            structure_type=stype,
            price=price,
            event_bar=pivot,
            confirming_bar=confirming,
            reason_code=reason,
            direction="up" if is_high else "down",
            details={
                "left": self.left,
                "right": self.right,
                "quy_tac": (
                    "high[pivot] > mọi high trong cửa sổ"
                    if is_high
                    else "low[pivot] < mọi low trong cửa sổ"
                ),
            },
        )
        out = [swing]

        prev = self._last_swing_high if is_high else self._last_swing_low
        if prev is not None:
            label, reason_code = self._compare_swing(prev.price, price, is_high)
            out.append(
                self._make_event(
                    structure_type=label,
                    price=price,
                    event_bar=pivot,
                    confirming_bar=confirming,
                    reason_code=reason_code,
                    direction="up" if is_high else "down",
                    reference_event_id=prev.event_id,
                    details={
                        "gia_swing_truoc": prev.price,
                        "gia_swing_nay": price,
                        "chenh_lech": round(price - prev.price, 10),
                        "dung_sai_bang_gia": self.label_eq_tolerance,
                    },
                )
            )
            if is_high:
                self._last_high_label = label
                if label == StructureType.HH:
                    self._last_hh_id = swing.event_id
                elif label == StructureType.LH:
                    self._last_lh_id = swing.event_id
            else:
                self._last_low_label = label
                if label == StructureType.HL:
                    self._last_hl_id = swing.event_id
                elif label == StructureType.LL:
                    self._last_ll_id = swing.event_id
            self._refresh_bias_from_labels()

        level = _Level(swing.event_id, price, pivot.index, confirming.index)
        self._level_seq += 1
        key = (price, self._level_seq, level.event_id)
        if is_high:
            self._last_swing_high = swing
            self._high_levels.append(level)
            self._high_by_id[level.event_id] = level
            self._high_unbroken[level.event_id] = level
            bisect.insort(self._high_by_price, key)
        else:
            self._last_swing_low = swing
            self._low_levels.append(level)
            self._low_by_id[level.event_id] = level
            self._low_unbroken[level.event_id] = level
            bisect.insort(self._low_by_price, key)
        return out

    def _compare_swing(self, prev: float, cur: float, is_high: bool) -> tuple[str, str]:
        tol = self.label_eq_tolerance
        if cur > prev + tol:
            return (
                (StructureType.HH, ReasonCode.SEQ_HIGHER_HIGH)
                if is_high
                else (StructureType.HL, ReasonCode.SEQ_HIGHER_LOW)
            )
        if cur < prev - tol:
            return (
                (StructureType.LH, ReasonCode.SEQ_LOWER_HIGH)
                if is_high
                else (StructureType.LL, ReasonCode.SEQ_LOWER_LOW)
            )
        return (
            (StructureType.EQH, ReasonCode.SEQ_EQUAL_HIGH)
            if is_high
            else (StructureType.EQL, ReasonCode.SEQ_EQUAL_LOW)
        )

    # ------------------------------------------------------------------

    def _refresh_bias_from_labels(self) -> None:
        """Cập nhật bias khi cả hai phía đã có nhãn (không phải EQH/EQL)."""
        hi = self._last_high_label
        lo = self._last_low_label
        if hi is None or lo is None:
            return
        if hi in (StructureType.EQH,) or lo in (StructureType.EQL,):
            return
        if hi == StructureType.HH and lo == StructureType.HL:
            self._bias = "bullish"
        elif hi == StructureType.LH and lo == StructureType.LL:
            self._bias = "bearish"
        elif hi == StructureType.HH and lo == StructureType.LL:
            self._bias = "none"
        # LH+HL: đỉnh/đáy hồi — giữ bias hiện tại.

    def _check_bos(self, bar: Bar) -> list[StructureEvent]:
        events: list[StructureEvent] = []
        bias_snapshot = self._bias

        active_high = self._active_level(self._high_unbroken)
        major_high = self._major_high()
        if active_high is not None and bar.close > active_high.price + self.bos_buffer:
            stype, reason, phan_loai = self._classify_up_break(
                bar.close, active_high, major_high, bias_snapshot
            )
            events.append(
                self._make_event(
                    structure_type=stype,
                    price=active_high.price,
                    event_bar=bar,
                    confirming_bar=bar,
                    reason_code=reason,
                    direction="up",
                    reference_event_id=active_high.event_id,
                    details={
                        "muc_bi_pha": active_high.price,
                        "gia_dong_cua": bar.close,
                        "bien_pha_vo": self.bos_buffer,
                        "nen_tao_muc": active_high.bar_index,
                        "phan_loai": phan_loai,
                        "bias_truoc": bias_snapshot,
                        "muc_chinh": major_high.price if major_high else None,
                        "muc_active": active_high.price,
                    },
                )
            )
            self._break_highs(bar.close)

        active_low = self._active_level(self._low_unbroken)
        major_low = self._major_low()
        if active_low is not None and bar.close < active_low.price - self.bos_buffer:
            stype, reason, phan_loai = self._classify_down_break(
                bar.close, active_low, major_low, bias_snapshot
            )
            events.append(
                self._make_event(
                    structure_type=stype,
                    price=active_low.price,
                    event_bar=bar,
                    confirming_bar=bar,
                    reason_code=reason,
                    direction="down",
                    reference_event_id=active_low.event_id,
                    details={
                        "muc_bi_pha": active_low.price,
                        "gia_dong_cua": bar.close,
                        "bien_pha_vo": self.bos_buffer,
                        "nen_tao_muc": active_low.bar_index,
                        "phan_loai": phan_loai,
                        "bias_truoc": bias_snapshot,
                        "muc_chinh": major_low.price if major_low else None,
                        "muc_active": active_low.price,
                    },
                )
            )
            self._break_lows(bar.close)

        new_bias = bias_snapshot
        for ev in events:
            if ev.structure_type == StructureType.CHOCH_UP:
                new_bias = "bullish"
            elif ev.structure_type == StructureType.CHOCH_DOWN:
                new_bias = "bearish"
        if new_bias != bias_snapshot:
            self._bias = new_bias
            self._last_high_label = None
            self._last_low_label = None
            self._last_hh_id = None
            self._last_hl_id = None
            self._last_lh_id = None
            self._last_ll_id = None
            for ev in events:
                ev.details["bias_sau"] = self._bias
        else:
            for ev in events:
                ev.details["bias_sau"] = bias_snapshot

        return events

    def _classify_up_break(
        self,
        close: float,
        active: _Level,
        major: Optional[_Level],
        bias: str,
    ) -> tuple[str, str, str]:
        if not self.enable_choch or bias == "none":
            return StructureType.BOS_UP, ReasonCode.BOS_CLOSE_ABOVE_SWING_HIGH, "chinh"
        broke_major = major is not None and close > major.price + self.bos_buffer
        is_major_active = major is not None and active.event_id == major.event_id
        if bias == "bearish":
            if broke_major or is_major_active:
                return StructureType.CHOCH_UP, ReasonCode.CHOCH_CLOSE_ABOVE_SWING_HIGH, "choch"
            return StructureType.BOS_INTERNAL_UP, ReasonCode.BOS_INTERNAL_CLOSE_ABOVE, "noi_bo"
        if broke_major or is_major_active:
            return StructureType.BOS_UP, ReasonCode.BOS_CLOSE_ABOVE_SWING_HIGH, "chinh"
        return StructureType.BOS_INTERNAL_UP, ReasonCode.BOS_INTERNAL_CLOSE_ABOVE, "noi_bo"

    def _classify_down_break(
        self,
        close: float,
        active: _Level,
        major: Optional[_Level],
        bias: str,
    ) -> tuple[str, str, str]:
        if not self.enable_choch or bias == "none":
            return StructureType.BOS_DOWN, ReasonCode.BOS_CLOSE_BELOW_SWING_LOW, "chinh"
        broke_major = major is not None and close < major.price - self.bos_buffer
        is_major_active = major is not None and active.event_id == major.event_id
        if bias == "bullish":
            if broke_major or is_major_active:
                return StructureType.CHOCH_DOWN, ReasonCode.CHOCH_CLOSE_BELOW_SWING_LOW, "choch"
            return StructureType.BOS_INTERNAL_DOWN, ReasonCode.BOS_INTERNAL_CLOSE_BELOW, "noi_bo"
        if broke_major or is_major_active:
            return StructureType.BOS_DOWN, ReasonCode.BOS_CLOSE_BELOW_SWING_LOW, "chinh"
        return StructureType.BOS_INTERNAL_DOWN, ReasonCode.BOS_INTERNAL_CLOSE_BELOW, "noi_bo"

    @staticmethod
    def _active_level(unbroken: dict[str, _Level]) -> Optional[_Level]:
        """Mức chưa bị phá có chỉ số xác nhận lớn nhất (dict giữ thứ tự xác nhận)."""
        return next(reversed(unbroken.values()), None)

    @staticmethod
    def _level_by_id(by_id: dict[str, _Level], event_id: Optional[str]) -> Optional[_Level]:
        if not event_id:
            return None
        lv = by_id.get(event_id)
        return lv if lv is not None and not lv.broken else None

    def _break_highs(self, close: float) -> None:
        """Đánh dấu đã phá mọi mức high chưa phá có ``close > giá + bos_buffer``.

        ``giá + bos_buffer`` không giảm khi giá tăng (kể cả khi làm tròn số thực), nên các mức
        thoả điều kiện là một đoạn ĐẦU của danh sách xếp tăng theo giá — đúng tập mà vòng quét
        toàn bộ danh sách trước đây đánh dấu."""
        lst, k = self._high_by_price, 0
        while k < len(lst) and close > lst[k][0] + self.bos_buffer:
            self._high_unbroken.pop(lst[k][2]).broken = True
            k += 1
        if k:
            del lst[:k]

    def _break_lows(self, close: float) -> None:
        """Như ``_break_highs`` cho ``close < giá − bos_buffer``: một đoạn CUỐI của danh sách."""
        lst = self._low_by_price
        k = len(lst)
        while k > 0 and close < lst[k - 1][0] - self.bos_buffer:
            k -= 1
            self._low_unbroken.pop(lst[k][2]).broken = True
        if k < len(lst):
            del lst[k:]

    def _major_high(self) -> Optional[_Level]:
        if self._bias == "bullish":
            return self._level_by_id(self._high_by_id, self._last_hh_id)
        if self._bias == "bearish":
            return self._level_by_id(self._high_by_id, self._last_lh_id)
        return None

    def _major_low(self) -> Optional[_Level]:
        if self._bias == "bullish":
            return self._level_by_id(self._low_by_id, self._last_hl_id)
        if self._bias == "bearish":
            return self._level_by_id(self._low_by_id, self._last_ll_id)
        return None

    # ------------------------------------------------------------------

    def _make_event(
        self,
        *,
        structure_type: str,
        price: float,
        event_bar: Bar,
        confirming_bar: Bar,
        reason_code: str,
        direction: Optional[str] = None,
        reference_event_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> StructureEvent:
        event_id = "%s@%d>%d" % (
            structure_type,
            event_bar.index,
            confirming_bar.index,
        )
        if event_id in self._emitted_ids:  # pragma: no cover - phòng vệ
            raise RuntimeError("Trùng event_id: %s" % event_id)
        self._emitted_ids.add(event_id)
        return StructureEvent(
            event_id=event_id,
            structure_type=structure_type,
            price=price,
            event_bar_index=event_bar.index,
            event_time=event_bar.bar_time,
            event_close_time=event_bar.close_time,
            confirmed_bar_index=confirming_bar.index,
            confirmed_at=confirming_bar.close_time,
            algorithm=self.name,
            algorithm_version=self.version,
            reason_code=reason_code,
            direction=direction,
            reference_event_id=reference_event_id,
            details=details or {},
        )

    # ------------------------------------------------------------------

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        """Mức swing đang hoạt động SAU khi xử lý nến ``bar``.

        Đây chính là mức mà quy tắc BOS sẽ so sánh ở các nến tiếp theo, nên
        đường vẽ từ chuỗi này luôn chỉ chứa thông tin đã khả dụng tại nến đó.
        """
        hi = self._active_level(self._high_unbroken)
        lo = self._active_level(self._low_unbroken)
        return {
            "muc_high": hi.price if hi else None,
            "muc_low": lo.price if lo else None,
            "bias": self._bias,
        }

    def pending_state(self) -> dict[str, Any]:
        """Trạng thái tạm thời — dùng để hiển thị, KHÔNG phải sự kiện xác nhận."""
        active_high = self._active_level(self._high_unbroken)
        active_low = self._active_level(self._low_unbroken)
        return {
            "so_nen_da_xu_ly": len(self._bars),
            "muc_swing_high_dang_hoat_dong": (
                {
                    "gia": active_high.price,
                    "nen": active_high.bar_index,
                    "event_id": active_high.event_id,
                }
                if active_high
                else None
            ),
            "muc_swing_low_dang_hoat_dong": (
                {
                    "gia": active_low.price,
                    "nen": active_low.bar_index,
                    "event_id": active_low.event_id,
                }
                if active_low
                else None
            ),
            "bias": self._bias,
            "so_muc_high_da_pha": len(self._high_levels) - len(self._high_unbroken),
            "so_muc_low_da_pha": len(self._low_levels) - len(self._low_unbroken),
            "nen_dang_cho_xac_nhan": (
                list(range(max(0, len(self._bars) - self.right), len(self._bars)))
                if self._bars
                else []
            ),
        }
