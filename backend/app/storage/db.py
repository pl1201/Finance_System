"""Lưu trữ SQLite: dataset, nến, lần chạy, sự kiện, bộ nhãn, đánh giá.

Dữ liệu nằm trong ``data/lab.sqlite``; file CSV gốc được sao lưu nguyên vẹn
vào ``data/raw/``. Nhờ đó lịch sử thí nghiệm vẫn mở lại được sau khi khởi
động lại ứng dụng.

``Database`` ghép các repo theo mảng (``*_repo.py``) nên mọi nơi vẫn gọi
``db.get_run(...)``, ``db.list_label_sets(...)``… như trước. Lược đồ và
migration ở ``schema.py``.
"""
from __future__ import annotations

import sqlite3

from backend.app.storage.base import DB_LOCK, connect_sqlite, ensure_parent, utcnow_iso
from backend.app.storage.datasets_repo import DatasetRepo
from backend.app.storage.evals_repo import EvaluationRepo
from backend.app.storage.labels_repo import LabelRepo
from backend.app.storage.runs_repo import RunRepo
from backend.app.storage.schema import SCHEMA, migrate

__all__ = ["Database", "utcnow_iso"]


class Database(DatasetRepo, RunRepo, LabelRepo, EvaluationRepo):
    def __init__(self, path: str) -> None:
        self.path = path
        ensure_parent(path)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        return connect_sqlite(self.path)

    def _init_schema(self) -> None:
        with DB_LOCK, self.connect() as conn:
            conn.executescript(SCHEMA)
            migrate(conn)
