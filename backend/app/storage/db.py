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
    revision      INTEGER NOT NULL DEFAULT 1,
    updated_at    TEXT,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS labels (
    label_set_id    TEXT NOT NULL,
    seq             INTEGER NOT NULL,
    structure_type  TEXT NOT NULL,
    bar_index       INTEGER NOT NULL,
    price           REAL NOT NULL,
    notes           TEXT NOT NULL DEFAULT '',
    source          TEXT NOT NULL DEFAULT 'human',
    source_algorithm TEXT NOT NULL DEFAULT '',
    source_detail   TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (label_set_id, seq),
    FOREIGN KEY (label_set_id) REFERENCES label_sets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_labels_set ON labels(label_set_id);

CREATE TABLE IF NOT EXISTS evaluations (
    id               TEXT PRIMARY KEY,
    created_at       TEXT NOT NULL,
    dataset_id       TEXT NOT NULL,
    label_set_id     TEXT,
    protocol_json    TEXT NOT NULL,
    protocol_hash    TEXT NOT NULL,
    baseline_run_id  TEXT,
    run_ids_json     TEXT NOT NULL,
    result_json      TEXT NOT NULL,
    duration_ms      REAL NOT NULL,
    note_vi          TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_eval_dataset ON evaluations(dataset_id, created_at);
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
            self._migrate(conn)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Thêm cột cho DB đã tạo từ phiên bản trước. An toàn khi chạy lại."""
        def cols(table: str) -> set[str]:
            return {r["name"] for r in conn.execute("PRAGMA table_info(%s)" % table)}

        have = cols("label_sets")
        if "revision" not in have:
            # Bộ nhãn đã có trước khi hỗ trợ ghi đè: coi như bản 1.
            conn.execute("ALTER TABLE label_sets ADD COLUMN revision INTEGER NOT NULL DEFAULT 1")
        if "updated_at" not in have:
            conn.execute("ALTER TABLE label_sets ADD COLUMN updated_at TEXT")
            conn.execute("UPDATE label_sets SET updated_at = created_at WHERE updated_at IS NULL")

        have_labels = cols("labels")
        # Nguồn gốc từng nhãn: người tự gán hay đề xuất tự động đã được duyệt.
        # Nhãn cũ đều do người gán.
        if "source" not in have_labels:
            conn.execute("ALTER TABLE labels ADD COLUMN source TEXT NOT NULL DEFAULT 'human'")
        if "source_algorithm" not in have_labels:
            conn.execute("ALTER TABLE labels ADD COLUMN source_algorithm TEXT NOT NULL DEFAULT ''")
        if "source_detail" not in have_labels:
            conn.execute("ALTER TABLE labels ADD COLUMN source_detail TEXT NOT NULL DEFAULT ''")

        if "label_set_revision" not in cols("evaluations"):
            # Ghi lại bản nhãn mà mỗi đánh giá đã dùng, để ghi đè nhãn về sau
            # không làm kết quả cũ trở nên không giải thích được.
            conn.execute("ALTER TABLE evaluations ADD COLUMN label_set_revision INTEGER")

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
                """INSERT INTO label_sets
                   (id, dataset_id, version, annotator, rubric_vi, created_at,
                    revision, updated_at)
                   VALUES (:id,:dataset_id,:version,:annotator,:rubric_vi,:created_at,
                           1,:created_at)""",
                meta,
            )
            conn.executemany(
                """INSERT INTO labels (label_set_id, seq, structure_type, bar_index, price, notes,
                                         source, source_algorithm, source_detail)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        meta["id"], i, lb["structure_type"], int(lb["bar_index"]),
                        float(lb["price"]), lb.get("notes") or "",
                        lb.get("source") or "human", lb.get("source_algorithm") or "",
                        lb.get("source_detail") or "",
                    )
                    for i, lb in enumerate(labels)
                ],
            )

    def list_label_sets(self, dataset_id: Optional[str] = None) -> list[dict[str, Any]]:
        sql = (
            "SELECT ls.*, "
            "(SELECT COUNT(*) FROM labels l WHERE l.label_set_id = ls.id) AS n_labels, "
            "(SELECT COUNT(*) FROM labels l WHERE l.label_set_id = ls.id "
            " AND l.source <> 'human') AS n_auto "
            "FROM label_sets ls"
        )
        args: list[Any] = []
        if dataset_id:
            sql += " WHERE ls.dataset_id = ?"
            args.append(dataset_id)
        sql += " ORDER BY ls.created_at DESC"
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

    def update_label_set(self, meta: dict[str, Any], labels: list[dict[str, Any]]) -> int:
        """Ghi đè nội dung một bộ nhãn, tăng ``revision``. Trả về revision mới.

        ``dataset_id`` KHÔNG đổi: một bộ nhãn luôn thuộc đúng dataset đã tạo ra
        nó, vì ``bar_index`` chỉ có nghĩa trong dataset đó.
        """
        with _LOCK, self.connect() as conn:
            row = conn.execute(
                "SELECT revision FROM label_sets WHERE id = ?", (meta["id"],)
            ).fetchone()
            if not row:
                raise KeyError(meta["id"])
            new_rev = int(row["revision"] or 1) + 1
            conn.execute(
                """UPDATE label_sets
                      SET version = :version, annotator = :annotator,
                          rubric_vi = :rubric_vi, updated_at = :updated_at,
                          revision = :revision
                    WHERE id = :id""",
                {**meta, "revision": new_rev},
            )
            conn.execute("DELETE FROM labels WHERE label_set_id = ?", (meta["id"],))
            conn.executemany(
                """INSERT INTO labels (label_set_id, seq, structure_type, bar_index, price, notes,
                                         source, source_algorithm, source_detail)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        meta["id"], i, lb["structure_type"], int(lb["bar_index"]),
                        float(lb["price"]), lb.get("notes") or "",
                        lb.get("source") or "human", lb.get("source_algorithm") or "",
                        lb.get("source_detail") or "",
                    )
                    for i, lb in enumerate(labels)
                ],
            )
        return new_rev

    def evaluations_using_label_set(self, label_set_id: str) -> list[dict[str, Any]]:
        """Các đánh giá đã lưu có dùng bộ nhãn này (để cảnh báo trước khi ghi đè)."""
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT id, created_at, label_set_revision
                     FROM evaluations WHERE label_set_id = ?
                    ORDER BY created_at DESC""",
                (label_set_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_label_set(self, label_set_id: str) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute("DELETE FROM labels WHERE label_set_id = ?", (label_set_id,))
            conn.execute("DELETE FROM label_sets WHERE id = ?", (label_set_id,))

    def insert_evaluation(self, row: dict[str, Any]) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute(
                """INSERT INTO evaluations
                   (id, created_at, dataset_id, label_set_id, label_set_revision,
                    protocol_json, protocol_hash,
                    baseline_run_id, run_ids_json, result_json, duration_ms, note_vi)
                   VALUES (:id,:created_at,:dataset_id,:label_set_id,:label_set_revision,
                           :protocol_json,:protocol_hash,
                           :baseline_run_id,:run_ids_json,:result_json,:duration_ms,:note_vi)""",
                row,
            )

    def list_evaluations(self, dataset_id: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
        sql = ("SELECT id, created_at, dataset_id, label_set_id, label_set_revision, "
               "protocol_hash, baseline_run_id, run_ids_json, duration_ms, note_vi "
               "FROM evaluations")
        args: list[Any] = []
        if dataset_id:
            sql += " WHERE dataset_id = ?"
            args.append(dataset_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
        with self.connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["run_ids"] = json.loads(d.pop("run_ids_json") or "[]")
            out.append(d)
        return out

    def get_evaluation(self, eval_id: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            r = conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["protocol"] = json.loads(d.pop("protocol_json") or "{}")
        d["result"] = json.loads(d.pop("result_json") or "{}")
        d["run_ids"] = json.loads(d.pop("run_ids_json") or "[]")
        return d

    def delete_evaluation(self, eval_id: str) -> None:
        with _LOCK, self.connect() as conn:
            conn.execute("DELETE FROM evaluations WHERE id = ?", (eval_id,))


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
