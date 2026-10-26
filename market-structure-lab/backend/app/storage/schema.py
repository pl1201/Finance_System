"""Lược đồ SQLite và migration thêm cột cho DB tạo từ phiên bản trước."""
from __future__ import annotations

import sqlite3

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


def migrate(conn: sqlite3.Connection) -> None:
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
