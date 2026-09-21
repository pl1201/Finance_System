"""Lưu trữ SQLite: dataset, nến, lần chạy và sự kiện.

Dữ liệu nằm trong ``data/lab.sqlite``; file CSV gốc được sao lưu nguyên vẹn
vào ``data/raw/``. Nhờ đó lịch sử thí nghiệm vẫn mở lại được sau khi khởi
động lại ứng dụng.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

_LOCK = threading.Lock()

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS datasets (
    id                    TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    symbol                TEXT NOT NULL,
    timeframe             TEXT NOT NULL,
    source                TEXT NOT NULL,
    price_type            TEXT NOT NULL DEFAULT 'unspecified',
    source_timezone       TEXT NOT NULL,
    timestamp_convention  TEXT NOT NULL,
    row_count             INTEGER NOT NULL,
    start_time            TEXT,
    end_time              TEXT,
    checksum_sha256       TEXT NOT NULL,
    file_checksum_sha256  TEXT,
    raw_path              TEXT,
    is_synthetic          INTEGER NOT NULL DEFAULT 0,
    quality_json          TEXT NOT NULL DEFAULT '{}',
    mapping_json          TEXT NOT NULL DEFAULT '{}',
    notes                 TEXT NOT NULL DEFAULT '',
    created_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bars (
    dataset_id  TEXT NOT NULL,
    idx         INTEGER NOT NULL,
    bar_time    TEXT NOT NULL,
    open        REAL NOT NULL,
    high        REAL NOT NULL,
    low         REAL NOT NULL,
    close       REAL NOT NULL,
    volume      REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (dataset_id, idx),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_bars_time ON bars(dataset_id, bar_time);

CREATE TABLE IF NOT EXISTS runs (
    run_id              TEXT PRIMARY KEY,
    label               TEXT NOT NULL DEFAULT '',
    dataset_id          TEXT NOT NULL,
    dataset_checksum    TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    timeframe           TEXT NOT NULL,
    algorithm           TEXT NOT NULL,
    algorithm_version   TEXT NOT NULL,
    params_json         TEXT NOT NULL,
    range_start         TEXT,
    range_end           TEXT,
    range_start_index   INTEGER NOT NULL DEFAULT 0,
    range_end_index     INTEGER NOT NULL DEFAULT 0,
    bars_processed      INTEGER NOT NULL,
    warmup_bars         INTEGER NOT NULL,
    duration_ms         REAL NOT NULL,
    data_status         TEXT NOT NULL,
    stats_json          TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_runs_dataset ON runs(dataset_id, created_at);

CREATE TABLE IF NOT EXISTS events (
    run_id               TEXT NOT NULL,
    seq                  INTEGER NOT NULL,
    event_id             TEXT NOT NULL,
    structure_type       TEXT NOT NULL,
    price                REAL NOT NULL,
    event_bar_index      INTEGER NOT NULL,
    event_time           TEXT NOT NULL,
    event_close_time     TEXT NOT NULL,
    confirmed_bar_index  INTEGER NOT NULL,
    confirmed_at         TEXT NOT NULL,
    confirmation_lag_bars INTEGER NOT NULL,
    algorithm            TEXT NOT NULL,
    algorithm_version    TEXT NOT NULL,
    reason_code          TEXT NOT NULL,
    direction            TEXT,
    reference_event_id   TEXT,
    details_json         TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (run_id, seq),
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_events_run ON events(run_id, confirmed_bar_index);

CREATE TABLE IF NOT EXISTS label_sets (
    id            TEXT PRIMARY KEY,
    dataset_id    TEXT NOT NULL,
    version       TEXT NOT NULL,
    annotator     TEXT NOT NULL,
    rubric_vi     TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS labels (
    label_set_id    TEXT NOT NULL,
    seq             INTEGER NOT NULL,
    structure_type  TEXT NOT NULL,
    bar_index       INTEGER NOT NULL,
    price           REAL NOT NULL,
    notes           TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (label_set_id, seq),
    FOREIGN KEY (label_set_id) REFERENCES label_sets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_labels_set ON labels(label_set_id);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._init_schema()

    # -- kết nối --------------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with _LOCK, self.connect() as conn:
            conn.executescript(SCHEMA)

    # -- dataset --------------------------------------------------------

    def insert_dataset(self, meta: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute(
                """INSERT INTO datasets
                   (id, name, symbol, timeframe, source, price_type, source_timezone,
                    timestamp_convention, row_count, start_time, end_time,
                    checksum_sha256, file_checksum_sha256, raw_path, is_synthetic,
                    quality_json, mapping_json, notes, created_at)
                   VALUES (:id,:name,:symbol,:timeframe,:source,:price_type,
                           :source_timezone,:timestamp_convention,:row_count,
                           :start_time,:end_time,:checksum_sha256,
                           :file_checksum_sha256,:raw_path,:is_synthetic,
                           :quality_json,:mapping_json,:notes,:created_at)""",
                meta,
            )
            conn.executemany(
                """INSERT INTO bars (dataset_id, idx, bar_time, open, high, low, close, volume)
                   VALUES (?,?,?,?,?,?,?,?)""",
                [
                    (
                        meta["id"],
                        i,
                        r["bar_time"].astimezone(timezone.utc).isoformat(),
                        r["open"], r["high"], r["low"], r["close"], r.get("volume") or 0.0,
                    )
                    for i, r in enumerate(rows)
                ],
            )

    def list_datasets(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM datasets ORDER BY created_at DESC"
            ).fetchall()
        return [_dataset_row_to_dict(r) for r in rows]

    def get_dataset(self, dataset_id: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            r = conn.execute(
                "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
            ).fetchone()
        return _dataset_row_to_dict(r) if r else None

    def delete_dataset(self, dataset_id: str) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))

    def dataset_exists_by_checksum(self, checksum: str) -> Optional[str]:
        with self.connect() as conn:
            r = conn.execute(
                "SELECT id FROM datasets WHERE checksum_sha256 = ?", (checksum,)
            ).fetchone()
        return r["id"] if r else None

    def get_bars(
        self,
        dataset_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT idx, bar_time, open, high, low, close, volume FROM bars WHERE dataset_id = ?"
        args: list[Any] = [dataset_id]
        if start:
            sql += " AND bar_time >= ?"
            args.append(start)
        if end:
            sql += " AND bar_time <= ?"
            args.append(end)
        sql += " ORDER BY idx"
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]

    # -- run ------------------------------------------------------------

    def insert_run(self, run: dict[str, Any], events: Iterable[dict[str, Any]]) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute(
                """INSERT INTO runs
                   (run_id, label, dataset_id, dataset_checksum, symbol, timeframe,
                    algorithm, algorithm_version, params_json, range_start, range_end,
                    range_start_index, range_end_index, bars_processed, warmup_bars,
                    duration_ms, data_status, stats_json, created_at)
                   VALUES (:run_id,:label,:dataset_id,:dataset_checksum,:symbol,:timeframe,
                           :algorithm,:algorithm_version,:params_json,:range_start,:range_end,
                           :range_start_index,:range_end_index,:bars_processed,:warmup_bars,
                           :duration_ms,:data_status,:stats_json,:created_at)""",
                run,
            )
            conn.executemany(
                """INSERT INTO events
                   (run_id, seq, event_id, structure_type, price, event_bar_index,
                    event_time, event_close_time, confirmed_bar_index, confirmed_at,
                    confirmation_lag_bars, algorithm, algorithm_version, reason_code,
                    direction, reference_event_id, details_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        run["run_id"], i, e["event_id"], e["structure_type"], e["price"],
                        e["event_bar_index"], e["event_time"], e["event_close_time"],
                        e["confirmed_bar_index"], e["confirmed_at"],
                        e["confirmation_lag_bars"], e["algorithm"], e["algorithm_version"],
                        e["reason_code"], e.get("direction"), e.get("reference_event_id"),
                        json.dumps(e.get("details") or {}, ensure_ascii=False),
                    )
                    for i, e in enumerate(events)
                ],
            )

    def list_runs(self, dataset_id: Optional[str] = None, limit: int = 200) -> list[dict[str, Any]]:
        sql = "SELECT r.*, d.name AS dataset_name, d.is_synthetic FROM runs r "
        sql += "LEFT JOIN datasets d ON d.id = r.dataset_id"
        args: list[Any] = []
        if dataset_id:
            sql += " WHERE r.dataset_id = ?"
            args.append(dataset_id)
        sql += " ORDER BY r.created_at DESC LIMIT ?"
        args.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [_run_row_to_dict(r) for r in rows]

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            r = conn.execute(
                """SELECT r.*, d.name AS dataset_name, d.is_synthetic
                   FROM runs r LEFT JOIN datasets d ON d.id = r.dataset_id
                   WHERE r.run_id = ?""",
                (run_id,),
            ).fetchone()
        return _run_row_to_dict(r) if r else None

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY seq", (run_id,)
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["details"] = json.loads(d.pop("details_json") or "{}")
            out.append(d)
        return out

    def delete_run(self, run_id: str) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))

    def insert_label_set(self, meta: dict[str, Any], labels: list[dict[str, Any]]) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute(
                """INSERT INTO label_sets (id, dataset_id, version, annotator, rubric_vi, created_at)
                   VALUES (:id,:dataset_id,:version,:annotator,:rubric_vi,:created_at)""",
                meta,
            )
            conn.executemany(
                """INSERT INTO labels (label_set_id, seq, structure_type, bar_index, price, notes)
                   VALUES (?,?,?,?,?,?)""",
                [
                    (
                        meta["id"], i, lb["structure_type"], int(lb["bar_index"]),
                        float(lb["price"]), lb.get("notes") or "",
                    )
                    for i, lb in enumerate(labels)
                ],
            )

    def list_label_sets(self, dataset_id: Optional[str] = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM label_sets"
        args: list[Any] = []
        if dataset_id:
            sql += " WHERE dataset_id = ?"
            args.append(dataset_id)
        sql += " ORDER BY created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]

    def get_label_set(self, label_set_id: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            r = conn.execute("SELECT * FROM label_sets WHERE id = ?", (label_set_id,)).fetchone()
            if not r:
                return None
            labs = conn.execute(
                "SELECT * FROM labels WHERE label_set_id = ? ORDER BY seq", (label_set_id,)
            ).fetchall()
        d = dict(r)
        d["labels"] = [dict(x) for x in labs]
        return d

    def delete_label_set(self, label_set_id: str) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute("DELETE FROM label_sets WHERE id = ?", (label_set_id,))


def _dataset_row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["quality"] = json.loads(d.pop("quality_json") or "{}")
    d["mapping"] = json.loads(d.pop("mapping_json") or "{}")
    d["is_synthetic"] = bool(d["is_synthetic"])
    return d


def _run_row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["params"] = json.loads(d.pop("params_json") or "{}")
    d["stats"] = json.loads(d.pop("stats_json") or "{}")
    d["is_synthetic"] = bool(d.get("is_synthetic") or 0)
    return d


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
