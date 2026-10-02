"""Lịch phiên khai báo (marketdata/session_calendar.py) — các mốc tính tay theo giờ New York."""
from datetime import datetime, timedelta, timezone

import pytest

from marketdata.session_calendar import (
    CUOI_TUAN, NGHI_LE, NGHI_PHIEN, THIEU_TRONG_PHIEN, SessionCalendar,
)


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def metals():
    return SessionCalendar.for_symbol("XAUUSD")


@pytest.fixture(scope="module")
def fx():
    return SessionCalendar.for_symbol("EURUSD")


def test_metals_regular_session_and_daily_break(metals):
    assert metals.is_open(utc(2024, 1, 10, 15, 0))                    # 10:00 NY
    assert metals.closure_reason(utc(2024, 1, 10, 22, 30)) == NGHI_PHIEN  # 17:30 NY mùa đông
    assert metals.is_open(utc(2024, 1, 10, 23, 0))                    # 18:00 NY mở phiên mới


def test_metals_dst_shifts_utc_break(metals):
    # 11/03/2024 Mỹ đã đổi giờ: nghỉ 17:00–18:00 NY = 21:00–22:00 UTC
    assert metals.closure_reason(utc(2024, 3, 11, 21, 30)) == NGHI_PHIEN
    assert metals.is_open(utc(2024, 3, 11, 22, 30))


def test_metals_weekend_and_holidays(metals):
    assert metals.closure_reason(utc(2024, 1, 13, 12, 0)) == CUOI_TUAN   # Thứ Bảy
    assert metals.closure_reason(utc(2024, 3, 29, 14, 0)) == NGHI_LE     # Good Friday
    assert metals.is_open(utc(2024, 1, 15, 19, 0))                      # MLK 14:00 NY còn mở
    assert metals.closure_reason(utc(2024, 1, 15, 20, 0)) == NGHI_LE     # 15:00 NY sau đóng sớm 14:30
    assert metals.closure_reason(utc(2018, 1, 15, 18, 30)) == NGHI_LE    # 2018: đóng sớm 13:00 NY


def test_metals_christmas_eve_override(metals):
    assert metals.is_open(utc(2024, 12, 24, 18, 0))                     # 13:00 NY
    assert metals.closure_reason(utc(2024, 12, 24, 19, 0)) == NGHI_LE    # 14:00 NY, sau 13:45
    assert {o["trading_day"] for o in metals.meta["ngoai_le"]} >= {"2024-12-24"}


def test_fx_no_daily_break_and_christmas(fx):
    assert fx.is_open(utc(2024, 1, 10, 22, 30))                          # 17:30 NY vẫn mở
    assert fx.closure_reason(utc(2024, 12, 25, 8, 0)) == NGHI_LE
    assert fx.closure_reason(utc(2024, 1, 12, 22, 30)) == CUOI_TUAN      # Thứ Sáu 17:30 NY
    assert fx.is_open(utc(2024, 1, 14, 22, 30))                          # Chủ nhật 17:30 NY


def test_classify_gap(metals):
    step = timedelta(minutes=1)
    # khoảng trống đúng giờ nghỉ 17:00–18:00 NY (mùa đông)
    assert metals.classify_gap(utc(2024, 1, 10, 22, 0), utc(2024, 1, 10, 23, 0), step) == (NGHI_PHIEN, 0)
    # mất 13:00–15:00 NY trong phiên thường → 120 phút thiếu
    assert metals.classify_gap(utc(2024, 1, 10, 18, 0), utc(2024, 1, 10, 20, 0), step) == (THIEU_TRONG_PHIEN, 120)
    # Thứ Sáu 17:00 → Chủ nhật 18:00 NY
    assert metals.classify_gap(utc(2024, 1, 12, 22, 0), utc(2024, 1, 14, 23, 0), step) == (CUOI_TUAN, 0)
