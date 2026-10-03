"""Tầng nghiệp vụ: nhập dữ liệu, chạy thuật toán, replay, so sánh, xuất kết quả.

Tầng này nối lõi thuật toán (``core/``) với lớp lưu trữ, và không chứa
bất kỳ chi tiết HTTP nào.
"""
from __future__ import annotations

import csv
import io
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app import config
from backend.app.storage.db import Database, utcnow_iso
from core.data import synthetic
from core.data.loader import (
    CsvImportError,
    load_csv,
    normalize_timezone_label,
    preview_csv,
    rows_checksum,
)
from core.data.mt5_source import Mt5SourceError, fetch_closed_rates, mt5_available
from core.data.resample import RESAMPLE_TARGETS, ResampleError, resample_ohlc
from core.data.validate import infer_timeframe, validate_and_clean
from core.engine import ReplaySession, run_algorithm
from core.registry import create_algorithm, get_algorithm_class, list_algorithms
from core.types import TIMESTAMP_CONVENTIONS, build_bars

db = Database(config.DB_PATH)


class ServiceError(Exception):
    """Lỗi nghiệp vụ có thông điệp hiển thị được cho người dùng."""


def _display_path(path: str) -> str:
    """Đường dẫn tương đối so với gốc dự án, giữ nguyên tuyệt đối nếu khác ổ đĩa."""
    try:
        return os.path.relpath(path, config.PROJECT_ROOT)
    except ValueError:
        # Trên Windows, relpath báo lỗi khi hai đường dẫn nằm trên hai ổ khác nhau
        # (xảy ra khi MSL_DATA_DIR trỏ sang ổ khác, ví dụ thư mục tạm khi chạy test).
        return os.path.abspath(path)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


def preview_upload(text: str) -> dict[str, Any]:
    try:
        pv = preview_csv(text)
    except CsvImportError as exc:
        raise ServiceError(str(exc)) from exc
    out = pv.to_dict()
    # Gợi ý timeframe từ cột thời gian, nếu ánh xạ đủ để thử nạp.
    out["suggested_timeframe"] = None
    try:
        probe = load_csv(text, source_timezone="UTC")
        out["suggested_timeframe"] = infer_timeframe(probe.rows[:500])
        out["parsed_rows_probe"] = len(probe.rows)
    except CsvImportError:
        pass
    return out


def import_dataset(
    *,
    text: str,
    filename: str,
    name: str,
    symbol: str,
    timeframe: str,
    source: str,
    source_timezone: str,
    timestamp_convention: str,
    price_type: str = "unspecified",
    mapping: Optional[dict[str, Optional[str]]] = None,
    notes: str = "",
    is_synthetic: bool = False,
) -> dict[str, Any]:
    """Nhập một dataset từ nội dung CSV. Lưu file gốc bất biến vào data/raw."""
    if timestamp_convention not in TIMESTAMP_CONVENTIONS:
        raise ServiceError(
            "Phải khai báo timestamp là mốc MỞ nến ('open') hay ĐÓNG nến ('close'). "
            "Công cụ không tự đoán."
        )
    if not (source_timezone or "").strip():
        raise ServiceError(
            "Phải khai báo múi giờ nguồn (ví dụ UTC, UTC+2). Công cụ không tự đoán."
        )
    if not (symbol or "").strip():
        raise ServiceError("Phải nhập symbol.")

    try:
        tz_label = normalize_timezone_label(source_timezone)
        loaded = load_csv(text, source_timezone=source_timezone, mapping=mapping)
    except CsvImportError as exc:
        raise ServiceError(str(exc)) from exc

    detected_tf = infer_timeframe(loaded.rows)
    tf = (timeframe or detected_tf or "").upper()
    if not tf:
        raise ServiceError(
            "Không xác định được timeframe. Hãy chọn timeframe thủ công."
        )

    return _persist_clean_dataset(
        loaded.rows,
        name=name,
        symbol=symbol,
        timeframe=tf,
        source=source,
        source_timezone=tz_label,
        timestamp_convention=timestamp_convention,
        price_type=price_type,
        notes=notes,
        is_synthetic=is_synthetic,
        filename=filename,
        raw_text=text,
        mapping=loaded.mapping_used,
        extra_quality={
            "detected_timeframe": detected_tf,
            "skipped_rows": loaded.skipped_rows,
            "delimiter": repr(loaded.delimiter),
        },
        file_checksum=loaded.checksum_sha256,
    )


def _rows_to_csv_text(rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["time", "open", "high", "low", "close", "volume"])
    for r in rows:
        bt = r["bar_time"]
        if hasattr(bt, "isoformat"):
            ts = bt.astimezone(timezone.utc).isoformat()
        else:
            ts = str(bt)
        w.writerow([ts, r["open"], r["high"], r["low"], r["close"], r.get("volume") or 0])
    return buf.getvalue()


def _persist_clean_dataset(
    rows: list[dict[str, Any]],
    *,
    name: str,
    symbol: str,
    timeframe: str,
    source: str,
    source_timezone: str,
    timestamp_convention: str,
    price_type: str = "unspecified",
    notes: str = "",
    is_synthetic: bool = False,
    filename: str = "data.csv",
    raw_text: Optional[str] = None,
    mapping: Optional[dict[str, Any]] = None,
    extra_quality: Optional[dict[str, Any]] = None,
    file_checksum: Optional[str] = None,
) -> dict[str, Any]:
    tf = (timeframe or "").upper().strip()
    clean_rows, report = validate_and_clean(rows, tf)
    if not clean_rows:
        raise ServiceError(
            "Dữ liệu không dùng được: %s"
            % "; ".join(i.message_vi for i in report.issues)
        )
    if len(clean_rows) > config.MAX_BARS_PER_DATASET:
        raise ServiceError(
            "Dataset quá lớn (%d nến, giới hạn %d)."
            % (len(clean_rows), config.MAX_BARS_PER_DATASET)
        )

    content_checksum = rows_checksum(clean_rows)
    existing = db.dataset_exists_by_checksum(content_checksum)
    if existing:
        raise ServiceError(
            "Dataset có nội dung trùng với dataset đã có (id=%s). "
            "Xoá dataset cũ hoặc dùng lại nó." % existing
        )

    dataset_id = "ds_" + uuid.uuid4().hex[:12]
    safe_name = "".join(c for c in (filename or "data.csv") if c.isalnum() or c in "._-")
    raw_path = os.path.join(config.RAW_DIR, "%s__%s" % (dataset_id, safe_name or "data.csv"))
    text_out = raw_text if raw_text is not None else _rows_to_csv_text(clean_rows)
    with open(raw_path, "w", encoding="utf-8", newline="") as f:
        f.write(text_out)

    quality = report.to_dict()
    if extra_quality:
        quality.update(extra_quality)

    meta = {
        "id": dataset_id,
        "name": (name or "").strip() or ("%s %s" % (symbol.upper(), tf)),
        "symbol": symbol.upper().strip(),
        "timeframe": tf,
        "source": (source or "").strip() or "không khai báo",
        "price_type": price_type or "unspecified",
        "source_timezone": source_timezone,
        "timestamp_convention": timestamp_convention,
        "row_count": len(clean_rows),
        "start_time": report.start_time.isoformat() if report.start_time else None,
        "end_time": report.end_time.isoformat() if report.end_time else None,
        "checksum_sha256": content_checksum,
        "file_checksum_sha256": file_checksum or "",
        "raw_path": _display_path(raw_path),
        "is_synthetic": 1 if is_synthetic else 0,
        "quality_json": json.dumps(quality, ensure_ascii=False),
        "mapping_json": json.dumps(mapping or {}, ensure_ascii=False),
        "notes": notes or "",
        "created_at": utcnow_iso(),
    }
    db.insert_dataset(meta, clean_rows)
    return db.get_dataset(dataset_id)  # type: ignore[return-value]


def import_from_rows(
    *,
    rows: list[dict[str, Any]],
    name: str,
    symbol: str,
    timeframe: str,
    source: str,
    source_timezone: str,
    timestamp_convention: str,
    price_type: str = "unspecified",
    notes: str = "",
    is_synthetic: bool = False,
    extra_quality: Optional[dict[str, Any]] = None,
    filename: str = "rows.csv",
) -> dict[str, Any]:
    """Nhập dataset từ list dict đã có bar_time UTC — dùng cho MT5 và resample."""
    if timestamp_convention not in TIMESTAMP_CONVENTIONS:
        raise ServiceError(
            "Phải khai báo timestamp là mốc MỞ nến ('open') hay ĐÓNG nến ('close'). "
            "Công cụ không tự đoán."
        )
    if not (source_timezone or "").strip():
        raise ServiceError(
            "Phải khai báo múi giờ nguồn (ví dụ UTC, UTC+2). Công cụ không tự đoán."
        )
    if not (symbol or "").strip():
        raise ServiceError("Phải nhập symbol.")
    if not (timeframe or "").strip():
        raise ServiceError("Phải chọn timeframe.")
    try:
        tz_label = normalize_timezone_label(source_timezone)
    except CsvImportError as exc:
        raise ServiceError(str(exc)) from exc
    return _persist_clean_dataset(
        rows,
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        source_timezone=tz_label,
        timestamp_convention=timestamp_convention,
        price_type=price_type,
        notes=notes,
        is_synthetic=is_synthetic,
        filename=filename,
        extra_quality=extra_quality,
    )


def resample_dataset(
    dataset_id: str,
    target_timeframe: str,
    gap_policy: str = "drop_incomplete",
) -> dict[str, Any]:
    ds = get_dataset_or_error(dataset_id)
    if ds["timestamp_convention"] != "open":
        raise ServiceError(
            "Tổng hợp nến yêu cầu dataset nguồn khai báo timestamp là mốc MỞ nến. "
            "Dataset này đang là %r — hãy nhập lại hoặc tổng hợp từ M1 đúng mốc mở."
            % ds["timestamp_convention"]
        )
    raw = db.get_bars(dataset_id)
    rows = [
        {
            "bar_time": datetime.fromisoformat(r["bar_time"]),
            "open": r["open"], "high": r["high"], "low": r["low"],
            "close": r["close"], "volume": r["volume"],
        }
        for r in raw
    ]
    try:
        out, report = resample_ohlc(
            rows, ds["timeframe"], target_timeframe, gap_policy=gap_policy
        )
    except ResampleError as exc:
        raise ServiceError(str(exc)) from exc
    if not out:
        raise ServiceError("Không tạo được nến đích (mọi bucket đều trống hoặc incomplete).")
    persist_rows = [
        {k: v for k, v in r.items() if k in ("bar_time", "open", "high", "low", "close", "volume")}
        for r in out
    ]
    syn_note = " [dataset nguồn là DỮ LIỆU MÔ PHỎNG]" if ds.get("is_synthetic") else ""
    imported = import_from_rows(
        rows=persist_rows,
        name="%s %s (từ %s)" % (ds["symbol"], target_timeframe, ds["timeframe"]),
        symbol=ds["symbol"],
        timeframe=target_timeframe,
        source="Tổng hợp từ dataset %s (%s→%s, utc_epoch, %s)"
        % (dataset_id, ds["timeframe"], target_timeframe, gap_policy),
        source_timezone=ds["source_timezone"],
        timestamp_convention="open",
        price_type=ds.get("price_type") or "unspecified",
        notes=(ds.get("notes") or "") + syn_note,
        is_synthetic=bool(ds.get("is_synthetic")),
        extra_quality={"resample": report.to_dict(), "source_dataset_id": dataset_id},
        filename="resample_%s_%s.csv" % (ds["symbol"], target_timeframe),
    )
    return {"dataset": imported, "resample": report.to_dict()}


def import_from_mt5(
    *,
    symbol: str,
    timeframe: str,
    source_timezone: str,
    timestamp_convention: str,
    count: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    terminal_path: str = "",
    price_type: str = "unspecified",
    name: str = "",
    notes: str = "",
) -> dict[str, Any]:
    if not mt5_available():
        raise ServiceError(
            "Chưa cài gói MetaTrader5. Lõi lab vẫn chạy được. "
            "Muốn lấy lịch sử: pip install MetaTrader5 và mở sẵn terminal."
        )
    d0 = datetime.fromisoformat(date_from) if date_from else None
    d1 = datetime.fromisoformat(date_to) if date_to else None
    try:
        packed = fetch_closed_rates(
            symbol, timeframe,
            date_from=d0, date_to=d1, count=count,
            drop_forming=True,
            terminal_path=terminal_path or None,
        )
    except Mt5SourceError as exc:
        raise ServiceError(str(exc)) from exc
    if not packed["rows"]:
        raise ServiceError("MT5 không trả nến đóng nào.")
    return import_from_rows(
        rows=packed["rows"],
        name=name or ("%s %s (MT5)" % (symbol.upper(), timeframe)),
        symbol=symbol,
        timeframe=timeframe,
        source="MetaTrader5 copy_rates (đã loại nến đang hình thành)",
        source_timezone=source_timezone,
        timestamp_convention=timestamp_convention,
        price_type=price_type,
        notes=(notes or "") + " " + packed["note_vi"],
        extra_quality={
            "mt5": {
                "dropped_forming": packed["dropped_forming"],
                "note_vi": packed["note_vi"],
            }
        },
        filename="mt5_%s_%s.csv" % (symbol, timeframe),
    )


def seed_sample_datasets(force: bool = False) -> list[dict[str, Any]]:
    """Tạo các dataset MÔ PHỎNG đi kèm để mở app là thử được ngay."""
    specs = [
        synthetic.SyntheticSpec("XAUUSD", "H1", 1800, seed=20260920),
        synthetic.SyntheticSpec("XAUUSD", "M15", 2400, seed=20260921),
        synthetic.SyntheticSpec("XAUUSD", "M5", 2400, seed=20260922),
        synthetic.SyntheticSpec("EURUSD", "H1", 1800, seed=20260923),
    ]
    created: list[dict[str, Any]] = []
    for spec in specs:
        result = synthetic.generate(spec)
        text = synthetic.to_csv_text(result)
        filename = "MOPHONG_%s_%s_seed%d.csv" % (spec.symbol, spec.timeframe, spec.seed)
        # Ghi bản sao ra data/raw để tái tạo/kiểm tra bằng tay.
        try:
            out = import_dataset(
                text=text,
                filename=filename,
                name="[MÔ PHỎNG] %s %s" % (spec.symbol, spec.timeframe),
                symbol=spec.symbol,
                timeframe=spec.timeframe,
                source="Bộ sinh dữ liệu mô phỏng nội bộ (core/data/synthetic.py, seed=%d)"
                % spec.seed,
                source_timezone="UTC",
                timestamp_convention="open",
                price_type="midpoint mô phỏng",
                notes=(
                    "DỮ LIỆU MÔ PHỎNG — KHÔNG PHẢI DỮ LIỆU THỊ TRƯỜNG THẬT. "
                    "Sinh bằng random.Random(seed=%d). Tái tạo bằng lệnh: "
                    "python scripts/generate_synthetic.py --symbol %s --timeframe %s "
                    "--bars %d --seed %d" % (spec.seed, spec.symbol, spec.timeframe, spec.bars, spec.seed)
                ),
                is_synthetic=True,
            )
            created.append(out)
        except ServiceError as exc:
            if force:
                raise
            # Đã tồn tại (trùng checksum) — bỏ qua.
            created.append({"skipped": True, "reason": str(exc), "spec": filename})
    return created


def get_dataset_or_error(dataset_id: str) -> dict[str, Any]:
    ds = db.get_dataset(dataset_id)
    if not ds:
        raise ServiceError("Không tìm thấy dataset %r." % dataset_id)
    return ds


def load_bars(
    dataset_id: str,
    range_start: Optional[str] = None,
    range_end: Optional[str] = None,
):
    """Đọc nến của dataset trong khoảng thời gian và dựng đối tượng ``Bar``."""
    ds = get_dataset_or_error(dataset_id)
    raw = db.get_bars(dataset_id, range_start, range_end)
    if not raw:
        raise ServiceError(
            "Khoảng thời gian đã chọn không có nến nào trong dataset này."
        )
    rows = [
        {
            "bar_time": datetime.fromisoformat(r["bar_time"]),
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r["volume"],
        }
        for r in raw
    ]
    bars = build_bars(rows, ds["timeframe"], ds["timestamp_convention"])
    return ds, bars, [r["idx"] for r in raw]


# ---------------------------------------------------------------------------
# Chạy thuật toán
# ---------------------------------------------------------------------------


def execute_run(
    *,
    dataset_id: str,
    algorithm: str,
    params: dict[str, Any] | None,
    range_start: Optional[str] = None,
    range_end: Optional[str] = None,
    label: str = "",
    save: bool = True,
) -> dict[str, Any]:
    ds, bars, source_indices = load_bars(dataset_id, range_start, range_end)
    try:
        cls = get_algorithm_class(algorithm)
        norm_params = cls.validate_params(params)
        cls.check_dataset(ds["timeframe"], norm_params)
        algo = cls(**norm_params)
    except (KeyError, ValueError) as exc:
        raise ServiceError(str(exc)) from exc

    try:
        result = run_algorithm(bars, algo)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    run_id = "run_" + uuid.uuid4().hex[:12]
    events = [e.to_dict() for e in result.events]

    run_row = {
        "run_id": run_id,
        "label": label or "",
        "dataset_id": dataset_id,
        "dataset_checksum": ds["checksum_sha256"],
        "symbol": ds["symbol"],
        "timeframe": ds["timeframe"],
        "algorithm": algo.name,
        "algorithm_version": algo.version,
        "params_json": json.dumps(norm_params, ensure_ascii=False),
        "range_start": bars[0].bar_time.isoformat(),
        "range_end": bars[-1].bar_time.isoformat(),
        "range_start_index": source_indices[0],
        "range_end_index": source_indices[-1],
        "bars_processed": result.bars_processed,
        "warmup_bars": result.warmup_bars,
        "duration_ms": result.duration_ms,
        "data_status": result.data_status,
        "stats_json": json.dumps(result.stats, ensure_ascii=False),
        "created_at": utcnow_iso(),
    }
    if save:
        db.insert_run(run_row, events)

    payload = dict(run_row)
    payload.pop("params_json")
    payload.pop("stats_json")
    payload["params"] = norm_params
    payload["stats"] = result.stats
    payload["saved"] = save
    payload["dataset_name"] = ds["name"]
    payload["is_synthetic"] = ds["is_synthetic"]
    payload["data_status_message_vi"] = result.data_status_message_vi
    payload["events"] = events
    payload["timeline"] = result.timeline
    payload["pending_state"] = algo.pending_state()
    return payload


def bars_payload(dataset_id: str, range_start: Optional[str], range_end: Optional[str]):
    ds, bars, _ = load_bars(dataset_id, range_start, range_end)
    return {
        "dataset": ds,
        "bars": [
            {
                "index": b.index,
                "bar_time": b.bar_time.isoformat(),
                "close_time": b.close_time.isoformat(),
                "time": int(b.bar_time.timestamp()),
                "close_ts": int(b.close_time.timestamp()),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ],
    }


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


class ReplayStore:
    """Giữ các phiên replay đang mở trong bộ nhớ tiến trình."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(
        self,
        *,
        dataset_id: str,
        algorithm: str,
        params: dict[str, Any] | None,
        range_start: Optional[str],
        range_end: Optional[str],
    ) -> tuple[str, dict[str, Any]]:
        ds, bars, _ = load_bars(dataset_id, range_start, range_end)
        try:
            cls = get_algorithm_class(algorithm)
            norm = cls.validate_params(params)
            cls.check_dataset(ds["timeframe"], norm)
            algo = cls(**norm)
        except (KeyError, ValueError) as exc:
            raise ServiceError(str(exc)) from exc

        sid = "rp_" + uuid.uuid4().hex[:10]
        session = ReplaySession(bars, algo)
        with self._lock:
            if len(self._sessions) >= config.MAX_REPLAY_SESSIONS:
                oldest = min(self._sessions, key=lambda k: self._sessions[k]["created_at"])
                self._sessions.pop(oldest, None)
            self._sessions[sid] = {
                "session": session,
                "dataset": ds,
                "algorithm": algorithm,
                "algorithm_version": algo.version,
                "params": norm,
                "created_at": datetime.now(timezone.utc).timestamp(),
                "bars": bars,
            }
        return sid, self._meta(sid)

    def _entry(self, sid: str) -> dict[str, Any]:
        entry = self._sessions.get(sid)
        if not entry:
            raise ServiceError(
                "Phiên replay %r không còn tồn tại (có thể do khởi động lại "
                "backend). Hãy tạo phiên mới." % sid
            )
        return entry

    def _meta(self, sid: str, since: Optional[int] = None) -> dict[str, Any]:
        e = self._entry(sid)
        snap = e["session"].snapshot(since)
        snap["session_id"] = sid
        snap["dataset"] = e["dataset"]
        snap["algorithm"] = e["algorithm"]
        snap["algorithm_version"] = e["algorithm_version"]
        snap["params"] = e["params"]
        return snap

    def snapshot(self, sid: str) -> dict[str, Any]:
        return self._meta(sid)

    def step(self, sid: str, n: int = 1, since: Optional[int] = None) -> dict[str, Any]:
        try:
            self._entry(sid)["session"].step_forward(n)
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return self._meta(sid, since)

    def next_event(self, sid: str, since: Optional[int] = None) -> dict[str, Any]:
        try:
            self._entry(sid)["session"].step_until_event()
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return self._meta(sid, since)

    def back(self, sid: str, n: int = 1, since: Optional[int] = None) -> dict[str, Any]:
        try:
            self._entry(sid)["session"].step_back(n)
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return self._meta(sid, since)

    def seek(self, sid: str, index: int, since: Optional[int] = None) -> dict[str, Any]:
        try:
            self._entry(sid)["session"].seek(index)
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return self._meta(sid, since)

    def reset(self, sid: str) -> dict[str, Any]:
        self._entry(sid)["session"].reset()
        return self._meta(sid)

    def close(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)

    def bars(self, sid: str) -> list[dict[str, Any]]:
        e = self._entry(sid)
        return [
            {
                "index": b.index,
                "bar_time": b.bar_time.isoformat(),
                "close_time": b.close_time.isoformat(),
                "time": int(b.bar_time.timestamp()),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in e["bars"]
        ]


replay_store = ReplayStore()


# ---------------------------------------------------------------------------
# So sánh và xuất
# ---------------------------------------------------------------------------


def compare_runs(run_id_a: str, run_id_b: str) -> dict[str, Any]:
    a = db.get_run(run_id_a)
    b = db.get_run(run_id_b)
    if not a or not b:
        raise ServiceError("Không tìm thấy một trong hai lần chạy cần so sánh.")

    warnings: list[str] = []
    if a["dataset_id"] != b["dataset_id"]:
        warnings.append(
            "Hai lần chạy dùng DATASET KHÁC NHAU. Khác biệt kết quả có thể do dữ liệu, "
            "không chỉ do tham số."
        )
    elif a["dataset_checksum"] != b["dataset_checksum"]:
        warnings.append("Dataset trùng id nhưng khác checksum nội dung.")
    if (a["range_start"], a["range_end"]) != (b["range_start"], b["range_end"]):
        warnings.append(
            "Hai lần chạy dùng KHOẢNG THỜI GIAN KHÁC NHAU (%s..%s so với %s..%s)."
            % (a["range_start"], a["range_end"], b["range_start"], b["range_end"])
        )
    if a["algorithm_version"] != b["algorithm_version"]:
        warnings.append(
            "Khác phiên bản thuật toán: %s so với %s."
            % (a["algorithm_version"], b["algorithm_version"])
        )

    ev_a = db.get_events(run_id_a)
    ev_b = db.get_events(run_id_b)
    key = lambda e: (e["structure_type"], e["event_bar_index"], e["confirmed_bar_index"])
    set_a = {key(e) for e in ev_a}
    set_b = {key(e) for e in ev_b}
    only_a = set_a - set_b
    only_b = set_b - set_a
    common = set_a & set_b

    types = sorted(
        set(a["stats"].get("so_su_kien_theo_loai", {}))
        | set(b["stats"].get("so_su_kien_theo_loai", {}))
    )
    by_type = [
        {
            "structure_type": t,
            "a": a["stats"].get("so_su_kien_theo_loai", {}).get(t, 0),
            "b": b["stats"].get("so_su_kien_theo_loai", {}).get(t, 0),
        }
        for t in types
    ]

    return {
        "run_a": a,
        "run_b": b,
        "canh_bao": warnings,
        "so_sanh_theo_loai": by_type,
        "so_su_kien_chung": len(common),
        "chi_co_o_a": len(only_a),
        "chi_co_o_b": len(only_b),
        "mau_chi_co_o_a": [
            {"structure_type": t, "event_bar_index": i, "confirmed_bar_index": c}
            for (t, i, c) in sorted(only_a, key=lambda x: x[1])[:25]
        ],
        "mau_chi_co_o_b": [
            {"structure_type": t, "event_bar_index": i, "confirmed_bar_index": c}
            for (t, i, c) in sorted(only_b, key=lambda x: x[1])[:25]
        ],
        "do_tre_a": a["stats"].get("do_tre_xac_nhan_chung_nen"),
        "do_tre_b": b["stats"].get("do_tre_xac_nhan_chung_nen"),
        "thoi_gian_tinh_toan_ms": {
            "a": a["duration_ms"],
            "b": b["duration_ms"],
        },
        "ghi_chu_vi": (
            "So sánh chỉ dựa trên sự kiện cấu trúc và hiệu năng. Không kết luận "
            "cấu hình nào 'đúng hơn' trừ khi đối chiếu với bộ nhãn tham chiếu "
            "do người gán."
        ),
    }


EXPORT_COLUMNS = [
    "run_id", "symbol", "timeframe", "seq", "event_id", "structure_type",
    "price", "event_bar_index", "event_time", "event_close_time",
    "confirmed_bar_index", "confirmed_at", "confirmation_lag_bars",
    "algorithm", "algorithm_version", "reason_code", "direction",
    "reference_event_id", "details_json",
]


def export_events_csv(run_id: str) -> tuple[str, str]:
    """Trả về (tên file, nội dung CSV) cho bảng sự kiện của một lần chạy."""
    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    events = db.get_events(run_id)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(EXPORT_COLUMNS)
    for e in events:
        w.writerow(
            [
                run_id, run["symbol"], run["timeframe"], e["seq"], e["event_id"],
                e["structure_type"], e["price"], e["event_bar_index"], e["event_time"],
                e["event_close_time"], e["confirmed_bar_index"], e["confirmed_at"],
                e["confirmation_lag_bars"], e["algorithm"], e["algorithm_version"],
                e["reason_code"], e["direction"] or "", e["reference_event_id"] or "",
                json.dumps(e["details"], ensure_ascii=False),
            ]
        )
    filename = "su_kien_%s_%s_%s.csv" % (run["symbol"], run["timeframe"], run_id)
    return filename, buf.getvalue()


def c2_cisd_run_metrics(run_id: str, horizon_bars: int = 16) -> dict[str, Any]:
    """Vòng đời setup + MFE/MAE đối chứng C2-only vs C2+CISD cho một run đã lưu.

    MFE/MAE dùng nến SAU thời điểm biết — chỉ phục vụ đánh giá, không đưa ngược
    vào detector. Chạy trên đúng khoảng nến của run (cùng snapshot dataset).
    """
    from core.eval.c2_cisd_metrics import excursion_metrics, lifecycle_metrics

    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    if run["algorithm"] != "c2_cisd_research":
        raise ServiceError("Chỉ số này chỉ dành cho run c2_cisd_research.")
    if not 1 <= int(horizon_bars) <= 500:
        raise ServiceError("Horizon phải trong 1–500 nến.")
    ds = get_dataset_or_error(run["dataset_id"])
    if ds["checksum_sha256"] != run["dataset_checksum"]:
        raise ServiceError("Dataset đã đổi nội dung so với lúc chạy — không tính MFE/MAE.")
    events = db.get_events(run_id)
    _, bars, _ = load_bars(run["dataset_id"], run["range_start"], run["range_end"])
    return {
        "run_id": run_id,
        "algorithm_version": run["algorithm_version"],
        "dataset_checksum": run["dataset_checksum"],
        "vong_doi": lifecycle_metrics(events),
        "mfe_mae": excursion_metrics(events, bars, int(horizon_bars)),
    }


def run_manifest(run_id: str) -> dict[str, Any]:
    """Hồ sơ đầy đủ của một lần chạy, đủ để chạy lại."""
    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    ds = db.get_dataset(run["dataset_id"])
    try:
        info = get_algorithm_class(run["algorithm"]).manifest_info(run.get("params") or {})
    except KeyError:
        info = {}
    return {
        "run": run,
        "dataset": ds,
        "algorithm_info": info,
        "ghi_chu_vi": (
            "Chạy lại bằng cùng dataset_checksum, algorithm_version và params "
            "sẽ cho cùng bộ sự kiện."
        ),
    }


def algorithms() -> list[dict[str, Any]]:
    return list_algorithms()


def save_label_set(
    *,
    dataset_id: str,
    annotator: str,
    version: str,
    rubric_vi: str,
    labels: list[dict[str, Any]],
) -> dict[str, Any]:
    get_dataset_or_error(dataset_id)
    if not (annotator or "").strip():
        raise ServiceError("Phải ghi tên người gán nhãn.")
    cleaned, warnings = _clean_labels(labels, dataset_id)
    sid = "lab_" + uuid.uuid4().hex[:12]
    db.insert_label_set(
        {
            "id": sid,
            "dataset_id": dataset_id,
            "version": (version or "1").strip(),
            "annotator": annotator.strip(),
            "rubric_vi": rubric_vi or "",
            "created_at": utcnow_iso(),
        },
        cleaned,
    )
    out = db.get_label_set(sid)
    assert out is not None
    out["warnings"] = warnings
    return out


#: Nguồn gốc của một nhãn tham chiếu.
#:
#: * ``human`` — người tự click gán.
#: * ``auto_accepted`` — thuật toán đề xuất, người đã xem và chấp nhận nguyên.
#: * ``auto_edited`` — thuật toán đề xuất, người chấp nhận rồi sửa (dời nến,
#:   đổi loại hoặc sửa giá).
#:
#: Không có nguồn "auto chưa duyệt": đề xuất chưa được người chấp nhận không
#: bao giờ được lưu vào kho nhãn.
LABEL_SOURCES = ("human", "auto_accepted", "auto_edited")


def _clean_labels(
    labels: list[dict[str, Any]], dataset_id: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """Kiểm tra và chuẩn hoá danh sách nhãn theo đúng dataset.

    ``bar_index`` chỉ có nghĩa trong dataset của nó, nên nhãn nằm ngoài phạm vi
    nến của dataset bị từ chối thay vì lưu âm thầm.
    """
    from core.labels import LABEL_TYPES, ReferenceLabel

    ds = get_dataset_or_error(dataset_id)
    n_bars = int(ds["row_count"])
    cleaned: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[tuple[str, int]] = set()

    for i, lb in enumerate(labels):
        st = (lb.get("structure_type") or "").strip()
        if st not in LABEL_TYPES:
            raise ServiceError(
                "Dòng %d: loại nhãn không hỗ trợ %r. Hỗ trợ: %s"
                % (i + 1, st, ", ".join(LABEL_TYPES))
            )
        try:
            bar_index = int(lb["bar_index"])
            price = float(lb["price"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ServiceError(
                "Dòng %d: bar_index/price không hợp lệ (%s)." % (i + 1, exc)
            ) from exc
        if bar_index < 0 or bar_index >= n_bars:
            raise ServiceError(
                "Dòng %d: bar_index %d nằm ngoài dataset %s %s (0..%d). "
                "Nhãn của dataset khác không dùng lại được."
                % (i + 1, bar_index, ds["symbol"], ds["timeframe"], n_bars - 1)
            )
        key = (st, bar_index)
        if key in seen:
            warnings.append(
                "Bỏ nhãn trùng: %s tại nến %d (chỉ giữ bản đầu tiên)." % (st, bar_index)
            )
            continue
        seen.add(key)
        ReferenceLabel(st, bar_index, price)
        source = (lb.get("source") or "human").strip()
        if source not in LABEL_SOURCES:
            raise ServiceError(
                "Dòng %d: nguồn nhãn %r không hợp lệ. Hỗ trợ: %s"
                % (i + 1, source, ", ".join(LABEL_SOURCES))
            )
        source_algorithm = (lb.get("source_algorithm") or "").strip()
        if source != "human" and not source_algorithm:
            raise ServiceError(
                "Dòng %d: nhãn nguồn %r phải ghi thuật toán đã đề xuất nó "
                "(source_algorithm)." % (i + 1, source)
            )
        cleaned.append({
            "structure_type": st,
            "bar_index": bar_index,
            "price": price,
            "notes": (lb.get("notes") or "").strip(),
            "source": source,
            "source_algorithm": source_algorithm if source != "human" else "",
            "source_detail": (lb.get("source_detail") or "").strip() if source != "human" else "",
        })

    cleaned.sort(key=lambda x: (x["bar_index"], x["structure_type"]))
    return cleaned, warnings


def update_label_set(
    *,
    label_set_id: str,
    annotator: str,
    version: str,
    rubric_vi: str,
    labels: list[dict[str, Any]],
    confirm_overwrite: bool = False,
) -> dict[str, Any]:
    """Ghi đè nội dung một bộ nhãn đã lưu (tăng ``revision``).

    Nếu bộ nhãn đã được dùng trong đánh giá đã lưu, phải có
    ``confirm_overwrite=True``: các kết quả cũ gắn với bản nhãn TRƯỚC đó và
    không tự tính lại.
    """
    ls = db.get_label_set(label_set_id)
    if not ls:
        raise ServiceError("Không tìm thấy bộ nhãn %r." % label_set_id)
    if not (annotator or "").strip():
        raise ServiceError("Phải ghi tên người gán nhãn.")

    used_by = db.evaluations_using_label_set(label_set_id)
    if used_by and not confirm_overwrite:
        raise ServiceError(
            "Bộ nhãn %s đã được dùng trong %d đánh giá đã lưu (%s). Ghi đè sẽ "
            "làm các kết quả đó gắn với bản nhãn cũ. Xác nhận ghi đè, hoặc bấm "
            "\"Lưu bộ nhãn\" để tạo bộ mới."
            % (label_set_id, len(used_by), ", ".join(e["id"] for e in used_by[:5]))
        )

    cleaned, warnings = _clean_labels(labels, ls["dataset_id"])
    new_rev = db.update_label_set(
        {
            "id": label_set_id,
            "version": (version or "1").strip(),
            "annotator": annotator.strip(),
            "rubric_vi": rubric_vi or "",
            "updated_at": utcnow_iso(),
        },
        cleaned,
    )
    out = db.get_label_set(label_set_id)
    assert out is not None
    out["warnings"] = warnings
    out["revision"] = new_rev
    out["ghi_chu_vi"] = (
        "Đã ghi đè thành bản %d. %d đánh giá đã lưu trước đó vẫn gắn với bản "
        "nhãn cũ và KHÔNG tự tính lại." % (new_rev, len(used_by))
    )
    return out


#: Cột CSV khi xuất/nhập nhãn tham chiếu.
LABEL_CSV_COLUMNS = [
    "structure_type", "bar_index", "price", "notes",
    "source", "source_algorithm", "source_detail",
]


def export_label_set_csv(label_set_id: str) -> tuple[str, str]:
    """Trả về (tên file, nội dung CSV) của một bộ nhãn.

    Các dòng bắt đầu bằng ``#`` là chú thích ghi nguồn gốc bộ nhãn; bộ nạp bỏ
    qua chúng, nên file xuất ra nạp lại được nguyên vẹn.
    """
    ls = db.get_label_set(label_set_id)
    if not ls:
        raise ServiceError("Không tìm thấy bộ nhãn %r." % label_set_id)
    ds = db.get_dataset(ls["dataset_id"])

    buf = io.StringIO()
    buf.write("# Bộ nhãn tham chiếu — Market Structure Lab\n")
    buf.write("# label_set_id=%s revision=%s version=%s\n"
              % (ls["id"], ls.get("revision") or 1, ls["version"]))
    buf.write("# annotator=%s\n" % (ls["annotator"],))
    buf.write("# dataset_id=%s symbol=%s timeframe=%s\n"
              % (ls["dataset_id"], (ds or {}).get("symbol", "?"), (ds or {}).get("timeframe", "?")))
    buf.write("# dataset_checksum=%s\n" % ((ds or {}).get("checksum_sha256", "?"),))
    buf.write("# rubric=%s\n" % ((ls.get("rubric_vi") or "").replace("\n", " ") or "(khong ghi)",))
    buf.write("# bar_index chi co nghia trong dung dataset tren.\n")

    w = csv.writer(buf, lineterminator="\n")
    w.writerow(LABEL_CSV_COLUMNS)
    for lb in ls.get("labels") or []:
        w.writerow([
            lb["structure_type"], lb["bar_index"], lb["price"], lb.get("notes") or "",
            lb.get("source") or "human", lb.get("source_algorithm") or "",
            lb.get("source_detail") or "",
        ])

    filename = "nhan_%s_%s_%s.csv" % (
        (ds or {}).get("symbol", "ds"), (ds or {}).get("timeframe", ""), ls["id"]
    )
    return filename, buf.getvalue()


def parse_label_csv(*, dataset_id: str, csv_text: str) -> dict[str, Any]:
    """Đọc CSV nhãn thành danh sách nháp đã kiểm tra — KHÔNG tự lưu.

    Người dùng vẫn phải bấm Lưu, nên chỉ có một đường ghi vào kho nhãn.
    """
    ds = get_dataset_or_error(dataset_id)
    text = (csv_text or "").lstrip("﻿")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise ServiceError("File không có dòng nhãn nào (ngoài chú thích).")

    warnings: list[str] = []
    header_meta = _label_csv_meta(text)
    if header_meta.get("dataset_checksum") and header_meta["dataset_checksum"] != ds["checksum_sha256"]:
        warnings.append(
            "File ghi dataset_checksum=%s nhưng dataset đang chọn có checksum %s. "
            "bar_index có thể trỏ sai nến."
            % (header_meta["dataset_checksum"][:12] + "…", ds["checksum_sha256"][:12] + "…")
        )

    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    if not reader.fieldnames:
        raise ServiceError("Không đọc được dòng tiêu đề của file CSV.")
    have = {(h or "").strip().lower() for h in reader.fieldnames}
    missing = [c for c in ("structure_type", "bar_index", "price") if c not in have]
    if missing:
        raise ServiceError(
            "CSV thiếu cột bắt buộc: %s. Cột bắt buộc: structure_type, bar_index, "
            "price (tuỳ chọn: %s)"
            % (", ".join(missing), ", ".join(LABEL_CSV_COLUMNS[3:]))
        )

    raw: list[dict[str, Any]] = []
    for row in reader:
        norm = {(k or "").strip().lower(): (v or "") for k, v in row.items()}
        raw.append({
            "structure_type": norm.get("structure_type", ""),
            "bar_index": norm.get("bar_index", ""),
            "price": norm.get("price", ""),
            "notes": norm.get("notes", ""),
            # File cũ không có cột nguồn -> coi là người gán.
            "source": norm.get("source", "") or "human",
            "source_algorithm": norm.get("source_algorithm", ""),
            "source_detail": norm.get("source_detail", ""),
        })

    cleaned, dup_warnings = _clean_labels(raw, dataset_id)
    warnings.extend(dup_warnings)
    return {
        "labels": cleaned,
        "warnings": warnings,
        "meta_trong_file": header_meta,
        "dataset": {"id": ds["id"], "symbol": ds["symbol"], "timeframe": ds["timeframe"]},
        "ghi_chu_vi": (
            "Đã đọc %d nhãn vào bộ nháp. Kiểm tra rồi bấm Lưu — công cụ không "
            "tự ghi vào kho nhãn." % len(cleaned)
        ),
    }


# ---------------------------------------------------------------------------
# Auto label (đề xuất) + người duyệt
# ---------------------------------------------------------------------------


def auto_label_algorithms() -> list[dict[str, Any]]:
    """Các thuật toán đề xuất được nhãn cấu trúc, kèm loại nhãn mỗi cái sinh ra."""
    from core.labels import LABEL_TYPES

    out = []
    for a in list_algorithms():
        types = [t for t in a.get("emits_types") or [] if t in LABEL_TYPES]
        if types:
            out.append({**a, "label_types": types})
    return out


def suggest_auto_labels(
    *,
    dataset_id: str,
    algorithm: str,
    params: dict[str, Any] | None,
    start_index: Optional[int] = None,
    end_index: Optional[int] = None,
    types: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Chạy một thuật toán có sẵn và trả về ĐỀ XUẤT nhãn trong khoảng nến.

    Không ghi gì vào kho nhãn. Người dùng phải chấp nhận từng đề xuất (hoặc
    chấp nhận hàng loạt có chủ đích) rồi bấm Lưu.

    Thuật toán chạy trên TOÀN BỘ dataset rồi mới lọc theo khoảng: nhãn là
    đánh giá hồi cứu nên được phép nhìn các nến sau, và nhờ vậy pivot ở sát
    mép phải của khoảng vẫn có đủ nến bên phải để xác nhận.
    """
    from core.labels import LABEL_TYPES

    ds = get_dataset_or_error(dataset_id)
    n_bars = int(ds["row_count"])
    try:
        cls = get_algorithm_class(algorithm)
    except KeyError as exc:
        raise ServiceError(str(exc)) from exc

    label_types = [t for t in cls.emits_types if t in LABEL_TYPES]
    if not label_types:
        usable = ", ".join(a["name"] for a in auto_label_algorithms()) or "(không có)"
        raise ServiceError(
            "Thuật toán %r không sinh loại nhãn cấu trúc nào nên không dùng để "
            "đề xuất nhãn được. Dùng: %s." % (algorithm, usable)
        )

    start = 0 if start_index is None else int(start_index)
    end = n_bars - 1 if end_index is None else int(end_index)
    if start < 0 or end > n_bars - 1 or start > end:
        raise ServiceError(
            "Khoảng nến %d → %d không hợp lệ cho dataset %s %s (0 → %d)."
            % (start, end, ds["symbol"], ds["timeframe"], n_bars - 1)
        )

    warnings: list[str] = []
    wanted = set(label_types)
    if types:
        bad = [t for t in types if t not in LABEL_TYPES]
        if bad:
            raise ServiceError("Loại nhãn không hỗ trợ: %s" % ", ".join(bad))
        not_emitted = [t for t in types if t not in label_types]
        if not_emitted:
            warnings.append(
                "%s không sinh loại %s — không có đề xuất cho các loại này."
                % (cls.name, ", ".join(not_emitted))
            )
        wanted = set(types) & set(label_types)

    try:
        norm = cls.validate_params(params)
        cls.check_dataset(ds["timeframe"], norm)
        algo = cls(**norm)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    _, bars, _ = load_bars(dataset_id)
    try:
        result = run_algorithm(bars, algo)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    detail = "%s v%s %s" % (
        algo.name, algo.version, json.dumps(norm, sort_keys=True, ensure_ascii=False)
    )
    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for e in result.events:
        if e.structure_type not in wanted:
            continue
        if not (start <= e.event_bar_index <= end):
            continue
        key = (e.structure_type, e.event_bar_index)
        if key in seen:
            continue
        seen.add(key)
        d = e.to_dict()
        suggestions.append({
            "structure_type": e.structure_type,
            "bar_index": e.event_bar_index,
            "price": e.price,
            "event_id": e.event_id,
            "confirmed_bar_index": e.confirmed_bar_index,
            "confirmation_lag_bars": e.confirmation_lag_bars,
            "reason_code": e.reason_code,
            "reason_text_vi": d.get("reason_text_vi") or "",
            "structure_text_vi": d.get("structure_text_vi") or "",
            "source": "auto_accepted",
            "source_algorithm": algo.name,
            "source_detail": detail,
        })
    suggestions.sort(key=lambda x: (x["bar_index"], x["structure_type"]))

    # Nến sát cuối dataset có thể chưa đủ nến bên phải để xác nhận — thiếu đề
    # xuất ở đó không có nghĩa là không có cấu trúc.
    tail = algo.warmup_bars()
    if end > n_bars - 1 - tail:
        warnings.append(
            "Khoảng chạm %d nến cuối dataset: thuật toán có thể chưa đủ nến bên "
            "phải để xác nhận cấu trúc ở đó. Hãy tự rà phần này." % tail
        )

    by_type: dict[str, int] = {}
    for sg in suggestions:
        by_type[sg["structure_type"]] = by_type.get(sg["structure_type"], 0) + 1

    return {
        "dataset": {"id": ds["id"], "symbol": ds["symbol"], "timeframe": ds["timeframe"]},
        "algorithm": algo.name,
        "algorithm_version": algo.version,
        "params": norm,
        "source_detail": detail,
        "start_index": start,
        "end_index": end,
        "types": sorted(wanted),
        "suggestions": suggestions,
        "so_de_xuat_theo_loai": by_type,
        "warnings": warnings,
        "ghi_chu_vi": (
            "%d đề xuất từ %s trong nến %d → %d. Đây CHƯA phải nhãn: chỉ đề xuất "
            "được bạn chấp nhận mới vào bộ nháp, và vẫn phải bấm Lưu. Nhãn chấp "
            "nhận từ đề xuất được ghi nguồn gốc để trang Đánh giá cảnh báo khi "
            "chấm chính thuật toán đã đề xuất chúng."
            % (len(suggestions), detail, start, end)
        ),
    }


def label_provenance(labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Đếm nhãn theo nguồn gốc: người gán / auto chấp nhận nguyên / auto người đã sửa."""
    human = 0
    by_algo: dict[str, int] = {}
    edited_by_algo: dict[str, int] = {}
    for lb in labels:
        src = lb.get("source") or "human"
        if src == "human":
            human += 1
            continue
        a = lb.get("source_algorithm") or "?"
        bucket = edited_by_algo if src == "auto_edited" else by_algo
        bucket[a] = bucket.get(a, 0) + 1
    return {
        "tong": len(labels),
        "nguoi_gan": human,
        "auto_da_duyet": sum(by_algo.values()),
        "auto_da_sua": sum(edited_by_algo.values()),
        "auto_theo_thuat_toan": by_algo,
        "auto_sua_theo_thuat_toan": edited_by_algo,
    }


def provenance_warnings(
    labels: list[dict[str, Any]], run_algorithms: list[str]
) -> list[str]:
    """Cảnh báo khi chấm một thuật toán trên nhãn do chính nó đề xuất.

    Nhãn tham chiếu phải độc lập với thuật toán được chấm (tài liệu nhóm, mục
    5.8). Nhãn auto đã duyệt vẫn mang dấu của thuật toán đề xuất: người duyệt
    có xu hướng chấp nhận cái được gợi ý, nên F1 sẽ cao hơn thực tế.
    """
    prov = label_provenance(labels)
    out: list[str] = []
    total = prov["tong"] or 0
    for algo_name in sorted(set(run_algorithms)):
        n = prov["auto_theo_thuat_toan"].get(algo_name, 0)
        e = prov["auto_sua_theo_thuat_toan"].get(algo_name, 0)
        if n:
            out.append(
                "%d/%d nhãn trong bộ này do chính %s đề xuất rồi người duyệt chấp "
                "nhận. Chấm %s trên bộ nhãn này bị thiên lệch (nhãn không độc lập "
                "với thuật toán) — precision/recall/F1 sẽ cao hơn thực tế. Dùng bộ "
                "nhãn người tự gán, hoặc bộ auto từ thuật toán KHÁC, để so sánh "
                "công bằng." % (n, total, algo_name, algo_name)
            )
        if e:
            out.append(
                "%d/%d nhãn xuất phát từ đề xuất của %s rồi được người sửa (dời nến, "
                "đổi loại hoặc giá). Ít phụ thuộc hơn nhãn chấp nhận nguyên nhưng vẫn "
                "neo theo gợi ý của thuật toán — kết quả có thể thiên lệch nhẹ."
                % (e, total, algo_name)
            )
    return out


def _label_csv_meta(text: str) -> dict[str, str]:
    """Đọc các dòng chú thích ``# key=value`` ở đầu file xuất."""
    meta: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("#"):
            if s:
                break
            continue
        for part in s.lstrip("#").strip().split(" "):
            if "=" in part:
                k, v = part.split("=", 1)
                if k and v:
                    meta[k.strip()] = v.strip()
    return meta


def evaluate_run_against_labels(
    run_id: str,
    label_set_id: str,
    time_tolerance_bars: int = 1,
    price_tolerance: float = 0.0,
) -> dict[str, Any]:
    from core.labels import ReferenceLabel, evaluate_detection
    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    ls = db.get_label_set(label_set_id)
    if not ls:
        raise ServiceError("Không tìm thấy bộ nhãn %r." % label_set_id)
    if ls["dataset_id"] != run["dataset_id"]:
        raise ServiceError("Bộ nhãn và lần chạy không cùng dataset.")
    events = db.get_events(run_id)
    labels = [
        ReferenceLabel(
            structure_type=x["structure_type"],
            bar_index=x["bar_index"],
            price=x["price"],
            notes=x.get("notes") or "",
            seq=x["seq"],
        )
        for x in ls["labels"]
    ]
    try:
        ev = evaluate_detection(
            events,
            labels,
            annotator=ls["annotator"],
            label_set_id=ls["id"],
            label_set_version=ls["version"],
            rubric_vi=ls["rubric_vi"],
            time_tolerance_bars=time_tolerance_bars,
            price_tolerance=price_tolerance,
        )
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    out = ev.to_dict()
    out["nguon_nhan"] = label_provenance(ls["labels"])
    out["canh_bao_nguon_nhan"] = provenance_warnings(ls["labels"], [run["algorithm"]])
    if out["canh_bao_nguon_nhan"]:
        out["note_vi"] = ((out.get("note_vi") or "") + " CẢNH BÁO: " +
                          " ".join(out["canh_bao_nguon_nhan"])).strip()
    return out


def compare_run_to_mql5(
    run_id: str,
    csv_text: str,
    csv_checksum_override: Optional[str] = None,
    time_tolerance_bars: int = 0,
    price_tolerance: float = 0.0,
) -> dict[str, Any]:
    from core.mql5_compare import compare_python_mql5
    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    events = db.get_events(run_id)
    try:
        return compare_python_mql5(
            events,
            csv_text,
            python_checksum=run["dataset_checksum"],
            python_version=run["algorithm_version"],
            csv_checksum_override=csv_checksum_override,
            time_tolerance_bars=time_tolerance_bars,
            price_tolerance=price_tolerance,
        )
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc


def eval_meta() -> dict[str, Any]:
    from core.eval.protocol import (
        MATCHER_VERSIONS,
        PROTOCOL_VERSION,
        describe_targets,
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "matcher_versions": list(MATCHER_VERSIONS),
        "targets": describe_targets(),
        "atr_source": "wilder_confirm_bar",
        "note_vi": (
            "Precision/recall/F1 chỉ khi có bộ nhãn do người gán trong khoảng chấm. "
            "Không có đồng hồ chất lượng hay nhãn «thuật toán tốt nhất»."
        ),
    }


def evaluate_algorithm_runs(
    *,
    run_ids: list[str],
    protocol_raw: dict[str, Any] | None,
    label_set_id: Optional[str] = None,
    baseline_run_id: Optional[str] = None,
    save: bool = True,
    note_vi: str = "",
) -> dict[str, Any]:
    from core.eval.evaluate import evaluate_runs
    from core.eval.protocol import EvalProtocol
    from core.labels import ReferenceLabel

    if not run_ids:
        raise ServiceError("Chọn ít nhất một lần chạy để đánh giá.")
    try:
        protocol = EvalProtocol.from_dict(protocol_raw)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    runs: list[dict[str, Any]] = []
    bars_by_run: dict[str, list] = {}
    dataset_meta = None
    for rid in run_ids:
        run = db.get_run(rid)
        if not run:
            raise ServiceError("Không tìm thấy lần chạy %r." % rid)
        run = dict(run)
        run["events"] = db.get_events(rid)
        _, bars, _ = load_bars(run["dataset_id"], run.get("range_start"), run.get("range_end"))
        bars_by_run[rid] = bars
        if dataset_meta is None:
            dataset_meta = get_dataset_or_error(run["dataset_id"])
        runs.append(run)

    labels: list[ReferenceLabel] = []
    label_set_meta = None
    annotator = ""
    extra_note = note_vi.strip()
    if label_set_id:
        ls = db.get_label_set(label_set_id)
        if not ls:
            raise ServiceError("Không tìm thấy bộ nhãn %r." % label_set_id)
        annotator = (ls.get("annotator") or "").strip()
        if not annotator:
            raise ServiceError("Bộ nhãn thiếu tên người gán — không tính precision ẩn danh.")
        label_set_meta = {
            "id": ls["id"],
            "version": ls["version"],
            "annotator": annotator,
            "rubric_vi": ls.get("rubric_vi") or "",
            "dataset_id": ls["dataset_id"],
            "n_labels": len(ls.get("labels") or []),
            # Bộ nhãn có thể bị ghi đè về sau; ghi lại bản đã dùng để kết quả
            # này vẫn giải thích được.
            "revision": ls.get("revision") or 1,
            "nguon_nhan": label_provenance(ls.get("labels") or []),
        }
        kept = []
        skipped = []
        for run in runs:
            if run["dataset_id"] != ls["dataset_id"]:
                skipped.append(run["run_id"])
            else:
                kept.append(run)
        runs = kept
        if skipped:
            extra_note = (
                (extra_note + " " if extra_note else "")
                + "Bỏ run khác dataset với bộ nhãn: %s." % ", ".join(skipped)
            )
        if not runs:
            raise ServiceError("Không còn lần chạy nào cùng dataset với bộ nhãn.")
        labels = [
            ReferenceLabel(
                structure_type=x["structure_type"],
                bar_index=x["bar_index"],
                price=x["price"],
                notes=x.get("notes") or "",
                seq=x["seq"],
            )
            for x in ls["labels"]
        ]
        dataset_meta = get_dataset_or_error(ls["dataset_id"])

    if baseline_run_id and baseline_run_id not in [r["run_id"] for r in runs]:
        baseline_run_id = None

    result = evaluate_runs(
        runs,
        protocol=protocol,
        labels=labels,
        bars_by_run=bars_by_run,
        dataset_meta={
            "id": dataset_meta["id"],
            "name": dataset_meta["name"],
            "symbol": dataset_meta["symbol"],
            "timeframe": dataset_meta["timeframe"],
            "is_synthetic": dataset_meta["is_synthetic"],
            "row_count": dataset_meta["row_count"],
        } if dataset_meta else {},
        label_set_meta=label_set_meta,
        baseline_run_id=baseline_run_id,
        annotator=annotator,
    )
    prov_warn: list[str] = []
    if label_set_id and label_set_meta:
        prov_warn = provenance_warnings(
            db.get_label_set(label_set_id)["labels"],  # type: ignore[index]
            [r["algorithm"] for r in runs],
        )
    result["nguon_nhan"] = (label_set_meta or {}).get("nguon_nhan")
    result["canh_bao_nguon_nhan"] = prov_warn
    if prov_warn:
        extra_note = ((extra_note + " ") if extra_note else "") + "CẢNH BÁO: " + " ".join(prov_warn)
    if extra_note:
        result["note_vi"] = ((result.get("note_vi") or "") + " " + extra_note).strip()

    eval_id = "ev_" + uuid.uuid4().hex[:12]
    result["evaluation_id"] = eval_id
    result["saved"] = bool(save)
    if save:
        created = utcnow_iso()
        db.insert_evaluation(
            {
                "id": eval_id,
                "created_at": created,
                "dataset_id": (dataset_meta or {}).get("id") or runs[0]["dataset_id"],
                "label_set_id": label_set_id,
                "label_set_revision": (label_set_meta or {}).get("revision"),
                "protocol_json": json.dumps(protocol.to_dict(), ensure_ascii=False),
                "protocol_hash": protocol.fingerprint(),
                "baseline_run_id": baseline_run_id,
                "run_ids_json": json.dumps([r["run_id"] for r in runs], ensure_ascii=False),
                "result_json": json.dumps(result, ensure_ascii=False),
                "duration_ms": result["duration_ms"],
                "note_vi": result.get("note_vi") or "",
            }
        )
        result["created_at"] = created
    return result


def get_evaluation_or_error(eval_id: str) -> dict[str, Any]:
    row = db.get_evaluation(eval_id)
    if not row:
        raise ServiceError("Không tìm thấy đánh giá %r." % eval_id)
    return row


def evaluation_report_markdown(eval_id: str) -> tuple[str, str]:
    row = get_evaluation_or_error(eval_id)
    result = row["result"]
    proto = result.get("protocol") or row.get("protocol") or {}
    lines = [
        "# Báo cáo đánh giá thuật toán",
        "",
        "- Mã: `%s`" % row["id"],
        "- Lúc: %s" % row["created_at"],
        "- Protocol: %s · matcher `%s` · hash `%s`"
        % (proto.get("version"), proto.get("matcher_version"), row["protocol_hash"]),
        "- Mục tiêu: %s" % (result.get("target_label_vi") or proto.get("target")),
        "- Dataset: %s" % ((result.get("dataset") or {}).get("name") or row["dataset_id"]),
        "- Bộ nhãn: %s" % (row.get("label_set_id") or "không có"),
        "- Baseline: `%s`" % (row.get("baseline_run_id") or "—"),
        "",
        result.get("note_vi") or "",
        "",
        "## Các lần chạy",
        "",
        "| Run | Thuật toán | F1 | Precision | Recall | Trễ P90 | Median trễ | /100 nến | Nhân quả |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for g in result.get("groups") or []:
        if not g.get("comparable"):
            for ex in g.get("excluded") or []:
                lines.append(
                    "| `%s` | — | — | — | — | — | — | — | %s |"
                    % (ex.get("run_id"), ex.get("reason_vi"))
                )
            continue
        for r in g.get("runs") or []:
            q, lag, den, val = r["quality"], r["lag"], r["density"], r["validity"]

            def fmt(x: Any, d: int = 3) -> str:
                if x is None:
                    return "—"
                if isinstance(x, float):
                    return ("%." + str(d) + "f") % x
                return str(x)

            mark = " baseline" if r.get("is_baseline") else ""
            lines.append(
                "| `%s`%s | %s v%s | %s | %s | %s | %s | %s | %s | %s |"
                % (
                    r["run_id"], mark,
                    r.get("algorithm"), r.get("algorithm_version"),
                    fmt(q.get("f1")), fmt(q.get("precision")), fmt(q.get("recall")),
                    fmt(lag.get("p90"), 1), fmt(lag.get("median"), 1),
                    fmt(den.get("per_100"), 2),
                    val.get("status_label_vi") or val.get("status"),
                )
            )
    lines.extend(["", "Không phải win-rate, P&L hay xếp hạng thuật toán tốt nhất.", ""])
    filename = "evaluation_%s.md" % row["id"]
    return filename, "\n".join(lines)
