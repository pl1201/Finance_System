"""Kiểu dữ liệu dùng chung cho lõi thuật toán cấu trúc thị trường.

Lõi này KHÔNG phụ thuộc web framework, notebook hay MT5. Chỉ dùng thư viện
chuẩn Python để có thể tái sử dụng ở bất kỳ môi trường nào.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.vocab import FAMILIES
from core.vocab.baseline import BaselineReason, BaselineType
from core.vocab.c2_cisd import C2CisdReason, C2CisdType
from core.vocab.dc import DcReason, DcType
from core.vocab.ict import IctReason, IctType
from core.vocab.swing import SwingReason, SwingType

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


class StructureType(SwingType, BaselineType, C2CisdType, DcType, IctType):
    """Mọi loại sự kiện cấu trúc. Khai báo theo họ trong ``core/vocab/``."""

    ALL = (SwingType.SWING_ALL + BaselineType.BASELINE_ALL + C2CisdType.C2_CISD_TYPES + DcType.DC_TYPES
           + IctType.ICT_TYPES)


class ReasonCode(SwingReason, BaselineReason, C2CisdReason, DcReason, IctReason):
    """Mã lý do để truy vết vì sao một sự kiện được sinh ra. Khai báo trong ``core/vocab/``."""


#: Giải thích tiếng Việt cho từng mã lý do (dùng cho tooltip giao diện).
REASON_TEXT_VI: dict[str, str] = {}
#: Giải thích tiếng Việt cho từng loại cấu trúc.
STRUCTURE_TEXT_VI: dict[str, str] = {}
for _family in FAMILIES:
    REASON_TEXT_VI.update(_family.REASON_TEXT_VI)
    STRUCTURE_TEXT_VI.update(_family.STRUCTURE_TEXT_VI)


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
