"""Dataset: xem trước / nhập CSV, tổng hợp nến, nhập MT5, dữ liệu mẫu, đọc nến."""
from __future__ import annotations

import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app import config
from backend.app.errors import NotFoundError, ServiceError
from backend.app.services.common import bar_payload, db, get_dataset_or_error, load_bars
from backend.app.storage import utcnow_iso
from core.data import synthetic
from core.data.loader import (
    CsvImportError,
    load_csv,
    normalize_timezone_label,
    preview_csv,
    rows_checksum,
)
from core.data.mt5_source import Mt5SourceError, fetch_closed_rates, mt5_available
from core.data.resample import ResampleError, resample_ohlc
from core.data.validate import infer_timeframe, validate_and_clean
from core.types import TIMESTAMP_CONVENTIONS


def list_datasets() -> list[dict[str, Any]]:
    return db.list_datasets()


def get_dataset(dataset_id: str) -> dict[str, Any]:
    ds = db.get_dataset(dataset_id)
    if not ds:
        raise NotFoundError("Không tìm thấy dataset %s" % dataset_id)
    return ds


def delete_dataset(dataset_id: str) -> dict[str, Any]:
    get_dataset(dataset_id)
    db.delete_dataset(dataset_id)
    return {"deleted": dataset_id}


def mt5_status() -> dict[str, Any]:
    return {
        "available": mt5_available(),
        "note_vi": (
            "Gói MetaTrader5 là tuỳ chọn. Chưa cài thì lõi lab vẫn chạy. "
            "copy_rates_from_pos index 0 là nến đang hình thành — lab loại nến đó. "
            "Người dùng vẫn phải khai báo múi giờ nguồn và quy ước timestamp "
            "(MT5 thường là mốc MỞ, UTC)."
        ),
    }


def _display_path(path: str) -> str:
    """Đường dẫn tương đối so với gốc dự án, giữ nguyên tuyệt đối nếu khác ổ đĩa."""
    try:
        return os.path.relpath(path, config.PROJECT_ROOT)
    except ValueError:
        # Trên Windows, relpath báo lỗi khi hai đường dẫn nằm trên hai ổ khác nhau
        # (xảy ra khi MSL_DATA_DIR trỏ sang ổ khác, ví dụ thư mục tạm khi chạy test).
        return os.path.abspath(path)


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


def bars_payload(dataset_id: str, range_start: Optional[str], range_end: Optional[str]):
    """``index`` đếm từ nến đầu khoảng (như sự kiện của run chạy khoảng đó); ``dataset_index`` đếm
    từ nến đầu dataset (như nhãn tham chiếu)."""
    ds, bars, src_idx = load_bars(dataset_id, range_start, range_end)
    return {
        "dataset": ds,
        "bars": [dict(bar_payload(b, src_idx[i]), close_ts=int(b.close_time.timestamp())) for i, b in enumerate(bars)],
    }
