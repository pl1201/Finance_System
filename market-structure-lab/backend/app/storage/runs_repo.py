"""Repo: Lần chạy và sự kiện của nó. Mixin của ``Database`` — dùng ``self.connect()``."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable, Optional

from backend.app.storage.base import DB_LOCK


class RunRepo:
    def insert_run(self, run: dict[str, Any], events: Iterable[dict[str, Any]]) -> None:
        with DB_LOCK, self.connect() as conn:
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
        with DB_LOCK, self.connect() as conn:
            conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))


def _run_row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["params"] = json.loads(d.pop("params_json") or "{}")
    d["stats"] = json.loads(d.pop("stats_json") or "{}")
    d["is_synthetic"] = bool(d.get("is_synthetic") or 0)
    return d
