"""Chỉ báo thành phần tính bằng thư viện chuẩn Python (không TA-Lib).

Công thức được chốt để đối chiếu với MQL5. Mọi smoothing đều ghi rõ
Wilder hay SMA — đây là chỗ hay lệch khi so iATR / iADX / iMA.

Các hàm nhận chuỗi giá đã đóng theo thời gian tăng dần và trả về ``None``
trong giai đoạn warm-up.
"""
from __future__ import annotations

from typing import Optional, Sequence


def true_range(high: float, low: float, prev_close: Optional[float]) -> float:
    """True Range. Nến đầu (không có close trước): ``high - low``."""
    span = high - low
    if prev_close is None:
        return span
    return max(span, abs(high - prev_close), abs(low - prev_close))


def wilder_seed(values: Sequence[float], period: int) -> Optional[float]:
    """Giá trị Wilder đầu tiên = SMA của ``period`` mẫu."""
    if period < 1 or len(values) < period:
        return None
    return sum(values[:period]) / period


def wilder_next(prev: float, current: float, period: int) -> float:
    """Bước Wilder: ``(prev * (period - 1) + current) / period``.

    Trùng smoothing của ``iATR`` / ``iADX`` trên MT5 (không phải EMA α=2/(n+1)).
    """
    return (prev * (period - 1) + current) / period


class WilderATR:
    """ATR Wilder online, warm-up ``period`` nến (giá trị đầu tại index ``period-1``)."""

    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError("atr_period phai >= 1")
        self.period = period
        self._trs: list[float] = []
        self._prev_close: Optional[float] = None
        self.value: Optional[float] = None

    def update(self, high: float, low: float, close: float) -> Optional[float]:
        tr = true_range(high, low, self._prev_close)
        self._prev_close = close
        if self.value is None:
            self._trs.append(tr)
            if len(self._trs) == self.period:
                self.value = sum(self._trs) / self.period
            return self.value
        self.value = wilder_next(self.value, tr, self.period)
        return self.value


class WilderADX:
    """ADX / +DI / -DI theo smoothing Wilder, cùng họ với ``iADX`` MQL5.

    Warm-up: cần 1 nến cho DM (so với nến trước) + ``period`` nến để seed
    +DM/-DM/TR + ``period`` nến nữa để seed ADX từ DX.

    Giá trị ADX đầu tiên xuất hiện tại index ``2 * period`` (0-based), tức sau
    ``2 * period + 1`` nến đã đóng. Trước đó ``update`` trả ``None``.
    """

    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError("adx_period phai >= 1")
        self.period = period
        self._prev_high: Optional[float] = None
        self._prev_low: Optional[float] = None
        self._prev_close: Optional[float] = None
        self._plus_buf: list[float] = []
        self._minus_buf: list[float] = []
        self._tr_buf: list[float] = []
        self._dx_buf: list[float] = []
        self._s_plus: Optional[float] = None
        self._s_minus: Optional[float] = None
        self._s_tr: Optional[float] = None
        self.adx: Optional[float] = None
        self.plus_di: Optional[float] = None
        self.minus_di: Optional[float] = None

    def update(self, high: float, low: float, close: float) -> Optional[float]:
        if self._prev_high is None:
            self._prev_high = high
            self._prev_low = low
            self._prev_close = close
            return None

        up = high - self._prev_high
        down = self._prev_low - low
        plus_dm = up if up > down and up > 0 else 0.0
        minus_dm = down if down > up and down > 0 else 0.0
        tr = true_range(high, low, self._prev_close)
        self._prev_high = high
        self._prev_low = low
        self._prev_close = close

        if self._s_tr is None:
            self._plus_buf.append(plus_dm)
            self._minus_buf.append(minus_dm)
            self._tr_buf.append(tr)
            if len(self._tr_buf) < self.period:
                return None
            self._s_plus = sum(self._plus_buf) / self.period
            self._s_minus = sum(self._minus_buf) / self.period
            self._s_tr = sum(self._tr_buf) / self.period
        else:
            self._s_plus = wilder_next(self._s_plus, plus_dm, self.period)
            self._s_minus = wilder_next(self._s_minus, minus_dm, self.period)
            self._s_tr = wilder_next(self._s_tr, tr, self.period)

        if self._s_tr == 0:
            self.plus_di = 0.0
            self.minus_di = 0.0
            dx = 0.0
        else:
            self.plus_di = 100.0 * self._s_plus / self._s_tr
            self.minus_di = 100.0 * self._s_minus / self._s_tr
            di_sum = self.plus_di + self.minus_di
            dx = 0.0 if di_sum == 0 else 100.0 * abs(self.plus_di - self.minus_di) / di_sum

        if self.adx is None:
            self._dx_buf.append(dx)
            if len(self._dx_buf) < self.period:
                return None
            self.adx = sum(self._dx_buf) / self.period
            return self.adx
        self.adx = wilder_next(self.adx, dx, self.period)
        return self.adx


class SMA:
    """Đường trung bình đơn giản — tương đương ``iMA(..., MODE_SMA)``, không EMA."""

    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError("sma_period phai >= 1")
        self.period = period
        self._buf: list[float] = []
        self.value: Optional[float] = None

    def update(self, close: float) -> Optional[float]:
        self._buf.append(close)
        if len(self._buf) > self.period:
            self._buf.pop(0)
        if len(self._buf) < self.period:
            self.value = None
            return None
        self.value = sum(self._buf) / self.period
        return self.value


class DonchianWidth:
    """Bề rộng vùng giá: ``max(high) - min(low)`` trên ``period`` nến đóng."""

    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError("range_period phai >= 1")
        self.period = period
        self._highs: list[float] = []
        self._lows: list[float] = []
        self.value: Optional[float] = None

    def update(self, high: float, low: float) -> Optional[float]:
        self._highs.append(high)
        self._lows.append(low)
        if len(self._highs) > self.period:
            self._highs.pop(0)
            self._lows.pop(0)
        if len(self._highs) < self.period:
            self.value = None
            return None
        self.value = max(self._highs) - min(self._lows)
        return self.value
