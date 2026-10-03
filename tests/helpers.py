"""Tiện ích dựng nến cho test."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from core.types import Bar, build_bars

START = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)


def make_bars(
    ohlc: Sequence[tuple[float, float, float, float]],
    timeframe: str = "H1",
    convention: str = "open",
    start: datetime = START,
) -> list[Bar]:
    """Dựng nến H1 liên tiếp từ danh sách (open, high, low, close)."""
    from core.types import timeframe_delta

    delta = timeframe_delta(timeframe)
    rows = []
    for i, (o, h, l, c) in enumerate(ohlc):
        rows.append(
            {
                "bar_time": start + i * delta,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": 100.0,
            }
        )
    bars = build_bars(rows, timeframe, convention)
    for b in bars:
        assert b.is_valid_ohlc(), "Fixture sai: nến %d vi phạm quan hệ OHLC" % b.index
    return bars


def page_scripts(html: str) -> list[str]:
    """Đường dẫn các file JS mà một trang HTML nạp (bỏ tham số ?v=)."""
    import re

    return [m.split("?")[0] for m in re.findall(r'<script src="([^"]+)"', html)]


def assert_page_scripts_served(client, path: str) -> list[str]:
    """Mọi script của trang phải trả 200 — bắt lỗi gõ sai tên file khi tách module."""
    html = client.get(path).text
    srcs = page_scripts(html)
    assert srcs, "Trang %s không nạp script nào" % path
    for src in srcs:
        assert client.get(src).status_code == 200, (path, src)
    return srcs


def types_at(events: Iterable, structure_type: str) -> list:
    return [e for e in events if e.structure_type == structure_type]


def signature(events: Iterable) -> list[tuple]:
    """Khoá so sánh ổn định giữa các lần chạy."""
    return [
        (e.structure_type, e.event_bar_index, e.confirmed_bar_index, round(e.price, 10))
        for e in events
    ]
