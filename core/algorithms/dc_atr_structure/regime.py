"""Phân loại Tăng / Giảm / Range / Chưa rõ từ swing DC ĐÃ XÁC NHẬN.

Module tách riêng khỏi detector DC (``dc_atr_structure``): chỉ nhận pivot đã
xác nhận + close/ATR của nến hiện tại, không tác động ngược vào detector.
Đặc tả: ``docs/thuat_toan_dc_atr_structure.md`` mục 7.

Đây là **định nghĩa vận hành do lab đề xuất**, không phải chân lý gán nhãn thị
trường và không phải dự báo:

* ``UPTREND``   : nhãn của đỉnh gần nhất là HH và của đáy gần nhất là HL.
* ``DOWNTREND`` : LH + LL.
* ``RANGE``     : m đỉnh và m đáy gần nhất tạo hai cụm hẹp, tách nhau, đủ rộng,
  close hiện tại nằm giữa. Biên/buffer khoá từ lúc vào Range.
* ``UNKNOWN``   : còn lại (thiếu pivot, nhãn mâu thuẫn, có EQ, Range không đạt,
  vừa phá biên Range).

Thứ tự gọi tại mỗi nến (adapter đảm bảo):

1. :meth:`RegimeClassifier.check_range_break` — close hiện tại so với biên khoá.
   Nếu phá, nến này bị chặn phân loại lại.
2. :meth:`RegimeClassifier.on_pivot` — chỉ khi detector vừa xác nhận pivot.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.types import ReasonCode

CLASSIFIER_NAME = "dc_regime"
CLASSIFIER_VERSION = "0.1.0"

UPTREND = "UPTREND"
DOWNTREND = "DOWNTREND"
RANGE = "RANGE"
UNKNOWN = "UNKNOWN"
STATES = (UPTREND, DOWNTREND, RANGE, UNKNOWN)

STATE_TEXT_VI = {
    UPTREND: "Tăng",
    DOWNTREND: "Giảm",
    RANGE: "Range",
    UNKNOWN: "Chưa rõ",
}

#: Lý do chi tiết (máy đọc được) cho UNKNOWN / Range không đạt.
WHY_THIEU_PIVOT = "thieu_pivot"
WHY_MAU_THUAN = "nhan_mau_thuan"
WHY_CO_EQ = "co_nhan_EQ"
WHY_PHA_BIEN = "vua_pha_bien_range"
WHY_CHUA_PIVOT = "chua_co_pivot"

_HIGH_LABELS = ("HH", "LH", "EQH")
_LOW_LABELS = ("HL", "LL", "EQL")


@dataclass(frozen=True)
class PivotRef:
    """Thông tin tối thiểu của một pivot DC đã xác nhận."""

    pivot_id: str
    kind: str                 # "high" | "low"
    price: float
    label: Optional[str]      # HH/LH/EQH hoặc HL/LL/EQL; None nếu pivot đầu loại
    extreme_index: int
    confirmed_index: int


@dataclass(frozen=True)
class RegimeParams:
    swings_per_side: int = 3
    cluster_tolerance_atr: float = 0.5
    min_width_atr: float = 1.0
    break_buffer_atr: float = 0.25

    def __post_init__(self) -> None:
        if self.swings_per_side < 3:
            raise ValueError("range_swings_per_side phải >= 3")
        if self.cluster_tolerance_atr < 0 or self.break_buffer_atr < 0:
            raise ValueError("Dung sai cụm và buffer phá range không được âm")
        if not self.min_width_atr > 0:
            raise ValueError("range_min_width_atr phải > 0")


@dataclass(frozen=True)
class RegimeTransition:
    """Một lần trạng thái THỰC SỰ đổi. Adapter biến nó thành StructureEvent."""

    kind: str                 # "REGIME" | "RANGE_START" | "RANGE_EXIT"
    from_state: str
    to_state: str
    bar_index: int
    close: float
    reason_code: str
    reason_vi: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LockedRange:
    range_id: str
    upper: float
    lower: float
    atr: float
    buffer: float
    start_index: int
    evidence_ids: tuple[str, ...]
    high_prices: tuple[float, ...]
    low_prices: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "range_id": self.range_id,
            "upper": self.upper,
            "lower": self.lower,
            "atr_luc_vao": self.atr,
            "buffer": self.buffer,
            "bien_tren_pha": self.upper + self.buffer,
            "bien_duoi_pha": self.lower - self.buffer,
            "start_index": self.start_index,
            "evidence_ids": list(self.evidence_ids),
            "high_prices": list(self.high_prices),
            "low_prices": list(self.low_prices),
        }


class RegimeClassifier:
    """Máy trạng thái regime, tuần tự và nhân quả. ``reset()`` xoá sạch."""

    def __init__(self, params: RegimeParams, *, id_prefix: str = "") -> None:
        self.params = params
        self.id_prefix = id_prefix
        self.reset()

    # ------------------------------------------------------------------ state

    def reset(self) -> None:
        self.state: str = UNKNOWN
        self.why: str = WHY_CHUA_PIVOT
        self.reason_vi: str = "Chưa có pivot DC xác nhận trong segment."
        self.trend_evidence: tuple[str, ...] = ()
        self._highs: list[PivotRef] = []
        self._lows: list[PivotRef] = []
        self._range: Optional[LockedRange] = None
        self._last_range: Optional[LockedRange] = None
        self._blocked_index: Optional[int] = None
        self._last_range_check: Optional[dict[str, Any]] = None

    @property
    def active_range(self) -> Optional[LockedRange]:
        return self._range

    # ------------------------------------------------------------- bước 3

    def check_range_break(self, bar_index: int, close: float) -> Optional[RegimeTransition]:
        """Kiểm tra close hiện tại với biên Range đã khoá. Wick không được xét."""
        rng = self._range
        if self.state != RANGE or rng is None:
            return None
        up = close > rng.upper + rng.buffer
        down = close < rng.lower - rng.buffer
        if not (up or down):
            return None
        code = ReasonCode.DC_RANGE_CLOSE_BREAK_UP if up else ReasonCode.DC_RANGE_CLOSE_BREAK_DOWN
        self._last_range = rng
        self._range = None
        self._blocked_index = bar_index
        self.state = UNKNOWN
        self.why = WHY_PHA_BIEN
        self.trend_evidence = ()
        self.reason_vi = (
            "Close %s biên %s ± buffer của %s; chờ pivot mới ở nến sau để phân loại lại."
            % ("vượt" if up else "thủng", "trên" if up else "dưới", rng.range_id)
        )
        return RegimeTransition(
            kind="RANGE_EXIT",
            from_state=RANGE,
            to_state=UNKNOWN,
            bar_index=bar_index,
            close=close,
            reason_code=code,
            reason_vi=self.reason_vi,
            details={
                "range": rng.to_dict(),
                "huong_pha": "up" if up else "down",
                "close_pha": close,
                "nguong_pha": rng.upper + rng.buffer if up else rng.lower - rng.buffer,
                "chi_xet_lai_tu_nen": bar_index + 1,
            },
        )

    # ------------------------------------------------------------- bước 5

    def on_pivot(
        self, pivot: PivotRef, bar_index: int, close: float, atr: Optional[float]
    ) -> Optional[RegimeTransition]:
        """Ghi nhận pivot vừa xác nhận rồi phân loại (trừ khi nến bị chặn)."""
        if pivot.kind == "high":
            self._highs.append(pivot)
        elif pivot.kind == "low":
            self._lows.append(pivot)
        else:  # pragma: no cover - phòng vệ
            raise ValueError("pivot.kind phải là 'high' hoặc 'low'")

        if self._blocked_index == bar_index:
            # Nến phá biên: không tái tạo range / chuyển trend từ cùng bằng chứng.
            return None

        trend, why, evidence = self._trend_evidence()
        prev_state = self.state

        if prev_state == RANGE:
            if trend is None:
                return None  # giữ Range và biên cũ
            closed = self._range
            self._range = None
            self._last_range = closed
            return self._set_state(
                trend, why, evidence, bar_index, close,
                extra={"range_dong": closed.to_dict() if closed else None},
            )

        if trend is not None:
            return self._set_state(trend, why, evidence, bar_index, close)

        rng, check = self._try_range(bar_index, close, atr)
        self._last_range_check = check
        if rng is not None:
            self._range = rng
            self.state = RANGE
            self.why = "range"
            self.trend_evidence = ()
            self.reason_vi = (
                "Range: %d đỉnh trong cụm rộng %.6g, %d đáy trong cụm rộng %.6g "
                "(≤ %.6g); biên [%.6g, %.6g], buffer %.6g."
                % (
                    len(rng.high_prices), check["spread_high"], len(rng.low_prices),
                    check["spread_low"], check["cluster_limit"], rng.lower, rng.upper,
                    rng.buffer,
                )
            )
            return RegimeTransition(
                kind="RANGE_START",
                from_state=prev_state,
                to_state=RANGE,
                bar_index=bar_index,
                close=close,
                reason_code=ReasonCode.DC_RANGE_CLUSTERS,
                reason_vi=self.reason_vi,
                details={"range": rng.to_dict(), "kiem_tra_range": check},
            )

        return self._set_state(
            UNKNOWN, why, evidence, bar_index, close, extra={"kiem_tra_range": check}
        )

    # ------------------------------------------------------------- helpers

    def _set_state(
        self,
        new_state: str,
        why: str,
        evidence: tuple[str, ...],
        bar_index: int,
        close: float,
        extra: Optional[dict[str, Any]] = None,
    ) -> Optional[RegimeTransition]:
        prev = self.state
        self.state = new_state
        self.why = why
        self.trend_evidence = evidence
        self.reason_vi = self._explain(new_state, why, extra)
        if new_state == prev:
            return None
        if new_state == UPTREND:
            code = ReasonCode.DC_TREND_HH_HL
        elif new_state == DOWNTREND:
            code = ReasonCode.DC_TREND_LH_LL
        else:
            code = ReasonCode.DC_NO_TREND_NO_RANGE
        details = {
            "ly_do": why,
            "bang_chung": list(evidence),
            "nhan_dinh_gan_nhat": self._highs[-1].label if self._highs else None,
            "nhan_day_gan_nhat": self._lows[-1].label if self._lows else None,
        }
        if extra:
            details.update(extra)
        return RegimeTransition(
            kind="REGIME",
            from_state=prev,
            to_state=new_state,
            bar_index=bar_index,
            close=close,
            reason_code=code,
            reason_vi=self.reason_vi,
            details=details,
        )

    def _explain(self, state: str, why: str, extra: Optional[dict[str, Any]]) -> str:
        if state == UPTREND:
            return "Đỉnh DC gần nhất HH và đáy DC gần nhất HL."
        if state == DOWNTREND:
            return "Đỉnh DC gần nhất LH và đáy DC gần nhất LL."
        base = {
            WHY_THIEU_PIVOT: "Chưa đủ hai đỉnh và hai đáy DC trong segment để so sánh.",
            WHY_MAU_THUAN: "Nhãn đỉnh/đáy gần nhất mâu thuẫn (không cùng HH+HL hay LH+LL).",
            WHY_CO_EQ: "Có nhãn EQH/EQL (bằng giá trong dung sai) — chưa đủ bằng chứng trend.",
        }.get(why, "Chưa rõ.")
        chk = (extra or {}).get("kiem_tra_range")
        if chk and not chk.get("dat"):
            base += " Range không đạt: %s." % chk.get("ly_do_vi", "")
        return base

    def _trend_evidence(self) -> tuple[Optional[str], str, tuple[str, ...]]:
        if len(self._highs) < 2 or len(self._lows) < 2:
            return None, WHY_THIEU_PIVOT, ()
        h, lo = self._highs[-1], self._lows[-1]
        evidence = (h.pivot_id, lo.pivot_id)
        if h.label == "HH" and lo.label == "HL":
            return UPTREND, "HH+HL", evidence
        if h.label == "LH" and lo.label == "LL":
            return DOWNTREND, "LH+LL", evidence
        if h.label == "EQH" or lo.label == "EQL":
            return None, WHY_CO_EQ, evidence
        return None, WHY_MAU_THUAN, evidence

    def _try_range(
        self, bar_index: int, close: float, atr: Optional[float]
    ) -> tuple[Optional[LockedRange], dict[str, Any]]:
        p = self.params
        m = p.swings_per_side
        check: dict[str, Any] = {"dat": False, "m": m, "bar_index": bar_index, "close": close}
        if len(self._highs) < m or len(self._lows) < m:
            check["ly_do_vi"] = "cần %d đỉnh và %d đáy, có %d/%d" % (
                m, m, len(self._highs), len(self._lows))
            return None, check
        if atr is None or not atr > 0:
            check["ly_do_vi"] = "ATR tại lúc đánh giá không > 0"
            return None, check
        highs = self._highs[-m:]
        lows = self._lows[-m:]
        hp = tuple(x.price for x in highs)
        lp = tuple(x.price for x in lows)
        spread_h = max(hp) - min(hp)
        spread_l = max(lp) - min(lp)
        limit = p.cluster_tolerance_atr * atr
        upper, lower = max(hp), min(lp)
        width = upper - lower
        min_width = p.min_width_atr * atr
        check.update({
            "atr": atr,
            "high_prices": list(hp),
            "low_prices": list(lp),
            "spread_high": spread_h,
            "spread_low": spread_l,
            "cluster_limit": limit,
            "upper": upper,
            "lower": lower,
            "width": width,
            "min_width": min_width,
            "min_high": min(hp),
            "max_low": max(lp),
        })
        fails = []
        if spread_h > limit:
            fails.append("cụm đỉnh rộng %.6g > %.6g" % (spread_h, limit))
        if spread_l > limit:
            fails.append("cụm đáy rộng %.6g > %.6g" % (spread_l, limit))
        if not min(hp) > max(lp):
            fails.append("hai cụm chồng nhau (đỉnh thấp nhất %.6g ≤ đáy cao nhất %.6g)"
                         % (min(hp), max(lp)))
        if width < min_width:
            fails.append("biên hẹp %.6g < %.6g" % (width, min_width))
        if not (lower <= close <= upper):
            fails.append("close %.6g đã ngoài [%.6g, %.6g]" % (close, lower, upper))
        if fails:
            check["ly_do_vi"] = "; ".join(fails)
            return None, check
        check["dat"] = True
        check["ly_do_vi"] = "đạt đủ điều kiện"
        rng = LockedRange(
            range_id="%srange@%d" % (self.id_prefix, bar_index),
            upper=upper,
            lower=lower,
            atr=atr,
            buffer=p.break_buffer_atr * atr,
            start_index=bar_index,
            evidence_ids=tuple(x.pivot_id for x in highs + lows),
            high_prices=hp,
            low_prices=lp,
        )
        return rng, check

    # ------------------------------------------------------------- hiển thị

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "state_vi": STATE_TEXT_VI[self.state],
            "ly_do": self.why,
            "ly_do_vi": self.reason_vi,
            "bang_chung_trend": list(self.trend_evidence),
            "range": self._range.to_dict() if self._range else None,
            "range_vua_dong": self._last_range.to_dict() if self._last_range else None,
            "so_dinh_xac_nhan": len(self._highs),
            "so_day_xac_nhan": len(self._lows),
            "nhan_dinh_gan_nhat": self._highs[-1].label if self._highs else None,
            "nhan_day_gan_nhat": self._lows[-1].label if self._lows else None,
            "kiem_tra_range_gan_nhat": self._last_range_check,
            "chan_phan_loai_tai_nen": self._blocked_index,
            "classifier": CLASSIFIER_NAME,
            "classifier_version": CLASSIFIER_VERSION,
        }
