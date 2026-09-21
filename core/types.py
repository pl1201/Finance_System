"""Kiểu dữ liệu dùng chung cho lõi thuật toán cấu trúc thị trường.

Lõi này KHÔNG phụ thuộc web framework, notebook hay MT5. Chỉ dùng thư viện
chuẩn Python để có thể tái sử dụng ở bất kỳ môi trường nào.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# --------------------------------------------------------------------------
# Timeframe
# --------------------------------------------------------------------------

#: Các timeframe được hỗ trợ và độ dài tương ứng (giây).
TIMEFRAME_SECONDS: dict[str, int] = {
    "M1": 60,
    "M5": 5 * 60,
    "M15": 15 * 60,
    "M30": 30 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}


def timeframe_delta(timeframe: str) -> timedelta:
    """Độ dài một nến của timeframe."""
    tf = (timeframe or "").upper().strip()
    if tf not in TIMEFRAME_SECONDS:
        raise ValueError(
            "Timeframe khong ho tro: %r. Ho tro: %s"
            % (timeframe, ", ".join(TIMEFRAME_SECONDS))
        )
    return timedelta(seconds=TIMEFRAME_SECONDS[tf])


#: Quy ước timestamp của nến: mốc mở nến hay mốc đóng nến.
TIMESTAMP_CONVENTIONS = ("open", "close")


# --------------------------------------------------------------------------
# Bar
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Bar:
    """Một nến ĐÃ ĐÓNG.

    ``bar_time``  : timestamp của nến theo quy ước dataset (UTC, tz-aware).
    ``close_time``: thời điểm nến đóng (UTC, tz-aware). Với quy ước ``open``
                    thì ``close_time = bar_time + timeframe``; với quy ước
                    ``close`` thì ``close_time = bar_time``.

    Lõi thuật toán luôn dùng ``close_time`` làm mốc "thời điểm thông tin
    khả dụng", không dùng ``bar_time``.
    """

    index: int
    bar_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def is_valid_ohlc(self) -> bool:
        return (
            self.low <= self.open <= self.high
            and self.low <= self.close <= self.high
            and self.low <= self.high
        )


def build_bars(
    rows: list[dict[str, Any]],
    timeframe: str,
    timestamp_convention: str,
) -> list[Bar]:
    """Dựng danh sách ``Bar`` từ các dict đã chuẩn hoá (``bar_time`` là UTC)."""
    if timestamp_convention not in TIMESTAMP_CONVENTIONS:
        raise ValueError(
            "timestamp_convention phai la 'open' hoac 'close', nhan %r"
            % (timestamp_convention,)
        )
    delta = timeframe_delta(timeframe)
    bars: list[Bar] = []
    for i, r in enumerate(rows):
        bt: datetime = r["bar_time"]
        if bt.tzinfo is None:
            bt = bt.replace(tzinfo=timezone.utc)
        ct = bt + delta if timestamp_convention == "open" else bt
        bars.append(
            Bar(
                index=i,
                bar_time=bt,
                close_time=ct,
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=float(r.get("volume") or 0.0),
            )
        )
    return bars


# --------------------------------------------------------------------------
# Structure event
# --------------------------------------------------------------------------


class StructureType:
    """Từ điển loại cấu trúc do thuật toán swing pivot sinh ra."""

    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    SWING_HIGH_L2 = "SWING_HIGH_L2"
    SWING_LOW_L2 = "SWING_LOW_L2"
    HH = "HH"          # higher high
    LH = "LH"          # lower high
    EQH = "EQH"        # equal high — KHÔNG ép thành HH/LH
    HL = "HL"          # higher low
    LL = "LL"          # lower low
    EQL = "EQL"        # equal low — KHÔNG ép thành HL/LL
    BOS_UP = "BOS_UP"
    BOS_DOWN = "BOS_DOWN"
    BOS_INTERNAL_UP = "BOS_INTERNAL_UP"
    BOS_INTERNAL_DOWN = "BOS_INTERNAL_DOWN"
    CHOCH_UP = "CHOCH_UP"
    CHOCH_DOWN = "CHOCH_DOWN"
    BASELINE_UP = "BASELINE_UP"
    BASELINE_DOWN = "BASELINE_DOWN"
    BASELINE_RANGE = "BASELINE_RANGE"
    BASELINE_UNCERTAIN = "BASELINE_UNCERTAIN"
    HMM_STATE_CHANGE = "HMM_STATE_CHANGE"

    ALL = (
        SWING_HIGH, SWING_LOW, SWING_HIGH_L2, SWING_LOW_L2,
        HH, LH, EQH, HL, LL, EQL,
        BOS_UP, BOS_DOWN, BOS_INTERNAL_UP, BOS_INTERNAL_DOWN,
        CHOCH_UP, CHOCH_DOWN,
        BASELINE_UP, BASELINE_DOWN, BASELINE_RANGE, BASELINE_UNCERTAIN,
        HMM_STATE_CHANGE,
    )


class ReasonCode:
    """Mã lý do để truy vết vì sao một sự kiện được sinh ra."""

    PIVOT_HIGH_STRICT = "PIVOT_HIGH_STRICT"
    PIVOT_LOW_STRICT = "PIVOT_LOW_STRICT"
    SEQ_HIGHER_HIGH = "SEQ_HIGHER_HIGH"
    SEQ_LOWER_HIGH = "SEQ_LOWER_HIGH"
    SEQ_EQUAL_HIGH = "SEQ_EQUAL_HIGH"
    SEQ_HIGHER_LOW = "SEQ_HIGHER_LOW"
    SEQ_LOWER_LOW = "SEQ_LOWER_LOW"
    SEQ_EQUAL_LOW = "SEQ_EQUAL_LOW"
    BOS_CLOSE_ABOVE_SWING_HIGH = "BOS_CLOSE_ABOVE_SWING_HIGH"
    BOS_CLOSE_BELOW_SWING_LOW = "BOS_CLOSE_BELOW_SWING_LOW"
    BOS_INTERNAL_CLOSE_ABOVE = "BOS_INTERNAL_CLOSE_ABOVE"
    BOS_INTERNAL_CLOSE_BELOW = "BOS_INTERNAL_CLOSE_BELOW"
    CHOCH_CLOSE_ABOVE_SWING_HIGH = "CHOCH_CLOSE_ABOVE_SWING_HIGH"
    CHOCH_CLOSE_BELOW_SWING_LOW = "CHOCH_CLOSE_BELOW_SWING_LOW"
    BASELINE_RULE_CROSS = "BASELINE_RULE_CROSS"
    HMM_FILTERED_STATE_CHANGE = "HMM_FILTERED_STATE_CHANGE"
    PIVOT_HIGH_L2 = "PIVOT_HIGH_L2"
    PIVOT_LOW_L2 = "PIVOT_LOW_L2"
    SEQ_HIGHER_HIGH_L2 = "SEQ_HIGHER_HIGH_L2"
    SEQ_LOWER_HIGH_L2 = "SEQ_LOWER_HIGH_L2"
    SEQ_EQUAL_HIGH_L2 = "SEQ_EQUAL_HIGH_L2"
    SEQ_HIGHER_LOW_L2 = "SEQ_HIGHER_LOW_L2"
    SEQ_LOWER_LOW_L2 = "SEQ_LOWER_LOW_L2"
    SEQ_EQUAL_LOW_L2 = "SEQ_EQUAL_LOW_L2"


#: Giải thích tiếng Việt cho từng mã lý do (dùng cho tooltip giao diện).
REASON_TEXT_VI: dict[str, str] = {
    ReasonCode.PIVOT_HIGH_STRICT: (
        "High của nến pivot LỚN HƠN TUYỆT ĐỐI mọi high trong cửa sổ trái/phải. "
        "Trường hợp bằng nhau không được nhận là pivot ở phiên bản này."
    ),
    ReasonCode.PIVOT_LOW_STRICT: (
        "Low của nến pivot NHỎ HƠN TUYỆT ĐỐI mọi low trong cửa sổ trái/phải. "
        "Trường hợp bằng nhau không được nhận là pivot ở phiên bản này."
    ),
    ReasonCode.SEQ_HIGHER_HIGH: (
        "Swing high đã xác nhận CAO HƠN swing high đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_LOWER_HIGH: (
        "Swing high đã xác nhận THẤP HƠN swing high đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_EQUAL_HIGH: (
        "Hai swing high liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQH, không ép thành HH hoặc LH."
    ),
    ReasonCode.SEQ_HIGHER_LOW: (
        "Swing low đã xác nhận CAO HƠN swing low đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_LOWER_LOW: (
        "Swing low đã xác nhận THẤP HƠN swing low đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_EQUAL_LOW: (
        "Hai swing low liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQL, không ép thành HL hoặc LL."
    ),
    ReasonCode.BOS_CLOSE_ABOVE_SWING_HIGH: (
        "Giá ĐÓNG CỬA vượt lên trên mức swing high đã xác nhận (cộng biên phá vỡ). "
        "Mỗi mức chỉ phát tín hiệu một lần."
    ),
    ReasonCode.BOS_CLOSE_BELOW_SWING_LOW: (
        "Giá ĐÓNG CỬA xuống dưới mức swing low đã xác nhận (trừ biên phá vỡ). "
        "Mỗi mức chỉ phát tín hiệu một lần. Đây là BOS chính hoặc BOS khi chưa có bias."
    ),
    ReasonCode.BOS_INTERNAL_CLOSE_ABOVE: (
        "Giá đóng cửa vượt đỉnh swing nội bộ (không phải mức high cực trị còn nguyên). "
        "Chưa phá mức chính."
    ),
    ReasonCode.BOS_INTERNAL_CLOSE_BELOW: (
        "Giá đóng cửa thủng đáy swing nội bộ (không phải mức low cực trị còn nguyên). "
        "Chưa phá mức chính."
    ),
    ReasonCode.CHOCH_CLOSE_ABOVE_SWING_HIGH: (
        "CHoCH tăng: giá đóng cửa phá mức swing high CHÍNH trong lúc bias đang giảm. "
        "Bias chuyển sang tăng sau nến này."
    ),
    ReasonCode.CHOCH_CLOSE_BELOW_SWING_LOW: (
        "CHoCH giảm: giá đóng cửa phá mức swing low CHÍNH trong lúc bias đang tăng. "
        "Bias chuyển sang giảm sau nến này."
    ),
    ReasonCode.BASELINE_RULE_CROSS: (
        "Phân loại baseline chỉ báo thay đổi: độ dốc SMA chuẩn hoá ATR, ADX và "
        "bề rộng vùng giá (Donchian/ATR) thỏa bộ ngưỡng đã khai báo."
    ),
    ReasonCode.HMM_FILTERED_STATE_CHANGE: (
        "State MAP của bộ lọc HMM online (bước forward) thay đổi so với nến trước. "
        "Không dùng smoothing/Viterbi trên toàn chuỗi."
    ),
    ReasonCode.PIVOT_HIGH_L2: (
        "Đỉnh cấp 2: pivot cấp 1 giữa cao hơn tuyệt đối hai đỉnh cấp 1 liền kề "
        "trên chuỗi pivot (không phải ba nến liên tiếp). Chỉ xác nhận khi đỉnh "
        "cấp 1 bên phải đã xác nhận — không gắn về lúc đỉnh giữa hình thành."
    ),
    ReasonCode.PIVOT_LOW_L2: (
        "Đáy cấp 2: pivot cấp 1 giữa thấp hơn tuyệt đối hai đáy cấp 1 liền kề "
        "trên chuỗi pivot. Chỉ xác nhận khi đáy cấp 1 bên phải đã xác nhận."
    ),
    ReasonCode.SEQ_HIGHER_HIGH_L2: (
        "Đỉnh cấp 2 vừa xác nhận CAO HƠN đỉnh cấp 2 đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_LOWER_HIGH_L2: (
        "Đỉnh cấp 2 vừa xác nhận THẤP HƠN đỉnh cấp 2 đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_EQUAL_HIGH_L2: (
        "Hai đỉnh cấp 2 liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQH, không ép thành HH hoặc LH."
    ),
    ReasonCode.SEQ_HIGHER_LOW_L2: (
        "Đáy cấp 2 vừa xác nhận CAO HƠN đáy cấp 2 đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_LOWER_LOW_L2: (
        "Đáy cấp 2 vừa xác nhận THẤP HƠN đáy cấp 2 đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_EQUAL_LOW_L2: (
        "Hai đáy cấp 2 liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQL, không ép thành HL hoặc LL."
    ),
}

#: Giải thích tiếng Việt cho từng loại cấu trúc.
STRUCTURE_TEXT_VI: dict[str, str] = {
    StructureType.SWING_HIGH: "Đỉnh swing đã xác nhận",
    StructureType.SWING_LOW: "Đáy swing đã xác nhận",
    StructureType.SWING_HIGH_L2: "Đỉnh swing cấp 2 (lọc trên chuỗi đỉnh cấp 1)",
    StructureType.SWING_LOW_L2: "Đáy swing cấp 2 (lọc trên chuỗi đáy cấp 1)",
    StructureType.HH: "Đỉnh cao hơn (Higher High)",
    StructureType.LH: "Đỉnh thấp hơn (Lower High)",
    StructureType.EQH: "Đỉnh bằng nhau (Equal High)",
    StructureType.HL: "Đáy cao hơn (Higher Low)",
    StructureType.LL: "Đáy thấp hơn (Lower Low)",
    StructureType.EQL: "Đáy bằng nhau (Equal Low)",
    StructureType.BOS_UP: "Phá vỡ cấu trúc chính lên (BOS tăng)",
    StructureType.BOS_DOWN: "Phá vỡ cấu trúc chính xuống (BOS giảm)",
    StructureType.BOS_INTERNAL_UP: "BOS nội bộ lên",
    StructureType.BOS_INTERNAL_DOWN: "BOS nội bộ xuống",
    StructureType.CHOCH_UP: "Đổi hướng cấu trúc lên (CHoCH tăng)",
    StructureType.CHOCH_DOWN: "Đổi hướng cấu trúc xuống (CHoCH giảm)",
    StructureType.BASELINE_UP: "Baseline chỉ báo: hướng tăng",
    StructureType.BASELINE_DOWN: "Baseline chỉ báo: hướng giảm",
    StructureType.BASELINE_RANGE: "Baseline chỉ báo: biên độ hẹp / ADX yếu",
    StructureType.BASELINE_UNCERTAIN: "Baseline chỉ báo: chưa đủ điều kiện",
    StructureType.HMM_STATE_CHANGE: "HMM online: state lọc (forward) đổi",
}


@dataclass
class StructureEvent:
    """Một sự kiện cấu trúc do thuật toán sinh ra.

    Phân biệt ba mốc thời gian:

    * ``event_time``       : timestamp của NẾN chứa cấu trúc (theo quy ước dataset).
    * ``event_close_time`` : thời điểm nến đó ĐÓNG.
    * ``confirmed_at``     : thời điểm thuật toán THỰC SỰ xác nhận được cấu trúc
      (= ``close_time`` của nến xác nhận). Marker chỉ được phép xuất hiện trong
      chế độ replay từ mốc này trở đi.
    """

    event_id: str
    structure_type: str
    price: float

    event_bar_index: int
    event_time: datetime
    event_close_time: datetime

    confirmed_bar_index: int
    confirmed_at: datetime

    algorithm: str
    algorithm_version: str
    reason_code: str

    direction: Optional[str] = None            # "up" | "down" | None
    reference_event_id: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def confirmation_lag_bars(self) -> int:
        return self.confirmed_bar_index - self.event_bar_index

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["event_time"] = self.event_time.isoformat()
        d["event_close_time"] = self.event_close_time.isoformat()
        d["confirmed_at"] = self.confirmed_at.isoformat()
        d["confirmation_lag_bars"] = self.confirmation_lag_bars
        d["structure_text_vi"] = STRUCTURE_TEXT_VI.get(
            self.structure_type, self.structure_type
        )
        d["reason_text_vi"] = REASON_TEXT_VI.get(self.reason_code, "")
        return d


# --------------------------------------------------------------------------
# Trạng thái dữ liệu
# --------------------------------------------------------------------------

DATA_STATUS_OK = "OK"
DATA_STATUS_WARMUP = "WARMUP_INSUFFICIENT"
DATA_STATUS_INVALID = "DATA_INVALID"
