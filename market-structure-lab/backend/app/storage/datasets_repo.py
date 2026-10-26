"""Repo: Dataset và nến. Mixin của ``Database`` — dùng ``self.connect()``."""
from __future__ import annotations

import json
import sqlite3
from datetime import timezone
from typing import Any, Optional

from backend.app.storage.base import DB_LOCK


class DatasetRepo:
    def insert_dataset(self, meta: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        with DB_LOCK, self.connect() as conn:
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
        with DB_LOCK, self.connect() as conn:
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


def _dataset_row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["quality"] = json.loads(d.pop("quality_json") or "{}")
    d["mapping"] = json.loads(d.pop("mapping_json") or "{}")
    d["is_synthetic"] = bool(d["is_synthetic"])
    return d
