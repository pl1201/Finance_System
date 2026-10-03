"""Khoá ghi dùng chung cho mọi repo (SQLite một tiến trình) và mốc thời gian UTC."""
from __future__ import annotations

import threading
from datetime import datetime, timezone

#: Tuần tự hoá các lệnh GHI; đọc không cần khoá (SQLite WAL).
DB_LOCK = threading.Lock()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
