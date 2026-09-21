"""Thuật toán Swing phân cấp: fractal cấp 1 rồi HH/LH trên đỉnh cấp 2.

Đặc tả đầy đủ: ``docs/thuat_toan_swing_cap_2.md``.
Tóm tắt quy tắc (phiên bản 1.0.0):

**1. Pivot cấp 1** — giống ``swing_pivot`` v1.1.0: cửa sổ left/right, so sánh
tuyệt đối, xác nhận khi nến ``c + right`` đóng.

**2. Cấp 2** — trên *chuỗi* đỉnh cấp 1 đã xác nhận (không phải ba nến liên
tiếp). Ba đỉnh liên tiếp ``P_{k-1}, P_k, P_{k+1}``: ``P_k`` là đỉnh cấp 2 khi
``P_k > P_{k-1}`` và ``P_k > P_{k+1}``. Đáy đối xứng. Xác nhận cấp 2 đúng lúc
pivot cấp 1 bên phải được xác nhận — không gắn tín hiệu về lúc đỉnh giữa
hình thành.

**3. HH/LH** — chỉ so hai đỉnh cấp 2 liên tiếp (tol mặc định 0). Không phát
nhãn HH cấp 1. Không phát BOS.

Đây là thí nghiệm lọc cấu trúc, chưa phải ICT đầy đủ.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.types import Bar, ReasonCode, StructureEvent, StructureType


@dataclass
class _L1:
    """Một pivot cấp 1 đã xác nhận."""

    event_id: str
    price: float
    bar: Bar
    confirmed_index: int


class SwingHierarchyAlgorithm(StructureAlgorithm):
    name = "swing_hierarchy"
    display_name_vi = "Swing phân cấp (cấp 1 + cấp 2)"
    version = "1.0.0"
    description_vi = (
        "Fractal cấp 1 (left/right=3) rồi lọc đỉnh/đáy cấp 2 trên chuỗi pivot. "
        "HH/LH chỉ so hai đỉnh cấp 2 liên tiếp. Không gồm BOS. Xác nhận cấp 2 "
        "khi pivot cấp 1 bên phải đã đóng — không gắn tín hiệu về lúc đỉnh giữa hình thành."
    )

    @classmethod
    def param_specs(cls) -> tuple[ParamSpec, ...]:
        return (
            ParamSpec(
                name="left",
                label_vi="Số nến bên trái (cấp 1)",
                type="int",
                default=3,
                min=1,
                max=50,
                step=1,
                help_vi=(
                    "Số nến phía trước nến pivot cấp 1 phải có high thấp hơn "
                    "(hoặc low cao hơn) nến pivot."
                ),
            ),
            ParamSpec(
                name="right",
                label_vi="Số nến bên phải (cấp 1)",
                type="int",
                default=3,
                min=1,
                max=50,
                step=1,
                help_vi=(
                    "Số nến phía sau nến pivot cấp 1. Pivot cấp 1 chỉ xác nhận "
                    "khi nến này đóng. Cấp 2 xác nhận muộn hơn — lúc pivot cấp 1 "
                    "bên phải của bộ ba được xác nhận."
                ),
            ),
            ParamSpec(
                name="label_eq_tolerance",
                label_vi="Dung sai 'bằng giá' cấp 2 (đơn vị giá)",
                type="float",
                default=0.0,
                min=0.0,
                step=0.01,
                help_vi=(
                    "Chỉ dùng khi gắn HH/LH/EQH giữa hai đỉnh cấp 2. "
                    "Không dùng khi lọc cấp 2 (lọc luôn so sánh nghiêm ngặt). "
                    "Mặc định 0.0."
                ),
            ),
            ParamSpec(
                name="emit_level1",
                label_vi="Hiện thêm đỉnh/đáy cấp 1",
                type="bool",
                default=True,
                help_vi=(
                    "Bật: phát SWING_HIGH/SWING_LOW fractal để đối chiếu. "
                    "Tắt: chỉ còn cấp 2 và nhãn HH/LH cấp 2. Dù bật hay tắt "
                    "cũng không gắn HH cấp 1."
                ),
            ),
        )

    def __init__(self, **params: Any) -> None:
        p = self.validate_params(params)
        self.left: int = p["left"]
        self.right: int = p["right"]
        self.label_eq_tolerance: float = p["label_eq_tolerance"]
        self.emit_level1: bool = p["emit_level1"]
        self.params: dict[str, Any] = p
        self.reset()

    def reset(self) -> None:
        self._bars: list[Bar] = []
        self._l1_highs: list[_L1] = []
        self._l1_lows: list[_L1] = []
        self._last_l2_high: Optional[StructureEvent] = None
        self._last_l2_low: Optional[StructureEvent] = None
        self._l2_high_count: int = 0
        self._l2_low_count: int = 0
        self._emitted_ids: set[str] = set()

    def warmup_bars(self) -> int:
        return self.left + self.right + 1

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        if self._bars and bar.index <= self._bars[-1].index:
            raise ValueError(
                "Nến phải được nạp theo thứ tự tăng dần: nhận index=%s sau index=%s"
                % (bar.index, self._bars[-1].index)
            )
        self._bars.append(bar)
        return self._confirm_level1_then_level2(bar)

    def _confirm_level1_then_level2(self, confirming: Bar) -> list[StructureEvent]:
        i = len(self._bars) - 1
        c = i - self.right
        if c < self.left:
            return []

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
            events.extend(self._on_level1(pivot, confirming, side="high"))
        if is_low:
            events.extend(self._on_level1(pivot, confirming, side="low"))
        return events

    def _on_level1(self, pivot: Bar, confirming: Bar, side: str) -> list[StructureEvent]:
        is_high = side == "high"
        price = pivot.high if is_high else pivot.low
        stype = StructureType.SWING_HIGH if is_high else StructureType.SWING_LOW
        reason = (
            ReasonCode.PIVOT_HIGH_STRICT if is_high else ReasonCode.PIVOT_LOW_STRICT
        )
        out: list[StructureEvent] = []

        swing = self._make_event(
            structure_type=stype,
            price=price,
            event_bar=pivot,
            confirming_bar=confirming,
            reason_code=reason,
            direction="up" if is_high else "down",
            details={
                "cap_do": 1,
                "left": self.left,
                "right": self.right,
                "quy_tac": (
                    "high[pivot] > mọi high trong cửa sổ"
                    if is_high
                    else "low[pivot] < mọi low trong cửa sổ"
                ),
            },
        )
        if self.emit_level1:
            out.append(swing)

        rec = _L1(
            event_id=swing.event_id,
            price=price,
            bar=pivot,
            confirmed_index=confirming.index,
        )
        seq = self._l1_highs if is_high else self._l1_lows
        seq.append(rec)
        out.extend(self._maybe_level2(side, confirming))
        return out

    def _maybe_level2(self, side: str, confirming: Bar) -> list[StructureEvent]:
        is_high = side == "high"
        seq = self._l1_highs if is_high else self._l1_lows
        if len(seq) < 3:
            return []
        left, mid, right = seq[-3], seq[-2], seq[-1]
        if is_high:
            is_l2 = mid.price > left.price and mid.price > right.price
            stype = StructureType.SWING_HIGH_L2
            reason = ReasonCode.PIVOT_HIGH_L2
        else:
            is_l2 = mid.price < left.price and mid.price < right.price
            stype = StructureType.SWING_LOW_L2
            reason = ReasonCode.PIVOT_LOW_L2
        if not is_l2:
            return []

        l2 = self._make_event(
            structure_type=stype,
            price=mid.price,
            event_bar=mid.bar,
            confirming_bar=confirming,
            reason_code=reason,
            direction="up" if is_high else "down",
            reference_event_id=mid.event_id,
            details={
                "cap_do": 2,
                "gia_l1_trai": left.price,
                "gia_l1_giua": mid.price,
                "gia_l1_phai": right.price,
                "nen_l1_trai": left.bar.index,
                "nen_l1_giua": mid.bar.index,
                "nen_l1_phai": right.bar.index,
                "id_l1_giua": mid.event_id,
                "xac_nhan_khi": (
                    "pivot cấp 1 bên phải vừa xác nhận; không gắn về lúc đỉnh giữa hình thành"
                ),
                "quy_tac": (
                    "P_giua > P_trai và P_giua > P_phai (ba đỉnh cấp 1 liên tiếp)"
                    if is_high
                    else "Q_giua < Q_trai và Q_giua < Q_phai (ba đáy cấp 1 liên tiếp)"
                ),
            },
        )
        out = [l2]

        prev = self._last_l2_high if is_high else self._last_l2_low
        if prev is not None:
            label, reason_code = self._compare_l2(prev.price, mid.price, is_high)
            out.append(
                self._make_event(
                    structure_type=label,
                    price=mid.price,
                    event_bar=mid.bar,
                    confirming_bar=confirming,
                    reason_code=reason_code,
                    direction="up" if is_high else "down",
                    reference_event_id=prev.event_id,
                    details={
                        "cap_do": 2,
                        "so_sanh": (
                            "hai đỉnh cấp 2 liên tiếp"
                            if is_high
                            else "hai đáy cấp 2 liên tiếp"
                        ),
                        "gia_swing_truoc": prev.price,
                        "gia_swing_nay": mid.price,
                        "chenh_lech": round(mid.price - prev.price, 10),
                        "dung_sai_bang_gia": self.label_eq_tolerance,
                    },
                )
            )

        if is_high:
            self._last_l2_high = l2
            self._l2_high_count += 1
        else:
            self._last_l2_low = l2
            self._l2_low_count += 1
        return out

    def _compare_l2(self, prev: float, cur: float, is_high: bool) -> tuple[str, str]:
        tol = self.label_eq_tolerance
        if cur > prev + tol:
            return (
                (StructureType.HH, ReasonCode.SEQ_HIGHER_HIGH_L2)
                if is_high
                else (StructureType.HL, ReasonCode.SEQ_HIGHER_LOW_L2)
            )
        if cur < prev - tol:
            return (
                (StructureType.LH, ReasonCode.SEQ_LOWER_HIGH_L2)
                if is_high
                else (StructureType.LL, ReasonCode.SEQ_LOWER_LOW_L2)
            )
        return (
            (StructureType.EQH, ReasonCode.SEQ_EQUAL_HIGH_L2)
            if is_high
            else (StructureType.EQL, ReasonCode.SEQ_EQUAL_LOW_L2)
        )

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

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        """Mốc so HH/LH tiếp theo = đỉnh/đáy cấp 2 gần nhất đã xác nhận."""
        return {
            "muc_high": self._last_l2_high.price if self._last_l2_high else None,
            "muc_low": self._last_l2_low.price if self._last_l2_low else None,
            "so_dinh_cap_1": len(self._l1_highs),
            "so_day_cap_1": len(self._l1_lows),
        }

    def pending_state(self) -> dict[str, Any]:
        def _tail(seq: list[_L1], n: int = 3) -> list[dict[str, Any]]:
            return [
                {"gia": x.price, "nen": x.bar.index, "xac_nhan_tai": x.confirmed_index}
                for x in seq[-n:]
            ]

        return {
            "so_nen_da_xu_ly": len(self._bars),
            "so_dinh_cap_1": len(self._l1_highs),
            "so_day_cap_1": len(self._l1_lows),
            "so_dinh_cap_2": self._l2_high_count,
            "so_day_cap_2": self._l2_low_count,
            "ba_dinh_cap_1_gan_nhat": _tail(self._l1_highs),
            "ba_day_cap_1_gan_nhat": _tail(self._l1_lows),
            "gia_dinh_cap_2_gan_nhat": (
                self._last_l2_high.price if self._last_l2_high else None
            ),
            "gia_day_cap_2_gan_nhat": (
                self._last_l2_low.price if self._last_l2_low else None
            ),
            "nen_dang_cho_xac_nhan": (
                list(range(max(0, len(self._bars) - self.right), len(self._bars)))
                if self._bars
                else []
            ),
        }
