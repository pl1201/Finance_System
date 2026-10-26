"""Hồi quy thuật toán trên các run đã lưu (AGENTS.md §7.3) — CHỈ ĐỌC database.

Ba chế độ:

* mặc định — chạy lại mọi run đã lưu với đúng dataset/khoảng/tham số và so
  ``event_id``, giá, ``confirmed_bar_index``, ``reason_code`` với sự kiện trong DB.
  Run lưu ở phiên bản thuật toán khác phiên bản hiện tại được báo riêng (khác là bình thường).
* ``--snapshot FILE`` — ghi «dấu vân tay» đầy đủ của mỗi cấu hình (sự kiện, timeline,
  thống kê trừ thời gian tính, pending_state, manifest_info, warm-up, trạng thái dữ liệu,
  lỗi nếu có) cho run đã lưu + ma trận thuật toán × dataset mặc định.
* ``--compare FILE`` — tính lại như ``--snapshot`` và so với file đã ghi; dùng khi refactor
  (yêu cầu: khớp tuyệt đối).

Chỉ dùng ``core`` và ``sqlite3`` — không phụ thuộc backend, nên dùng được cả khi tách backend.

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe scripts\\regression_saved_runs.py
    .\\.venv\\Scripts\\python.exe scripts\\regression_saved_runs.py --snapshot truoc.json
    .\\.venv\\Scripts\\python.exe scripts\\regression_saved_runs.py --compare truoc.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from typing import Any, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core.engine import run_algorithm  # noqa: E402
from core.registry import get_algorithm_class, list_algorithms  # noqa: E402
from core.types import build_bars  # noqa: E402

#: Dataset cho ma trận mặc định (bỏ qua nếu DB không có).
MATRIX_DATASETS = (
    "ds_db1583cd4dde",  # XAUUSD M15 2024 (giờ đã sửa)
    "ds_933fa5ec67e2",  # XAUUSD M5 2024
    "ds_771a79d4d604",  # XAUUSD H1 2024
    "ds_56a66d04bab9",  # [MÔ PHỎNG] XAUUSD M15
    "ds_e5d08565689b",  # [MÔ PHỎNG] XAUUSD H1
)

_TIMING_KEYS = ("thoi_gian_tinh_toan_ms", "toc_do_nen_tren_giay", "duration_ms")


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _strip_timing(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _strip_timing(v) for k, v in x.items() if k not in _TIMING_KEYS}
    if isinstance(x, list):
        return [_strip_timing(v) for v in x]
    return x


def _digest(obj: Any) -> str:
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]


class BarCache:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._ds: dict[str, Optional[dict[str, Any]]] = {}

    def dataset(self, ds_id: str) -> Optional[dict[str, Any]]:
        if ds_id not in self._ds:
            r = self.conn.execute("SELECT * FROM datasets WHERE id = ?", (ds_id,)).fetchone()
            self._ds[ds_id] = dict(r) if r else None
        return self._ds[ds_id]

    def bars(self, ds_id: str, start: Optional[str], end: Optional[str]):
        ds = self.dataset(ds_id)
        sql = "SELECT bar_time, open, high, low, close, volume FROM bars WHERE dataset_id = ?"
        args: list[Any] = [ds_id]
        if start:
            sql += " AND bar_time >= ?"
            args.append(start)
        if end:
            sql += " AND bar_time <= ?"
            args.append(end)
        sql += " ORDER BY idx"
        rows = [
            {"bar_time": datetime.fromisoformat(r["bar_time"]), "open": r["open"], "high": r["high"],
             "low": r["low"], "close": r["close"], "volume": r["volume"]}
            for r in self.conn.execute(sql, args)
        ]
        return ds, build_bars(rows, ds["timeframe"], ds["timestamp_convention"])


def run_config(cache: BarCache, ds_id: str, algorithm: str, params: dict[str, Any],
               start: Optional[str], end: Optional[str]) -> dict[str, Any]:
    """Chạy một cấu hình; trả kết quả đầy đủ hoặc lỗi (lỗi cũng là một phần của hành vi)."""
    ds = cache.dataset(ds_id)
    if ds is None:
        return {"skip": "dataset không có trong DB"}
    try:
        cls = get_algorithm_class(algorithm)
        norm = cls.validate_params(params)
        cls.check_dataset(ds["timeframe"], norm)
        info = cls.manifest_info(norm)
        algo = cls(**norm)
        _, bars = cache.bars(ds_id, start, end)
        res = run_algorithm(bars, algo)
    except (KeyError, ValueError) as exc:
        return {"error": "%s: %s" % (type(exc).__name__, exc)}
    return {
        "algorithm_version": algo.version,
        "params": norm,
        "events": [e.to_dict() for e in res.events],
        "timeline": res.timeline,
        "stats": _strip_timing(res.stats),
        "pending_state": algo.pending_state(),
        "manifest_info": info,
        "warmup_bars": res.warmup_bars,
        "bars_processed": res.bars_processed,
        "data_status": res.data_status,
        "data_status_message_vi": res.data_status_message_vi,
    }


def fingerprint(out: dict[str, Any]) -> dict[str, Any]:
    if "events" not in out:
        return out
    parts = {k: _digest(v) for k, v in out.items() if k not in ("algorithm_version",)}
    parts["algorithm_version"] = out["algorithm_version"]
    parts["n_events"] = len(out["events"])
    return parts


def configs(conn: sqlite3.Connection, with_matrix: bool) -> list[dict[str, Any]]:
    out = []
    for r in conn.execute("SELECT * FROM runs ORDER BY created_at, run_id"):
        out.append({
            "key": "run:" + r["run_id"], "run_id": r["run_id"], "dataset_id": r["dataset_id"],
            "algorithm": r["algorithm"], "saved_version": r["algorithm_version"],
            "params": json.loads(r["params_json"] or "{}"),
            "start": r["range_start"], "end": r["range_end"],
        })
    if with_matrix:
        for a in list_algorithms():
            for ds_id in MATRIX_DATASETS:
                out.append({"key": "matrix:%s@%s" % (a["name"], ds_id), "dataset_id": ds_id,
                            "algorithm": a["name"], "params": {}, "start": None, "end": None})
    return out


def compare_with_db(conn: sqlite3.Connection, cfg: dict[str, Any], out: dict[str, Any]) -> str:
    if "events" not in out:
        return "LỖI " + out.get("error", out.get("skip", ""))
    rows = conn.execute(
        "SELECT event_id, price, confirmed_bar_index, reason_code FROM events WHERE run_id = ? ORDER BY seq",
        (cfg["run_id"],),
    ).fetchall()
    saved = [(r["event_id"], round(r["price"], 9), r["confirmed_bar_index"], r["reason_code"]) for r in rows]
    fresh = [(e["event_id"], round(e["price"], 9), e["confirmed_bar_index"], e["reason_code"]) for e in out["events"]]
    if saved == fresh:
        return "khớp (%d sự kiện)" % len(saved)
    diff = next((i for i, (a, b) in enumerate(zip(saved, fresh)) if a != b), min(len(saved), len(fresh)))
    return "KHÁC: DB %d vs chạy lại %d sự kiện, lệch từ sự kiện #%d" % (len(saved), len(fresh), diff)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--snapshot", metavar="FILE")
    g.add_argument("--compare", metavar="FILE")
    ap.add_argument("--no-matrix", action="store_true", help="chỉ run đã lưu, bỏ ma trận mặc định")
    a = ap.parse_args()

    conn = _connect(a.db)
    cache = BarCache(conn)
    t0 = time.time()
    cfgs = configs(conn, with_matrix=bool(a.snapshot or a.compare) and not a.no_matrix)

    if not (a.snapshot or a.compare):
        bad = 0
        for cfg in cfgs:
            out = run_config(cache, cfg["dataset_id"], cfg["algorithm"], cfg["params"], cfg["start"], cfg["end"])
            msg = compare_with_db(conn, cfg, out)
            ver = out.get("algorithm_version")
            note = "" if ver in (None, cfg["saved_version"]) else " (lưu ở v%s, hiện tại v%s)" % (cfg["saved_version"], ver)
            if not msg.startswith("khớp") and not note:
                bad += 1
            print("%-18s %-20s %s%s" % (cfg["run_id"], cfg["algorithm"], msg, note))
        print("\n%d run, %d khác ở cùng phiên bản, %.1f s" % (len(cfgs), bad, time.time() - t0))
        return 1 if bad else 0

    result = {}
    for cfg in cfgs:
        out = run_config(cache, cfg["dataset_id"], cfg["algorithm"], cfg["params"], cfg["start"], cfg["end"])
        result[cfg["key"]] = fingerprint(out)
    if a.snapshot:
        with open(a.snapshot, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
        print("Đã ghi %d cấu hình vào %s (%.1f s)" % (len(result), a.snapshot, time.time() - t0))
        return 0
    with open(a.compare, encoding="utf-8") as f:
        before = json.load(f)
    diffs = []
    for k in sorted(set(before) | set(result)):
        if before.get(k) != result.get(k):
            b, n = before.get(k) or {}, result.get(k) or {}
            fields = sorted(x for x in set(b) | set(n) if b.get(x) != n.get(x))
            diffs.append("%s: khác ở %s" % (k, ", ".join(fields) or "(thiếu)"))
    for d in diffs:
        print(d)
    print("%d cấu hình, %d khác (%.1f s)" % (len(result), len(diffs), time.time() - t0))
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())
