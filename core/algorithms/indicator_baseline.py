"""Baseline chỉ báo: độ dốc SMA/ATR + ADX + bề rộng Donchian.

Đối chứng đơn giản theo mục 13 tài liệu nhóm — không phải bộ phân loại
regime của sản phẩm. Đặc tả: ``docs/thuat_toan_indicator_baseline.md``.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Optional

from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.indicators import DonchianWidth, SMA, WilderADX, WilderATR
from core.types import Bar, ReasonCode, StructureEvent, StructureType


_CLASS_TO_TYPE = {
    "up": StructureType.BASELINE_UP,
    "down": StructureType.BASELINE_DOWN,
    "range": StructureType.BASELINE_RANGE,
    "uncertain": StructureType.BASELINE_UNCERTAIN,
}


class IndicatorBaselineAlgorithm(StructureAlgorithm):
    name = "indicator_baseline"
    display_name_vi = "Baseline chỉ báo (SMA/ATR, ADX, Donchian)"
    version = "1.0.0"
    description_vi = (
        "Đối chứng: phân loại up/down/range/uncertain từ độ dốc SMA chuẩn hoá "
        "ATR (Wilder), ADX Wilder và bề rộng Donchian/ATR. Không dùng TA-Lib."
    )

    @classmethod
    def param_specs(cls) -> tuple[ParamSpec, ...]:
        return (
            ParamSpec("sma_period", "Chu kỳ SMA", "int", 20, min=2, max=500, step=1,
                      help_vi="SMA close, MODE_SMA (trung bình cộng), không EMA."),
            ParamSpec("slope_lookback", "Lookback độ dốc SMA (nến)", "int", 5, min=1, max=100, step=1,
                      help_vi="slope = SMA[t] - SMA[t - lookback]."),
            ParamSpec("atr_period", "Chu kỳ ATR Wilder", "int", 14, min=1, max=200, step=1,
                      help_vi="Smoothing Wilder như iATR MQL5, không phải EMA 2/(n+1)."),
            ParamSpec("adx_period", "Chu kỳ ADX Wilder", "int", 14, min=2, max=200, step=1,
                      help_vi="Smoothing Wilder như iADX. Warm-up 2*period nến."),
            ParamSpec("range_period", "Chu kỳ Donchian", "int", 20, min=2, max=500, step=1,
                      help_vi="Bề rộng = max(high) - min(low) trên cửa sổ này."),
            ParamSpec("slope_min", "Ngưỡng |độ dốc|/ATR tối thiểu", "float", 0.15, min=0.0, step=0.01,
                      help_vi="Cần |SMA_t - SMA_{t-k}| / ATR >= ngưỡng (và ADX đủ) để gắn up/down."),
            ParamSpec("adx_trend_min", "Ngưỡng ADX tối thiểu cho hướng", "float", 20.0, min=0.0, step=0.5,
                      help_vi="ADX >= ngưỡng mới được phân loại up/down."),
            ParamSpec("range_narrow_max", "Ngưỡng Donchian/ATR tối đa cho range", "float", 3.0, min=0.0, step=0.1,
                      help_vi="range_width/ATR <= ngưỡng và ADX < adx_trend_min → range."),
        )

    def __init__(self, **params: Any) -> None:
        p = self.validate_params(params)
        self.sma_period: int = p["sma_period"]
        self.slope_lookback: int = p["slope_lookback"]
        self.atr_period: int = p["atr_period"]
        self.adx_period: int = p["adx_period"]
        self.range_period: int = p["range_period"]
        self.slope_min: float = p["slope_min"]
        self.adx_trend_min: float = p["adx_trend_min"]
        self.range_narrow_max: float = p["range_narrow_max"]
        self.params: dict[str, Any] = p
        self.reset()

    def reset(self) -> None:
        self._bars: list[Bar] = []
        self._sma = SMA(self.sma_period)
        self._atr = WilderATR(self.atr_period)
        self._adx = WilderADX(self.adx_period)
        self._donchian = DonchianWidth(self.range_period)
        self._sma_hist: deque[float] = deque(maxlen=self.slope_lookback + 1)
        self._last_class: Optional[str] = None
        self._emitted_ids: set[str] = set()
        self._last_point: Optional[dict[str, Any]] = None

    def warmup_bars(self) -> int:
        return max(
            self.sma_period + self.slope_lookback,
            self.atr_period,
            2 * self.adx_period,
            self.range_period,
        )

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        if self._bars and bar.index <= self._bars[-1].index:
            raise ValueError(
                "Nến phải được nạp theo thứ tự tăng dần: nhận index=%s sau index=%s"
                % (bar.index, self._bars[-1].index)
            )
        self._bars.append(bar)

        sma = self._sma.update(bar.close)
        atr = self._atr.update(bar.high, bar.low, bar.close)
        adx = self._adx.update(bar.high, bar.low, bar.close)
        width = self._donchian.update(bar.high, bar.low)
        if sma is not None:
            self._sma_hist.append(sma)

        slope = None
        slope_norm = None
        if sma is not None and len(self._sma_hist) > self.slope_lookback:
            slope = sma - self._sma_hist[0]
            if atr not in (None, 0):
                slope_norm = slope / atr

        width_norm = None
        if width is not None and atr not in (None, 0):
            width_norm = width / atr

        klass = self._classify(slope_norm, adx, width_norm)
        self._last_point = {
            "sma": sma,
            "atr": atr,
            "adx": adx,
            "plus_di": self._adx.plus_di,
            "minus_di": self._adx.minus_di,
            "slope": slope,
            "slope_norm": slope_norm,
            "range_width": width,
            "range_width_norm": width_norm,
            "class": klass,
        }

        if klass is None:
            return []
        if klass == self._last_class:
            return []
        self._last_class = klass
        stype = _CLASS_TO_TYPE[klass]
        event_id = "%s@%d>%d" % (stype, bar.index, bar.index)
        self._emitted_ids.add(event_id)
        return [
            StructureEvent(
                event_id=event_id,
                structure_type=stype,
                price=bar.close,
                event_bar_index=bar.index,
                event_time=bar.bar_time,
                event_close_time=bar.close_time,
                confirmed_bar_index=bar.index,
                confirmed_at=bar.close_time,
                algorithm=self.name,
                algorithm_version=self.version,
                reason_code=ReasonCode.BASELINE_RULE_CROSS,
                direction="up" if klass == "up" else ("down" if klass == "down" else None),
                details={
                    "class": klass,
                    "sma": sma,
                    "atr": atr,
                    "adx": adx,
                    "plus_di": self._adx.plus_di,
                    "minus_di": self._adx.minus_di,
                    "slope": slope,
                    "slope_norm": slope_norm,
                    "range_width": width,
                    "range_width_norm": width_norm,
                    "nguong": {
                        "slope_min": self.slope_min,
                        "adx_trend_min": self.adx_trend_min,
                        "range_narrow_max": self.range_narrow_max,
                    },
                    "smoothing": "Wilder ATR/ADX; SMA không EMA",
                },
            )
        ]

    def _classify(
        self,
        slope_norm: Optional[float],
        adx: Optional[float],
        width_norm: Optional[float],
    ) -> Optional[str]:
        if slope_norm is None or adx is None or width_norm is None:
            return None
        if adx >= self.adx_trend_min and abs(slope_norm) >= self.slope_min:
            return "up" if slope_norm > 0 else "down"
        if width_norm <= self.range_narrow_max and adx < self.adx_trend_min:
            return "range"
        return "uncertain"

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        return dict(self._last_point) if self._last_point else None

    def pending_state(self) -> dict[str, Any]:
        p = self._last_point or {}
        return {
            "so_nen_da_xu_ly": len(self._bars),
            "class": p.get("class"),
            "adx": p.get("adx"),
            "slope_norm": p.get("slope_norm"),
            "range_width_norm": p.get("range_width_norm"),
            "warming_up": p.get("class") is None,
        }
