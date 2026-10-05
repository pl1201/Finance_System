"""Dùng chung cho mọi service: kết nối DB của ứng dụng, tra dataset, đọc nến."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from backend.app import config
from backend.app.errors import ServiceError
from backend.app.storage import Database
from core.types import build_bars

db = Database(config.DB_PATH)


def get_dataset_or_error(dataset_id: str) -> dict[str, Any]:
    ds = db.get_dataset(dataset_id)
    if not ds:
        raise ServiceError("Không tìm thấy dataset %r." % dataset_id)
    return ds


def resolve_dataset_params(cls: Any, params: Optional[dict[str, Any]], ds: dict[str, Any]) -> dict[str, Any]:
    """Tham số phụ thuộc dataset, đổi TRƯỚC khi validate: ``session_calendar='auto'`` → lịch khai báo
    theo mã của dataset. Run lưu tên lịch cụ thể nên tái lập được."""
    from core.data.session_calendar import resolve_calendar_name

    p = dict(params or {})
    if any(spec.name == "session_calendar" for spec in cls.param_specs()):
        p["session_calendar"] = resolve_calendar_name(p.get("session_calendar"), ds.get("symbol") or "")
    return p


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
