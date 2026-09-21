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
        algo = cls(**norm_params)
    except (KeyError, ValueError) as exc:
        raise ServiceError(str(exc)) from exc

    result = run_algorithm(bars, algo)
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

    def _meta(self, sid: str) -> dict[str, Any]:
        e = self._entry(sid)
        snap = e["session"].snapshot()
        snap["session_id"] = sid
        snap["dataset"] = e["dataset"]
        snap["algorithm"] = e["algorithm"]
        snap["algorithm_version"] = e["algorithm_version"]
        snap["params"] = e["params"]
        return snap

    def snapshot(self, sid: str) -> dict[str, Any]:
        return self._meta(sid)

    def step(self, sid: str, n: int = 1) -> dict[str, Any]:
        self._entry(sid)["session"].step_forward(n)
        return self._meta(sid)

    def back(self, sid: str, n: int = 1) -> dict[str, Any]:
        self._entry(sid)["session"].step_back(n)
        return self._meta(sid)

    def seek(self, sid: str, index: int) -> dict[str, Any]:
        self._entry(sid)["session"].seek(index)
        return self._meta(sid)

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


def run_manifest(run_id: str) -> dict[str, Any]:
    """Hồ sơ đầy đủ của một lần chạy, đủ để chạy lại."""
    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    ds = db.get_dataset(run["dataset_id"])
    return {
        "run": run,
        "dataset": ds,
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
    from core.labels import LABEL_TYPES, ReferenceLabel
    cleaned = []
    for i, lb in enumerate(labels):
        st = (lb.get("structure_type") or "").strip()
        if st not in LABEL_TYPES:
            raise ServiceError("Loại nhãn không hỗ trợ: %r" % st)
        cleaned.append({
            "structure_type": st,
            "bar_index": int(lb["bar_index"]),
            "price": float(lb["price"]),
            "notes": lb.get("notes") or "",
        })
        ReferenceLabel(st, int(lb["bar_index"]), float(lb["price"]))
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
    return db.get_label_set(sid)  # type: ignore[return-value]


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
    return ev.to_dict()


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
