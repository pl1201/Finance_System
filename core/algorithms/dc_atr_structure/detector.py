"""Detector Directional Change tuần tự trên CLOSE — không biết gì về regime.

* Khởi tạo sau warm-up: anchor = close hiện tại, khoá ngưỡng anchor, chờ close đi
  ≥ ngưỡng về một phía để chọn hướng. Không phát pivot ở anchor.
* ``SEEK_HIGH``: close > ứng viên → cập nhật ứng viên và khoá Δ mới tại nến đó; ngược
  lại close ≤ ứng viên − Δ → pivot đỉnh tại ứng viên, chuyển ``SEEK_LOW`` với ứng viên
  = close hiện tại. ``SEEK_LOW`` đối xứng.
* Δ = k × ATR[e] (mode ``atr``) hoặc |close[e]| × pct / 100 (mode ``percent``), e là nến
  cực trị. Δ giữ nguyên tới khi có cực trị nghiêm ngặt mới.

Đặc tả: ``docs/thuat_toan_dc_atr_structure.md``. Adapter dựng ``StructureEvent``: ``algorithm.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from core.types import Bar

PHASE_WARMUP = "WARMUP"
PHASE_WAIT_ATR = "WAIT_ATR"
PHASE_SEEK_DIRECTION = "SEEK_DIRECTION"
PHASE_SEEK_HIGH = "SEEK_HIGH"
PHASE_SEEK_LOW = "SEEK_LOW"

PHASE_TEXT_VI = {
    PHASE_WARMUP: "Warm-up ATR",
    PHASE_WAIT_ATR: "Chờ ATR > 0",
    PHASE_SEEK_DIRECTION: "Chờ chọn hướng từ anchor",
    PHASE_SEEK_HIGH: "Đang theo dõi đỉnh",
    PHASE_SEEK_LOW: "Đang theo dõi đáy",
}


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@dataclass(frozen=True)
class Candidate:
    """Ứng viên cực trị — CHƯA xác nhận, có thể thay đổi."""

    side: str                 # "high" | "low"
    price: float              # close của nến cực trị
    index: int
    bar_time: datetime
    close_time: datetime
    atr: float                # ATR tại nến cực trị
    delta: float              # ngưỡng đảo chiều đã khoá
    threshold_set_at: datetime


@dataclass(frozen=True)
class DcPivot:
    """Pivot DC đã xác nhận (dữ liệu thô, adapter dựng StructureEvent)."""

    kind: str                 # "high" | "low"
    price: float
    extreme_index: int
    extreme_bar_time: datetime
    extreme_close_time: datetime
    atr_at_extreme: float
    delta: float
    threshold_set_at: datetime
    confirm_index: int
    confirm_close_time: datetime
    confirm_close: float

    @property
    def reversal_distance(self) -> float:
        return abs(self.price - self.confirm_close)


class DcDetector:
    """Detector Directional Change tuần tự trên close. Không biết gì về regime."""

    def __init__(self, mode: str, atr_multiplier: float, reversal_pct: float) -> None:
        if mode not in ("atr", "percent"):
            raise ValueError("threshold_mode phải là 'atr' hoặc 'percent'")
        self.mode = mode
        self.k = atr_multiplier
        self.pct = reversal_pct
        self.reset()

    def reset(self) -> None:
        self.phase = PHASE_WARMUP
        self.wait_reason = "Chưa đủ nến để có ATR đầu tiên."
        self.candidate: Optional[Candidate] = None
        self.anchor: Optional[dict[str, Any]] = None

    def threshold(self, close: float, atr: Optional[float]) -> Optional[float]:
        """Δ tại một nến; ``None`` khi không hợp lệ (ATR chưa có hoặc = 0)."""
        if atr is None or not atr > 0:
            return None
        if self.mode == "atr":
            delta = self.k * atr
        else:
            delta = abs(close) * self.pct / 100.0
        return delta if delta > 0 else None

    def _set_candidate(self, side: str, bar: Bar, atr: Optional[float]) -> None:
        delta = self.threshold(bar.close, atr)
        if delta is None:
            self.candidate = None
            self.phase = PHASE_WAIT_ATR
            self.wait_reason = (
                "Cần đặt ứng viên mới tại nến #%d nhưng ATR = 0 — chờ ATR hợp lệ, "
                "không phát pivot với ngưỡng 0." % bar.index
            )
            return
        self.candidate = Candidate(
            side=side,
            price=bar.close,
            index=bar.index,
            bar_time=bar.bar_time,
            close_time=bar.close_time,
            atr=float(atr),
            delta=delta,
            threshold_set_at=bar.close_time,
        )
        self.phase = PHASE_SEEK_HIGH if side == "high" else PHASE_SEEK_LOW
        self.wait_reason = ""

    def update(self, bar: Bar, atr: Optional[float]) -> Optional[DcPivot]:
        close = bar.close
        if self.phase in (PHASE_WARMUP, PHASE_WAIT_ATR):
            if atr is None:
                self.phase = PHASE_WARMUP
                self.wait_reason = "Chưa đủ nến để có ATR đầu tiên."
                return None
            delta = self.threshold(close, atr)
            if delta is None:
                self.phase = PHASE_WAIT_ATR
                self.wait_reason = "ATR = 0 tại nến #%d — chưa khởi tạo detector." % bar.index
                return None
            self.anchor = {
                "price": close,
                "index": bar.index,
                "atr": float(atr),
                "delta": delta,
                "set_at": _iso(bar.close_time),
            }
            self.phase = PHASE_SEEK_DIRECTION
            self.wait_reason = ""
            return None  # nhánh khởi tạo không chọn hướng trong cùng nến

        if self.phase == PHASE_SEEK_DIRECTION:
            a = self.anchor
            assert a is not None
            if close >= a["price"] + a["delta"]:
                self._set_candidate("high", bar, atr)
            elif close <= a["price"] - a["delta"]:
                self._set_candidate("low", bar, atr)
            return None  # chỉ chọn hướng, không phát reversal cùng nến

        c = self.candidate
        assert c is not None
        if self.phase == PHASE_SEEK_HIGH:
            if close > c.price:
                self._set_candidate("high", bar, atr)
                return None
            if close <= c.price - c.delta:
                pivot = self._pivot(c, bar)
                self._set_candidate("low", bar, atr)
                return pivot
            return None
        # PHASE_SEEK_LOW
        if close < c.price:
            self._set_candidate("low", bar, atr)
            return None
        if close >= c.price + c.delta:
            pivot = self._pivot(c, bar)
            self._set_candidate("high", bar, atr)
            return pivot
        return None

    @staticmethod
    def _pivot(c: Candidate, bar: Bar) -> DcPivot:
        return DcPivot(
            kind=c.side,
            price=c.price,
            extreme_index=c.index,
            extreme_bar_time=c.bar_time,
            extreme_close_time=c.close_time,
            atr_at_extreme=c.atr,
            delta=c.delta,
            threshold_set_at=c.threshold_set_at,
            confirm_index=bar.index,
            confirm_close_time=bar.close_time,
            confirm_close=bar.close,
        )

    def snapshot(self) -> dict[str, Any]:
        c = self.candidate
        return {
            "phase": self.phase,
            "phase_vi": PHASE_TEXT_VI[self.phase],
            "ly_do_cho": self.wait_reason or None,
            "anchor": dict(self.anchor) if self.anchor and self.phase == PHASE_SEEK_DIRECTION else None,
            "ung_vien": None if c is None else {
                "side": c.side,
                "candidate_price": c.price,
                "candidate_index": c.index,
                "candidate_time": _iso(c.bar_time),
                "candidate_atr": c.atr,
                "delta_e": c.delta,
                "threshold_set_at": _iso(c.threshold_set_at),
                "muc_xac_nhan": c.price - c.delta if c.side == "high" else c.price + c.delta,
                "ghi_chu_vi": "Ứng viên, có thể thay đổi — chưa phải pivot, không tính vào metric.",
            },
        }
