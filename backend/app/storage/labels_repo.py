"""Repo: Bộ nhãn tham chiếu và nhãn. Mixin của ``Database`` — dùng ``self.connect()``."""
from __future__ import annotations

from typing import Any, Optional

from backend.app.storage.base import DB_LOCK


class LabelRepo:
    def insert_label_set(self, meta: dict[str, Any], labels: list[dict[str, Any]]) -> None:
        with DB_LOCK, self.connect() as conn:
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
        with DB_LOCK, self.connect() as conn:
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
        with DB_LOCK, self.connect() as conn:
            conn.execute("DELETE FROM labels WHERE label_set_id = ?", (label_set_id,))
            conn.execute("DELETE FROM label_sets WHERE id = ?", (label_set_id,))
