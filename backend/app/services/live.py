"""Luồng live chỉ đọc từ MT5 (``docs/plans/plan_mt5_live.md``): nến đã đóng → ``ict_structure`` tăng dần → bản ghi dự báo
chỉ ghi thêm → điểm forward. Không gửi lệnh (mọi lời gọi MT5 qua ``core.data.mt5_source.ReadOnlyMt5``), không P&L.

* Một luồng nền hỏi MT5 cho mọi luồng đang chạy (mặc định 10 giây; lỗi thì giãn dần tới 5 phút).
* Gói MetaTrader5 chỉ có **một kết nối mỗi tiến trình**: manager giữ một ``Mt5Reader`` (một terminal mỗi lúc), mọi lời
  gọi MT5 tuần tự dưới ``_mt5_lock``. Nhập lịch sử từ MT5 (trang dữ liệu) tự nối / ngắt riêng — luồng live nối lại ở lần
  hỏi sau.
* Bộ chạy trong bộ nhớ là ``ReplaySession`` ghim ở nến cuối, dựng lại từ nến đã lưu khi mở (tất định): bản ghi dựng lại
  phải trùng bản ghi đã lưu, phiên bản thuật toán phải trùng phiên bản của luồng. Lỗi giữa một lô nến (thuật toán, bản
  ghi, kho) → bỏ luồng khỏi bộ nhớ, luồng nền dựng lại từ kho.
* Chỉ nến sau phần lịch sử (chỉ số ≥ ``history_bars``) có bản ghi; điểm forward chính chỉ tính bản ghi kịp thời
  (``core.eval.forward.is_timely``).
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from backend.app import config
from backend.app.errors import NotFoundError, ServiceError
from backend.app.services.common import bar_payload, resolve_dataset_params
from backend.app.storage.live_repo import LiveStore
from core.data.mt5_source import Mt5Reader, Mt5SourceError, mt5_available, server_offset
from core.data.validate import first_bar_error
from core.engine import ReplaySession
from core.eval import forward
from core.registry import get_algorithm_class
from core.types import Bar, timeframe_delta

ALGORITHM = "ict_structure"
RUNNING, STOPPED, DATA_ERROR, OUTDATED, MISMATCH = "running", "stopped", "data_error", "outdated", "rebuild_mismatch"
STATUS_VI = {
    RUNNING: "đang chạy",
    STOPPED: "đã dừng",
    DATA_ERROR: "lỗi dữ liệu — dừng nạp",
    OUTDATED: "hết hiệu lực — phiên bản thuật toán đã đổi, không ghi dự báo mới",
    MISMATCH: "dựng lại không trùng bản ghi đã lưu — dừng",
}
MIN_HISTORY, MAX_BARS = 2000, 100_000
#: Khung ≤ H1: dự báo 1h / 4h; khoảng cách nến luôn là bội số bước kể cả qua đổi giờ của broker ``ny+7`` (nến H4 / D1
#: theo giờ server thì lệch 1 giờ UTC mỗi lần Mỹ đổi giờ).
MAX_STEP = timedelta(hours=1)
POLL_SECONDS, MAX_BACKOFF = 10.0, 300.0
OHLC = ("open", "high", "low", "close")


def _roundtrip(x: Any) -> Any:
    """Bản ghi đúng như sẽ đọc lại từ kho (tuple → list) — để so bản dựng lại với bản đã lưu."""
    return json.loads(json.dumps(x, ensure_ascii=False))


class _Feed:
    """Luồng đang mở: nến, phiên replay ghim ở nến cuối, bản ghi (chỉ số → bản ghi), lỗi lần hỏi gần nhất."""

    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row
        self.step = timeframe_delta(row["timeframe"])
        self.algo = get_algorithm_class(row["algorithm"])(**json.loads(row["params_json"]))
        self.q80 = forward.quantile_80(self.algo.params)
        self.bars: list[Bar] = []
        self.session = ReplaySession(self.bars, self.algo)     # phiên giữ chính list này: nối nến rồi step_forward(1)
        self.records: dict[int, dict[str, Any]] = {}
        self.timely: set[int] = set()
        self.revisions: set[tuple] = set()                     # (chỉ số, OHLC MT5 trả) đã ghi
        self.error: Optional[str] = None
        self.last_poll: Optional[str] = None
        self.next_poll = 0.0
        self.backoff = POLL_SECONDS
        self.scores: Optional[tuple[tuple[int, int], dict[str, Any]]] = None   # (số nến, số bản ghi) → điểm forward

    def push(self, r: dict[str, Any]) -> Bar:
        bar = Bar(len(self.bars), r["bar_time"], r["bar_time"] + self.step, r["open"], r["high"], r["low"], r["close"],
                  r["volume"])
        self.bars.append(bar)
        self.session.step_forward(1)
        return bar

    def record(self, bar: Bar) -> dict[str, Any]:
        rec = self.algo.forecast_record()
        if rec is None or rec["t"] != bar.index:
            raise ServiceError("Thuật toán không đưa bản ghi dự báo cho nến %d." % bar.index)
        return _roundtrip(rec)


class LiveManager:
    def __init__(self, store_path: Optional[str] = None, api: Any = None,
                 clock: Optional[Callable[[], datetime]] = None, poll_seconds: float = POLL_SECONDS) -> None:
        self._store_path = store_path
        self._store: Optional[LiveStore] = None
        self.api = api                                  # None = gói MetaTrader5; test truyền bản giả
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.poll_seconds = poll_seconds
        self._feeds: dict[str, _Feed] = {}
        self._reopen: set[str] = set()                  # luồng đang chạy bị bỏ khỏi bộ nhớ sau lỗi — luồng nền dựng lại
        self._lock = threading.RLock()                  # trạng thái luồng đã mở (nến, phiên, bản ghi)
        self._open_lock = threading.Lock()              # dựng luồng từng cái một, ngoài khoá trên (vài giây)
        self._mt5_lock = threading.Lock()               # một kết nối MT5 mỗi tiến trình: gọi tuần tự
        self._reader: Optional[Mt5Reader] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    @property
    def store(self) -> LiveStore:
        if self._store is None:                         # kho tạo khi dùng lần đầu, không tạo lúc import
            self._store = LiveStore(self._store_path or config.LIVE_DB_PATH)
        return self._store

    # ------------------------------------------------------------------ MT5 (một kết nối)
    def _mt5(self, terminal_path: str) -> Mt5Reader:
        """Reader dùng chung (gọi khi giữ ``_mt5_lock``). Đổi terminal chỉ khi không luồng đang chạy nào dùng terminal cũ."""
        r = self._reader
        if r is not None and (r.terminal_path or "") != (terminal_path or ""):
            busy = [f.row["id"] for f in list(self._feeds.values())
                    if f.row["status"] == RUNNING and (f.row["terminal_path"] or "") == (r.terminal_path or "")]
            if busy:
                raise Mt5SourceError("Gói MetaTrader5 chỉ nối một terminal mỗi lúc: đang nối %r cho luồng %s."
                                     % (r.terminal_path or "mặc định", ", ".join(busy)))
            r.close()
            r = None
        if r is None:
            r = self._reader = Mt5Reader(self.api, terminal_path)
        return r

    def _closed_bars(self, terminal_path: str, *args: Any) -> list[dict[str, Any]]:
        with self._mt5_lock:
            reader = self._mt5(terminal_path)
            try:
                return reader.closed_bars(*args)
            except Mt5SourceError:
                reader.close()                          # lần sau nối lại
                raise

    # ------------------------------------------------------------------ tạo, mở
    def create(self, *, symbol: str, mt5_symbol: str, timeframe: str, server_tz: str, history_bars: int = 20_000,
               params: Optional[dict[str, Any]] = None, terminal_path: str = "") -> dict[str, Any]:
        symbol, tf = (symbol or "").upper().strip(), (timeframe or "").upper().strip()
        mt5_symbol, server_tz = (mt5_symbol or symbol).strip(), (server_tz or "").strip()
        if not symbol:
            raise ServiceError("Phải nhập mã lab (vd XAUUSD) — dùng để chọn lịch phiên.")
        if not MIN_HISTORY <= history_bars <= MAX_BARS:
            raise ServiceError("Số nến lịch sử phải trong %d … %d." % (MIN_HISTORY, MAX_BARS))
        now = self.clock()
        cls = get_algorithm_class(ALGORITHM)
        try:
            if timeframe_delta(tf) > MAX_STEP:
                raise ValueError("Luồng live chỉ cho khung ≤ H1 (dự báo 1h / 4h).")
            server_offset(server_tz, now)
            norm = cls.validate_params(resolve_dataset_params(cls, dict(params or {}, timeframe=tf), {"symbol": symbol}))
            cls.check_dataset(tf, norm)
            forward.quantile_80(norm)
            rows = self._closed_bars(terminal_path, mt5_symbol, tf, history_bars, server_tz, now)
            err = first_bar_error(rows, timeframe_delta(tf))
            if err:
                raise ValueError("Dữ liệu MT5 lỗi: %s." % err)
            if len(rows) < MIN_HISTORY:
                raise ValueError("MT5 chỉ trả %d nến đã đóng; cần ≥ %d (tăng «Max bars in chart» của terminal)."
                                 % (len(rows), MIN_HISTORY))
        except (KeyError, ValueError, Mt5SourceError) as exc:
            raise ServiceError(str(exc)) from exc
        params_json = json.dumps(norm, sort_keys=True, ensure_ascii=False)
        row = {"id": "lv_" + uuid.uuid4().hex[:10], "created_at": now.isoformat(), "symbol": symbol,
               "mt5_symbol": mt5_symbol, "timeframe": tf, "server_tz": server_tz, "terminal_path": terminal_path or "",
               "algorithm": ALGORITHM, "algorithm_version": cls.version, "params_json": params_json,
               "params_sha256": hashlib.sha256(params_json.encode("utf-8")).hexdigest(), "history_bars": len(rows),
               "forward_from": (rows[-1]["bar_time"] + timeframe_delta(tf)).isoformat(), "status": RUNNING,
               "status_note": ""}
        self.store.create_feed(row, rows, now.isoformat())
        self._get(row["id"])                            # dựng từ kho, đúng như khi khởi động lại
        self._ensure_thread()
        return self.status(row["id"])

    def _build(self, row: dict[str, Any]) -> _Feed:
        """Dựng luồng từ kho: nạp lại mọi nến; bản ghi dựng lại phải trùng bản ghi đã lưu (cùng phiên bản thuật toán).
        Chưa ai thấy luồng này nên không cần khoá chung. Code mới không dựng được luồng cũ → lỗi rõ (kho giữ nguyên)."""
        version = get_algorithm_class(row["algorithm"]).version
        try:
            feed = _Feed(row)
        except (KeyError, ValueError, TypeError) as exc:
            if version != row["algorithm_version"] and row["status"] == RUNNING:
                self.store.set_status(row["id"], OUTDATED, "code %s không dựng được: %s" % (version, exc))
            raise ServiceError("Luồng %s (thuật toán %s) không dựng lại được bằng code %s: %s. Nến và bản ghi vẫn trong kho."
                               % (row["id"], row["algorithm_version"], version, exc)) from exc
        stored = {f["idx"]: f for f in self.store.get_forecasts(row["id"])}
        same_version = version == row["algorithm_version"]
        mismatch = None
        for r in self.store.get_bars(row["id"]):
            bar = feed.push(dict(r, bar_time=datetime.fromisoformat(r["bar_time"])))
            if same_version and mismatch is None and bar.index >= row["history_bars"]:
                f = stored.get(bar.index)
                if f is None or f["record"] != feed.record(bar):
                    mismatch = bar.index
        feed.records = {i: f["record"] for i, f in stored.items()}
        feed.timely = {i for i, f in stored.items() if f["timely"]}
        feed.revisions = {(r["idx"], *(r["seen"][c] for c in OHLC)) for r in self.store.get_revisions(row["id"])}
        if not same_version and row["status"] != OUTDATED:
            self._set_status(feed, OUTDATED, "luồng %s, code %s" % (row["algorithm_version"], version))
        elif mismatch is not None and row["status"] != MISMATCH:
            self._set_status(feed, MISMATCH, "bản ghi nến %d khác bản đã lưu" % mismatch)
        return feed

    def _get(self, feed_id: str) -> _Feed:
        feed = self._feeds.get(feed_id)
        if feed is not None:
            return feed
        with self._open_lock:
            feed = self._feeds.get(feed_id)
            if feed is None:
                row = self.store.get_feed(feed_id)
                if row is None:
                    raise NotFoundError("Không có luồng live %s." % feed_id)
                feed = self._build(row)
                with self._lock:
                    self._feeds[feed_id] = feed
            return feed

    def _set_status(self, feed: _Feed, status: str, note: str = "") -> None:
        feed.row = dict(feed.row, status=status, status_note=note)
        self.store.set_status(feed.row["id"], status, note)
        self.store.log(feed.row["id"], self.clock().isoformat(), "info", "%s%s" % (STATUS_VI[status],
                                                                                   (": " + note) if note else ""))

    # ------------------------------------------------------------------ hỏi MT5
    def poll(self, feed_id: str) -> int:
        """Một lần hỏi MT5 cho luồng: nến mới đã đóng → thuật toán → bản ghi (một giao dịch). Trả số nến mới."""
        feed = self._get(feed_id)
        row = feed.row
        if row["status"] != RUNNING:
            return 0
        now = self.clock()
        last = feed.bars[-1]
        need = min(MAX_BARS, max(3, int((now - last.close_time) / feed.step) + 3))
        rows = self._closed_bars(row["terminal_path"], row["mt5_symbol"], row["timeframe"], need, row["server_tz"], now)
        with self._lock:
            if feed.row["status"] != RUNNING or self._feeds.get(feed_id) is not feed:   # dừng / bỏ trong lúc hỏi MT5
                return 0
            feed.last_poll = now.isoformat()
            self._revisions(feed, rows, now)
            new = [r for r in rows if r["bar_time"] > last.bar_time]
            if not new:
                return 0
            err = first_bar_error(new, feed.step, last.bar_time)
            if err:
                self._set_status(feed, DATA_ERROR, err)
                return 0
            start = len(feed.bars)
            try:
                done = [(b, feed.record(b)) for b in map(feed.push, new)]
                written = self.clock()
                forecasts = [{"idx": b.index, "close_time": b.close_time.isoformat(), "written_at": written.isoformat(),
                              "timely": forward.is_timely(written, b.close_time, feed.step), "record": rec}
                             for b, rec in done]
                self.store.append(row["id"], start, new, forecasts, now.isoformat())
            except Exception:
                self._feeds.pop(feed_id, None)          # bộ nhớ đã đi trước kho: bỏ, luồng nền dựng lại từ kho
                self._reopen.add(feed_id)
                raise
            for f in forecasts:
                feed.records[f["idx"]] = f["record"]
                if f["timely"]:
                    feed.timely.add(f["idx"])
            return len(new)

    def _revisions(self, feed: _Feed, rows: list[dict[str, Any]], now: datetime) -> None:
        """Nến đã lưu mà MT5 nay trả OHLC khác → ghi một lần (broker sửa lịch sử); nến đã lưu không đổi."""
        tail = {b.bar_time: b for b in feed.bars[-(len(rows) + 1):]}
        for r in rows:
            b = tail.get(r["bar_time"])
            if b is None:
                continue
            seen = {c: r[c] for c in OHLC}
            stored = {c: getattr(b, c) for c in OHLC}
            key = (b.index, *seen.values())
            if seen != stored and key not in feed.revisions:
                feed.revisions.add(key)
                self.store.add_revision(feed.row["id"], b.index, now.isoformat(), stored, seen)

    # ------------------------------------------------------------------ luồng nền
    def start(self) -> None:
        """Backend khởi động: luồng nền tự mở lại các luồng đang chạy."""
        self._ensure_thread()

    def shutdown(self) -> None:
        self._stop.set()
        with self._mt5_lock:
            if self._reader is not None:
                self._reader.close()

    def _ensure_thread(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._stop.clear()
                self._thread = threading.Thread(target=self._loop, name="msl-live", daemon=True)
                self._thread.start()

    def _log_safe(self, feed_id: str, level: str, msg: str) -> None:
        try:
            self.store.log(feed_id, self.clock().isoformat(), level, msg)
        except Exception:                               # kho hỏng: không để luồng nền chết vì ghi nhật ký
            pass

    def _reopen_feeds(self, ids: list[str]) -> None:
        for fid in ids:
            try:
                self._get(fid)
                self._reopen.discard(fid)
            except Exception as exc:                    # từng luồng một: luồng hỏng không chặn luồng khác
                self._reopen.add(fid)
                self._log_safe(fid, "error", "không mở lại được: %s" % exc)

    def _loop(self) -> None:
        try:
            self._reopen_feeds([r["id"] for r in self.store.list_feeds() if r["status"] == RUNNING])
        except Exception:
            pass
        while not self._stop.wait(1.0):
            if self._reopen:
                self._reopen_feeds(list(self._reopen))
            for fid, feed in list(self._feeds.items()):
                if feed.row["status"] != RUNNING or time.monotonic() < feed.next_poll:
                    continue
                try:
                    self.poll(fid)
                    feed.error, feed.backoff = None, self.poll_seconds
                except Exception as exc:                # MT5 / kho / lỗi lạ: ghi, giãn lần hỏi, không chết luồng nền
                    msg = str(exc) if isinstance(exc, (Mt5SourceError, ServiceError)) else "lỗi: %r" % (exc,)
                    if msg != feed.error:
                        self._log_safe(fid, "error", msg)
                    feed.error, feed.backoff = msg, min(MAX_BACKOFF, feed.backoff * 2)
                feed.next_poll = time.monotonic() + feed.backoff

    # ------------------------------------------------------------------ điều khiển
    def stop(self, feed_id: str) -> dict[str, Any]:
        feed = self._get(feed_id)
        with self._lock:
            if feed.row["status"] == RUNNING:
                self._set_status(feed, STOPPED)
        return self.status(feed_id)

    def resume(self, feed_id: str) -> dict[str, Any]:
        feed = self._get(feed_id)
        with self._lock:
            if feed.row["status"] in (OUTDATED, MISMATCH):
                raise ServiceError("Luồng %s: %s. Tạo luồng mới để chạy tiếp." % (feed_id, STATUS_VI[feed.row["status"]]))
            if feed.row["status"] != RUNNING:
                self._set_status(feed, RUNNING)
                feed.error, feed.next_poll, feed.backoff = None, 0.0, self.poll_seconds
        self._ensure_thread()
        return self.status(feed_id)

    # ------------------------------------------------------------------ đọc
    def list_feeds(self) -> dict[str, Any]:
        rows = self.store.list_feeds()
        return {"goi_mt5": mt5_available(), "algorithm": ALGORITHM,
                "luong": [{k: r[k] for k in ("id", "symbol", "mt5_symbol", "timeframe", "server_tz", "status",
                                             "algorithm_version", "created_at", "history_bars")}
                          | {"status_vi": STATUS_VI[r["status"]]} for r in rows]}

    def status(self, feed_id: str) -> dict[str, Any]:
        return self._status(self._get(feed_id))

    def _status(self, feed: _Feed) -> dict[str, Any]:
        """Trạng thái của luồng đã mở (không tra lại ``_get`` — gọi được khi đang giữ ``_lock``)."""
        with self._lock:
            row, last = feed.row, feed.bars[-1]
            return {
                **{k: row[k] for k in ("id", "symbol", "mt5_symbol", "timeframe", "server_tz", "algorithm",
                                       "algorithm_version", "params_sha256", "created_at", "history_bars",
                                       "forward_from", "status", "status_note")},
                "status_vi": STATUS_VI[row["status"]], "phien_ban_code": feed.algo.version, "loi": feed.error,
                "lan_hoi_cuoi": feed.last_poll, "so_nen": len(feed.bars), "nen_cuoi_dong_luc": last.close_time.isoformat(),
                "so_ban_ghi": len(feed.records), "kip_thoi": len(feed.timely), "sua_lich_su": len(feed.revisions),
                "nhat_ky": self.store.recent_logs(row["id"], 5),
            }

    def snapshot(self, feed_id: str, since: Optional[int] = None) -> dict[str, Any]:
        """Như snapshot của replay (con trỏ = nến cuối) + trạng thái luồng; ``since`` → kèm nến mới sau ``delta_since``
        (``since = -1``: mọi nến, đọc cùng lúc với sự kiện / timeline). ``since`` ≥ con trỏ (không có nến mới) → chỉ con trỏ +
        trạng thái luồng, không dựng lại pending_state."""
        feed = self._get(feed_id)
        with self._lock:
            row, cursor = feed.row, feed.session.cursor
            if since is not None and since >= cursor:
                return {"cursor": cursor, "delta_since": cursor, "bars_moi": [], "live": self._status(feed)}
            snap = feed.session.snapshot(None if since is None else max(-1, since))
            s = snap["delta_since"]
            snap.update(
                session_id=row["id"], live=self._status(feed), algorithm=row["algorithm"],
                algorithm_version=feed.algo.version, params=feed.algo.params,
                timeline=list(snap["timeline"]),        # bản sao: luồng nền nối tiếp timeline sau khi nhả khoá
                dataset={"id": row["id"], "name": "Live %s %s (MT5 %s, chỉ đọc)" % (row["symbol"], row["timeframe"],
                                                                                 row["mt5_symbol"]),
                         "symbol": row["symbol"], "timeframe": row["timeframe"], "is_synthetic": False},
                bars_moi=None if s is None else [bar_payload(b) for b in feed.bars[s + 1:]],
            )
            return snap

    def llm_context(self, feed_id: str, digits: int) -> dict[str, Any]:
        """Bản tóm gọn ở nến cuối của luồng cho trợ lý tổng hợp (``llm_context`` của thuật toán, plan_tro_ly_tong_hop.md
        §3); ``digits`` = số chữ số giá như chart."""
        feed = self._get(feed_id)
        with self._lock:
            ctx = feed.algo.llm_context(feed.session.events, symbol=feed.row["symbol"], digits=digits)
        if ctx is None:
            raise ServiceError("Luồng chưa có nến.")
        return ctx

    def bars(self, feed_id: str) -> list[dict[str, Any]]:
        feed = self._get(feed_id)
        with self._lock:
            bars = list(feed.bars)
        return [bar_payload(b) for b in bars]

    def forward_scores(self, feed_id: str) -> dict[str, Any]:
        feed = self._get(feed_id)
        with self._lock:
            row, last = feed.row, feed.bars[-1]
            n_rec, n_timely, key, cached = len(feed.records), len(feed.timely), (len(feed.bars), len(feed.records)), feed.scores
            if cached is None or cached[0] != key:      # điểm chỉ đổi khi có nến mới: chỉ chép khi phải chấm lại
                bars, records, timely = list(feed.bars), dict(feed.records), set(feed.timely)
        if cached is not None and cached[0] == key:
            tam = cached[1]
        else:
            tam = forward.score(bars, records, feed.q80, feed.step, only=timely)
            feed.scores = (key, tam)
        return {
            "tam": tam, "so_ban_ghi": n_rec, "kip_thoi": n_timely, "ghi_bu": n_rec - n_timely,
            "sua_lich_su": len(feed.revisions), "forward_tu": row["forward_from"],
            "nen_cuoi_dong_luc": last.close_time.isoformat(), "phien_ban_ban_ghi": row["algorithm_version"],
            "toi_thieu_ket_luan": forward.MIN_SCORED,
            "ghi_chu_vi": "Điểm thật trên nến chưa từng thấy: chỉ bản ghi kịp thời (ghi trước khi nến kế tiếp đóng), chấm "
                          "bằng nến đã lưu, cùng định nghĩa với điểm trong lần chạy; B0 = cùng cách bỏ giờ NY / bỏ tuổi "
                          "trạng thái. Dưới %d dự báo đã chấm thì chưa kết luận." % forward.MIN_SCORED,
        }

    def hint(self, mt5_symbol: str, server_tz: str = "", terminal_path: str = "") -> dict[str, Any]:
        """Gợi ý kiểm khai báo giờ server (không tự áp): giờ tick cuối − đồng hồ máy, so với khai báo."""
        now = self.clock()
        try:
            with self._mt5_lock:
                lech = self._mt5(terminal_path).offset_hint(mt5_symbol.strip(), now)
            declared = int(server_offset(server_tz, now).total_seconds()) if server_tz.strip() else None
        except Mt5SourceError as exc:
            raise ServiceError(str(exc)) from exc
        out: dict[str, Any] = {"co_tick": lech is not None, "khai_bao_giay": declared,
                               "ghi_chu_vi": "Giờ tick cuối − đồng hồ máy, làm tròn 30 phút. Chỉ đúng khi thị trường "
                                             "đang mở và vừa có tick; lab không tự áp."}
        if lech is not None:
            out.update(lech_giay=lech, tin_duoc=-12 * 3600 <= lech <= 14 * 3600,
                       khop=None if declared is None else lech == declared)
        return out


live_manager = LiveManager()
