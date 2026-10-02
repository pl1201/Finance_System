"""Giải mã file nến M1 ``.bi5`` của Dukascopy — dựng file giả, không cần mạng."""
import lzma
import struct
from datetime import date, datetime, timezone

import pytest

from marketdata import dukascopy as dk


def bi5(records):
    """records: (giây từ đầu ngày, open, close, low, high, volume) — đúng thứ tự trường của Dukascopy."""
    raw = b"".join(struct.pack(">5if", *r) for r in records)
    return lzma.compress(raw, format=lzma.FORMAT_ALONE)


def test_decode_scales_price_and_skips_flat_candles():
    data = bi5([(0, 2030500, 2031000, 2030000, 2031500, 1.5),
                (60, 2031000, 2031000, 2031000, 2031000, 0.0)])   # nến phẳng volume 0 = thị trường đóng
    e = int(datetime(2024, 1, 10, tzinfo=timezone.utc).timestamp())
    assert dk.decode_ohlc("XAUUSD", date(2024, 1, 10), data) == {e: (2030.5, 2031.5, 2030.0, 2031.0)}


def test_decode_rejects_unexpected_field_order():
    with pytest.raises(ValueError):
        dk.decode_ohlc("EURUSD", date(2024, 1, 10), bi5([(0, 100, 200, 300, 50, 1.0)]))  # high < low


def test_decode_empty_day():
    assert dk.decode_ohlc("EURUSD", date(2024, 1, 13), b"") == {}
