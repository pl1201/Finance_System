"""Kho live riêng (``live.sqlite``, plan_mt5_live.md §2, §4): luồng live, nến MT5, bản ghi dự báo, lần broker sửa lịch sử.

Tách khỏi ``lab.sqlite``: nến live không trộn vào dataset nghiên cứu. Nến, bản ghi dự báo và lần sửa lịch sử **chỉ ghi
thêm** — trigger chặn ``UPDATE`` / ``DELETE`` ngay trong SQLite, nên không «chấm lại cho đẹp» được. Luồng không xoá được
và chỉ đổi được trạng thái (chạy / dừng / lỗi): trigger chặn sửa mọi cột khác.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Iterable

from backend.app.storage.base import connect_sqlite, ensure_parent

APPEND_ONLY = ("live_bar", "live_forecast", "live_revision", "llm_log", "llm_data")

SCHEMA = """
CREATE TABLE IF NOT EXISTS live_feed (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    mt5_symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    server_tz TEXT NOT NULL,
    terminal_path TEXT NOT NULL DEFAULT '',
    algorithm TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    params_json TEXT NOT NULL,
    params_sha256 TEXT NOT NULL,
    history_bars INTEGER NOT NULL,
    forward_from TEXT NOT NULL,
    status TEXT NOT NULL,
    status_note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS live_bar (
    feed_id TEXT NOT NULL REFERENCES live_feed(id),
    idx INTEGER NOT NULL,
    bar_time TEXT NOT NULL,
    open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL, volume REAL NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (feed_id, idx)
);
CREATE TABLE IF NOT EXISTS live_forecast (
    feed_id TEXT NOT NULL REFERENCES live_feed(id),
    idx INTEGER NOT NULL,
    close_time TEXT NOT NULL,
    written_at TEXT NOT NULL,
    timely INTEGER NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY (feed_id, idx)
);
CREATE TABLE IF NOT EXISTS live_revision (
    feed_id TEXT NOT NULL REFERENCES live_feed(id),
    idx INTEGER NOT NULL,
    seen_at TEXT NOT NULL,
    stored_json TEXT NOT NULL,
    seen_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_log (
    nguon TEXT NOT NULL,
    nguon_id TEXT NOT NULL,
    nguon_info TEXT NOT NULL,
    at TEXT NOT NULL,
    mode TEXT NOT NULL,
    cau_hoi TEXT NOT NULL,
    tra_loi TEXT NOT NULL,
    nen INTEGER NOT NULL,
    nen_dong_luc TEXT NOT NULL,
    mo_hinh TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cached_tokens INTEGER,
    cost REAL,
    so_la TEXT NOT NULL,
    cat_ngan INTEGER NOT NULL,
    data_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_data (
    data_sha256 TEXT PRIMARY KEY,
    data_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS live_log (
    feed_id TEXT NOT NULL,
    at TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);
""" + "".join(
    "CREATE TRIGGER IF NOT EXISTS {t}_no_{op} BEFORE {OP} ON {t} "
    "BEGIN SELECT RAISE(ABORT, '{t}: chỉ ghi thêm, không sửa / xoá'); END;\n".format(t=t, op=op.lower(), OP=op)
    for t in APPEND_ONLY for op in ("UPDATE", "DELETE")) + """
CREATE TRIGGER IF NOT EXISTS live_feed_no_delete BEFORE DELETE ON live_feed
BEGIN SELECT RAISE(ABORT, 'live_feed: không xoá luồng'); END;
CREATE TRIGGER IF NOT EXISTS live_feed_fixed BEFORE UPDATE OF id, created_at, symbol, mt5_symbol, timeframe, server_tz,
    terminal_path, algorithm, algorithm_version, params_json, params_sha256, history_bars, forward_from ON live_feed
BEGIN SELECT RAISE(ABORT, 'live_feed: chỉ đổi được trạng thái'); END;
"""

BAR_COLS = ("bar_time", "open", "high", "low", "close", "volume")


class LiveStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()                   # khoá ghi riêng — không chờ khoá của lab.sqlite
        ensure_parent(path)
        with self._lock, self.connect() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(llm_log)")]
            if cols and "nguon" not in cols:            # llm_log bản đầu (chỉ luồng live, cột feed_id): giữ nguyên dưới tên
                conn.execute("ALTER TABLE llm_log RENAME TO llm_log_v1")      # mới — chỉ ghi thêm, không sửa hàng
            conn.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        return connect_sqlite(self.path)

    # ------------------------------------------------------------------ luồng
    def create_feed(self, feed: dict[str, Any], bars: list[dict[str, Any]], fetched_at: str) -> None:
        """Luồng mới + nến lịch sử, một giao dịch."""
        with self._lock, self.connect() as conn:
            conn.execute("INSERT INTO live_feed (%s) VALUES (%s)" % (", ".join(feed), ", ".join("?" * len(feed))),
                         tuple(feed.values()))
            self._insert_bars(conn, feed["id"], 0, bars, fetched_at)

    def set_status(self, feed_id: str, status: str, note: str = "") -> None:
        with self._lock, self.connect() as conn:
            conn.execute("UPDATE live_feed SET status = ?, status_note = ? WHERE id = ?", (status, note, feed_id))

    def get_feed(self, feed_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM live_feed WHERE id = ?", (feed_id,)).fetchone()
        return dict(row) if row else None

    def list_feeds(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM live_feed ORDER BY created_at DESC")]

    # ------------------------------------------------------------------ nến, bản ghi
    @staticmethod
    def _insert_bars(conn: sqlite3.Connection, feed_id: str, start: int, bars: list[dict[str, Any]],
                     fetched_at: str) -> None:
        conn.executemany(
            "INSERT INTO live_bar (feed_id, idx, %s, fetched_at) VALUES (?, ?, %s, ?)"
            % (", ".join(BAR_COLS), ", ".join("?" * len(BAR_COLS))),
            [(feed_id, start + i, b["bar_time"].isoformat(), *(b[c] for c in BAR_COLS[1:]), fetched_at)
             for i, b in enumerate(bars)])

    def append(self, feed_id: str, start: int, bars: list[dict[str, Any]], forecasts: Iterable[dict[str, Any]],
               fetched_at: str) -> None:
        """Nến mới (chỉ số từ ``start``) và bản ghi dự báo của chúng, một giao dịch."""
        with self._lock, self.connect() as conn:
            self._insert_bars(conn, feed_id, start, bars, fetched_at)
            conn.executemany(
                "INSERT INTO live_forecast (feed_id, idx, close_time, written_at, timely, record_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(feed_id, f["idx"], f["close_time"], f["written_at"], int(f["timely"]),
                  json.dumps(f["record"], ensure_ascii=False)) for f in forecasts])

    def get_bars(self, feed_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT idx, %s FROM live_bar WHERE feed_id = ? ORDER BY idx" % ", ".join(BAR_COLS), (feed_id,))]

    def get_forecasts(self, feed_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT idx, close_time, written_at, timely, record_json FROM live_forecast "
                                "WHERE feed_id = ? ORDER BY idx", (feed_id,)).fetchall()
        return [dict(idx=r["idx"], close_time=r["close_time"], written_at=r["written_at"], timely=bool(r["timely"]),
                     record=json.loads(r["record_json"])) for r in rows]

    # ------------------------------------------------------------------ sửa lịch sử, nhật ký
    def add_revision(self, feed_id: str, idx: int, seen_at: str, stored: dict[str, Any], seen: dict[str, Any]) -> None:
        with self._lock, self.connect() as conn:
            conn.execute("INSERT INTO live_revision (feed_id, idx, seen_at, stored_json, seen_json) VALUES (?, ?, ?, ?, ?)",
                         (feed_id, idx, seen_at, json.dumps(stored), json.dumps(seen)))

    def get_revisions(self, feed_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT idx, seen_at, stored_json, seen_json FROM live_revision WHERE feed_id = ? "
                                "ORDER BY rowid", (feed_id,)).fetchall()
        return [dict(idx=r["idx"], seen_at=r["seen_at"], stored=json.loads(r["stored_json"]),
                     seen=json.loads(r["seen_json"])) for r in rows]

    # ------------------------------------------------------------------ trợ lý tổng hợp (plan_tro_ly_tong_hop.md §4)
    def add_llm_log(self, row: dict[str, Any], data_json: str) -> None:
        """Một lượt hỏi — đáp của trợ lý (nguồn: luồng live hoặc phiên replay trang Thử nghiệm); dữ liệu gửi đi lưu một
        lần theo sha256 (các câu hỏi cùng nến dùng chung)."""
        with self._lock, self.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO llm_data (data_sha256, data_json) VALUES (?, ?)",
                         (row["data_sha256"], data_json))
            conn.execute("INSERT INTO llm_log (%s) VALUES (%s)" % (", ".join(row), ", ".join("?" * len(row))),
                         tuple(row.values()))

    def log(self, feed_id: str, at: str, level: str, message: str) -> None:
        with self._lock, self.connect() as conn:
            conn.execute("INSERT INTO live_log (feed_id, at, level, message) VALUES (?, ?, ?, ?)",
                         (feed_id, at, level, message))

    def recent_logs(self, feed_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT at, level, message FROM live_log WHERE feed_id = ? ORDER BY rowid DESC LIMIT ?", (feed_id, limit))]
