"""Lấy lịch sử OHLC từ terminal MetaTrader 5.

Gói ``MetaTrader5`` là **tuỳ chọn**. Module này phải import được khi chưa
cài gói đó — ``core/`` không phụ thuộc MT5 để chạy test và notebook.

``copy_rates_from_pos(..., start_pos=0)``: index 0 là nến **đang hình thành**.
Mặc định lab loại nến đó (`drop_forming=True`). ``copy_rates_range`` cũng loại
nến cuối nếu thời điểm đóng lý thuyết vẫn ở tương lai so với đồng hồ máy.

Đầu ra: list dict ``{bar_time, open, high, low, close, volume}`` — cùng schema
mà ``validate_and_clean`` / ``import_dataset`` nhận. ``bar_time`` là UTC,
mốc **mở nến** (MT5 dùng datetime mở nến).

**Chỉ đọc** (plan_mt5_live.md §2): mọi lời gọi MT5 đi qua ``ReadOnlyMt5`` — chỉ các hàm
trong ``ALLOWED`` (đọc nến, tick cuối, trạng thái terminal); lệnh, vị thế, tài khoản không
gọi được. ``initialize`` chỉ nhận đường dẫn terminal: không đăng nhập, không mật khẩu.

Giờ: ``time`` của MT5 là **giờ server của broker** viết như epoch. ``Mt5Reader`` (luồng
live) quy về UTC theo khai báo ``server_tz`` (``UTC±hh:mm`` hoặc ``ny+7``); lab không đoán.
``fetch_closed_rates`` (nhập lịch sử) giữ cách cũ: chỉ gắn nhãn múi giờ (plan §3, §10).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from core.data.htf_stream import NY_TZ
from core.data.loader import CsvImportError, tz_offset
from core.types import TIMEFRAME_SECONDS

try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:  # pragma: no cover - môi trường không cài gói
    mt5 = None  # type: ignore


class Mt5SourceError(RuntimeError):
    """Không lấy được dữ liệu MT5 (thiếu gói, terminal, symbol, …)."""


#: Hàm MT5 lab được gọi — chỉ đọc. Không có ``order_*``, ``positions_*``, ``orders_*``, ``history_*``, ``account_info``.
ALLOWED = frozenset({"initialize", "shutdown", "last_error", "version", "terminal_info", "symbol_select",
                     "symbol_info_tick", "copy_rates_from_pos", "copy_rates_range"})
#: Khai báo giờ server «giờ New York + 7» (đổi giờ theo Mỹ, nến ngày mở 17:00 New York — broker GMT+2 / GMT+3).
NY_PLUS_7 = "ny+7"


class ReadOnlyMt5:
    """Lớp bọc quanh gói ``MetaTrader5`` (hoặc bản giả trong test): chỉ lộ ``ALLOWED`` và hằng ``TIMEFRAME_*``, tên khác
    → ``Mt5SourceError``. ``initialize`` chỉ nhận đường dẫn terminal (terminal phải đăng nhập sẵn)."""

    def __init__(self, api: Any) -> None:
        self._api = api

    def initialize(self, path: Optional[str] = None) -> bool:
        return self._api.initialize(path) if path else self._api.initialize()

    def __getattr__(self, name: str) -> Any:
        if name in ALLOWED or name.startswith("TIMEFRAME_"):
            return getattr(self._api, name)
        raise Mt5SourceError("Lab chỉ đọc nến từ MT5 — không gọi %r (plan_mt5_live.md §2)." % name)


def _fixed_offset(server_tz: str) -> Optional[timedelta]:
    """Offset cố định của khai báo; None = ``ny+7``; bỏ trống / sai → ``Mt5SourceError`` (không mặc định UTC)."""
    if not server_tz.strip():
        raise Mt5SourceError("Phải khai báo giờ server của broker (UTC, UTC+2, UTC-05:00 hoặc ny+7) — lab không đoán.")
    if server_tz.strip().lower() == NY_PLUS_7:
        return None
    try:
        return tz_offset(server_tz)
    except CsvImportError as exc:
        raise Mt5SourceError("Giờ server %r không hợp lệ: dùng UTC, UTC+2, UTC-05:00 hoặc ny+7." % server_tz) from exc


def server_offset(server_tz: str, at: datetime) -> timedelta:
    """Giờ server − UTC tại thời điểm ``at`` (UTC) theo khai báo."""
    fixed = _fixed_offset(server_tz)
    return fixed if fixed is not None else at.astimezone(NY_TZ).utcoffset() + timedelta(hours=7)


def utc_converter(server_tz: str) -> Callable[[int], datetime]:
    """Hàm quy ``time`` của MT5 (giờ server viết như epoch) → UTC theo khai báo (phân tích khai báo một lần)."""
    fixed = _fixed_offset(server_tz)

    def to_utc(epoch: int) -> datetime:
        wall = datetime(1970, 1, 1) + timedelta(seconds=int(epoch))
        if fixed is not None:
            return (wall - fixed).replace(tzinfo=timezone.utc)
        return (wall - timedelta(hours=7)).replace(tzinfo=NY_TZ).astimezone(timezone.utc)

    return to_utc


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


class Mt5Reader:
    """Kết nối chỉ đọc giữ mở giữa các lần hỏi (luồng live); lỗi thì đóng để lần sau nối lại."""

    def __init__(self, api: Any = None, terminal_path: Optional[str] = None) -> None:
        raw = api if api is not None else mt5
        if raw is None:
            raise Mt5SourceError("Chưa cài gói MetaTrader5. pip install MetaTrader5, mở terminal và đăng nhập sẵn.")
        self.api = ReadOnlyMt5(raw)
        self.terminal_path = terminal_path
        self._open = False
        self._selected: set[str] = set()                # symbol đã chọn trên Market Watch trong kết nối này

    def _connect(self, symbol: str) -> None:
        if not self._open:
            if not self.api.initialize(self.terminal_path):
                raise Mt5SourceError("Không kết nối được terminal MT5 (%s): terminal đã mở và đăng nhập chưa?"
                                     % (self.api.last_error(),))
            self._open = True
        if symbol not in self._selected:
            if not self.api.symbol_select(symbol, True):
                self.close()
                raise Mt5SourceError("Không chọn được symbol %r trên Market Watch. Kiểm tra tên (hậu tố broker)."
                                     % symbol)
            self._selected.add(symbol)

    def close(self) -> None:
        if self._open:
            self._open, self._selected = False, set()
            try:
                self.api.shutdown()
            except Exception:
                pass

    def closed_bars(self, symbol: str, timeframe: str, count: int, server_tz: str, now: datetime) -> list[dict[str, Any]]:
        """Tối đa ``count`` nến đã đóng gần nhất (cũ → mới), ``bar_time`` UTC mốc mở. Nến ở vị trí 0 (mới nhất — nến hiện
        tại của MT5) luôn bị bỏ, kể cả khi đồng hồ máy / khai báo giờ nói đã đóng: chỉ nhận một nến khi nến sau nó đã
        xuất hiện, nên khai báo lệch hay đồng hồ máy chạy nhanh không đưa được nến đang hình thành vào kho. Giá: nến cuối
        trước giờ nghỉ / cuối tuần tới muộn (khi phiên mở lại). Nến mở sau đồng hồ máy → khai báo giờ server sai → lỗi."""
        tf = (timeframe or "").upper().strip()
        if tf not in _TF_ATTR:
            raise Mt5SourceError("Timeframe không hỗ trợ từ MT5: %r" % timeframe)
        self._connect(symbol)
        rates = self.api.copy_rates_from_pos(symbol, int(getattr(self.api, _TF_ATTR[tf])), 0, int(count) + 1)
        if rates is None:
            err = self.api.last_error()
            self.close()
            raise Mt5SourceError("copy_rates trả None: %s" % (err,))
        to_utc = utc_converter(server_tz)
        rows = sorted((dict(_rate_to_row(r), bar_time=to_utc(r["time"])) for r in rates), key=lambda r: r["bar_time"])
        if rows and rows[-1]["bar_time"] > now:
            raise Mt5SourceError("Nến mới nhất mở lúc %s UTC — sau đồng hồ máy %s: khai báo giờ server %r có lẽ sai."
                                 % (rows[-1]["bar_time"].isoformat(), now.isoformat(), server_tz))
        return [r for r in rows[:-1] if not _is_forming(r["bar_time"], tf, now)][-int(count):]

    def offset_hint(self, symbol: str, now: datetime) -> Optional[int]:
        """Gợi ý để người dùng kiểm khai báo (không tự áp): giờ tick cuối − đồng hồ máy (giây), làm tròn 30 phút. Chỉ có
        nghĩa khi thị trường đang mở và vừa có tick; None khi chưa có tick."""
        self._connect(symbol)
        tick = self.api.symbol_info_tick(symbol)
        if tick is None or not getattr(tick, "time", 0):
            return None
        return round((int(tick.time) - int(now.timestamp())) / 1800) * 1800


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
    raw = _api if _api is not None else mt5
    tf = (timeframe or "").upper().strip()
    if tf not in TIMEFRAME_SECONDS:
        raise Mt5SourceError("Timeframe không hỗ trợ: %r" % timeframe)
    if raw is None:
        raise Mt5SourceError(
            "Chưa cài gói MetaTrader5. pip install MetaTrader5 rồi mở terminal."
        )
    api = ReadOnlyMt5(raw)
    if not api.initialize(terminal_path):
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
