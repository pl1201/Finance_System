"""Lịch phiên KHAI BÁO (``calendars/*.json``) — giờ thị trường mở/đóng theo nguồn đã ghi.

Lịch không được suy từ dữ liệu. File lịch liệt kê từng phiên ``{trading_day, open, close, kind}``
(giờ New York có offset) và các ngày đóng cửa; sinh bằng ``python -m marketdata.build_calendars``.

Dùng để:

* biết một thời điểm có nằm trong phiên không (``is_open``);
* phân loại một khoảng trống giữa hai nến: đóng cửa theo lịch (nghỉ hằng ngày / cuối tuần / lễ) hay
  **thiếu dữ liệu trong phiên** (``classify_gap``).
"""
from __future__ import annotations

import bisect
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from . import CAL_DIR  # noqa: E402 — ROOT/calendars

#: Lịch mặc định theo mã.
DEFAULT_FOR_SYMBOL = {"XAUUSD": "cme_globex_metals", "EURUSD": "fx_spot"}

NGHI_PHIEN = "nghi_phien"      # nghỉ hằng ngày giữa hai phiên liền nhau
CUOI_TUAN = "cuoi_tuan"
NGHI_LE = "nghi_le"            # đóng sớm hoặc đóng cả ngày theo lịch lễ
THIEU_TRONG_PHIEN = "thieu_trong_phien"


@dataclass(frozen=True)
class Session:
    trading_day: date
    open: datetime   # UTC
    close: datetime  # UTC
    kind: str        # regular | early_close


class SessionCalendar:
    def __init__(self, name: str, sessions: list[Session], meta: dict) -> None:
        self.name = name
        self.sessions = sorted(sessions, key=lambda s: s.open)
        self.meta = meta
        self._opens = [s.open for s in self.sessions]
        self.closed_days = {date.fromisoformat(d) for d in meta.get("ngay_dong_cua", [])}
        self.first = self.sessions[0].open if self.sessions else None
        self.last = self.sessions[-1].close if self.sessions else None

    @classmethod
    def load(cls, name_or_path: str) -> "SessionCalendar":
        path = name_or_path if name_or_path.endswith(".json") else os.path.join(CAL_DIR, name_or_path + ".json")
        raw = json.load(open(path, encoding="utf-8"))
        sessions = [Session(date.fromisoformat(s["trading_day"]),
                            datetime.fromisoformat(s["open"]).astimezone(timezone.utc),
                            datetime.fromisoformat(s["close"]).astimezone(timezone.utc),
                            s.get("kind", "regular"))
                    for s in raw["sessions"]]
        return cls(raw["meta"].get("name", os.path.basename(path)), sessions, raw["meta"])

    @classmethod
    def for_symbol(cls, symbol: str) -> "SessionCalendar":
        return cls.load(DEFAULT_FOR_SYMBOL[symbol.upper()])

    def covers(self, t: datetime) -> bool:
        return self.first is not None and self.first <= t < self.last

    def session_at(self, t: datetime) -> Optional[Session]:
        i = bisect.bisect_right(self._opens, t) - 1
        if i >= 0 and self.sessions[i].open <= t < self.sessions[i].close:
            return self.sessions[i]
        return None

    def is_open(self, t: datetime) -> bool:
        return self.session_at(t) is not None

    def closure_reason(self, t: datetime) -> Optional[str]:
        """None nếu đang trong phiên; ngược lại lý do đóng cửa theo lịch."""
        i = bisect.bisect_right(self._opens, t) - 1
        if i >= 0 and t < self.sessions[i].close:
            return None
        prev = self.sessions[i] if i >= 0 else None
        nxt = self.sessions[i + 1] if i + 1 < len(self.sessions) else None
        if prev is None or nxt is None:
            return CUOI_TUAN
        if prev.kind == "early_close":
            return NGHI_LE
        d = prev.trading_day + timedelta(days=1)
        while d < nxt.trading_day:
            if d in self.closed_days:
                return NGHI_LE
            d += timedelta(days=1)
        return CUOI_TUAN if (nxt.trading_day - prev.trading_day).days > 1 else NGHI_PHIEN

    def classify_gap(self, first_missing: datetime, next_bar: datetime, step: timedelta) -> tuple[str, int]:
        """Khoảng trống [first_missing, next_bar): (loại, số ô thiếu nằm TRONG phiên).

        Loại = ``thieu_trong_phien`` nếu có ít nhất một ô nằm trong phiên; ngược lại lý do đóng cửa
        (lễ được ưu tiên hơn cuối tuần, cuối tuần hơn nghỉ hằng ngày)."""
        missing, reasons = 0, set()
        t = first_missing
        while t < next_bar:
            r = self.closure_reason(t)
            if r is None:
                missing += 1
            else:
                reasons.add(r)
            t += step
        if missing:
            return THIEU_TRONG_PHIEN, missing
        for r in (NGHI_LE, CUOI_TUAN, NGHI_PHIEN):
            if r in reasons:
                return r, 0
        return NGHI_PHIEN, 0
