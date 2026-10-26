"""Khoá ghi dùng chung cho mọi repo (SQLite một tiến trình), mở kết nối SQLite và mốc thời gian UTC."""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone

#: Tuần tự hoá các lệnh GHI; đọc không cần khoá (SQLite WAL).
DB_LOCK = threading.Lock()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def connect_sqlite(path: str) -> sqlite3.Connection:
    """Kết nối SQLite của lab: chờ khoá 30 giây, hàng dạng ``Row``, bật khoá ngoại."""
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
