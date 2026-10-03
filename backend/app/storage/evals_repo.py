"""Repo: Đánh giá đã lưu. Mixin của ``Database`` — dùng ``self.connect()``."""
from __future__ import annotations

import json
from typing import Any, Optional

from backend.app.storage.base import DB_LOCK


class EvaluationRepo:
    def insert_evaluation(self, row: dict[str, Any]) -> None:
        with DB_LOCK, self.connect() as conn:
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
        with DB_LOCK, self.connect() as conn:
            conn.execute("DELETE FROM evaluations WHERE id = ?", (eval_id,))
