"""Directional Change theo CLOSE với ngưỡng ATR khoá tại cực trị + regime.

Đặc tả đầy đủ: ``docs/thuat_toan_dc_atr_structure.md`` (lập từ
``docs/plan_dc_atr_trend_range.md``). Tóm tắt thứ tự xử lý tại MỖI nến đóng t:

1. Validate nến (hữu hạn, OHLC hợp lệ, thời gian tăng nghiêm ngặt, đúng bước
   timeframe). Khoảng cách khác bước timeframe → gap: kết thúc segment, bỏ ứng
   viên, ATR, lịch sử pivot/range và warm-up lại (``gap_policy=reset``, mặc định).
   Với ``gap_policy=bridge_short`` (từ v0.2.0), gap ngắn hơn hoặc bằng
   ``bridge_max_gap_hours`` được NỐI: giữ segment, ứng viên, ATR, lịch sử; TR của
   nến đầu sau gap tính với close trước gap (gồm cả bước nhảy giá). Gap dài hơn
   vẫn reset.
2. Cập nhật ATR Wilder (seed = trung bình n TR đầu có close trước) — cần n+1
   nến mỗi segment.
3. Kiểm tra close phá Range đang khoá (classifier), chặn phân loại lại ở nến này.
4. Detector DC cập nhật ứng viên hoặc xác nhận pivot (tối đa một pivot / nến);
   gắn nhãn HH/LH/EQH hoặc HL/LL/EQL so với pivot cùng loại liền trước.
5. Có pivot và không bị chặn → classifier xét Trend, rồi Range, rồi Chưa rõ.
6. Ghi timeline/pending; chỉ phát sự kiện regime khi trạng thái thực sự đổi.

Detector DC:

* Khởi tạo sau warm-up: anchor = close hiện tại, khoá ngưỡng anchor, chờ close
  đi ≥ ngưỡng về một phía để chọn hướng. Không phát pivot ở anchor.
* ``SEEK_HIGH``: close > ứng viên → cập nhật ứng viên và khoá Δ mới tại nến đó;
  ngược lại close ≤ ứng viên − Δ → ``DC_HIGH`` tại ứng viên, chuyển ``SEEK_LOW``
  với ứng viên = close hiện tại. ``SEEK_LOW`` đối xứng.
* Δ = k × ATR[e] (mode ``atr``) hoặc |close[e]| × pct / 100 (mode ``percent``),
  e là nến cực trị. Δ giữ nguyên tới khi có cực trị nghiêm ngặt mới.

Thuật toán nghiên cứu dựa trên luật — không phải AI, không phải công thức ICT
chuẩn, không phải dự báo đảo chiều. Không sao chép code nguồn ngoài; ZigZag /
DC (Tao 2018) chỉ là tài liệu tham khảo nguyên lý.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.algorithms.dc_regime import (
    CLASSIFIER_NAME,
    CLASSIFIER_VERSION,
    DOWNTREND,
    RANGE,
    STATE_TEXT_VI,
    UNKNOWN,
    UPTREND,
    PivotRef,
    RegimeClassifier,
    RegimeParams,
    RegimeTransition,
)
from core.indicators import WilderATRPrevClose
from core.types import (
    TIMEFRAME_SECONDS,
    Bar,
    ReasonCode,
    StructureEvent,
    StructureType,
)

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

#: Trạng thái regime trên timeline khi ATR chưa sẵn sàng (không phải regime).
REGIME_WARMUP = "WARMUP"

GAP_RESET = "reset"
GAP_BRIDGE_SHORT = "bridge_short"
GAP_POLICIES = (GAP_RESET, GAP_BRIDGE_SHORT)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _fmt(x: float) -> str:
    return "%.6g" % x


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


_INT_RE = re.compile(r"^[+-]?\d+$")


class DcAtrStructureAlgorithm(StructureAlgorithm):
    name = "dc_atr_structure"
    display_name_vi = "DC theo close + ATR (Trend/Range, nghiên cứu)"
    version = "0.2.0"
    description_vi = (
        "Directional Change trên giá CLOSE: đỉnh/đáy xác nhận khi close đảo chiều "
        "≥ Δ, Δ = k×ATR (hoặc % close) khoá tại nến cực trị. Gắn HH/HL/LH/LL/EQ, rồi "
        "phân loại Tăng/Giảm/Range/Chưa rõ bằng module riêng từ swing đã xác nhận. "
        "Gap dữ liệu reset segment (hoặc nối gap ngắn nếu chọn). Định nghĩa vận hành của lab, "
        "không phải dự báo."
    )
    emits_types = StructureType.DC_TYPES

    @classmethod
    def param_specs(cls) -> tuple[ParamSpec, ...]:
        return (
            ParamSpec("timeframe", "Khung của dataset", "choice", "M15",
                      choices=tuple(TIMEFRAME_SECONDS),
                      help_vi="Tự điền theo dataset. Dùng để phát hiện gap (khoảng cách "
                              "nến khác bước khung). Sai khung → từ chối chạy."),
            ParamSpec("gap_policy", "Xử lý gap dữ liệu", "choice", GAP_RESET,
                      choices=GAP_POLICIES,
                      help_vi="reset: mọi khoảng cách khác bước khung (kể cả nghỉ phiên) kết thúc "
                              "segment và warm-up lại. bridge_short: nối gap ≤ số giờ bên dưới "
                              "(giữ ứng viên/ATR/lịch sử; TR tính cả bước nhảy qua gap); gap dài "
                              "hơn (vd cuối tuần) vẫn reset."),
            ParamSpec("bridge_max_gap_hours", "Nối gap tối đa (giờ)", "float", 2.0,
                      min=0.0, max=72.0, step=0.25, show_if=("gap_policy", GAP_BRIDGE_SHORT),
                      help_vi="Khoảng từ bar_time nến trước tới nến sau gap. Mặc định 2 giờ: nối "
                              "nghỉ phiên hằng ngày của XAUUSD (~1,25 giờ), reset ở cuối tuần."),
            ParamSpec("price_source", "Giá tìm cực trị", "choice", "close",
                      choices=("close",),
                      help_vi="MVP chỉ dùng CLOSE. OHLC chỉ để tính ATR và vẽ nến. "
                              "Pivot close khác pivot wick."),
            ParamSpec("threshold_mode", "Kiểu ngưỡng đảo chiều", "choice", "atr",
                      choices=("atr", "percent"),
                      help_vi="atr: Δ = k × ATR tại nến cực trị. percent: Δ = |close| × % / 100 "
                              "(đối chứng)."),
            ParamSpec("atr_period", "Chu kỳ ATR (Wilder)", "int", 14, min=2, max=500, step=1,
                      help_vi="Số TR để seed ATR. Cần period+1 nến mỗi segment. Cả mode "
                              "percent cũng warm-up ATR (dùng cho nhãn/range)."),
            ParamSpec("atr_multiplier", "Hệ số k (× ATR)", "float", 1.5, min=0.0, max=50.0,
                      step=0.1, show_if=("threshold_mode", "atr"),
                      help_vi="k > 0. Δ = k × ATR[e], khoá tới khi có cực trị mới."),
            ParamSpec("reversal_pct", "Ngưỡng % đảo chiều", "float", 0.2, min=0.0, max=50.0,
                      step=0.01, show_if=("threshold_mode", "percent"),
                      help_vi="0.2 nghĩa là 0,2% (không phải 20%). Yêu cầu close > 0."),
            ParamSpec("label_tolerance_atr", "Dung sai HH/EQ (× ATR)", "float", 0.1,
                      min=0.0, max=10.0, step=0.05,
                      help_vi="|chênh| ≤ dung sai × ATR tại cực trị hiện tại → EQH/EQL."),
            ParamSpec("range_swings_per_side", "Số đỉnh/đáy cho Range (m)", "int", 3,
                      min=3, max=20, step=1,
                      help_vi="Range xét m đỉnh và m đáy DC gần nhất trong segment."),
            ParamSpec("range_cluster_tolerance_atr", "Độ rộng cụm tối đa (× ATR)", "float",
                      0.5, min=0.0, max=20.0, step=0.05,
                      help_vi="Mỗi cụm đỉnh/đáy phải có max − min ≤ giá trị × ATR."),
            ParamSpec("range_min_width_atr", "Chiều rộng Range tối thiểu (× ATR)", "float",
                      1.0, min=0.0, max=50.0, step=0.1,
                      help_vi="Biên trên − biên dưới ≥ giá trị × ATR (> 0)."),
            ParamSpec("range_break_buffer_atr", "Buffer phá Range (× ATR)", "float", 0.25,
                      min=0.0, max=20.0, step=0.05,
                      help_vi="Close phải vượt biên ± buffer (ATR khoá lúc vào Range). "
                              "Wick không đủ."),
        )

    @classmethod
    def validate_params(cls, raw: dict[str, Any] | None) -> dict[str, Any]:
        raw = dict(raw or {})
        specs = {s.name: s for s in cls.param_specs()}
        unknown = sorted(set(raw) - set(specs))
        if unknown:
            raise ValueError("Tham số không hỗ trợ: %s" % ", ".join(unknown))
        for name, v in raw.items():
            spec = specs[name]
            if spec.type in ("int", "float") and isinstance(v, bool):
                raise ValueError("Tham số '%s' phải là số, nhận bool" % name)
            if spec.type == "int":
                if isinstance(v, float) and not (math.isfinite(v) and v.is_integer()):
                    raise ValueError("Tham số '%s' phải là số nguyên (nhận %r)" % (name, v))
                if isinstance(v, str) and not _INT_RE.match(v.strip()):
                    raise ValueError("Tham số '%s' phải là số nguyên (nhận %r)" % (name, v))
            if spec.type == "float" and isinstance(v, str):
                try:
                    float(v)
                except ValueError as exc:
                    raise ValueError("Tham số '%s' phải là số (nhận %r)" % (name, v)) from exc
        p = super().validate_params(raw)
        for name, spec in specs.items():
            if spec.type == "float" and not math.isfinite(p[name]):
                raise ValueError("Tham số '%s' phải hữu hạn (nhận %r)" % (name, p[name]))
        for name in ("atr_multiplier", "reversal_pct", "range_min_width_atr", "bridge_max_gap_hours"):
            if not p[name] > 0:
                raise ValueError("Tham số '%s' phải > 0 (nhận %s)" % (name, p[name]))
        # Liên trường: tham số của mode không dùng vẫn được lưu nhưng ghi rõ
        # trong manifest là không có hiệu lực.
        return p

    @classmethod
    def check_dataset(cls, timeframe: str, params: dict[str, Any]) -> None:
        tf = (timeframe or "").upper()
        if tf != params.get("timeframe"):
            raise ValueError(
                "dc_atr_structure: tham số timeframe=%s không khớp dataset %s. Chọn lại "
                "khung trong form (dùng để phát hiện gap)." % (params.get("timeframe"), timeframe)
            )

    @classmethod
    def manifest_info(cls, params: dict[str, Any]) -> dict[str, Any]:
        mode = params.get("threshold_mode", "atr")
        return {
            "detector": {"name": cls.name, "version": cls.version},
            "classifier": {"name": CLASSIFIER_NAME, "version": CLASSIFIER_VERSION},
            "price_source": "close",
            "price_source_vi": "Cực trị tìm trên CLOSE; OHLC chỉ dùng cho ATR và vẽ nến.",
            "atr": {
                "loai": "Wilder",
                "period": params.get("atr_period"),
                "seed": WilderATRPrevClose.SEED_METHOD,
                "seed_vi": "Nến đầu segment chỉ lấy close trước; ATR đầu = trung bình n TR "
                           "đầu tiên (cần n+1 nến); sau đó ATR = ((n−1)·ATR + TR)/n.",
            },
            "threshold": {
                "mode": mode,
                "cong_thuc": (
                    "delta_e = atr_multiplier × ATR[e]" if mode == "atr"
                    else "delta_e = |close[e]| × reversal_pct / 100"
                ),
                "khoa": "Khoá tại nến cực trị e tới khi có cực trị nghiêm ngặt mới.",
                "tham_so_khong_hieu_luc": ["reversal_pct"] if mode == "atr" else ["atr_multiplier"],
            },
            "timestamp": "event_time = bar_time nến cực trị (quy ước dataset); confirmed_at = "
                         "close_time nến làm đủ điều kiện đảo chiều.",
            "gap_policy": params.get("gap_policy", GAP_RESET),
            "bridge_max_gap_hours": (
                params.get("bridge_max_gap_hours")
                if params.get("gap_policy") == GAP_BRIDGE_SHORT else None
            ),
            "gap_policy_vi": (
                "Khoảng cách nến khác bước timeframe (kể cả nghỉ phiên, cuối tuần) → kết thúc "
                "segment, bỏ ứng viên/ATR/lịch sử classifier, warm-up lại."
                if params.get("gap_policy", GAP_RESET) == GAP_RESET else
                "Gap ≤ %s giờ được nối: giữ segment, ứng viên, Δ đã khoá, ATR và lịch sử "
                "classifier; TR nến đầu sau gap tính với close trước gap. Gap dài hơn → reset "
                "như policy reset." % params.get("bridge_max_gap_hours")
            ) + " Chưa suy đoán lịch phiên broker; chỉ dựa vào độ dài khoảng trống.",
            "params": dict(params),
            "spec": "docs/thuat_toan_dc_atr_structure.md",
            "tham_khao": [
                "https://www.bracil.net/finance/papers/Tao-PhD2018.pdf",
                "https://github.com/jbn/ZigZag (nguyên lý; không sao chép code)",
            ],
            "ghi_chu_vi": "Thuật toán nghiên cứu dựa trên luật. Trend/Range là định nghĩa "
                          "vận hành của lab, không phải chân lý hay dự báo.",
        }

    # ------------------------------------------------------------------ vòng đời

    def __init__(self, **params: Any) -> None:
        p = self.validate_params(params)
        self.params = p
        self.step_seconds = TIMEFRAME_SECONDS[p["timeframe"]]
        self._step = timedelta(seconds=self.step_seconds)
        self.mode = p["threshold_mode"]
        self.gap_policy = p["gap_policy"]
        self._bridge_max = timedelta(hours=p["bridge_max_gap_hours"])
        self.regime_params = RegimeParams(
            swings_per_side=p["range_swings_per_side"],
            cluster_tolerance_atr=p["range_cluster_tolerance_atr"],
            min_width_atr=p["range_min_width_atr"],
            break_buffer_atr=p["range_break_buffer_atr"],
        )
        self.reset()

    def reset(self) -> None:
        self._segment = 0
        self._segment_start_index: Optional[int] = None
        self._prev_bar: Optional[Bar] = None
        self._n_bars = 0
        self._n_gaps = 0
        self._n_bridged = 0
        self._n_eligible = 0
        self._regime_bars = {UPTREND: 0, DOWNTREND: 0, RANGE: 0, UNKNOWN: 0}
        self._runs: list[tuple[str, int]] = []
        self._run_state: Optional[str] = None
        self._run_len = 0
        self._atr_value: Optional[float] = None
        self._new_segment_state()

    def _new_segment_state(self) -> None:
        p = self.params
        self._atr = WilderATRPrevClose(p["atr_period"])
        self._atr_value = None
        self._det = DcDetector(self.mode, p["atr_multiplier"], p["reversal_pct"])
        self._cls = RegimeClassifier(
            self.regime_params, id_prefix="dc:s%d:" % self._segment
        )
        self._last_pivot: dict[str, Optional[dict[str, Any]]] = {"high": None, "low": None}
        self._last_any_pivot: Optional[dict[str, Any]] = None

    def warmup_bars(self) -> int:
        return self.params["atr_period"] + 1

    # ------------------------------------------------------------------ on_bar

    def _validate_bar(self, bar: Bar) -> None:
        vals = (bar.open, bar.high, bar.low, bar.close)
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals):
            raise ValueError("Nến #%d có giá không hữu hạn (NaN/inf)." % bar.index)
        if not bar.is_valid_ohlc():
            raise ValueError("Nến #%d vi phạm quan hệ OHLC (low ≤ open/close ≤ high)." % bar.index)
        span = (bar.close_time - bar.bar_time).total_seconds()
        if span not in (0, self.step_seconds):
            raise ValueError(
                "Nến #%d không phải khung %s (bar_time→close_time = %ds)."
                % (bar.index, self.params["timeframe"], span)
            )
        if self.mode == "percent" and not bar.close > 0:
            raise ValueError("Mode percent yêu cầu close > 0 (nến #%d close=%s)." % (bar.index, bar.close))
        prev = self._prev_bar
        if prev is not None:
            if bar.index <= prev.index:
                raise ValueError(
                    "Nến phải nạp theo index tăng dần: nhận #%d sau #%d." % (bar.index, prev.index)
                )
            if bar.bar_time <= prev.bar_time:
                raise ValueError(
                    "Timestamp trùng hoặc lùi tại nến #%d (%s ≤ %s). Không tự sắp lại."
                    % (bar.index, _iso(bar.bar_time), _iso(prev.bar_time))
                )

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        self._validate_bar(bar)
        out: list[StructureEvent] = []

        # 1. gap → reset segment
        prev = self._prev_bar
        gap = None if prev is None else bar.bar_time - prev.bar_time
        if gap is not None and gap != self._step and self._bridges(gap):
            self._n_bridged += 1
            out.append(self._bridge_event(bar, prev))
        elif gap is not None and gap != self._step:
            gap_details = self._gap_details(bar, prev)
            self._n_gaps += 1
            self._close_run()
            self._segment += 1
            self._new_segment_state()
            self._segment_start_index = bar.index
            out.append(self._gap_event(bar, gap_details))
        if self._segment_start_index is None:
            self._segment_start_index = bar.index
        self._prev_bar = bar
        self._n_bars += 1

        # 2. ATR
        atr = self._atr.update(bar.high, bar.low, bar.close)
        self._atr_value = atr

        # 3. phá Range đã khoá (close hiện tại)
        tr = self._cls.check_range_break(bar.index, bar.close)
        if tr is not None:
            out.append(self._regime_event(tr, bar))

        # 4. DC
        pivot = self._det.update(bar, atr)
        if pivot is not None:
            ev, ref = self._pivot_event(pivot, bar, atr)
            out.append(ev)
            # 5. classifier (tự bỏ qua nếu nến vừa phá Range)
            tr2 = self._cls.on_pivot(ref, bar.index, bar.close, atr)
            if tr2 is not None:
                out.append(self._regime_event(tr2, bar))

        # 6. thống kê thời gian theo regime (chỉ nến đã có ATR)
        if atr is not None:
            self._n_eligible += 1
            st = self._cls.state
            self._regime_bars[st] += 1
            if st == self._run_state:
                self._run_len += 1
            else:
                self._close_run()
                self._run_state = st
                self._run_len = 1
        return out

    def _close_run(self) -> None:
        if self._run_state is not None and self._run_len > 0:
            self._runs.append((self._run_state, self._run_len))
        self._run_state = None
        self._run_len = 0

    # ------------------------------------------------------------------ events

    def _event(
        self,
        stype: str,
        *,
        key: str,
        price: float,
        event_index: int,
        event_time: datetime,
        event_close_time: datetime,
        bar: Bar,
        reason: str,
        direction: Optional[str] = None,
        ref: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> StructureEvent:
        d = {"segment": self._segment}
        if details:
            d.update(details)
        return StructureEvent(
            event_id="dc:s%d:%s:%s" % (self._segment, stype, key),
            structure_type=stype,
            price=float(price),
            event_bar_index=event_index,
            event_time=event_time,
            event_close_time=event_close_time,
            confirmed_bar_index=bar.index,
            confirmed_at=bar.close_time,
            algorithm=self.name,
            algorithm_version=self.version,
            reason_code=reason,
            direction=direction,
            reference_event_id=ref,
            details=d,
        )

    def _bridges(self, gap: timedelta) -> bool:
        """``bridge_short``: nối gap dương không dài hơn ngưỡng. ``reset``: không bao giờ."""
        return self.gap_policy == GAP_BRIDGE_SHORT and self._step < gap <= self._bridge_max

    def _bridge_event(self, bar: Bar, prev: Bar) -> StructureEvent:
        gap_s = (bar.bar_time - prev.bar_time).total_seconds()
        return self._event(
            StructureType.DC_GAP_BRIDGED,
            key=str(bar.index),
            price=bar.close,
            event_index=bar.index,
            event_time=bar.bar_time,
            event_close_time=bar.close_time,
            bar=bar,
            reason=ReasonCode.DC_GAP_BRIDGED,
            details={
                "nen_truoc_gap": prev.index,
                "bar_time_truoc_gap": _iso(prev.bar_time),
                "bar_time_sau_gap": _iso(bar.bar_time),
                "khoang_cach_giay": gap_s,
                "so_buoc_khung": gap_s / self.step_seconds,
                "close_truoc_gap": prev.close,
                "buoc_nhay_open": bar.open - prev.close,
                "regime_luc_noi": REGIME_WARMUP if self._atr_value is None else self._cls.state,
                "ung_vien_giu_nguyen": self._det.snapshot()["ung_vien"],
                "gap_policy": self.gap_policy,
                "bridge_max_gap_hours": self.params["bridge_max_gap_hours"],
            },
        )

    def _gap_details(self, bar: Bar, prev: Bar) -> dict[str, Any]:
        """Chụp trạng thái segment cũ TRƯỚC khi reset (để giải thích trên UI)."""
        gap_s = (bar.bar_time - prev.bar_time).total_seconds()
        return {
            "segment_cu": self._segment,
            "segment_moi": self._segment + 1,
            "nen_truoc_gap": prev.index,
            "bar_time_truoc_gap": _iso(prev.bar_time),
            "bar_time_sau_gap": _iso(bar.bar_time),
            "khoang_cach_giay": gap_s,
            "so_buoc_khung": gap_s / self.step_seconds,
            "regime_truoc_gap": REGIME_WARMUP if self._atr_value is None else self._cls.state,
            "ung_vien_bi_bo": self._det.snapshot()["ung_vien"],
            "gap_policy": self.gap_policy,
            "bridge_max_gap_hours": self.params["bridge_max_gap_hours"]
            if self.gap_policy == GAP_BRIDGE_SHORT else None,
        }

    def _gap_event(self, bar: Bar, details: dict[str, Any]) -> StructureEvent:
        return self._event(
            StructureType.DC_SEGMENT_GAP,
            key=str(bar.index),
            price=bar.close,
            event_index=bar.index,
            event_time=bar.bar_time,
            event_close_time=bar.close_time,
            bar=bar,
            reason=ReasonCode.DC_GAP_RESET,
            details=details,
        )

    def _pivot_event(
        self, pv: DcPivot, bar: Bar, atr_now: Optional[float]
    ) -> tuple[StructureEvent, PivotRef]:
        is_high = pv.kind == "high"
        stype = StructureType.DC_HIGH if is_high else StructureType.DC_LOW
        key = "%d>%d" % (pv.extreme_index, pv.confirm_index)
        event_id = "dc:s%d:%s:%s" % (self._segment, stype, key)

        prev = self._last_pivot[pv.kind]
        label = label_code = None
        tol = diff = None
        if prev is not None:
            tol = self.params["label_tolerance_atr"] * pv.atr_at_extreme
            diff = pv.price - prev["price"]
            if pv.price > prev["price"] + tol:
                label, label_code = (("HH", ReasonCode.SEQ_HIGHER_HIGH) if is_high
                                     else ("HL", ReasonCode.SEQ_HIGHER_LOW))
            elif pv.price < prev["price"] - tol:
                label, label_code = (("LH", ReasonCode.SEQ_LOWER_HIGH) if is_high
                                     else ("LL", ReasonCode.SEQ_LOWER_LOW))
            else:
                label, label_code = (("EQH", ReasonCode.SEQ_EQUAL_HIGH) if is_high
                                     else ("EQL", ReasonCode.SEQ_EQUAL_LOW))

        if self.mode == "atr":
            formula = "Δ = k × ATR%d[e] = %s × %s = %s" % (
                self.params["atr_period"], _fmt(self.params["atr_multiplier"]),
                _fmt(pv.atr_at_extreme), _fmt(pv.delta))
        else:
            formula = "Δ = |close[e]| × %s%% = %s × %s / 100 = %s" % (
                _fmt(self.params["reversal_pct"]), _fmt(pv.price),
                _fmt(self.params["reversal_pct"]), _fmt(pv.delta))
        level = pv.price - pv.delta if is_high else pv.price + pv.delta
        rule = ("close[t] = %s ≤ %s − %s = %s" if is_high else "close[t] = %s ≥ %s + %s = %s") % (
            _fmt(pv.confirm_close), _fmt(pv.price), _fmt(pv.delta), _fmt(level))

        prev_same_segment_any = self._last_any_pivot
        amplitude = None
        if prev_same_segment_any is not None and prev_same_segment_any["atr"] > 0:
            amplitude = {
                "tu_pivot": prev_same_segment_any["id"],
                "bien_do": abs(pv.price - prev_same_segment_any["price"]),
                "atr_pivot_dau": prev_same_segment_any["atr"],
                "bien_do_atr": abs(pv.price - prev_same_segment_any["price"]) / prev_same_segment_any["atr"],
            }

        details = {
            "price_source": "close",
            "gia_theo": "close",
            "threshold_mode": self.mode,
            "atr_period": self.params["atr_period"],
            "atr_multiplier": self.params["atr_multiplier"] if self.mode == "atr" else None,
            "reversal_pct": self.params["reversal_pct"] if self.mode == "percent" else None,
            "candidate_index": pv.extreme_index,
            "candidate_atr": pv.atr_at_extreme,
            "delta_e": pv.delta,
            "threshold_set_at": _iso(pv.threshold_set_at),
            "cong_thuc_nguong": formula,
            "dieu_kien_xac_nhan": rule,
            "muc_xac_nhan": level,
            "confirmation_close": pv.confirm_close,
            "reversal_distance": pv.reversal_distance,
            "reversal_distance_atr": pv.reversal_distance / pv.atr_at_extreme,
            "atr_luc_xac_nhan": atr_now,
            "lag_bars": pv.confirm_index - pv.extreme_index,
            "lag_seconds": (pv.confirm_close_time - pv.extreme_close_time).total_seconds(),
            "nhan": label,
            "nhan_reason_code": label_code,
            "nhan_tham_chieu": prev["id"] if prev else None,
            "nhan_gia_truoc": prev["price"] if prev else None,
            "nhan_gia_nay": pv.price,
            "nhan_chenh_lech": diff,
            "nhan_dung_sai": tol,
            "nhip": amplitude,
        }
        ev = self._event(
            stype,
            key=key,
            price=pv.price,
            event_index=pv.extreme_index,
            event_time=pv.extreme_bar_time,
            event_close_time=pv.extreme_close_time,
            bar=bar,
            reason=(ReasonCode.DC_CLOSE_REVERSAL_FROM_HIGH if is_high
                    else ReasonCode.DC_CLOSE_REVERSAL_FROM_LOW),
            direction="up" if is_high else "down",
            ref=prev["id"] if prev else None,
            details=details,
        )
        rec = {
            "id": event_id,
            "price": pv.price,
            "atr": pv.atr_at_extreme,
            "index": pv.extreme_index,
            "time": int(pv.extreme_bar_time.timestamp()),
            "kind": pv.kind,
            "label": label,
        }
        self._last_pivot[pv.kind] = rec
        self._last_any_pivot = rec
        ref = PivotRef(
            pivot_id=event_id,
            kind=pv.kind,
            price=pv.price,
            label=label,
            extreme_index=pv.extreme_index,
            confirmed_index=pv.confirm_index,
        )
        return ev, ref

    def _regime_event(self, tr: RegimeTransition, bar: Bar) -> StructureEvent:
        if tr.kind == "RANGE_START":
            stype = StructureType.DC_RANGE_START
        elif tr.kind == "RANGE_EXIT":
            stype = StructureType.DC_RANGE_EXIT
        elif tr.to_state == UPTREND:
            stype = StructureType.DC_REGIME_UP
        elif tr.to_state == DOWNTREND:
            stype = StructureType.DC_REGIME_DOWN
        else:
            stype = StructureType.DC_REGIME_UNKNOWN
        direction = None
        if tr.to_state == UPTREND:
            direction = "up"
        elif tr.to_state == DOWNTREND:
            direction = "down"
        elif tr.kind == "RANGE_EXIT":
            direction = tr.details.get("huong_pha")
        details = {
            "tu_trang_thai": tr.from_state,
            "sang_trang_thai": tr.to_state,
            "sang_trang_thai_vi": STATE_TEXT_VI[tr.to_state],
            "giai_thich_vi": tr.reason_vi,
            "atr_luc_danh_gia": self._atr_value,
            "classifier_version": CLASSIFIER_VERSION,
            "ghi_chu_vi": "Trạng thái bắt đầu từ lúc biết (nến này), không tô ngược về nến cực trị.",
        }
        details.update(tr.details)
        evidence = details.get("bang_chung") or []
        ref = evidence[0] if evidence else None
        return self._event(
            stype,
            key=str(bar.index),
            price=tr.close,
            event_index=bar.index,
            event_time=bar.bar_time,
            event_close_time=bar.close_time,
            bar=bar,
            reason=tr.reason_code,
            direction=direction,
            ref=ref,
            details=details,
        )

    # ------------------------------------------------------------------ hiển thị

    def _regime_label(self) -> str:
        return REGIME_WARMUP if self._atr_value is None else self._cls.state

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        c = self._det.candidate
        rng = self._cls.active_range
        last = self._last_any_pivot
        return {
            "dc_segment": self._segment,
            "dc_phase": self._det.phase,
            "regime": self._regime_label(),
            "atr": self._atr_value,
            "dc_threshold": c.delta if c else None,
            "dc_cand_price": c.price if c else None,
            "dc_cand_index": c.index if c else None,
            "dc_cand_side": c.side if c else None,
            "dc_cand_time": int(c.bar_time.timestamp()) if c else None,
            "dc_last_pivot_price": last["price"] if last else None,
            "dc_last_pivot_time": last["time"] if last else None,
            "range_upper": rng.upper if rng else None,
            "range_lower": rng.lower if rng else None,
            "range_buffer": rng.buffer if rng else None,
            "range_id": rng.range_id if rng else None,
        }

    def pending_state(self) -> dict[str, Any]:
        det = self._det.snapshot()
        return {
            "dc": det,
            "regime": self._regime_label(),
            "regime_vi": ("Warm-up (chưa có ATR)" if self._atr_value is None
                          else STATE_TEXT_VI[self._cls.state]),
            "classifier": self._cls.snapshot(),
            "atr_hien_tai": self._atr_value,
            "segment": self._segment,
            "segment_bat_dau_tu_nen": self._segment_start_index,
            "so_gap": self._n_gaps,
            "so_segment": self._segment + 1 if self._n_bars else 0,
            "so_nen_da_xu_ly": self._n_bars,
            "so_nen_du_dieu_kien": self._n_eligible,
            "pivot_cuoi": dict(self._last_any_pivot) if self._last_any_pivot else None,
            "gap_policy": self.gap_policy,
            "so_gap_noi": self._n_bridged,
            "ghi_chu_vi": (
                "Trạng thái theo swing ĐÃ XÁC NHẬN — không phản ánh mọi thay đổi trong nến. "
                "Ứng viên chưa phải pivot."
            ),
        }

    def run_stats(self, events: list[StructureEvent]) -> Optional[dict[str, Any]]:
        from core.eval.dc_metrics import dc_run_metrics

        runs = list(self._runs)
        if self._run_state is not None and self._run_len:
            runs.append((self._run_state, self._run_len))
        return dc_run_metrics(
            [e.to_dict() for e in events],
            n_bars=self._n_bars,
            n_eligible=self._n_eligible,
            n_gaps=self._n_gaps,
            n_bridged=self._n_bridged,
            gap_policy=self.gap_policy,
            n_segments=self._segment + 1 if self._n_bars else 0,
            regime_bars=dict(self._regime_bars),
            regime_runs=runs,
            step_seconds=self.step_seconds,
        )
