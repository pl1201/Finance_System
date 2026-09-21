"""Lấy lịch sử OHLC từ terminal MetaTrader 5.

Gói ``MetaTrader5`` là **tuỳ chọn**. Module này phải import được khi chưa
cài gói đó — ``core/`` không phụ thuộc MT5 để chạy test và notebook.

``copy_rates_from_pos(..., start_pos=0)``: index 0 là nến **đang hình thành**.
Mặc định lab loại nến đó (`drop_forming=True`). ``copy_rates_range`` cũng loại
nến cuối nếu thời điểm đóng lý thuyết vẫn ở tương lai so với đồng hồ máy.

Đầu ra: list dict ``{bar_time, open, high, low, close, volume}`` — cùng schema
mà ``validate_and_clean`` / ``import_dataset`` nhận. ``bar_time`` là UTC,
mốc **mở nến** (MT5 dùng datetime mở nến).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.types import TIMEFRAME_SECONDS

try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:  # pragma: no cover - môi trường không cài gói
    mt5 = None  # type: ignore


class Mt5SourceError(RuntimeError):
    """Không lấy được dữ liệu MT5 (thiếu gói, terminal, symbol, …)."""


_TF_ATTR = {
    "M1": "TIMEFRAME_M1",
    "M5": "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H4": "TIMEFRAME_H4",
    "D1": "TIMEFRAME_D1",
}


def mt5_available() -> bool:
    return mt5 is not None


def _tf_const(timeframe: str) -> int:
    if mt5 is None:
        raise Mt5SourceError(
            "Chưa cài gói MetaTrader5. Lõi vẫn chạy được; muốn lấy lịch sử từ "
            "terminal thì: pip install MetaTrader5 (và mở sẵn MT5)."
        )
    tf = (timeframe or "").upper().strip()
    attr = _TF_ATTR.get(tf)
    if attr is None:
        raise Mt5SourceError("Timeframe không hỗ trợ từ MT5: %r" % timeframe)
    return int(getattr(mt5, attr))


def _rate_to_row(rate: Any) -> dict[str, Any]:
    # MT5 trả numpy void: time (epoch giây, UTC), open, high, low, close, tick_volume, ...
    ts = int(rate["time"])
    vol = 0.0
    try:
        vol = float(rate["tick_volume"])
    except (ValueError, TypeError, IndexError):
        try:
            vol = float(rate["real_volume"])
        except (ValueError, TypeError, IndexError):
            vol = 0.0
    return {
        "bar_time": datetime.fromtimestamp(ts, tz=timezone.utc),
        "open": float(rate["open"]),
        "high": float(rate["high"]),
        "low": float(rate["low"]),
        "close": float(rate["close"]),
        "volume": vol,
    }


def _is_forming(bar_time: datetime, timeframe: str, now: datetime) -> bool:
    close_time = bar_time + timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
    return close_time > now


def fetch_closed_rates(
    symbol: str,
    timeframe: str,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    count: Optional[int] = None,
    drop_forming: bool = True,
    terminal_path: Optional[str] = None,
    now: Optional[datetime] = None,
    _api: Any = None,
) -> dict[str, Any]:
    """Lấy nến đã đóng. ``_api`` để test (mock), mặc định dùng gói MetaTrader5."""
    api = _api if _api is not None else mt5
    tf = (timeframe or "").upper().strip()
    if tf not in TIMEFRAME_SECONDS:
        raise Mt5SourceError("Timeframe không hỗ trợ: %r" % timeframe)
    if api is None:
        raise Mt5SourceError(
            "Chưa cài gói MetaTrader5. pip install MetaTrader5 rồi mở terminal."
        )

    kwargs = {}
    if terminal_path:
        kwargs["path"] = terminal_path
    if not api.initialize(**kwargs):
        err = api.last_error() if hasattr(api, "last_error") else None
        raise Mt5SourceError("Không initialize được MT5: %s" % (err,))
    try:
        if not api.symbol_select(symbol, True):
            raise Mt5SourceError(
                "Không chọn được symbol %r trên Market Watch. Kiểm tra tên (hậu tố broker)."
                % symbol
            )
        tf_const = int(getattr(api, _TF_ATTR[tf])) if hasattr(api, _TF_ATTR[tf]) else _tf_const(tf)

        rates = None
        mode = "count" if count else "range"
        if count is not None:
            if count < 1:
                raise Mt5SourceError("count phải >= 1.")
            # start_pos=0 gồm nến đang hình thành.
            rates = api.copy_rates_from_pos(symbol, tf_const, 0, int(count))
        else:
            if date_from is None or date_to is None:
                raise Mt5SourceError("Cần date_from và date_to, hoặc count.")
            d0 = date_from if date_from.tzinfo else date_from.replace(tzinfo=timezone.utc)
            d1 = date_to if date_to.tzinfo else date_to.replace(tzinfo=timezone.utc)
            rates = api.copy_rates_range(symbol, tf_const, d0, d1)

        if rates is None:
            err = api.last_error() if hasattr(api, "last_error") else None
            raise Mt5SourceError("copy_rates trả None: %s" % (err,))

        rows = [_rate_to_row(r) for r in rates]
        dropped = 0
        clock = now or datetime.now(timezone.utc)
        if drop_forming and rows:
            # copy_rates_from_pos: phần tử 0 là nến đang hình thành.
            if mode == "count" and _is_forming(rows[0]["bar_time"], tf, clock):
                rows = rows[1:]
                dropped += 1
            # range / còn lại: nến cuối có thể chưa đóng.
            if rows and _is_forming(rows[-1]["bar_time"], tf, clock):
                rows = rows[:-1]
                dropped += 1

        rows.sort(key=lambda r: r["bar_time"])
        return {
            "rows": rows,
            "symbol": symbol,
            "timeframe": tf,
            "dropped_forming": dropped,
            "timestamp_convention": "open",
            "source_timezone": "UTC+00:00",
            "note_vi": (
                "Nến MT5 dùng mốc MỞ, thời gian epoch UTC. "
                "Đã loại %d nến đang hình thành. "
                "copy_rates_from_pos index 0 là nến hiện tại — lab loại khi drop_forming=true."
                % dropped
            ),
        }
    finally:
        try:
            api.shutdown()
        except Exception:
            pass
