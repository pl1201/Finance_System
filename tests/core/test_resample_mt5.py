"""Test tổng hợp nến và nguồn MT5 (mock, không cần terminal)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.data.mt5_source import Mt5SourceError, fetch_closed_rates, mt5_available
from core.data.resample import ResampleError, bucket_start_utc, resample_ohlc
from core.types import TIMEFRAME_SECONDS


START = datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc)


def _m1(n: int, start: datetime = START) -> list[dict]:
    rows = []
    px = 2000.0
    for i in range(n):
        o = px
        h, l, c = px + 0.5, px - 0.4, px + 0.1
        rows.append({
            "bar_time": start + timedelta(minutes=i),
            "open": o, "high": h, "low": l, "close": c, "volume": 10.0 + i,
        })
        px = c
    return rows


def test_bucket_utc_epoch_m5():
    t = datetime(2024, 1, 2, 10, 7, tzinfo=timezone.utc)
    assert bucket_start_utc(t, "M5") == datetime(2024, 1, 2, 10, 5, tzinfo=timezone.utc)


def test_bucket_h4_utc_khong_lech_broker():
    t = datetime(2024, 1, 2, 6, 30, tzinfo=timezone.utc)
    assert bucket_start_utc(t, "H4") == datetime(2024, 1, 2, 4, 0, tzinfo=timezone.utc)


def test_resample_m1_len_m5_tinh_tay():
    rows = _m1(10)  # 10:00 .. 10:09 → hai nến M5 đủ 5 M1
    out, rep = resample_ohlc(rows, "M1", "M5")
    assert len(out) == 2
    assert out[0]["bar_time"] == START
    assert out[0]["open"] == rows[0]["open"]
    assert out[0]["close"] == rows[4]["close"]
    assert out[0]["high"] == max(r["high"] for r in rows[:5])
    assert out[0]["low"] == min(r["low"] for r in rows[:5])
    assert out[0]["volume"] == sum(r["volume"] for r in rows[:5])
    assert out[1]["bar_time"] == START + timedelta(minutes=5)
    assert out[1]["open"] == rows[5]["open"]
    assert out[1]["close"] == rows[9]["close"]
    assert rep.expected_source_per_bucket == 5
    assert rep.buckets_incomplete_dropped == 0


def test_resample_thieu_nen_drop_incomplete():
    rows = _m1(7)  # 10:00-10:04 đủ; 10:05-10:06 thiếu
    out, rep = resample_ohlc(rows, "M1", "M5", gap_policy="drop_incomplete")
    assert len(out) == 1
    assert rep.buckets_incomplete_dropped == 1
    out2, rep2 = resample_ohlc(rows, "M1", "M5", gap_policy="emit_available")
    assert len(out2) == 2
    assert out2[1]["incomplete"] is True
    assert out2[1]["source_bar_count"] == 2
    assert rep2.buckets_incomplete_emitted == 1


def test_resample_khong_lap_khoang_trong():
    rows = _m1(5) + _m1(5, START + timedelta(minutes=20))
    out, rep = resample_ohlc(rows, "M1", "M5")
    assert len(out) == 2
    gap = out[1]["bar_time"] - out[0]["bar_time"]
    assert gap == timedelta(minutes=20)
    # không đúc nến 10:05, 10:10, 10:15


def test_resample_tu_choi_xuong_timeframe_nho():
    with pytest.raises(ResampleError, match="Không tách được"):
        resample_ohlc(_m1(10), "H1", "M5")


def test_mt5_available_khong_vo_import():
    # Chỉ cần không ném lỗi; máy có thể chưa cài gói.
    assert mt5_available() in (True, False)


class _FakeMT5:
    TIMEFRAME_H1 = 16385

    def __init__(self, rates):
        self.rates = rates
        self.shut = False

    def initialize(self, **kwargs):
        return True

    def shutdown(self):
        self.shut = True

    def symbol_select(self, symbol, _b):
        return symbol == "XAUUSD"

    def last_error(self):
        return (1, "ok")

    def copy_rates_from_pos(self, symbol, tf, start, count):
        assert start == 0
        return self.rates[:count]

    def copy_rates_range(self, symbol, tf, d0, d1):
        return self.rates


def _rate(epoch, o, h, l, c, forming=False):
    return {
        "time": epoch,
        "open": o, "high": h, "low": l, "close": c,
        "tick_volume": 100,
    }


def test_mt5_loai_nen_dang_hinh_thanh_index_0():
    now = datetime(2024, 6, 3, 12, 30, tzinfo=timezone.utc)
    # nến đang chạy: 12:00 H1 đóng lúc 13:00 > now
    forming = int(datetime(2024, 6, 3, 12, 0, tzinfo=timezone.utc).timestamp())
    closed = int(datetime(2024, 6, 3, 11, 0, tzinfo=timezone.utc).timestamp())
    older = int(datetime(2024, 6, 3, 10, 0, tzinfo=timezone.utc).timestamp())
    api = _FakeMT5([
        _rate(forming, 10, 11, 9, 10.5),
        _rate(closed, 9, 10, 8, 9.5),
        _rate(older, 8, 9, 7, 8.5),
    ])
    out = fetch_closed_rates(
        "XAUUSD", "H1", count=3, drop_forming=True, now=now, _api=api
    )
    assert out["dropped_forming"] == 1
    assert len(out["rows"]) == 2
    assert out["rows"][0]["bar_time"] == datetime(2024, 6, 3, 10, 0, tzinfo=timezone.utc)
    assert out["timestamp_convention"] == "open"
    assert api.shut is True


def test_mt5_thieu_goi_bao_loi_ro(monkeypatch):
    import core.data.mt5_source as mod
    monkeypatch.setattr(mod, "mt5", None)
    with pytest.raises(Mt5SourceError):
        fetch_closed_rates("XAUUSD", "H1", count=10)


def test_mt5_symbol_sai():
    api = _FakeMT5([])
    with pytest.raises(Mt5SourceError):
        fetch_closed_rates("NOSYM", "H1", count=2, _api=api)
