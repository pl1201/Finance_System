"""Đối chiếu sự kiện Python với CSV do script MQL5 xuất (cùng checksum dataset)."""
from __future__ import annotations

from typing import Any, Optional

from backend.app.errors import ServiceError
from backend.app.services.common import db


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
